---
name: free-short-drama
slug: free-short-drama
displayName: "短视频全自动流水线"
title: "短视频全自动流水线 free-short-drama"
version: 1.1.1
summary: "零外部依赖、可独立安装的 WorkBuddy 技能：输入一句话想法或文案，全自动产出成片+素材包+宣发物料。生图优先用 Agnes 免费档（agnes_generate_image），未配置时退回内置 ImageGen（Hy Image 3.5，按张消耗平台积分约 5-10/张）；图生视频用 Agnes 免费档，配音 edge-tts，合成 ffmpeg，仅生图环节可能消耗积分。"
license: MIT
description: "从一句话想法到成片的全自动短视频流水线，零外部技能依赖、可独立安装。生图优先用 Agnes 免费档（agnes_generate_image，需在连接器信任 agnes-ai MCP 并填免费档密钥），未配置时退回 WorkBuddy 内置 ImageGen（Hy Image 3.5，按张消耗平台积分约 5-10/张）；图生视频用 Agnes 免费档，配音用 edge-tts，合成用本地 ffmpeg。所有写作/分镜/形象/配音方法论已内嵌，无需 qianjin 系列即可完整运行；若 ~/.workbuddy/skills/qianjin-* 存在则自动增强。适用于用户想把文案或题材自动做成短视频、且不希望手动写剧本分镜的场景。"
read_when:
  - 用户说"把想法免费做成短视频""一键出短剧""从文案自动生成视频""零成本做短视频"
  - 用户提供一个题材/钩子/文案，要求系统自动完成写作、分镜、生图、视频且不依赖其他技能
  - 用户希望不手动写剧本/分镜，全流程自动产出且尽量零成本（生图优先 Agnes 免费档）
agent_created: true
---

# 免费短视频全自动流水线 free-short-drama

独立短剧总控。输入可以只是一句话想法 / 题材方向 / 一段文案，负责把它全自动推进到「成片 + 素材包 + 宣发物料」，全程不要求用户手搓剧本或分镜。

本技能是**自包含**的：所有写作、分镜、形象、配音方法论都已内嵌在本文件与 `references/` 中，复制这一个文件夹即可运行，不依赖任何外部技能。若 `~/.workbuddy/skills/qianjin-*` 系列已安装，则自动调用以获得更强效果；不存在时直接按内嵌方法论执行，流程不中断。

## 输入
- 必要：一句话想法 / 题材方向 / 钩子 / 现成文案（如"国学向：己所不欲勿施于人"或一段分镜文案）
- 可选：时长（默认 60s）、画幅（默认 9:16，国风可 16:9）、赛道（泰式神反转 / 国风情绪 / 都市爽文，默认按内容自判）、是否要配音 / BGM、目标平台（决定封面尺寸：抖音 / 视频号 / 小红书 = 竖屏 1080×1920，B站 / YouTube / 公众号 = 横屏 16:9）

## 全局原则
1. **全自动优先**：除明显歧义（如性别 / 年代冲突无法自判）外，不要在每一步停下来问用户。自行决策并推进，每个阶段结束用一句话汇报进度即可。
2. **自包含、零硬依赖**：优先调用已安装的 `qianjin-*` 技能（见「工具与资源」）以获得增强；若未安装，**直接遵循本文件与 `references/` 内嵌方法论**执行，绝不因缺少外部技能而中断。
3. **形象一致性**：所有角色在生图阶段必须锁定「形象锁定卡」（脸型 / 发色 / 服饰 / 配色 / 标志性道具），三视图共用同一视觉描述，确保后续图生视频不漂移。
4. **落盘结构**：所有产物写入 `drama-projects/<剧名>/`：
   - `script.md` 完整内容（梗概 / 三幕 / 逐场台词）
   - `storyboard.csv` 分镜表（镜头号 / 景别 / 画面 / 台词 / 时长 / 运镜 / 音效 / 所需角色）
   - `characters/` 角色设定图与三视图 + `characters/形象锁定卡.md`
   - `clips/` 视频片段
   - `final/` 合成成片
   - `manifest.json` 供 drama-studio 平台导入
   - `promo/` 宣发物料（多平台文案）+ 平台封面图 `promo/cover_vertical.png` / `promo/cover_horizontal.png`（Agnes 免费档生图，未配置时退回 ImageGen 混元消耗积分作备用）

## 工作流程（全自动，严格顺序）

