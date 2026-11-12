#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_all_segments.py — 统一串行生成多集图生视频段（单提交通道，最省免费额度）

为什么合并：Agnes 免费档限速「每分钟放行 1 个请求」且是**共享队列**。
若多集各跑一个生成器，会各自空转重试（实测 64 段任务里 24 次"队列已满"= 24 次
被浪费的提交配额）。**单一串行通道**把提交请求排成一队，空转大幅减少。

断点续跑：已存在的 clips/vid/segN.mp4（>100KB）自动跳过，中断后重跑即可。

用法:
  python gen_all_segments.py --root <drama-projects根> \
      养好情绪 看淡输赢 守住本心 留白 接纳不完美 降低期待 允许一切发生 三餐四季
"""
import argparse
import json
import os
import subprocess
import sys
import time

SK = "C:/Users/ZQJ/.workbuddy/skills/free-short-drama/scripts"
PY = "C:/Users/ZQJ/.workbuddy/binaries/python/versions/3.13.12/python.exe"


def need(proj, name):
    """返回该集待生成的段列表（已存在的跳过）。"""
    items_path = os.path.join(proj, "vid_prompts.json")
    if not os.path.exists(items_path):
        subprocess.run([PY, os.path.join(SK, "make_vid_prompts.py"),
                        "--project", proj], check=False)
    with open(items_path, encoding="utf-8") as f:
        items = json.load(f)
    viddir = os.path.join(proj, "clips", "vid")
    os.makedirs(viddir, exist_ok=True)
    todo = []
    for it in items:
        dest = os.path.join(viddir, it["file"])
        if os.path.exists(dest) and os.path.getsize(dest) > 100000:
            continue
        todo.append(it)
    return todo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--size", default="720P")
    ap.add_argument("--seconds", default="5")
    ap.add_argument("episodes", nargs="+")
    args = ap.parse_args()

    # 1) 汇总所有集待生成的段，写成"单集单段"的临时任务，逐条串行提交
    queue = []
    for name in args.episodes:
        proj = os.path.join(args.root, name)
        if not os.path.isdir(proj):
            print(f"跳过（无目录）: {name}")
            continue
        todo = need(proj, name)
        if not todo:
            print(f"{name}: 8 段已齐")
            continue
        for it in todo:
            queue.append((name, proj, it))
    total = len(queue)
    print(f"=== 待生成 {total} 段（单通道串行）===")

    # 2) 逐段调用生成器（每次只提交一段，失败即退避重试该段）
    done = 0
    for name, proj, it in queue:
        tmp = os.path.join(proj, f".vidseg_{it['file']}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([it], f, ensure_ascii=False)
        for attempt in range(1, 61):
            r = subprocess.run(
                [PY, "-u", os.path.join(SK, "agnes_video_segments.py"),
                 "--project", proj, "--prompts", os.path.basename(tmp),
                 "--aspect", args.aspect, "--size", args.size,
                 "--seconds", args.seconds],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = (r.stdout or "") + (r.stderr or "")
            tail = [l for l in out.splitlines() if l.strip()][-2:]
            for l in tail:
                print(f"  [{name}/{it['file']}] {l.strip()}")
            if os.path.exists(os.path.join(proj, "clips", "vid", it["file"])):
                done += 1
                print(f"=== 进度 {done}/{total}  {name} {it['file']} ===")
                break
            print(f"  [{name}/{it['file']}] 尝试 {attempt} 未成功，等待重试")
            time.sleep(62)
        try:
            os.remove(tmp)
        except OSError:
            pass

    print(f"=== 全部完成：{done}/{total} ===")


if __name__ == "__main__":
    main()
