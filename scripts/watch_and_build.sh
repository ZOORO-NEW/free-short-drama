#!/usr/bin/env bash
# watch_and_build.sh — 监控各集视频段生成进度，全部就绪后自动合成横竖成片
set -u
ROOT="E:/workbuddy/2026-09-28-20-26-24/drama-projects"
PY="C:/Users/ZQJ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
PP="C:/Users/ZQJ/.workbuddy/binaries/python/envs/default/Lib/site-packages"
SK="C:/Users/ZQJ/.workbuddy/skills/free-short-drama/scripts"
export PYTHONPATH="$PP"

EPISODES="$*"
DEADLINE=$(( $(date +%s) + 21600 ))   # 最多守候 6 小时

while [ $(date +%s) -lt $DEADLINE ]; do
  alldone=1
  line=""
  for name in $EPISODES; do
    P="$ROOT/$name"
    n=$(grep -c '[^[:space:]]' "$P/transcript.txt" 2>/dev/null || echo 0)
    v=$(ls "$P"/clips/vid/seg*.mp4 2>/dev/null | wc -l)
    line="$line $name:$v/$n"
    [ "$v" -ge "$n" ] || alldone=0
  done
  echo "[$(date +%H:%M:%S)]$line"
  if [ "$alldone" = "1" ]; then
    echo "=== 全部视频段就绪，开始合成 ==="
    for name in $EPISODES; do
      P="$ROOT/$name"
      n=$(grep -c '[^[:space:]]' "$P/transcript.txt")
      chord=$(grep -o '"chord_freqs": *"[^"]*"' "$P/manifest.json" 2>/dev/null | sed 's/.*: *"//;s/"//')
      vol=$(grep -o '"bgm_vol": *[0-9.]*' "$P/manifest.json" 2>/dev/null | sed 's/.*: *//')
      [ -z "$chord" ] && chord="Cmaj7"; [ -z "$vol" ] && vol="2.2"
      echo "--- $name 16:9 ---"
      "$PY" "$SK/build_from_video.py" --project "$P" --title "$name" \
        --bgm-chord "$chord" --bgm-vol "$vol" --size 1920x1080 | tail -2
    done
    echo "=== 合成完成 ==="
    break
  fi
  sleep 120
done