### 阶段1 创意优化 → 故事内核
把想法优化为**故事内核**（人物 / 大纲 / 反转，不到剧本格式）：
- 创作前思考层：定代入锚（具体情绪 + 一个落地细节）、逻辑链（前因→行为→后果自洽）、视角边界（正文禁出现"大纲/伏笔/反转/爽点"等创作词）。
- 一次抛 3-5 个差异化脑洞，每标注【情感核 + 反转点 + 平台适配】。
- 人物以「情绪困境」驱动（最在乎什么 / 最怕什么），反差设计（伟大一面 + 脆弱一面）。
- 按爆款节奏出大纲（每章章首吸引 + 章中递进 + 章末钩子），每章标情绪目标 + 慢镜头位置。
- 反转做 4-6 层，从人物选择长出，不靠设定硬推。
- 过「成稿三审」（文笔 / 逻辑 / 代入感），不过不改完不发。
- 产出 `script.md`（故事内核版：梗概 / 三幕 / 人物情绪困境 / 反转链），提取「角色清单」（姓名 / 身份 / 性格 / 视觉关键词 / 情绪困境）交给阶段2。

### 阶段2 剧本与分镜拆解
把故事内核**翻译**为可拍摄的短剧剧本 + 分镜脚本（视听转化层）：
- 创作前思考层：视觉锚（每场可见画面）/ 听觉锚（对白可念）/ 时长账（总时长切到镜头）。
- 剧本：场景标题（INT./EXT. 地点-时间）+ 动作行（现在时、只写可拍画面、禁心理描写）+ 角色名(情绪) + 对白（口语、声口一致）+ 转场（硬切 CUT TO / SMASH CUT 反转）。
- 分镜：按爆款节奏（单镜 2-5s、每 3-5s 一信息点）输出镜头表，列：镜头号 / 景别 / 画面描述 / 台词 / 时长 / 运镜 / 音效 / 所需角色。
- 节奏：前 3 秒钩子、每 3-5s 一信息点、反转点安排在 15s / 30s / 45s 附近、结尾留空镜或反应特写。
- 过「可拍性三审」（格式合规 / 镜头可执行 / 对白可念），不过不改完不发。
- 产出 `script.md`（补全剧本正文）+ `storyboard.csv`（分镜表）。

### 阶段3 角色形象锁定（含三视图）
遍历角色清单，对每个主角：
- 生图优先级：**优先用 Agnes 免费档 `agnes_generate_image`** 生成「角色设定图」+「正面 / 侧面 / 全身三视图」（需在连接器官方页信任 `agnes-ai` MCP 并填免费档密钥，生图≈0 积分）。**未配置 Agnes 时退回** WorkBuddy 内置 ImageGen（混元 Hy Image 3.5，按张消耗平台积分约 5-10/张）作备用——注意混元生图会消耗积分，不要默认走它。
- 按国风系 8 维（头部比例 3-5 头身写意 / 身体比例微含胸颔首溜肩宽袍大袖 / 五官细长凤眼单眼皮柳叶眉樱桃小口留白 50-60% / 色彩朱砂红藏青黛绿藤黄月白+金≤3% / 轮廓流动飘逸一波三折 / 记忆点朝代纹样+手持器物+发饰 / 情绪含蓄收幅度约为萌系 1/3 / 气质传统元素纯度+线条流动+色彩古韵+内敛）形成「形象锁定卡」文本，存 `characters/形象锁定卡.md`。
- 三视图共用同一视觉描述防漂移。
- Agnes 同时负责图生视频（动图）与静图生图；未配置 Agnes 图生视频时退回 ImageGen 出关键帧 + 说明（视频合成需用户本地 ffmpeg / 剪映，并明确告知）。

### 阶段4 视频制作（图生视频 + 配音合成）
- 图生视频：对每个分镜，以该镜头所需角色的「设定图 / 三视图」为参考，用图生视频能力产出动态片段。
  - 优先 Agnes `agnes_generate_video`（agnes-video-v2.0，异步，需用户在连接器页信任 `agnes-ai` MCP 并填免费档密钥）。
  - 未配置 Agnes 时退回 ImageGen 出关键帧 + 说明（视频合成需用户本地 ffmpeg / 剪映，并明确告知）。
