#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agnes_video_segments.py — Agnes 免费档图生视频：静态关键帧 → 真动态视频段

为什么必须有它：Ken Burns（zoompan）只是在静态图上做 2D 裁切缩放，画面内容不变，
观感仍是"图片在动"。图生视频由模型逐帧重绘（水波/雾气/光影真在变），才是真动态。

Agnes Video 2.5 参数体系（与旧 2.0 完全不同，混用即 400）：
  model       : agnes-video-2.5-flash（免费档，仅 720P）/ agnes-video-2.5（付费）
  mode        : text / keyframe / reference  ← 图生视频 = keyframe
  seconds     : 字符串 "4"–"12"，默认 "5"
  size        : 720P / 1080P / 1K / 2K（Flash 仅 720P）
  aspect_ratio: 21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16
  first_frame : 首帧图片 URL（必须是可公开访问的 URL，不能用 base64）
  查询        : GET /v1/agnesapi?video_id=..&model_name=..  （keyframe 必须带 model_name）
  注意        : 不接受 num_frames / width / height / fps / negative_prompt（传即 400）

免费档队列常满（video_queue_full），本脚本内置退避重试。

用法:
  python agnes_video_segments.py --project <项目目录> --prompts vid_prompts.json
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FLASH = "agnes-video-2.5-flash"
IMG_MODEL = "agnes-image-2.1-flash"
POLL_GAP = 10.0         # 官方建议 1~2s，但免费档有全局限速（每分钟 1 请求），实测 3s 会 429
POLL_TIMEOUT = 1800.0
QUEUE_RETRY = 40        # 队列满时的重试次数（免费档每分钟放行 1 个，需耐心排队）
MIN_SUBMIT_GAP = 62.0  # 提交间隔：免费档限速「每分钟 1 个请求」


def load_cfg():
    cfg = os.path.expanduser("~/.workbuddy/mcp.json")
    with open(cfg, encoding="utf-8") as f:
        servers = json.load(f).get("mcpServers", {})
    a = servers.get("agnes-ai")
    if not a:
        sys.exit("agnes-ai not found in mcp.json")
    env = a.get("env", {})
    return (env.get("AGNES_ENDPOINT", "https://api.agnes-ai.cn").rstrip("/"),
            env.get("AGNES_API_KEY"))


def _req(base, path, key, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path, data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:300]}


def upload_image(base, key, img_path):
    """把本地图片转成 first_frame 可用的值。

    实测：Agnes 视频接口接受 **Data URI**（data:image/png;base64,...），
    官方 ComfyUI 插件也是「本地图片超限时自动压缩再编码为 Data URI 上传」。
    ⚠️ 绝对不要用「调图像接口重新生成一张图」来拿公网 URL ——
    那样首帧会被模型替换成它凭空画的内容（实测出现过无人的治愈空镜
    被换成带正面人脸的人像），是严重错误。
    """
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return "data:image/png;base64," + b64


def submit(base, key, model, prompt, first_frame, seconds, size, aspect):
    body = {"model": model, "prompt": prompt, "mode": "keyframe",
            "seconds": str(seconds), "size": size, "aspect_ratio": aspect,
            "first_frame": first_frame, "n": 1}
    return _req(base, "/v1/videos", key, body, timeout=180)


def poll(base, key, video_id, model):
    t0 = time.time()
    n = 0
    while time.time() - t0 < POLL_TIMEOUT:
        st, d = _req(base, "/v1/agnesapi?video_id=%s&model_name=%s"
                     % (urllib.parse.quote(video_id), model), key, timeout=60)
        if st == 200:
            status = d.get("status")
            n += 1
            url = (d.get("metadata") or {}).get("url") or d.get("url")
            print(f"      poll#{n} status={status} progress={d.get('progress')}"
                  + ("  READY" if url and status in ("completed", "succeeded") else ""))
            if url and status in ("completed", "succeeded", "success"):
                return url
            if status in ("failed", "error", "cancelled"):
                raise RuntimeError(f"task {status}: {json.dumps(d)[:200]}")
        else:
            print(f"      poll#{n} HTTP {st}: {str(d)[:120]}")
        time.sleep(POLL_GAP)
    raise TimeoutError(f"video {video_id} 超时")


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--images-sub", default="images")
    ap.add_argument("--viddir", default="clips/vid")
    ap.add_argument("--model", default=FLASH)
    ap.add_argument("--seconds", default="5")
    ap.add_argument("--size", default="720P")
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    base, key = load_cfg()
    P = os.path.abspath(args.project)
    IMG = os.path.join(P, args.images_sub)
    OUT = os.path.join(P, args.viddir)
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(P, args.prompts), encoding="utf-8") as f:
        items = json.load(f)
    if isinstance(items, dict):
        for k in ("videos", "segments", "prompts"):
            if isinstance(items.get(k), list):
                items = items[k]
                break
        else:
            sys.exit("prompts 文件是对象但找不到 videos/segments/prompts 数组")
    if not isinstance(items, list) or not items:
        sys.exit("prompts 解析后不是非空数组")

    failed = []
    for i, it in enumerate(items, 1):
        it = it if isinstance(it, dict) else {"prompt": str(it)}
        name = it.get("file") or f"seg{i}.mp4"
        dest = os.path.join(OUT, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 100000 and not args.force:
            print(f"{name}: exists, skip")
            continue
        img_rel = it.get("image") or f"images/img{i}.png"
        img = os.path.join(P, img_rel)
        if not os.path.exists(img):
            print(f"{name}: FAIL 缺首帧 {img}")
            failed.append(name)
            continue
        prompt = it.get("prompt", "")
        print(f"{name}: 提交图生视频 (首帧={os.path.basename(img)}) model={args.model}")
        try:
            ff = upload_image(base, key, img)
            vid = None
            for t in range(1, QUEUE_RETRY + 1):
                st, d = submit(base, key, args.model, prompt, ff,
                               args.seconds, args.size, args.aspect)
                if st == 200:
                    vid = d.get("video_id") or d.get("task_id") or d.get("id")
                    print(f"      提交成功 video_id={vid} status={d.get('status')}")
                    break
                code = (d.get("code") or "")
                msg = (d.get("message") or d.get("_raw") or "")[:120]
                if code == "video_queue_full":
                    # 免费档限速：每分钟放行 1 个请求 → 等满 1 分钟再试
                    print(f"      队列已满，{int(MIN_SUBMIT_GAP)}s 后重试 ({t}/{QUEUE_RETRY})")
                    time.sleep(MIN_SUBMIT_GAP)
                    continue
                raise RuntimeError(f"HTTP {st} {code}: {msg}")
            if not vid:
                raise RuntimeError("队列持续繁忙，重试用尽")
            url = poll(base, key, vid, args.model)
            n = download(url, dest)
            print(f"{name}: OK {n//1024}KB")
        except Exception as e:
            print(f"{name}: FAIL {type(e).__name__}: {e}")
            failed.append(name)
        time.sleep(MIN_SUBMIT_GAP)

    if failed:
        print(f"PARTIAL: {len(failed)} 段失败 {failed}；可重跑补齐（已完成的会跳过）")
        sys.exit(1)
    print("ALL DONE")


if __name__ == "__main__":
    main()
