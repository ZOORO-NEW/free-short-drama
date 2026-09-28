# 音频合成 SOP（细节版）

短视频旁白最易"前两个字听不清"。本文记录根因、修法、命令与验收，供 `scripts/build_drama.sh` 之外的手动排障使用。

## 一、根因（已实测确认）

edge-tts 每段开头有：
- `~0.18–0.197s` 死静音（<-90dB）；
- 紧接首词**软起音**：0.1→0.2s 从 `-85dB` 爬到 `-24dB`，前半段压在听阈以下。

成片用 **AAC 编码会进一步压低这种低能量起音**，连续线性播放时播放器把这段开头当静音丢弃；**拖动进度条重定位**时解码器重置，反而把它播出来——现象就是"连起来听丢字、拖回去能听见"。`ffprobe` 查 `start_time=0`，排除全局 priming，锁定为逐段软起音被丢样。

## 二、修法（四步必须全做）

1. **裁前导死静音**：`atrim=start=0.15,asetpts=PTS-STARTPTS`
   仅裁掉真正无声/听不见的预卷，首词可听主体一字不丢。TRIM 固定 `0.15s` 对全段安全（静音终点 0.18–0.197，永不切入可听语音）。
2. **拉平软起音（终局修法）**：`acompressor=threshold=-45dB:ratio=6:attack=1:release=200:makeup=30dB,alimiter=limit=0.99:level=disabled`
   把首词软起音（-30~-40dB，AAC 会丢）抬到 **-14~-18dB**（远超 AAC 丢样阈值），主体峰值 ~-5dB 由 alimiter 兜底防爆音。
   ⚠️ 勿用纯 `volume=10dB`——只提整体不抬软起音，治标不治本。
3. **禁用 WAV 中间格式**：ffmpeg WAV + 音频滤镜会触发 3 倍时长膨胀 bug（192kHz）。所有处理在 concat 内一次完成。
4. **视频迁就音频**：视频按 `(ADUR-TRIM)/VDUR` setpts 拉伸；字幕时间轴按 Σ(ADUR-TRIM) 累加、词偏移扣 TRIM（见 `scripts/gen_subs.py` 的 `--trim` 参数，必须与 build 的 TRIM 一致）。

## 三、编码纪律

- 音频全程只在 concat 后**编码一次 AAC**（多次编码在段头丢 priming 吞字）。
- **filter_complex 必须手写完整**，严禁 shell 变量循环拼接：双引号内真实换行会让滤镜图解析失败、成片静默、退出码仍 0（bash 管道 grep 更会掩盖）。`scripts/build_drama.sh` 已用单行拼接 + 显式输入序号规避此坑；超长命令被沙箱拦截时，改写为 `.sh` 脚本再 `bash` 执行。
- ASS 金色 = `&H00D7FF&`（BGR 序，写 `&HFFD700&` 会变青色）。
- SRT force_style 字号基准 PlayResY=288：16:9 底字幕用 20–24（≈80px/字），≤20 字/行不折行；38 会满屏大字。

## 四、验收（必须解码最终 MP4 实测，非中间文件）

```bash
# 解码最终 MP4 的音频到 PCM
ffmpeg -y -i final/<剧名>.mp4 -vn -acodec pcm_s16le /tmp/final.wav

# 逐段起点后 0.05–0.1s 窗口 RMS（应 ≥ -25dB）
ffmpeg -hide_banner -ss 0.00 -t 0.05 -i /tmp/final.wav -af volumedetect -f null - 2>&1 | grep mean_volume
# 重复测每段起点（如 4.79s / 10.04s ...）

# 整片响度
ffmpeg -hide_banner -i /tmp/final.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

通过标准：
- 各段起点后 0.05–0.1s 窗口 RMS **≥ -25dB**（首词已可听；仍 ≤ -50dB 说明压缩器未生效或被 AAC 丢样）；
- 紧随窗口稳定在 -10~-20dB；
- 整片 mean ≈ -14~-18dB、max ≤ -0.5dB 不破音。
