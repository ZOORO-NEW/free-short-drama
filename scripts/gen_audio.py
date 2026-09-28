#!/usr/bin/env python3
"""gen_audio.py - 用 edge-tts 生成旁白 + 逐字时间戳。

用法:
    pip install edge-tts
    python gen_audio.py --input transcript.txt --voice zh-CN-YunjianNeural --outdir audio --start 1
    python gen_audio.py --input transcript.txt --voice zh-CN-XiaoxiaoNeural --rate "-12%"  # 治愈/舒缓降速

transcript.txt: 每行一段旁白（空行跳过）。
产出: audio/narr_i.mp3 与 audio/words_i.json（逐字时间戳, 单位秒）。

关键: edge-tts 7.2.8 会强制转义文本, 不支持 SSML/phoneme 强制多音字。
      且 Communicate.stream() 只能调用一次 —— 取词边界与保存音频必须用两个独立对象,
      否则报 "stream can only be called once"。
"""
import argparse
import asyncio
import json
import os
import sys

try:
    import edge_tts
except ImportError:
    sys.exit("请先安装 edge-tts: pip install edge-tts")


async def gen_one(text, voice, out_mp3, out_json, rate="+0%", pitch="+0Hz"):
    # boundary="WordBoundary" 才能拿到逐字时间戳（默认 SentenceBoundary 不行）
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch,
                                       boundary="WordBoundary")
    words = []
    async for item in communicate.stream():
        if item.get("type") == "WordBoundary":
            # offset/duration 单位 100ns, 转秒
            words.append({
                "t": item["text"],
                "s": round(item["offset"] / 1e7, 4),
                "d": round(item["duration"] / 1e7, 4),
            })
    if not words:  # 极端情况降级
        words.append({"t": text, "s": 0.0, "d": 0.0})
    # save 会再次调用 stream(), 而 stream 只能调一次, 故用独立对象保存
    communicate_save = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch,
                                            boundary="WordBoundary")
    await communicate_save.save(out_mp3)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="旁白文本, 每行一段")
    ap.add_argument("--voice", default="zh-CN-YunjianNeural")
    ap.add_argument("--rate", default="+0%", help='语速, 如 "-12%%" 降速更舒缓')
    ap.add_argument("--pitch", default="+0Hz", help='音高, 如 "-2Hz"')
    ap.add_argument("--outdir", default="audio")
    ap.add_argument("--start", type=int, default=1)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    with open(args.input, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    for i, line in enumerate(lines, start=args.start):
        mp3 = os.path.join(args.outdir, f"narr_{i}.mp3")
        js = os.path.join(args.outdir, f"words_{i}.json")
        print(f"[{i}] {line[:24]}...")
        asyncio.run(gen_one(line, args.voice, mp3, js, args.rate, args.pitch))
    print(f"done: {len(lines)} segments -> {args.outdir}")


if __name__ == "__main__":
    main()
