#!/usr/bin/env bash
# rebuild_motion.sh — 给已产出的治愈系集数批量重建运镜（不重生成图/旁白/BGM）
#
# 背景：旧版运镜只有 1.07~1.11 中心放大且无平移，肉眼几乎看不出动（"静态"观感）。
# 新版为 Ken Burns（推拉 + 左右/上下摇移），横版 zmax≈1.22~1.30，竖版≈1.12~1.20。
#
# 用法：
#   bash rebuild_motion.sh              # 重建全部集数
#   bash rebuild_motion.sh 养好情绪      # 只重建指定集数
#
# 注意：横版会重建画面段并复用已有 bgm.wav / words_i.json（不重新合成 BGM、不重新配音）。
#      竖版产出无声底片后自动混入同款 bgm.wav。

set -u
ROOT="E:/workbuddy/2026-09-28-20-26-24/drama-projects"
PY="C:/Users/ZQJ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
PP="C:/Users/ZQJ/.workbuddy/binaries/python/envs/default/Lib/site-packages"
SK="C:/Users/ZQJ/.workbuddy/skills/free-short-drama/scripts"
export PYTHONPATH="$PP"

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  targets=()
  for d in "$ROOT"/*/; do
    [ -f "$d/transcript.txt" ] && targets+=("$(basename "$d")")
  done
fi

for name in "${targets[@]}"; do
  P="$ROOT/$name"
  [ -d "$P" ] || { echo "跳过（无目录）: $name"; continue; }
  n=$(grep -c '[^[:space:]]' "$P/transcript.txt" 2>/dev/null || echo 0)
  chord=$(grep -o '"chord_freqs": *"[^"]*"' "$P/manifest.json" 2>/dev/null | sed 's/.*: *"//;s/"//')
  vol=$(grep -o '"bgm_vol": *[0-9.]*' "$P/manifest.json" 2>/dev/null | sed 's/.*: *//')
  wm=$(grep -o '"watermark_crop_16x9": *[0-9]*' "$P/manifest.json" 2>/dev/null | sed 's/.*: *//')
  [ -z "$chord" ] && chord="Cmaj7"; [ -z "$vol" ] && vol="2.2"; [ -z "$wm" ] && wm="0"
  [ -f "$P/bgm.wav" ] || { echo "跳过（无 bgm.wav）: $name"; continue; }

  echo "=== $name (${n}段 chord=$chord vol=$vol wm=$wm) ==="
  # 横版：清掉旧画面段强制重建
  rm -rf "$P/clips/h16"
  if "$PY" "$SK/build_healing_16x9.py" --project "$P" --title "$name" --wm "$wm" \
        --bgm-chord "$chord" --bgm-vol "$vol" --motion strong; then
    echo "  16:9 OK"
  else
    echo "  16:9 FAIL"; continue
  fi

  # 竖版：底片 + 手动混 BGM
  rm -f "$P"/clips/seg*.mp4
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$P/final/${name}_16x9.mp4")
  rm -f "$P/final/${name}.mp4"
  if "$PY" "$SK/build_vertical.py" --project "$P" --n "$n" --gap 0.7 --tail 1.6 \
        --w 1080 --h 1920 --watermark-crop "$wm" --motion strong --force >/dev/null 2>&1; then
    fade=$(python -c "print(max(0,float('$dur')-3.0))")
    ffmpeg -y -loglevel error -i "$P/final/${name}.mp4" -i "$P/bgm.wav" \
      -filter_complex "[1:a]volume=${vol},atrim=0:${dur},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=3,afade=t=out:st=${fade}:d=3[bg];[0:a][bg]amix=inputs=2:duration=first:normalize=0[a];[a]alimiter=limit=0.97[aout]" \
      -map 0:v -map [aout] -c:v copy -c:a aac -b:a 192k -movflags +faststart "$P/final/${name}_bgm.mp4" && \
    python -c "import os; os.replace(r'$P/final/${name}_bgm.mp4', r'$P/final/${name}.mp4')"
    echo "  9:16 OK"
  else
    echo "  9:16 FAIL"
  fi
done
echo "全部完成。"