- 配音：按角色分配音色生成 TTS 音频。用 edge-tts 中文自然语音（**默认 YunjianNeural 男声，治愈/情绪流首选**——实测真人感最佳；`XiaoxiaoNeural`/`XiaoyiNeural`/`YunyangNeural` 电子感/合成感偏重，情感片慎用），对齐分镜时间轴。可用本技能 `scripts/gen_audio.py` 生成 `narr_i.mp3` 并输出逐字时间戳 `words_i.json`（必须用 `boundary="WordBoundary"` 拿词级时间戳；edge-tts 7.2.8 会强制转义文本，不支持 SSML/phoneme 强制多音字）。
  - `--rate=-12%` 整体降速、`--pitch=-1Hz` 微降音高，可显著提升治愈/内省质感；**必须用 `--rate=-12%` 等号写法**，否则 `-12%` 会被 argparse 当成选项报错。
  - gen_audio.py 内取词边界与保存音频**必须用两个独立 Communicate 对象**（edge-tts 的 `stream()` 只能调用一次，否则报 "stream can only be called once"）。
- 字幕：用本技能 `scripts/gen_subs.py` 由词边界生成 `subs.srt`（底部词级同步台词）+ `subs_names.srt`（顶部金色人名条）。**禁止按"段时长均分行数"猜时间轴**（语速不均会造成字幕滞后、观众"每句开头几个字听不见"的错觉）；每行起止 = 行内首词起（-50ms 提前出字）~ 末词止（+200ms）。
- 合成（横屏 16:9 剧情片）：有 ffmpeg 时，用本技能 `scripts/build_drama.sh` 把「片段 + 配音 + 字幕」合成为 `final/<剧名>.mp4`；无 ffmpeg 时产出「合成命令脚本 + 素材清单」交付用户本地执行。
- 合成（竖屏 9:16 / 情绪流·图文口播）：用本技能 `scripts/build_vertical.py`。它是 `build_drama.sh` 的竖屏升级版，专治「图片 + 旁白 + 字幕」型短片：图片做 **Ken Burns 运镜**（推拉 + 摇移，免图生视频也有动感）、自动裁掉生图水印条、段间留呼吸停顿、片尾留白，并直接生成词级同步 ASS 字幕（竖屏安全边距）。用法：
  `python scripts/build_vertical.py --project drama-projects/<剧名> --n <段数> [--gap 0.7 --tail 1.6 --w 1080 --h 1920 --motion strong]`
  前置：`images/img1..N.(png|jpg)` + `clips/audio/narr_i.mp3` & `words_i.json` + `transcript.txt`。
  ⚠️ **改运镜参数后必须加 `--force`**（或先删 `clips/seg*.mp4`）：脚本原本「seg 存在就跳过」，会静默复用旧的静帧段。
- 合成（横屏 16:9 / 治愈系·情绪流系列）：用本技能 `scripts/build_healing_16x9.py`。段数自动按 `transcript.txt` 行数适配；**Ken Burns 运镜** + 自动裁生图水印条 + 段间呼吸停顿 + 词级同步底部字幕 + **BGM 铺底混音**（`bgm.wav` 缺失时用 ffmpeg lavfi 现场合成柔和和弦垫音，和弦由 `--bgm-chord` 指定）。用法：
  `python scripts/build_healing_16x9.py --project drama-projects/<剧名> --title <片名> [--wm 0 --bgm-chord Em9 --bgm-vol 2.2 --motion strong]`
  - **`--bgm-chord` 系列化必用**：脚本内置 `CHORDS` 表（C / Fmaj7 / Am9 / Gsus2 / Dmaj7 / Cadd9 / Em9 / Bbmaj7 / F#m7 / Amaj7 / **Ebmaj7 / Cmaj7 / Gmaj7 / Asus2**），每集换一种和弦避免 BGM 雷同；也支持自定义频率串（如 `220,277,330`）。
