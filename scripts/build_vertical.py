#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_vertical.py — 竖屏（9:16 / 3:4）情绪流视频合成管线
适用：治愈风 / 情绪流 / 图文口播等「图片 + 旁白 + 字幕」型短片（非多角色剧情）。

特性：
  - 图片 ken-burns 缓慢推近运镜（替代纯静帧，免图生视频也能有动感）
  - 自动裁掉生图水印条（--watermark-crop，默认 100px）
  - 段间留呼吸停顿 + 片尾留白（治愈节奏关键）
  - 由 edge-tts 词边界生成词级同步 ASS 字幕（白字深描边，竖屏安全边距）
  - 音频链：裁前导死静音 + 软起音压缩 + 限幅（见 references/audio-sop.md）

前置（沿用 free-short-drama 落盘结构）：
  <project>/transcript.txt            每行一段旁白
  <project>/images/img1.png ...      与段数一一对应的图（png/jpg 均可）
  <project>/clips/audio/narr_i.mp3 + words_i.json   （由 scripts/gen_audio.py 生成）

用法：
  python build_vertical.py --project drama-projects/向内自愈 --n 5
  python build_vertical.py --project . --n 5 --w 1080 --h 1920 --gap 0.7 --tail 1.6

可选：
  --fps 30 --trim 0.15 --zmax 1.06 --font-size 56 --margin-v 215
  --images-sub images --audio-sub clips/audio --out-name 成片
