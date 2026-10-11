---
name: voice-clone
description: 基于 MiniMax API 克隆用户本人声音、提供试听，并使用克隆音色生成文案配音。支持语速、情绪、停顿、发音及音色调节。用户说“克隆声音”“用我的声音配音”“生成旁白”时使用。
---

# Voice Clone

把本人录音 → 音色试听 → 文案与韵律确认 → 费用确认 → 配音交付组织成可重复使用的工作流。生成的是音频，不负责生成视频或唱歌。

## 环境

Python 3.10+；可选 ffmpeg（预处理、检查时长）。用户自行注册 MiniMax 国内站、完成个人或企业认证，并在运行环境中设置 `MINIMAX_API_KEY`。默认端点 `https://api.minimax.cn`。不要把密钥写入文件或输出到聊天。

必须在支持安装 SKILL.md、执行本地 Python 和联网请求的 AI 助手中使用。各客户端安装方式以其说明为准，不承诺任意平台自动安装。

以下命令从本 Skill 目录执行。

## 1. 接收本人录音

仅克隆用户本人的声音。录音为 mp3/m4a/wav，10 秒至 5 分钟，不超过 20 MB；建议 30–60 秒，单人、清晰、无背景音乐。先检查文件、时长和录音质量。

不要默认预处理。只有用户需要降噪时运行：

```bash
python3 scripts/preprocess_audio.py sample.wav --out output/clean.mp3
```

先交付处理后的试听，满意再克隆。音频会上传到 MiniMax，提前说明。

## 2. 克隆并交付试听

说明试听按字符计费，首次正式使用音色还会产生音色费用，取得用户同意后运行：

```bash
python3 scripts/clone_voice.py sample.wav --name myvoice --no-noise-reduction --no-volume-norm
```

把 output 中的试听交给用户，询问相似度。满意后设置本地默认音色：

```bash
python3 -c "import sys; sys.path.insert(0, 'scripts'); import voices_store; voices_store.set_default('myvoice')"
```

默认音色不表示已支付解锁费。记录在本地 voices.json；不要提交该文件。未正式使用的音色可能七天后被平台删除。

## 3. 韵律与费用确认（必须）

先展示可读的情绪、语速、停顿方案，不直接合成。默认语速 1.0、音色修改 0；按用户需要调整。

停顿使用官方语法，如 `这句结束。<#0.4#>下一句。`。不要使用未经支持的 `<#p:0.4#>` 或 `<#emotion:...#>`。单次请求的情绪通过 --emotion 指定；需要多段不同情绪时分段合成，不宣称文本标签自动切换情绪。

用户确认韵律后，说明此次预估费用，取得明确确认再发起合成。每次重跑也须告知费用。

价格参考（2026-10-11）：音色 9.90 元，首次正式合成使用时收费；speech-2.8-turbo 2.00 元/万计费字符，HD 3.50 元/万计费字符。中文汉字按 2 字符计，其余计费以官网为准。不要把试听或默认音色状态当成已解锁证明。

## 4. 合成与交付

```bash
python3 scripts/synthesize.py --text "要读的文案。<#0.4#>下一句。" --speed 1.0 --out output/narration.mp3
```

可选参数：--voice-id、--emotion、--speed、--modify-pitch、--modify-timbre、--modify-intensity、--language-boost、--watermark、--pronunciation。

发音示例：`--pronunciation '重:(zhong4),行长:(hang2)(zhang3)'`。

长文本可显式调用异步脚本（不是同步脚本自动切换）：

```bash
python3 scripts/synthesize_long.py --file narration.txt --out output/long.mp3
```

交付后检查文件可播放、时长与文本匹配，说明音色和参数。标明 AI 合成配音。不满意先诊断音色、节奏、情绪、发音问题，再取得重跑授权。

## 5. 音色管理

```bash
python3 scripts/delete_voice.py --list
python3 scripts/delete_voice.py YOUR_VOICE_ID
```

删除会影响远端音色，执行前取得用户明确确认。

## 隐私

密钥只通过环境变量读取。voices.json、录音、合成结果、账户信息和日志属于本地数据，不要公开提交。底层服务：MiniMax API。