- **⚠️⚠️ 真动态必须用「图生视频」——Ken Burns 永远不够（2026-10-14 / 10-22 两次用户反馈"图片都是静态的"）**
  **先看这条再决定要不要折腾运镜。** 用户第二次反馈时给出了参照物：另一工作区（`E:/workbuddy/2026-09-27-11-31-34/drama-projects/孙膑_善战者因其势而利导之`）的成片是真动态。查它的 `build-sunbin.sh` 发现**完全没有 zoompan**，每段直接吃一个已存在的 `clips/seg$i.mp4`（3–8MB / 121帧 / 24fps）→ **动态素材本身就是 AI 生成的视频**。
  **本质差异**：Ken Burns = 在静态照片上做 2D 裁切缩放，**画面内容永远不变**（哪怕幅度调到 zmax 1.30、变化量提升 20 倍，肉眼仍是"图片在动"）；图生视频 = 模型**逐帧重绘**（实测水波形态重绘、雾气浓淡重分布、岸线轮廓重绘）→ 这才是真动态。**只要首帧还是静态图，就达不到用户要求。**
  - 完整管线（新增 4 个脚本）：
    1. `make_vid_prompts.py --project <目录>` —— 按 `storyboard.csv` 画面描述**自动匹配运动模板**生成图生视频提示词（湖面→水波流动/云雾→飘移/枝叶→微风摇曳/草浪→起伏/光→角度缓慢变化…），免手写。**坑：storyboard 首行是表头「镜头」，过滤要用 `r[0].isdigit()`，否则多生成 1 段。**
    2. `agnes_video_segments.py --project <目录> --prompts vid_prompts.json --aspect 16:9 --size 720P --seconds 5` —— Agnes 免费档图生视频 → `clips/vid/segN.mp4`（断点续跑）。
    3. `build_from_video.py --project <目录> --title <片名> --bgm-chord <和弦> --bgm-vol <音量> --size 1920x1080` —— 用动态视频段合成（视频段比目标短→末帧 `tpad=clone` 补齐，长→裁掉）。`--size 1080x1920` 出竖版。
    4. 批量：`gen_all_dynamic.sh <集名...>`（只生成视频段）＋ `watch_and_build.sh <集名...>`（监控进度，全部就绪后自动合成横版）。
- **⚠️ Agnes 视频 API 已改版（2026-10-22）**：`agnes-video-v2.0` 下线 → `agnes-video-2.5`（**付费**，余额不足 403 `insufficient_user_quota`）与 **`agnes-video-2.5-flash`（免费档，仅 720P）**。查可用模型：`GET /v1/models`。**2.5 参数体系与 2.0 完全不同（混用即 400）**：
  | 项 | 2.5 正确用法 |
  |---|---|
  | 模式 | `mode`: `text` / **`keyframe`**（图生视频）/ `reference` |
  | 时长 | `seconds`: **字符串** `"4"`–`"12"`，默认 `"5"` |
  | 分辨率 | `size`: `720P`/`1080P`/`1K`/`2K`（Flash 仅 720P） |
  | 画幅 | `aspect_ratio`: `21:9`/`16:9`/`4:3`/`1:1`/`3:4`/`9:16` |
  | 首帧 | `first_frame`: 图片 URL **或 Data URI**（实测 Data URI 可用） |
  | 禁用 | `num_frames`/`width`/`height`/`fps`/`negative_prompt` 传了即 400 |
  | 查询 | `GET /v1/agnesapi?video_id=..&model_name=agnes-video-2.5-flash`（**keyframe 必须带 model_name**） |
