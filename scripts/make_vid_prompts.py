#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_vid_prompts.py — 按 storyboard.csv 的画面描述，自动生成图生视频提示词

为什么要自动化：图生视频的提示词必须描述"这个画面里什么东西在动"。
手写 64 段容易漏、也不一致；这里按画面关键词匹配运动模板，
保证「湖面→水波流动」「云雾→轻柔飘移」「枝叶→微风摇曳」等运动语义正确。

用法:
  python make_vid_prompts.py --project <项目目录> [--out vid_prompts.json]
"""
import argparse
import csv
import json
import os
import re

# 画面关键词 → 该画面里"应该动起来"的元素
RULES = [
    (r"湖|水面|池|塘|海|河|溪|泉", "水面泛起细密的波纹并缓缓流动，水面倒影轻轻摇曳"),
    (r"倒影|映", "倒影随水波轻轻晃动"),
    (r"云|雾|霭|烟|霭", "云雾轻柔地飘移扩散，浓淡层次缓缓变化"),
    (r"茶|炊烟|烟", "一缕细烟袅袅升起并渐渐散开"),
    (r"麦|稻|草甸|草坡|草地|草浪|原野|田野", "草浪随风轻轻起伏，一波接一波"),
    (r"树|枝|叶|花|草|藤|苔|松|柳|竹", "枝叶在微风中轻轻摇曳，光影随之流转"),
    (r"雨", "细雨缓缓飘落，空气中水汽氤氲"),
    (r"雪", "雪花缓缓飘落堆积"),
    (r"鸟|飞|雁", "鸟儿轻缓地振翅滑翔"),
    (r"蝶|虫", "轻轻扇动翅膀"),
    (r"光|阳|晖|曙|晨|暮|夕|暖|晨曦", "光线角度缓慢变化，光斑缓缓移动，明暗层次柔和过渡"),
    (r"窗|帘", "窗帘轻轻拂动，窗外光线缓缓变化"),
    (r"星|夜|月", "微光柔和闪烁，夜色缓缓流动"),
    (r"风|吹|拂", "轻风拂过，带起细微的流动"),
    (r"佛|禅|静|禅意", "空气中的微尘缓缓浮动，光线柔和流转"),
]

# 兜底：任何画面都适用的通用运动
GENERIC = "画面中的一切在微风中极缓慢地自然流动，细节柔和地变化"
CAMERA = "镜头极缓慢地向前推进，几乎不可察觉"

NEG = "无字幕，无文字，无水印，无人物脸部特写，真实自然的动态，宁静治愈，风格统一"


def build_motion(desc):
    hits = []
    for pat, motion in RULES:
        if re.search(pat, desc):
            hits.append(motion)
    if not hits:
        hits = [GENERIC]
    # 去重且最多取 3 条，避免提示词过长稀释重点
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return "，".join(out[:3])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default="vid_prompts.json")
    ap.add_argument("--camera", default=CAMERA)
    args = ap.parse_args()

    P = os.path.abspath(args.project)
    sb = os.path.join(P, "storyboard.csv")
    if not os.path.exists(sb):
        sys.exit(f"缺少 storyboard.csv: {sb}")

    with open(sb, encoding="utf-8") as f:
        rows = [r for r in csv.reader(f)
                if r and r[0].strip() and r[0].strip() != "镜头"
                and r[0].strip().isdigit()]
    items = []
    for i, r in enumerate(rows, 1):
        desc = r[2].strip() if len(r) > 2 else ""
        motion = build_motion(desc)
        prompt = f"{desc}。{motion}。{args.camera}。{NEG}"
        items.append({
            "file": f"seg{i}.mp4",
            "image": f"images/img{i}.png",
            "prompt": prompt,
            "scene": desc,
        })
    out = os.path.join(P, args.out)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(items)} items -> {out}")
    for it in items:
        print(f"  {it['file']}: {it['scene'][:28]}  =>  {it['prompt'][:70]}...")


if __name__ == "__main__":
    import sys
    main()
