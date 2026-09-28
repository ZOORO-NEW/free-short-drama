#!/usr/bin/env bash
# free-short-drama 合成脚本（通用版, 16:9 输出）
#
# 用法:
#   bash build_drama.sh <project_dir> <N> [ffmpeg_path]
#   bash build_drama.sh drama-projects/孔子_己所不欲 8
#
# 前置: 已在 <project_dir>/clips/ 放好 seg1..segN.mp4, 在 <project_dir>/clips/audio/ 放好
#       narr_1..narr_N.mp3 + gen_subs.py 产出的 subs.srt / subs_names.srt（复制到 final/）
# 依赖: ffmpeg / ffprobe（Windows 可用 WinGet 的 Gyan.FFmpeg，或填第3参数绝对路径）
#
# 关键纪律（详见 references/audio-sop.md）:
#   - 音频 atrim=start=0.15 裁前导死静音 + acompressor 拉平软起音 + alimiter 防爆音
#   - 视频按 (ADUR-0.15)/VDUR setpts 拉伸, 画面迁就音频
#   - filter_complex 单行拼接, 不循环变量换行（规避静默失败）
#   - 仅最后一次编码 AAC; 禁用 WAV 中间格式

set -e
B="$1"; N="$2"; FFMPEG="${3:-ffmpeg}"
[ -z "$B" ] || [ -z "$N" ] && { echo "用法: bash build_drama.sh <project_dir> <N> [ffmpeg]"; exit 1; }
C="$B/clips"; A="$C/audio"; F="$B/final"
TRIM=0.15
mkdir -p "$F"
cp "$A"/subs.srt "$A"/subs_names.srt "$F" 2>/dev/null || { echo "缺少 subs.srt / subs_names.srt, 请先跑 gen_subs.py"; exit 1; }
cd "$F"

# 1) 视频逐段拉伸到 (narr时长 - trim)
for i in $(seq 1 "$N"); do
  if [ -f "seg${i}_v.mp4" ] && [ "seg${i}_v.mp4" -nt "$C/seg$i.mp4" ]; then
    echo "seg$i: skip (exists)"; continue
  fi
  ADUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$A/narr_$i.mp3")
  VDUR=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$C/seg$i.mp4")
  FAC=$(awk "BEGIN{printf \"%.6f\", ($ADUR-$TRIM)/$VDUR}")
  echo "seg$i: video=$VDUR audio=$(awk "BEGIN{printf \"%.3f\",$ADUR-$TRIM") factor=$FAC"
  "$FFMPEG" -y -loglevel error -i "$C/seg$i.mp4" \
    -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,setpts=PTS*$FAC" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "seg${i}_v.mp4"
done

# 2) 构建 filter_complex（单行, 音频输入序号 = N+i-1）
FILTER=""
for i in $(seq 1 "$N"); do
  ai=$((N + i - 1))
  FILTER="$FILTER[$ai:a]atrim=start=$TRIM,asetpts=PTS-STARTPTS,acompressor=threshold=-45dB:ratio=6:attack=1:release=200:makeup=30dB,alimiter=limit=0.99:level=disabled[a$i];"
done
VIN=""; AIN=""
for i in $(seq 1 "$N"); do VIN="$VIN[$((i-1)):v]"; AIN="$AIN[a$i]"; done
FILTER="${FILTER}${VIN}${AIN}concat=n=$N:v=1:a=1[cv][ca];"
FILTER="${FILTER}[cv]subtitles=subs.srt:force_style='FontName=Microsoft YaHei,FontSize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Bold=1,Alignment=2,MarginV=60'[v1];"
FILTER="${FILTER}[v1]subtitles=subs_names.srt:force_style='FontName=Microsoft YaHei,FontSize=20,PrimaryColour=&H00D7FF&,OutlineColour=&H000000&,Outline=2,Bold=1,Alignment=7,MarginV=50'[out]"

INPUTS=""
for i in $(seq 1 "$N"); do INPUTS="$INPUTS -i seg${i}_v.mp4"; done
for i in $(seq 1 "$N"); do INPUTS="$INPUTS -i $A/narr_$i.mp3"; done

NAME=$(basename "$B")
"$FFMPEG" -y -loglevel error $INPUTS -filter_complex "$FILTER" -map "[out]" -map "[ca]" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k "$F/$NAME.mp4" \
  && echo "FINAL OK: $F/$NAME.mp4"