- **⚠️⚠️ 致命坑：为拿"公网 URL"而重新生图 → 首帧被替换（实测出现正面人脸）**：曾为把本地图变成 URL 而调图像接口传 `"keep the image exactly as is"`，结果**首帧被模型换成它凭空画的内容**——把"无人晨雾湖面"变成**带正面人脸的女性人像**，严重违反"无正面人脸"规格。**正确做法：本地图直接 base64 成 Data URI 传给 `first_frame`，绝不重新生图。**
- **Agnes 免费档视频限速**：**每分钟放行 1 个请求** + **共享队列**（他人也在排）→ 常返回 `503 video_queue_full`，需 **62s 退避重试**（脚本内置 40 次）。轮询间隔 **≥10s**（3s 会吃 `429 查询过于频繁`）。单段端到端 3~10 分钟 → 8 集 64 段需数小时，**必须后台长跑 + 日志落盘**（`-u` 且 `> log 2>&1`，否则管道缓冲看不到进度）。
- **图生视频输出尺寸不认 `aspect_ratio`**：传 `16:9` 实测返回 **1080×720**（早期一次 720×720）→ 合成时必须自行 `scale+crop` 兜底。
- **运镜幅度：别把图片做成静帧（2026-10-14 首次反馈时的中间解法）**
  旧版运镜只有 1.07~1.11 的中心放大、**无平移**，竖版 `zmax` 仅 1.06 → 肉眼几乎看不出在动（实测同段相隔 3 秒两帧 PSNR≈30，变化极微），观感就是一张张静态图在放。现已改为真 Ken Burns：
  - 共用 `build_healing_16x9.py` 里的 `motion_vf(D, zmax, preset, w, h, fps)`，5 种预设循环：`in_c`(中心推近) / `in_r`(右移推进) / `out_c`(中心拉远) / `in_l`(左移推进) / `in_u`(上移推进)；全部约束在画面内不露黑边。
  - 横版 `zmax` 1.22~1.30；**竖版须更温和（×0.92 → 1.12~1.20）**——竖版源图是 3:2 大幅裁切到 9:16，构图余量小，幅度照搬横版会裁掉主体、观感激进。
  - `--motion {off|soft|strong}`（默认 `strong`）：`off`=纯静帧、`soft`=旧版含蓄幅度、`strong`=肉眼可见。改参数后横版需先删 `clips/h16/`，竖版需加 `--force`。
  - **验证方法**：抽同段首尾两帧算 PSNR，`ffmpeg -i a.png -i b.png -lavfi psnr -f null -`。PSNR 越高越静；**低于 ~20 才算有明显运镜**（旧版 29.96 属于"看不出动"，新版 6.44）。
  - 已有成片批量补做运镜：`bash scripts/rebuild_motion.sh [集名 ...]`（不重生成图/旁白/BGM，自动从 `manifest.json` 读和弦与音量；不给集名则全量重跑，单集约 2 分钟）。
  - **BGM 基调（第 10 集起，用户要求）**：**起伏轻微、氛围感强、不沉闷、心情愉悦轻松**。`synth_bgm` 已升级为「明亮·氛围感版」：`lowpass` 850→**4200Hz**（去闷）+ 每音 **±0.3% 失谐**（暖宽、缓慢拍频＝轻微起伏）+ **高八度 shimmer**（氛围感）+ 轻微慢呼吸；和弦优先**明亮大七/挂二**（Ebmaj7 / Cmaj7 / Gmaj7 / Asus2）。⚠️ 该版把主垫 `amix` 改为 `normalize=0` 且用失谐双振荡，源电平会**暴涨约 11dB**，故已加**总线增益 `volume=0.27`** 拉回 −34dB 基准（默认 `--bgm-vol 2.2` 仍可用）；若再调 `synth_bgm` 增益/失谐，**务必先 `synth_bgm(path,30,chord)` 生成测试文件重测源电平**。
  - 生图用 Agnes 免费档（无水印）时加 `--wm 0`，用内置 ImageGen（带水印条）时保持 `--wm 72`。
  - **验收（每集必做；第 09 集定型最稳测床法）**：读 `clips/audio/words_i.json` 末字的 `s+d` 减去 `TRIM=0.15` 得该段**人声真实结束点**，在其后 0.7~1.0s 处取 **0.3s 窗**测 `volumedetect`，读数即 BGM 床（无语音尾巴污染，比"按公式 gap 窗口"或首尾乱扫准；勿用 `silencedetect`——BGM 床高于其常见 −22dB 阈值，测不出）。目标 **−26dB（比人声低 8~9dB）**；床会随和弦源电平漂移 5~6dB，偏响调小 `--bgm-vol`（第 06 集 1.4、第 09 集 Bbmaj7 源 −34.3dB 仍需 1.6）、偏轻调大（第 05 集 2.6）。整体 mean 目标 −18.5 ~ −19.5dB，max 不超 −3dB。第 10 集起明亮版因失谐拍频（约 1~2.8Hz）床位会自然浮动 **±2dB**，均 ≈ −25dB 即可，不必强求贴 −26（本集用 `--bgm-vol 1.8`）。
  前置：`transcript.txt`（每行一段）+ `images/img1..N.png` + `clips/audio/narr_i.mp3` & `words_i.json`；可选预置 `bgm.wav`。系列化追加新集见 `drama-projects/治愈系系列/index.md`。
- **生图避坑（务必遵守）**：内置 ImageGen **同一条消息并行多张会因文件名精确到秒而互相覆盖且静默无报错** → 必须**串行**：一次只发一张，拿到 `localPath` 立刻改名归位（如 `mv .../g1/*.png images/img1.png`），再发下一张。`output_dir` 并发生成时会归一到同一目录，不可依赖。

