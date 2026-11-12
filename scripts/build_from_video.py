#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_from_video.py — 用「真动态视频段」合成治愈系成片（替代静态图 + Ken Burns）

为什么需要它：静态图 + zoompan(Ken Burns) 只是在照片上做 2D 裁切缩放，
画面内容不变 → 用户观感"图片是静止的"。真正的动态必须由图生视频模型
逐帧重绘（水波/雾气/光影真在变），本脚本负责把那些视频段拼成成片。

与 build_healing_16x9.py 的差异：
  - 画面源：clips/vid/seg{i}.mp4（动态）而不是 images/img{i}.png
  - 段长：视频段固定 5.04s，超出部分用最后一帧冻结补齐，缩短部分裁掉
  - 音频链、字幕链、BGM 混音逻辑与 16:9 版完全一致

用法:
  python build_from_video.py --project <项目目录> --title <片名> \
      [--wm 0 --bgm-vol 2.2 --bgm-chord "196,246.94,293.66,369.99"] [--viddir clips/vid]
"""
import argparse
import json
import os
import re
import subprocess
import sys

TRIM = 0.15
W, H, FPS = 1920, 1080, 30
PUNCT = re.compile(r"[^\w\u4e00-\u9fff]")
FFMPEG, FFPROBE = "ffmpeg", "ffprobe"


def dur(p):
    return float(subprocess.check_output(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p]).decode().strip())


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
    return f"{int(t//3600):d}:{int((t%3600)//60):d}:{t%60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--wm", type=int, default=0, help="底部水印裁剪像素(0=不裁)")
    ap.add_argument("--bgm-vol", type=float, default=2.2)
    ap.add_argument("--bgm-chord", default="Cmaj7")
    ap.add_argument("--viddir", default="clips/vid")
    ap.add_argument("--size", default="1920x1080")
    args = ap.parse_args()

    BASE = os.path.abspath(args.project)
    os.chdir(BASE)
    AUD = os.path.join(BASE, "clips", "audio")
    VID = os.path.join(BASE, args.viddir)
    FINAL = os.path.join(BASE, "final")
    CLIPS = os.path.join(BASE, "clips", "hv")
    os.makedirs(FINAL, exist_ok=True)
    os.makedirs(CLIPS, exist_ok=True)
    title = args.title or os.path.basename(BASE)
    Wt, Ht = (int(x) for x in args.size.split("x"))

    with open(os.path.join(BASE, "transcript.txt"), encoding="utf-8") as f:
        texts = [l.strip() for l in f if l.strip()]
    N = len(texts)
    GAPS = [0.70] * (N - 1) + [1.60]
    adurs = [dur(os.path.join(AUD, f"narr_{i+1}.mp3")) for i in range(N)]
    targets = [adurs[i] - TRIM + GAPS[i] for i in range(N)]

    # ---- 视频段：裁切/缩放/补时长，输出统一规格 ----
    for i in range(1, N + 1):
        src = os.path.join(VID, f"seg{i}.mp4")
        if not os.path.exists(src):
            sys.exit(f"缺少视频段: {src}")
        D = max(2, round(targets[i - 1] * FPS))
        vd = dur(src)
        # 视频比目标短 → 末帧冻结补齐；长 → 裁掉。tpad 用克隆最后一帧。
        vf = (f"scale={Wt}:{Ht}:force_original_aspect_ratio=increase,"
              f"crop={Wt}:{Ht},setsar=1,fps={FPS},"
              f"tpad=stop_mode=clone:stop_duration=3")
        seg = os.path.join(CLIPS, f"seg{i}.mp4")
        run([FFMPEG, "-y", "-loglevel", "error", "-i", src, "-vf", vf,
             "-frames:v", str(D), "-r", str(FPS), "-c:v", "libx264",
             "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", seg])
        print(f"seg{i}: {targets[i-1]:.3f}s  (源视频 {vd:.2f}s → {D}帧)")

    T = sum(max(2, round(t * FPS)) for t in targets) / FPS

    # ---- 字幕（词级同步，逻辑同 16:9 版） ----
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

    # ---- 拼接 + 音频混音 + BGM ----
    bgm = os.path.join(BASE, "bgm.wav")
    if not os.path.exists(bgm):
        sys.exit(f"缺少 bgm.wav: {bgm}")

    comp = ("atrim=start=0.15,asetpts=PTS-STARTPTS,"
            "acompressor=threshold=-45dB:ratio=6:attack=1:release=200:makeup=30dB,"
            "alimiter=limit=0.99:level=disabled")
    parts = []
    parts.append("".join(f"[{i}:v]" for i in range(N)) + f"concat=n={N}:v=1:a=0[cv]")
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
        inputs += ["-i", f"clips/hv/seg{i}.mp4"]
    for i in range(1, N + 1):
        inputs += ["-i", f"clips/audio/narr_{i}.mp3"]
    inputs += ["-i", bgm]

    tag = "16x9" if Wt >= Ht else "9x16"
    out = os.path.join(FINAL, f"{title}_{tag}.mp4")
    run([FFMPEG, "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", ";".join(parts), "-map", "[out]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    print(f"FINAL OK: {out}  ({T:.2f}s)")


if __name__ == "__main__":
    main()
