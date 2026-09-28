#!/usr/bin/env python3
"""gen_subs.py - 由 edge-tts 逐字时间戳生成词级同步 SRT。

用法:
    python gen_subs.py --transcript transcript.txt --audiodir audio --outdir final --n 8 --trim 0.15
                       [--names "1-2:周公;3-5:孔子"]

产出: final/subs.srt（底部词级台词）+ final/subs_names.srt（顶部金色人名条）。

关键: 字幕由词边界生成, 禁止按"段时长均分行数"猜时间轴; 每行起止 = 行内首词起(-50ms) ~ 末词止(+200ms)。
时间轴按 Σ(ADUR-TRIM) 累加, 词偏移扣 TRIM, 必须与 build_drama.sh 的 TRIM 一致。
"""
import argparse
import json
import os
import re

PUNCT = re.compile(r"[^\w\u4e00-\u9fff]")


def fmt(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def split_text(text):
    parts, buf = [], ""
    for ch in text:
        buf += ch
        if ch in "，。！？；：、,.!?;:" and buf:
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)
    return parts


def load_words(audiodir, i):
    p = os.path.join(audiodir, f"words_{i}.json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--audiodir", default="audio")
    ap.add_argument("--outdir", default="final")
    ap.add_argument("--n", type=int, required=True, help="段数")
    ap.add_argument("--trim", type=float, default=0.15)
    ap.add_argument("--names", default="", help='人名条: "起段-止段:名称;..." 如 "1-2:周公"')
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    with open(args.transcript, encoding="utf-8") as f:
        texts = [l.strip() for l in f if l.strip()]

    segs, starts, acc = {}, {}, 0.0
    for i in range(1, args.n + 1):
        words = load_words(args.audiodir, i)
        segs[i] = words
        starts[i] = acc
        dur = (words[-1]["s"] + words[-1]["d"] - args.trim) if words else 0.0
        acc += max(dur, 0.0)

    out, idx = [], 1
    for i in range(1, args.n + 1):
        words = segs[i]
        base = starts[i]
        if not words or i - 1 >= len(texts):
            continue
        lines = split_text(texts[i - 1])
        wi = 0
        for ln in lines:
            matched, consumed, target = "", [], PUNCT.sub("", ln)
            while wi < len(words) and len(matched) < len(target):
                w = words[wi]
                matched += PUNCT.sub("", w["t"])
                consumed.append(w)
                wi += 1
            if not consumed:
                continue
            s0 = base + consumed[0]["s"] - args.trim - 0.05
            s1 = base + consumed[-1]["s"] + consumed[-1]["d"] - args.trim + 0.20
            out.append(f"{idx}\n{fmt(s0)} --> {fmt(s1)}\n{ln}\n")
            idx += 1
    with open(os.path.join(args.outdir, "subs.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    names_out, k = [], 1
    for spec in [s for s in args.names.split(";") if s.strip()]:
        try:
            rng, nm = spec.split(":")
            a, b = (int(x) for x in rng.split("-"))
            s0 = starts[a] + segs[a][0]["s"] - args.trim if segs[a] else starts[a]
            last = segs[b][-1]
            e1 = starts[b] + last["s"] + last["d"] - args.trim
            names_out.append(f"{k}\n{fmt(s0)} --> {fmt(e1)}\n{nm}\n")
            k += 1
        except Exception:
            continue
    with open(os.path.join(args.outdir, "subs_names.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(names_out))
    print(f"subs.srt ({idx - 1} events), subs_names.srt ({k - 1} events)")


if __name__ == "__main__":
    main()
