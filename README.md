# free-short-drama · 免费短视频全自动流水线

一个 **零外部依赖、可独立安装** 的 WorkBuddy 技能：输入一句话想法或一段文案，全自动产出「成片 + 素材包 + 宣发物料」。

- **生图**：WorkBuddy 内置免费混元 Hy Image 3.5（中文文字准确度高）
- **图生视频**：Agnes 免费档（可选，未配置则退化为关键帧 + 本地合成说明）
- **配音**：edge-tts（免费）
- **合成**：本地 ffmpeg（免费）
- **全流程外部花费 ≈ 0**

> 与作者的 `short-drama-autopilot` 不同，本技能**不依赖任何 qianjin-* 技能**——所有写作 / 分镜 / 形象 / 配音方法论已内嵌。若你的机器上装有 `qianjin-*` 系列，会自动增强；没有也完整可用。

## 安装（两种办法）

### 办法 A：复制文件夹（最简单）
1. 拿到 `free-short-drama/` 这个文件夹（含 `SKILL.md` / `scripts/` / `references/` / `README.md`）。
2. 复制到你的技能目录：
   - Windows：`C:\Users\你的用户名\.workbuddy\skills\free-short-drama\`
   - macOS / Linux：`~/.workbuddy/skills/free-short-drama/`
3. 重启 / 刷新 WorkBuddy，对话里即可用 `/free-short-drama` 触发。

### 办法 B：技能市场安装
在 WorkBuddy 技能市场搜索 `free-short-drama` 一键安装（若作者已上架）。

## 两个可选前提
- **图生视频（动图）**：在连接器官方页信任 `agnes-ai` MCP，填入**你自己的** Agnes 免费档密钥（免费档即够，串行间隔 ≥30s 防 429）。
- **本地合成**：确保机器装了 `ffmpeg` 且可在命令行调用（Windows 可用 `winget install Gyan.FFmpeg`）。未装也能用——技能会产出合成命令脚本交你本地执行。
- 混元生图、edge-tts 配音均为内置 / 免费，无需额外配置。

## 一句话使用
把文案或想法丢给 WorkBuddy，加一句：
> 用 free-short-drama 按这条文案做一条短视频：画面静图用混元 Hy Image 3.5 免费生图，动图走 Agnes 免费档，旁白用 edge-tts。

它会自动推进：故事内核 → 剧本分镜 → 形象锁定（三视图）→ 图生视频 + 配音 → 合成成片 → 宣发物料，产物落在 `drama-projects/<剧名>/`。

## 手动跑脚本（进阶 / 排障）
如需自己控制合成，技能自带脚本：

```bash
pip install edge-tts

# 1) 生成旁白 + 逐字时间戳
python scripts/gen_audio.py --input transcript.txt --voice zh-CN-YunjianNeural --outdir clips/audio --start 1

# 2) 生成词级字幕（--n 为段数, --names 可选顶部人名条）
python scripts/gen_subs.py --transcript transcript.txt --audiodir clips/audio --outdir final --n 8 --names "1-2:周公"

# 3) 合成成片（seg1..segN.mp4 放在 clips/, narr_i.mp3 在 clips/audio/）
bash scripts/build_drama.sh drama-projects/<剧名> 8
```

音频合成的关键纪律（前2字听不清的根因修法）见 `references/audio-sop.md`：裁前导死静音 `atrim=start=0.15` + 压缩器拉平软起音 + 禁 WAV 中间格式 + filter_complex 单行拼接。

## 目录结构
```
free-short-drama/
├── SKILL.md              # 技能主体（自包含方法论）
├── README.md             # 本文件
├── scripts/
│   ├── gen_audio.py      # edge-tts 配音 + 词级时间戳
│   ├── gen_subs.py       # 词级 SRT 生成
│   └── build_drama.sh    # ffmpeg 合成成片
└── references/
    └── audio-sop.md      # 音频合成细节 + 验收命令
```