"""
import argparse
import json
import os
import re
import subprocess
import sys

PUNCT = re.compile(r"[^\w\u4e00-\u9fff]")
FFMPEG, FFPROBE = "ffmpeg", "ffprobe"


def dur(p):
    return float(subprocess.check_output(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p]).decode().strip())


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("CMD FAIL:", " ".join(cmd)[:400]); print(r.stderr.decode(errors="replace")[-3000:])
        sys.exit(1)


def ass_time(t):
    t = max(0.0, t)
    return f"{int(t//3600):d}:{int((t%3600)//60):02d}:{t%60:05.2f}"


def split_text(t):
    parts, buf = [], ""
    for ch in t:
        buf += ch
        if ch in "，。！？；：、,.!?;:":
            parts.append(buf); buf = ""
    if buf:
        parts.append(buf)
    return parts


def find_img(images_dir, i):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(images_dir, f"img{i}{ext}")
        if os.path.exists(p):
            return p
    sys.exit(f"缺少图片: {images_dir}/img{i}.(png|jpg)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--trim", type=float, default=0.15)
    ap.add_argument("--gap", type=float, default=0.7, help="段间停顿秒")
    ap.add_argument("--tail", type=float, default=1.6, help="片尾留白秒")
    ap.add_argument("--trim-gap", default="", help="自定义逐段停顿, 逗号分隔, 覆盖 --gap")
    ap.add_argument("--zmax", type=float, default=1.06, help="推近终值(1.04~1.10 更含蓄)")
    ap.add_argument("--watermark-crop", type=int, default=100, help="裁掉底部水印像素")
    ap.add_argument("--font-size", type=int, default=56)
    ap.add_argument("--margin-v", type=int, default=215, help="字幕距底像素(竖屏安全区)")
    ap.add_argument("--images-sub", default="images")
    ap.add_argument("--audio-sub", default="clips/audio")
    ap.add_argument("--out-name", default="")
    a = ap.parse_args()

    B = os.path.abspath(a.project)
    IMG = os.path.join(B, a.images_sub)
    AUD = os.path.join(B, a.audio_sub)
    CLIPS = os.path.join(B, "clips")
    FINAL = os.path.join(B, "final")
    TMP = os.path.join(B, "tmp")
    for d in (FINAL, TMP):
        os.makedirs(d, exist_ok=True)
    os.chdir(B)  # ffmpeg 用相对路径, 规避中文绝对路径/冒号在滤镜中的转义问题

    N = a.n
    gaps = [a.gap] * N
    gaps[-1] = a.tail
    if a.trim_gap.strip():
        vals = [float(x) for x in a.trim_gap.split(",")]
        for i, v in enumerate(vals[:N]):
            gaps[i] = v

    with open(os.path.join(B, "transcript.txt"), encoding="utf-8") as f:
        texts = [l.strip() for l in f if l.strip()]
    adurs = [dur(os.path.join(AUD, f"narr_{i+1}.mp3")) for i in range(N)]
    targets = [adurs[i] - a.trim + gaps[i] for i in range(N)]

    # ---- 字幕（词级同步） ----
    acc, base = 0.0, []
    for i in range(N):
        base.append(acc); acc += (adurs[i] - a.trim) + gaps[i]
    events = []
    for i in range(N):
        with open(os.path.join(AUD, f"words_{i+1}.json"), encoding="utf-8") as f:
            words = json.load(f)
        wi = 0
        for ln in split_text(texts[i]):
            matched, consumed, target = "", [], PUNCT.sub("", ln)
            while wi < len(words) and len(matched) < len(target):
                w = words[wi]; matched += PUNCT.sub("", w["t"]); consumed.append(w); wi += 1
            if consumed:
                s0 = base[i] + consumed[0]["s"] - a.trim - 0.05
                s1 = base[i] + consumed[-1]["s"] + consumed[-1]["d"] - a.trim + 0.20
                events.append((s0, s1, ln))
    hdr = ("[Script Info]\nScriptType: v4.00+\n"
           f"PlayResX: {a.w}\nPlayResY: {a.h}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
           "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
           "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
           "MarginV, Encoding\n"
           f"Style: Main,Microsoft YaHei,{a.font_size},&H00FFFFFF,&H00FFFFFF,&H002A2F38,"
           f"&H96000000,-1,0,0,0,100,100,2,0,1,3.6,1.6,2,90,90,{a.margin_v},1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
           "Effect, Text\n")
    with open("final/subs.ass", "w", encoding="utf-8") as f:
        f.write(hdr + "\n".join(
            f"Dialogue: 0,{ass_time(s0)},{ass_time(s1)},Main,,0,0,0,,{ln}" for s0, s1, ln in events) + "\n")
    print(f"subtitles: {len(events)} cues")

    # ---- 逐段 ken-burns 视频 ----
    frames = 0
    for i in range(1, N + 1):
        clean = os.path.join(TMP, f"clean{i}.png")
        run([FFMPEG, "-y", "-loglevel", "error", "-i", find_img(IMG, i), "-vf",
             f"crop=iw:ih-{a.watermark_crop}:0:0,"
             f"scale={int(a.w*4/3)}:{int(a.h*4/3)}:force_original_aspect_ratio=increase,"
             f"crop={int(a.w*4/3)}:{int(a.h*4/3)},setsar=1", "-frames:v", "1", clean])
        D = max(2, round(targets[i-1] * a.fps))
        rate = (a.zmax - 1.0) / D
        vf = (f"zoompan=z='min(zoom+{rate:.6f},{a.zmax:.3f})':d={D}:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={a.w}x{a.h}:fps={a.fps},format=yuv420p")
        seg = os.path.join(CLIPS, f"seg{i}.mp4")
        if not os.path.exists(seg):
            run([FFMPEG, "-y", "-loglevel", "error", "-i", clean, "-vf", vf,
                 "-frames:v", str(D), "-r", str(a.fps), "-c:v", "libx264",
                 "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", seg])
        frames += D
        print(f"seg{i}: {targets[i-1]:.3f}s frames={D}")

    T = frames / a.fps
    comp = ("atrim=start=%.3f,asetpts=PTS-STARTPTS,"
            "acompressor=threshold=-45dB:ratio=6:attack=1:release=200:makeup=30dB,"
            "alimiter=limit=0.99:level=disabled" % a.trim)
    parts = ["[" + "][".join(f"{k}:v" for k in range(N)) + f"]concat=n={N}:v=1:a=0[cv]"]
    for i in range(N):
        parts.append(f"[{N+i}:a]{comp},apad=pad_dur={gaps[i]:.3f}[a{i+1}]")
    parts.append("[" + "][".join(f"a{k+1}" for k in range(N)) + f"]concat=n={N}:v=0:a=1[ca]")
    parts.append(f"[ca]afade=t=in:st=0:d=0.2,afade=t=out:st={T-1.0:.2f}:d=1.0[ca2]")
    parts.append(f"[cv]fade=t=in:st=0:d=0.8,fade=t=out:st={T-0.8:.2f}:d=0.8,ass=final/subs.ass[out]")

    inputs = []
    for i in range(1, N + 1):
        inputs += ["-i", f"clips/seg{i}.mp4"]
    for i in range(1, N + 1):
        inputs += ["-i", f"{a.audio_sub}/narr_{i}.mp3"]
    out = os.path.join(FINAL, (a.out_name or os.path.basename(B)) + ".mp4")
    run([FFMPEG, "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", ";".join(parts), "-map", "[out]", "-map", "[ca2]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    print(f"FINAL OK: {out}  ({T:.2f}s, {a.w}x{a.h})")


if __name__ == "__main__":
    main()
