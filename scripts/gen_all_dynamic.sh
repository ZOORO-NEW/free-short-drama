#!/usr/bin/env bash
# gen_all_dynamic.sh — 为指定集数批量生成图生视频段（只生成，不合成）
# 逐集串行，适配 Agnes 免费档「每分钟 1 个请求 + 共享队列」的限速。
set -u
ROOT="E:/workbuddy/2026-09-28-20-26-24/drama-projects"
PY="C:/Users/ZQJ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
PP="C:/Users/ZQJ/.workbuddy/binaries/python/envs/default/Lib/site-packages"
SK="C:/Users/ZQJ/.workbuddy/skills/free-short-drama/scripts"
export PYTHONPATH="$PP"

for name in "$@"; do
  P="$ROOT/$name"
  [ -d "$P" ] || { echo "跳过: $name"; continue; }
  [ -f "$P/vid_prompts.json" ] || "$PY" "$SK/make_vid_prompts.py" --project "$P" | head -1
  echo "===== $name ====="
  "$PY" -u "$SK/agnes_video_segments.py" --project "$P" \
    --prompts vid_prompts.json --aspect 16:9 --size 720P --seconds 5
  echo "===== $name 完成（$(ls "$P"/clips/vid/*.mp4 2>/dev/null | wc -l)/8 段） ====="
done
echo "全部完成。"
