#!/usr/bin/env bash
# rebuild_dynamic.sh — 把已产出的治愈系集数批量改造成「真动态视频」成片
#
# 背景：静态图 + Ken Burns(zoompan) 只是在照片上做 2D 裁切缩放，画面内容不变，
#       观感仍是"图片是静止的"。真动态必须由图生视频模型逐帧重绘。
#
# 本脚本对每集执行三步：
#   1) make_vid_prompts.py     按 storyboard 画面描述自动生成图生视频提示词
#   2) agnes_video_segments.py 用 Agnes 免费档逐段生成动态视频（自动重试队列满）
#   3) build_from_video.py    把动态视频段 + 旁白 + 字幕 + BGM 合成 16:9 成片
#      再手动混 BGM 出 9:16 竖版
#
# 用法:
#   bash rebuild_dynamic.sh              # 全部集数
#   bash rebuild_dynamic.sh 养好情绪 留白  # 指定集数
#
# 耗时提示：Agnes 免费档限速「每分钟 1 个请求」+ 单段生成 3~10 分钟，
#           8 集 × 8 段约需数小时，请后台运行。

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
    [ -f "$d/transcript.txt" ] && [ -d "$d/images" ] && targets+=("$(basename "$d")")
  done
fi

for name in "${targets[@]}"; do
  P="$ROOT/$name"
  [ -d "$P" ] || { echo "跳过（无目录）: $name"; continue; }
  n=$(grep -c '[^[:space:]]' "$P/transcript.txt" 2>/dev/null || echo 0)
  chord=$(grep -o '"chord_freqs": *"[^"]*"' "$P/manifest.json" 2>/dev/null | sed 's/.*: *"//;s/"//')
  vol=$(grep -o '"bgm_vol": *[0-9.]*' "$P/manifest.json" 2>/dev/null | sed 's/.*: *//')
  [ -z "$chord" ] && chord="Cmaj7"; [ -z "$vol" ] && vol="2.2"
  [ -f "$P/bgm.wav" ] || { echo "跳过（无 bgm.wav）: $name"; continue; }

  echo "############ $name (${n}段) ############"

  # 1) 提示词
  "$PY" "$SK/make_vid_prompts.py" --project "$P" | head -1

  # 2) 图生视频（免费档，可能需要排队重试，耗时最长）
  if ! "$PY" "$SK/agnes_video_segments.py" --project "$P" \
        --prompts vid_prompts.json --aspect 16:9 --size 720P --seconds 5; then
    echo "  [$name] 视频段未全部成功，先跳过合成（可重跑本脚本补齐）"
    continue
  fi

  # 3) 合成横版
  if ! "$PY" "$SK/build_from_video.py" --project "$P" --title "$name" \
        --bgm-chord "$chord" --bgm-vol "$vol" --size 1920x1080; then
    echo "  [$name] 16:9 合成失败"
    continue
  fi

  # 4) 竖版：用 vid_v 作为独立源目录合成，**绝不能替换 clips/vid**
  #    （历史 bug：曾 rm -rf clips/vid 再把竖版段 mv 回去 → 原始横版图生视频段被销毁）
  nvid=$(ls "$P/clips/vid"/seg*.mp4 2>/dev/null | wc -l)
  if [ "$nvid" = "$n" ]; then
    mkdir -p "$P/clips/vid_v"
    for i in $(seq 1 "$n"); do
      ffmpeg -y -loglevel error -i "$P/clips/vid/seg$i.mp4" \
        -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30" \
        -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "$P/clips/vid_v/seg$i.mp4"
    done
    if "$PY" "$SK/build_from_video.py" --project "$P" --title "$name" \
          --bgm-chord "$chord" --bgm-vol "$vol" --size 1080x1920 \
          --viddir clips/vid_v >/dev/null 2>&1; then
      echo "  [$name] 9:16 OK"
    else
      echo "  [$name] 9:16 合成失败"
    fi
  fi
  echo "  [$name] 完成"
done
echo "全部完成。"
