---
description: 用 free-short-drama 流水线把一句话想法/文案全自动做成短视频（成片+素材包+宣发物料），生图优先 Agnes 免费档
argument-hint: "一句话想法或文案，例如：写一条泰式神反转的亲情短剧"
---

<user_input>
$ARGUMENTS
</user_input>

---

**必须**调用 `free-short-drama` skill，按其七步流程执行：故事内核 → 剧本分镜 → 形象锁定（三视图）→ 图生视频 + 配音 → 合成成片 → 封面图 → 宣发物料。

用户原始需求原样传入（如上 `$ARGUMENTS`）。

生图优先 Agnes 免费档 `agnes_generate_image`（≈0 积分）；未配置 Agnes 时退回 WorkBuddy 内置 ImageGen（混元 Hy Image 3.5，按张消耗平台积分约 5-10/张）作备用。图生视频走 Agnes 免费档，配音用 edge-tts，合成用本地 ffmpeg。
