#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agnes_batch_images.py — 用 Agnes 免费档 API 串行生图并直接落位 imgN.png
读取 mcp.json 里的 agnes-ai 配置（endpoint + key），OpenAI 兼容 /v1/images/generations。
串行 + 重试，规避内置 ImageGen 同秒覆盖问题。
用法: python agnes_batch_images.py --prompts prompts.json --outdir images [--size 1536x1024]
"""
import argparse, base64, json, os, sys, time, urllib.request, urllib.error

def load_cfg():
    cfg = os.path.expanduser("~/.workbuddy/mcp.json")
    with open(cfg, encoding="utf-8") as f:
        servers = json.load(f).get("mcpServers", {})
    a = servers.get("agnes-ai")
    if not a:
        sys.exit("agnes-ai not found in mcp.json")
    env = a.get("env", {})
    return env.get("AGNES_ENDPOINT", "https://api.agnes-ai.cn").rstrip("/"), env.get("AGNES_API_KEY")

def gen_one(base, key, prompt, size, timeout=45):
    body = json.dumps({"model": "agnes-image-2.1-flash", "prompt": prompt,
                       "size": size, "n": 1}).encode()
    req = urllib.request.Request(base + "/v1/images/generations", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    item = (data.get("data") or [{}])[0]
    if item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=timeout) as r:
            return r.read()
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    raise RuntimeError("no url/b64 in response: " + json.dumps(data)[:300])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--size", default="1536x1024")
    ap.add_argument("--retries", type=int, default=30)
    args = ap.parse_args()
    base, key = load_cfg()
    os.makedirs(args.outdir, exist_ok=True)
    with open(args.prompts, encoding="utf-8") as f:
        prompts = json.load(f)
    # 兼容两种格式：顶层数组 [{"prompt":...}, ...]（推荐）
    # 或 {"images":[{"prompt":...}, ...]} / {"prompts":[...]} 包装对象。
    # 坑：若直接把 {"images":[...]} 传给 enumerate，会只遍历到键名 "images" 这一个元素，
    # 用字符串 "images" 当 prompt 生成 1 张图后静默结束（漏掉其余全部且不报错）。
    if isinstance(prompts, dict):
        for k in ("images", "prompts"):
            if isinstance(prompts.get(k), list):
                prompts = prompts[k]
                break
        else:
            sys.exit("prompts.json 是对象但找不到 images/prompts 数组；请改成顶层数组格式")
    if not isinstance(prompts, list) or not prompts:
        sys.exit("prompts.json 解析后不是非空数组，请检查格式")
    failed = []
    for i, p in enumerate(prompts, 1):
        if isinstance(p, dict):
            p = p.get("prompt", "")
        out = os.path.join(args.outdir, f"img{i}.png")
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            print(f"img{i}: exists, skip"); continue
        ok = False
        for t in range(1, args.retries + 1):
            try:
                t0 = time.time()
                png = gen_one(base, key, p, args.size)
                with open(out, "wb") as f:
                    f.write(png)
                print(f"img{i}: OK {len(png)//1024}KB in {time.time()-t0:.1f}s")
                ok = True; break
            except Exception as e:
                print(f"img{i}: attempt {t} FAIL: {e}")
                # Agnes 服务端偶发 500 抖动（长宕机+短暂恢复尖峰）：用极短退避密集探测，抓住短暂恢复窗口
                time.sleep(2 + (t % 2))
        if not ok:
            print(f"img{i}: GAVE UP after {args.retries} retries, will skip (re-run to retry)")
            failed.append(i)
        time.sleep(1)
    if failed:
        print(f"PARTIAL: {len(failed)} failed ({failed}); re-run script to fill gaps")
    else:
        print("ALL DONE")

if __name__ == "__main__":
    main()
