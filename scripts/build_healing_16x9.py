#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_healing_16x9.py — 16:9 (1920x1080) 治愈系/情绪流视频通用合成管线

用途：把「N 张无人物治愈图 + N 段旁白 + 可选 BGM」合成为 1920x1080 成片。
特点：段数自动从 transcript.txt 推断；缓慢 ken-burns 运镜；段间呼吸停顿；
      词级同步底部字幕；BGM 自动铺底（缺 bgm.wav 时用 ffmpeg lavfi 现场合成）。

用法：
  python build_healing_16x9.py --project <项目目录> [--title 片名] [--wm 72] [--bgm-vol 2.2]

项目目录约定：
  transcript.txt          每行 = 一段旁白（段数 = 非空行数）
  images/img1..N.png      关键帧（无人物，任意比例，自动裁水印条 + 补足 16:9）
  clips/audio/narr_i.mp3 + words_i.json   由 gen_audio.py 生成
  bgm.wav                 可选；缺失则自动合成
输出：final/<片名>_16x9.mp4  +  final/subs16.ass
"""
import argparse, json, os, re, subprocess, sys

TRIM = 0.15
W, H, FPS = 1920, 1080, 30
# 运镜预设：Ken Burns = 缓慢推拉 + 定向摇移。原版只有 1.07~1.11 中心放大、无平移，
# 肉眼几乎看不出"静帧感"（实测同段相隔3秒两帧 PSNR≈30）。现改为可感知的复合运镜。
# motion 强度：soft = 旧版含蓄幅度；strong = 默认，明显可见但不晕。
Z_CYCLES = {
    "soft":  [1.07, 1.10, 1.08, 1.11, 1.09],
    "strong": [1.26, 1.22, 1.30, 1.24, 1.28],
}
MOTION_CYCLE = ["in_c", "in_r", "out_c", "in_l", "in_u"]
PUNCT = re.compile(r"[^\w\u4e00-\u9fff]")
FFMPEG, FFPROBE = "ffmpeg", "ffprobe"


def motion_vf(D, zmax, preset, w=W, h=H, fps=FPS):
    """生成 zoompan 运镜滤镜：推近/拉远 + 定向摇移，全部限制在画面内不露黑边。"""
    zr = f"{zmax:.3f}"
    if preset == "off":
        return f"scale={w}:{h},format=yuv420p"
    if preset == "out_c":
        z = f"({zr}-({zr}-1)*on/{D})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z = f"(1+({zr}-1)*on/{D})"
        cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
        if preset == "in_r":
            x, y = f"(iw-iw/zoom)*on/{D}", cy
        elif preset == "in_l":
            x, y = f"(iw-iw/zoom)*(1-on/{D})", cy
        elif preset == "in_u":
            x, y = cx, f"(ih-ih/zoom)*on/{D}"
        elif preset == "in_d":
            x, y = cx, f"(ih-ih/zoom)*(1-on/{D})"
        else:
            x, y = cx, cy
    return (f"zoompan=z='{z}':x='{x}':y='{y}':d={D}:"
            f"s={w}x{h}:fps={fps},format=yuv420p")


def dur(p):
    o = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
                                 "format=duration", "-of", "csv=p=0", p])
    return float(o.decode().strip())


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("CMD FAIL:", " ".join(cmd)[:400])
        print(r.stderr.decode(errors="replace")[-3000:])
        sys.exit(1)


def split_text(t):
    parts, buf = [], ""
    for ch in t:
        buf += ch
        if ch in "，。！？；：、,.!?;:":
            parts.append(buf); buf = ""
    if buf:
        parts.append(buf)
    return parts


def ass_time(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


# 系列和弦库（每集轮换，避免 BGM 雷同）。
# 前期偏沉/内省的已用于 01-09；以下新增 Ebmaj7/Cmaj7/Gmaj7/Asus2 等明亮愉悦和弦，
# 用于「轻松愉悦、氛围感强、不沉闷」基调的后续集。
CHORDS = {
    "C":     [130.81, 196.00, 261.63, 329.63, 392.00],  # 平静抚慰
    "Fmaj7": [174.61, 220.00, 261.63, 263.20, 329.63],  # 温暖包容
    "Am9":   [110.00, 164.81, 261.63, 329.63, 493.88],  # 忧而不伤、低谷韧性
    "Gsus2": [98.00, 146.83, 196.00, 220.00, 293.66],   # 开阔平和、不争不比
    "Dmaj7": [73.42, 110.00, 146.83, 185.00, 277.18],   # 暖亮温柔、自我肯定
    "Cadd9": [130.81, 196.00, 293.66, 329.63, 392.00],  # 开阔释然、轻装向前
    "Em9":   [82.41, 196.00, 246.94, 293.66, 369.99],   # 沉静内省、安住当下
    "Bbmaj7":[116.54, 174.61, 220.00, 293.66, 349.23],  # 温厚夜色、安稳
    "F#m7":  [92.50, 138.59, 185.00, 220.00, 277.18],   # 微忧转明
    "Amaj7": [110.00, 164.81, 220.00, 277.18, 329.63],  # 明亮释怀
    # —— 以下为「轻松愉悦」基调新增 ——
    "Ebmaj7":[155.56, 233.08, 311.13, 392.00, 466.16],  # 温润明亮、松弛舒展
    "Cmaj7": [130.81, 196.00, 261.63, 329.63, 493.88],  # 清亮满足、坦然安定
    "Gmaj7": [146.83, 196.00, 246.94, 293.66, 392.00],  # 通透开阔、轻快
    "Asus2": [110.00, 164.81, 220.00, 329.63, 440.00],  # 开放自由、无拘
}


# BGM 总线增益：把合成出的源电平拉到历史基准 ≈ −34dB，
# 保证默认 --bgm-vol 2.2 时 BGM 床落在 −26~−27dB（比人声低 8~9dB）。
# 改完合成器后用 30s 样片实测 volumedetect 校准，目标源 mean ≈ −34dB。
BUSGAIN = 0.45


def synth_bgm(path, seconds, chord="Cmaj7"):
    """明亮治愈 BGM（轻柔琶音旋律 + 柔光铺底版）。

    彻底去除旧版「低频根音持续 drone + 失谐双振荡慢拍频」导致的闷/诡异感：
      · 删掉 <150Hz 的低频根音（上移八度），根除“嗡嗡嗡”；
      · 删掉失谐双振荡，不再有缓慢拍频（恐怖感来源）；
      · 主结构改为「轻柔琶音旋律」：和弦音上行/下行、每音独立包络、loop 铺满，
        听感明确是“音乐”而非嗡鸣 drone；
      · 铺底为明亮柔光垫音（lowpass 5.2k、轻微呼吸 tremolo）；
      · 叠一层极轻高音微光 + 高频空气感做氛围。
    用户要求：起伏轻微、氛围感强、不沉闷、轻松愉悦。"""
    if chord in CHORDS:
        freqs = [float(x) for x in CHORDS[chord]]
    else:
        freqs = [float(x) for x in chord.split(",")]
    print(f"synth_bgm: chord={chord} freqs={freqs}")

    def lift(f, lo=150.0):
        while f < lo:
            f *= 2
        return f

    # 铺底：把 <150Hz 的根音上移八度，避免“嗡”低频
    pad_freqs = [lift(f) for f in freqs]
    # 琶音：和弦音升 1~2 八度，进入明亮区(250~1000Hz)
    arp_base = [lift(f * 2, 250.0) for f in freqs]
    seq = [0, 1, 2, 3, 2, 1, 0, 2]
    arp_freqs = [arp_base[i % len(arp_base)] for i in seq]
    arp_freqs[-1] = arp_freqs[-1] * 2          # 收束音抬八度，明亮落点
    PHRASE, STEP, NOTE, SR = 8.0, 1.0, 0.95, 44100

    ins = []
    npad = len(pad_freqs)
    for f in pad_freqs:
        ins += ["-f", "lavfi", "-i", f"sine=frequency={f:.3f}:duration={seconds}"]
    arp_idx = []
    for k, f in enumerate(arp_freqs):
        ins += ["-f", "lavfi", "-i",
                f"sine=frequency={f:.3f}:duration={NOTE:.3f}"]
        arp_idx.append(npad + k)
    sh_freq = lift(freqs[-1] * 4, 600.0)
    ins += ["-f", "lavfi", "-i", f"sine=frequency={sh_freq:.3f}:duration={seconds}"]
    nsh = npad + len(arp_idx)
    ins += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:duration={seconds}:amplitude=0.15"]
    nnoise = nsh + 1

    padmix = "".join(f"[{i}:a]" for i in range(npad)) + \
             f"amix=inputs={npad}:duration=longest:normalize=0[padraw];"
    arp_fades = []
    for k in arp_idx:
        start_ms = int((k - npad) * STEP * 1000)
        arp_fades.append(
            f"[{k}:a]atrim=0:{NOTE:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.06,afade=t=out:st={NOTE-0.5:.3f}:d=0.5,"
            f"adelay=delays={start_ms}[a{k}];"
        )
    arp_mix = "".join(f"[a{k}]" for k in arp_idx) + \
              f"amix=inputs={len(arp_idx)}:duration=longest:normalize=0[araw];"
    loop_count = int(seconds // PHRASE) + 2
    phrase_samples = int(PHRASE * SR)
    arp_loop = (
        f"[araw]apad=whole_dur={PHRASE:.3f},"
        f"aloop=loop={loop_count}:size={phrase_samples},"
        f"atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS[aloop];"
    )
    sec = max(1, seconds - 5)
    fc = (
        padmix +
        "".join(arp_fades) +
        arp_mix +
        arp_loop +
        "[padraw]atrim=0:{0:.2f},asetpts=PTS-STARTPTS,".format(seconds) +
        "lowpass=f=5200,highpass=f=120,"
        "tremolo=f=0.15:d=0.22,"
        "aecho=0.8:0.6:260|700:0.3|0.15,"
        "volume=0.42[pad];"
        "[aloop]atrim=0:{0:.2f},asetpts=PTS-STARTPTS,".format(seconds) +
        "lowpass=f=6000,highpass=f=200,volume=0.30[arp];"
        f"[{nsh}:a]lowpass=f=4000,highpass=f=600,volume=0.04[sh];"
        f"[{nnoise}:a]lowpass=f=1800,highpass=f=300,volume=0.035[n];"
        "[pad][arp]amix=inputs=2:duration=longest:normalize=0[pa];"
        "[pa][sh]amix=inputs=2:duration=longest:normalize=0[pas];"
        "[pas][n]amix=inputs=2:duration=longest:normalize=0[bg];"
        f"[bg]volume={BUSGAIN},afade=t=in:st=0:d=4,afade=t=out:st={sec:.2f}:d=5,"
        "alimiter=limit=0.7[out]"
    )
    run([FFMPEG, "-y", "-loglevel", "error"] + ins + ["-filter_complex", fc,
         "-map", "[out]", "-t", str(seconds), "-ar", "44100", "-ac", "2", path])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--wm", type=int, default=72, help="底部水印裁剪像素")
    ap.add_argument("--bgm-vol", type=float, default=2.2)
    ap.add_argument("--bgm-chord", default="Cmaj7",
                    help="和弦名（见 CHORDS）或直接给逗号分隔的频率，如 220,277,330")
    ap.add_argument("--motion", default="strong", choices=["off", "soft", "strong"],
                    help="运镜强度：strong=推拉+摇移(默认，肉眼可见)/soft=旧版含蓄/off=纯静帧")
    ap.add_argument("--motion-only", action="store_true",
                    help="只重建画面段(保留音频与字幕)，用于快速预览运镜效果")
    args = ap.parse_args()

    BASE = os.path.abspath(args.project)
    os.chdir(BASE)
    IMG = os.path.join(BASE, "images")
    AUD = os.path.join(BASE, "clips", "audio")
    CLIPS = os.path.join(BASE, "clips", "h16")
    FINAL = os.path.join(BASE, "final")
    TMP = os.path.join(BASE, "tmp")
    for d in (CLIPS, FINAL, TMP):
        os.makedirs(d, exist_ok=True)
    title = args.title or os.path.basename(BASE)

    with open(os.path.join(BASE, "transcript.txt"), encoding="utf-8") as f:
        texts = [l.strip() for l in f if l.strip()]
    N = len(texts)
    GAPS = [0.70] * (N - 1) + [1.60]
    adurs = [dur(os.path.join(AUD, f"narr_{i+1}.mp3")) for i in range(N)]
    targets = [adurs[i] - TRIM + GAPS[i] for i in range(N)]
    T = sum(adurs) - N * TRIM + sum(GAPS)

    bgm = os.path.join(BASE, "bgm.wav")
    if not os.path.exists(bgm):
        print("bgm.wav 缺失，现场合成 ...")
        synth_bgm(bgm, int(T) + 15, args.bgm_chord)
    print(f"segments={N}  est_total={T:.2f}s  bgm={os.path.basename(bgm)}")

    # ---- 字幕 ----
    base_t, acc, events = [0.0] * N, 0.0, []
    for i in range(N):
        base_t[i] = acc
        acc += targets[i]
    for i in range(N):
        with open(os.path.join(AUD, f"words_{i+1}.json"), encoding="utf-8") as f:
            words = json.load(f)
        wi = 0
        for ln in split_text(texts[i]):
            matched, consumed, tgt = "", [], PUNCT.sub("", ln)
            while wi < len(words) and len(matched) < len(tgt):
                w = words[wi]
                matched += PUNCT.sub("", w["t"])
                consumed.append(w); wi += 1
            if not consumed:
                continue
            s0 = base_t[i] + consumed[0]["s"] - TRIM - 0.05
            s1 = base_t[i] + consumed[-1]["s"] + consumed[-1]["d"] - TRIM + 0.20
            events.append((s0, s1, ln))
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Main,Microsoft YaHei,46,&H00FFFFFF,&H00FFFFFF,&H002A2F38,"
        "&H96000000,-1,0,0,0,100,100,2,0,1,3.2,1.4,2,120,120,96,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )
    with open(os.path.join(FINAL, "subs16.ass"), "w", encoding="utf-8") as f:
        f.write(header + "\n".join(
            f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Main,,0,0,0,,{tx}"
            for a, b, tx in events) + "\n")
    print(f"subtitles: {len(events)} cues")

    # ---- 逐段：裁水印 + 运镜 ----
    frames = 0
    for i in range(1, N + 1):
        clean = os.path.join(TMP, f"clean_{i}.png")
        run([FFMPEG, "-y", "-loglevel", "error", "-i", os.path.join(IMG, f"img{i}.png"),
             "-vf", f"crop=iw:ih-{args.wm}:0:0,"
                    "scale=2496:1404:force_original_aspect_ratio=increase,"
                    "crop=2496:1404,setsar=1", "-frames:v", "1", clean])
        D = max(2, round(targets[i - 1] * FPS))
        zmax = Z_CYCLES[args.motion][(i - 1) % len(Z_CYCLES[args.motion])]
        preset = "off" if args.motion == "off" else MOTION_CYCLE[(i - 1) % len(MOTION_CYCLE)]
        vf = motion_vf(D, zmax, preset)
        run([FFMPEG, "-y", "-loglevel", "error", "-i", clean, "-vf", vf,
             "-frames:v", str(D), "-r", str(FPS), "-c:v", "libx264",
             "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
             os.path.join(CLIPS, f"seg{i}.mp4")])
        frames += D
        print(f"seg{i}: {targets[i-1]:.3f}s  motion={preset} zmax={zmax:.3f}")
    T = frames / FPS

    # ---- 拼接 + 音频混音 ----
    comp = ("atrim=start=0.15,asetpts=PTS-STARTPTS,"
            "acompressor=threshold=-45dB:ratio=6:attack=1:release=200:makeup=30dB,"
            "alimiter=limit=0.99:level=disabled")
    concat_v = "".join(f"[{i}:v]" for i in range(N)) + f"concat=n={N}:v=1:a=0[cv]"
    parts = [concat_v]
    for i in range(N):
        parts.append(f"[{N+i}:a]{comp},apad=pad_dur={GAPS[i]:.3f}[a{i+1}]")
    parts.append("".join(f"[a{i+1}]" for i in range(N)) + f"concat=n={N}:v=0:a=1[ca]")
    parts.append(f"[ca]afade=t=in:st=0:d=0.2,afade=t=out:st={T-1.0:.2f}:d=1.0[ca2]")
    parts.append(f"[{2*N}:a]volume={args.bgm_vol},atrim=0:{T:.2f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:st=0:d=3,afade=t=out:st={T-3.0:.2f}:d=3[bg]")
    parts.append("[ca2][bg]amix=inputs=2:duration=first:normalize=0[mx]")
    parts.append("[mx]alimiter=limit=0.97[aout]")
    parts.append(f"[cv]fade=t=in:st=0:d=0.8,fade=t=out:st={T-0.8:.2f}:d=0.8,"
                 "ass=final/subs16.ass[out]")

    inputs = []
    for i in range(1, N + 1):
        inputs += ["-i", f"clips/h16/seg{i}.mp4"]
    for i in range(1, N + 1):
        inputs += ["-i", f"clips/audio/narr_{i}.mp3"]
    inputs += ["-i", bgm]

    out = os.path.join(FINAL, f"{title}_16x9.mp4")
    run([FFMPEG, "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", ";".join(parts), "-map", "[out]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    print(f"FINAL OK: {out}  ({T:.2f}s)")


if __name__ == "__main__":
    main()
