#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_cover.py — 治愈系视频封面合成（底图 + 片名 + 副标题 + 系列角标）
用 ffmpeg drawtext 烧字，避免 AI 生图直接写汉字出乱码。
用法:
  python make_cover.py --bg bg.png --out cover.png --w 1920 --h 1080 \
      --title 苦尽甘来 --subtitle "愿正在低谷的你 · 慢慢走出阴霾" --tag "治愈系系列 · 第 03 集"
"""
import argparse, os, subprocess, sys, tempfile

FONT_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_R = "C:/Windows/Fonts/msyh.ttc"

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, required=True)
    ap.add_argument("--h", type=int, required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--title-size", type=int, default=None)
    ap.add_argument("--sub-size", type=int, default=None)
    ap.add_argument("--title-y", type=float, default=None, help="标题 y 位置(0-1 相对高)")
    args = ap.parse_args()

    W, H = args.w, args.h
    tsize = args.title_size or (120 if W > H else 128)
    ssize = args.sub_size or (46 if W > H else 52)
    ty = args.title_y if args.title_y is not None else (0.34 if W > H else 0.30)

    tmp = tempfile.mkdtemp()
    # 规避 Windows 盘符冒号在 filtergraph 内的转义坑：
    # fontfile/textfile 一律放临时目录，用相对路径；subprocess cwd 切到临时目录
    import shutil
    shutil.copy(FONT_B, os.path.join(tmp, "font_bold.ttc"))
    shutil.copy(FONT_R, os.path.join(tmp, "font_regular.ttc"))
    tf = {}
    for k, v in (("t", args.title), ("s", args.subtitle or ""), ("g", args.tag or "")):
        p = os.path.join(tmp, f"{k}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(v)
        tf[k] = p

    def dt(key, size, color, y, box=0.18, border=3.2, bold=True):
        fpath = "font_bold.ttc" if bold else "font_regular.ttc"
        return (f"drawtext=fontfile={fpath}:textfile={key}.txt:"
                f"fontsize={size}:fontcolor={color}:x=(w-text_w)/2:y={y}:"
                f"borderw={border}:bordercolor=black@0.55:shadowx=2:shadowy=2:"
                f"shadowcolor=black@0.4:box=1:boxcolor=black@{box}:boxborderw={int(size*0.45)}")

    vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"]
    if args.tag:
        vf.append(dt("g", int(ssize * 0.78), "0xE8DCC8", "h*0.055", box=0.0, border=2.2, bold=False))
    vf.append(dt("t", tsize, "0xFFFFFF", f"h*{ty:.3f}", box=0.22, border=4))
    if args.subtitle:
        vf.append(dt("s", ssize, "0xF2EAD9", f"h*{ty:.3f}+{tsize}*1.55", box=0.16, border=2.6))

    bg_abs = os.path.abspath(args.bg)
    out_abs = os.path.abspath(args.out)
    # 输出父目录不存在时 ffmpeg 会静默失败 → 自动创建，避免踩坑
    parent = os.path.dirname(out_abs)
    if parent:
        os.makedirs(parent, exist_ok=True)
    cmd = (["ffmpeg", "-y", "-loglevel", "error", "-i", bg_abs,
            "-vf", ",".join(vf), "-frames:v", "1", out_abs])
    r = subprocess.run(cmd, capture_output=True, cwd=tmp)
    if r.returncode != 0:
        print(r.stderr.decode(errors="replace")[-2000:]); sys.exit(1)
    print("COVER OK:", args.out)

if __name__ == "__main__":
    main()