### 阶段5 封面生成 + 打包宣发复用
- **封面图（Agnes 免费档优先）**：成片定稿后，优先用 Agnes 免费档 `agnes_generate_image` 生成平台封面图，按目标平台出尺寸：
  - 竖屏 1080×1920（抖音 / 视频号 / 小红书）→ `promo/cover_vertical.png`
  - 横屏 16:9（B站 / YouTube / 公众号）→ `promo/cover_horizontal.png`
  - 构图：剧名主标题（大字、国风描边 / 烫金）+ 1 句钩子副标题 + 主角立绘或高光场景，配色与「形象锁定卡」一致；若未配置 Agnes，退回 ImageGen（混元，汉字更准但仍按张消耗积分约 5-10/张）作备用。
  - 可选【片头封面帧】：用 ffmpeg 在成片开头拼接 2–3s 标题卡（由封面图 + ASS 标题文字合成）；不想烧进视频则仅交付封面图。给出合成命令 / 脚本，不臆造未实现参数。
- 生成 `manifest.json`（剧名 / 时长 / 分镜数 / 角色数 / 素材路径 / 封面路径）。
- 宣发：按一鱼多吃思路，把同一剧本 / 成片拆成公众号深度文、小红书图文、抖音口播、视频号短版，各平台适配结构与语气，存入 `promo/`。
- 告知用户：可把 `drama-projects/<剧名>/` 作为素材包在 drama-studio 平台「素材库 / 作品库」上传；或把 manifest 直接导入平台。

## 音频合成关键 SOP（必读，细节见 references/audio-sop.md）

短视频旁白最易"前两个字听不清"，根因与修法如下，合成时必须执行：
1. **真根因**：edge-tts 每段开头 ~0.18-0.197s 死静音（<-90dB）+ 紧接首词**软起音**（0.1→0.2s 从 -85dB 爬到 -24dB，前一半远低于听阈）；成片用 AAC 编码会进一步压低这种低能量起音，连续播放时被播放器当静音丢弃，拖动重定位反而播出来。
2. **裁前导死静音**：`atrim=start=0.15,asetpts=PTS-STARTPTS` 仅裁掉真正无声 / 听不见的预卷（首词可听主体一字不丢）。TRIM 固定 0.15s 对全段安全（静音终点 0.18-0.197，永不切入可听语音）。
3. **拉平软起音**：逐段快攻击向下压缩器 `acompressor=threshold=-45dB:ratio=6:attack=1:release=200:makeup=30dB,alimiter=limit=0.99:level=disabled`，把首词软起音（-30~-40dB，AAC 会丢）抬到 **-14~-18dB**（远超 AAC 丢样阈值），主体峰值 ~-5dB 由 alimiter 兜底防爆音。这是「连续播每段前2字没声、拖动能听见」的终局修法；勿用纯 `volume`（只提整体不抬软起音，治标不治本）。
4. **禁用 WAV 中间格式**：ffmpeg WAV + 音频滤镜会触发 3 倍时长膨胀 bug（192kHz）。
5. **视频迁就音频**：视频按 `(ADUR-TRIM)/VDUR` setpts 拉伸（画面跟裁后音频，音画严格同步）；字幕时间轴同样按 Σ(ADUR-TRIM) 累加、词偏移扣 TRIM。
6. **ASS 金色** = `&H00D7FF&`（BGR 序，写 `&HFFD700&` 会变青色）；SRT force_style 字号基准 PlayResY=288，16:9 底字幕用 20-24（≈80px/字），≤20 字/行不折行。
7. **filter_complex 必须手写完整**，严禁 shell 变量循环拼接（双引号内真实换行会致滤镜图解析失败、成片静默、退出码仍 0 的假象）；合成后用 `ffprobe` 实测成片存在且时长正确。
8. **验收（须解码最终 MP4 实测，非中间文件）**：抽各段起点后 0.05-0.1s 窗口测 volumedetect，RMS 应 ≥ -25dB；紧随窗口稳定在 -10~-20dB；整片 mean ≈ -14~-18dB、max ≤ -0.5dB 不破音。

## 工具与资源
- 写作：内嵌方法论（优先调用 `~/.workbuddy/skills/qianjin-novel-writer`（若有）/ `qianjin-writer`（若有），否则用内嵌三审法）
- 形象：内嵌国风系 8 维（优先调用 `qianjin-ip-design`（若有），否则用内嵌 8 维）
- 生图（静图优先级）：① **Agnes 免费档 `agnes_generate_image`（免费，默认）** 用于所有静图（角色设定图 / 三视图 / 场景图 / 带字画面 / 封面图）/ ② **未配置 Agnes 时退回** WorkBuddy 内置 ImageGen（混元 Hy Image 3.5，按张消耗平台积分约 5-10/张）作备用——混元生图会消耗积分，不要默认走它。
- **Agnes MCP 未连接时的直调兜底（免费，推荐）**：`~/.workbuddy/mcp.json` 里已配 `agnes-ai`（endpoint + key）时，即使 MCP 会话没连，也可用本技能 `scripts/agnes_batch_images.py` 直调 OpenAI 兼容接口 `POST /v1/images/generations`（模型 `agnes-image-2.1-flash`）批量串行生图：`python scripts/agnes_batch_images.py --prompts prompts.json --outdir images --size 1536x1024`。内置串行+重试+断点续跑（已存在的 imgN.png 跳过），落位即 `img1..N.png`；Agnes 图**无水印**，合成时传 `--wm 0`。
- **`prompts.json` 格式（必读，踩过坑）**：`agnes_batch_images.py` 遍历的是**顶层结构**。**推荐写成顶层数组** `[{"prompt":"..."},{"prompt":"..."}]`；也兼容 `{"images":[...]}` / `{"prompts":[...]}` 包装对象（脚本会自动解包）。⚠️若写成 `{"images":[...]}` 而脚本是旧版（未解包），会只遍历到键名 `"images"` 这一个元素 → 用字符串 `"images"` 当 prompt 生成 **1 张废图**后打印 `ALL DONE`，**静默漏掉其余全部且不报错**。生图后务必 `ls images/ | wc -l` 核对张数与预期一致。
- **Agnes 服务是「窗口期」而非稳定可用（2026-10-05 实测）**：探活返回 HTTP 200 ≠ 批量稳定。实测隔约 1 小时批量跑 8 帧时全量 HTTP 500（每张重试 30 次全败，9 分钟 0 张）。**推荐工作流（实测有效）**：① 开工探活 → ② 先试跑 2 帧确认稳定 → ③ 再补齐全量。回退内置 ImageGen 串行兜底的判据：任一 img 连续 30 次 500（视为长宕机，立即回退不要死等）。**偶发 HTTP 503 属可恢复抖动**（实测重试即成功），脚本自带重试即可，别误判为长宕机。回退记得切裁水印参数：ImageGen 图带水印 → `--wm 72` / `--watermark-crop 100`；Agnes 图无水印 → `--wm 0` / `--watermark-crop 0`，同一集勿混用。
- **一条 Bash 命令里 python 解释器路径只能出现一次**：`PYTHONPATH=<.../Lib/site-packages> <.../python.exe> <script.py> <args>`。若把解释器路径写两遍，第二个路径会被当成脚本名 → `can't find '__main__' module`。
- **生图并发坑（实测，必读）**：内置 ImageGen 的产出文件名只精确到秒（形如 `Chinese_traditional_ink_wash_g_2026-09-28T13-46-49.png`）。
  **同一条消息里并行发起多张生图，落在同一秒的会互相覆盖**——实测一次并行 6 张，最后只剩 3 张，且**静默无报错**（只有等 `ls` 时才发现）。
  因此：**多张生图必须串行**——一次只发一张，拿到返回的 `localPath` 后立即 `mv` 成 `images/imgN.png`，再发下一张。
  另外 `output_dir` 在串行时会被遵守；并行时可能整体失效、全部落到同一目录。
  若不慎已发生覆盖，可按「调用序号 + 秒级时间戳谁最后写入谁存活」反推幸存图是哪一张，只补生成丢失的那几张，避免重复烧积分。
- 视频：Agnes MCP（`agnes_generate_video`，免费档）/ 本地 ffmpeg 合成（`scripts/build_drama.sh` 管线）
- 配音：edge-tts（免费，`scripts/gen_audio.py` + `scripts/gen_subs.py`）
- 宣发：内嵌一鱼多吃思路（优先调用 `qianjin-content-repurposer`（若有））

## 约束
- 不编造分镜号、不跳过角色一致性校验、不臆造素材路径。
- 用户给的事实 / 价格 / 数据先核实再落稿。
- 全流程不要求用户手搓；只在「无法消歧的关键决策」时一次性询问（默认自判）。
- 若启用 Agnes：单次免费档需串行、段与段间隔 ≥30 秒防 429；开工前一句话告知用户预计算力成本（Agnes 生图 / 视频免费档≈0，仅当退回内置 ImageGen 备用时静图按张消耗约 5-10 积分/张）。
