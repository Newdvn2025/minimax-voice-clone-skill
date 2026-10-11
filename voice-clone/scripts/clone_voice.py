#!/usr/bin/env python3
"""克隆一段录音为音色。

流程：上传录音 → 调 voice_clone → 下载自带试听音频 → 写入 voices.json（标记为 pending）。
注意：克隆本身不扣 9.9，试听按字符计费（几厘钱）。9.9 解锁费在用户确认满意、
第一次用该音色做正式 t2a_v2 合成时才扣。

用法：
  python3 clone_voice.py <录音路径> --name <音色名> [选项]

示例：
  python3 clone_voice.py ~/r.mp3 --name myvoice --no-noise-reduction
  python3 clone_voice.py ~/r.mp3 --name myvoice --demo-text "大家好，欢迎来到我的频道"
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import minimax_client as mc
import voices_store as store


def main() -> int:
    p = argparse.ArgumentParser(description="MiniMax 声音克隆（试听按字符计费，满意再正式启用）")
    p.add_argument("audio", help="录音文件路径（mp3/m4a/wav，10秒–5分钟，<20MB）")
    p.add_argument("--name", required=True, help="音色名，如 myvoice")
    p.add_argument("--voice-id", help="自定义 voice_id（8-256字符，字母开头），默认自动生成")
    p.add_argument("--model", default="speech-2.8-hd",
                   choices=["speech-2.8-hd", "speech-2.8-turbo",
                            "speech-2.6-hd", "speech-2.6-turbo",
                            "speech-02-hd", "speech-02-turbo",
                            "speech-01-hd", "speech-01-turbo"],
                   help="克隆试听模型，默认 2.8-hd")
    p.add_argument("--demo-text", default="你好，这是我的克隆音色试听。",
                   help="试听文本（≤1000字符）")

    # 修音开关
    p.add_argument("--no-noise-reduction", action="store_true",
                   help="关闭降噪（默认开启；录音很干净时可关）")
    p.add_argument("--no-volume-norm", action="store_true",
                   help="关闭音量归一化（默认开启）")

    # 高级校验
    p.add_argument("--expected-text",
                   help="录音里实际说的话（≤200字符）。提供后服务会做 ASR 校验，"
                        "识别不上来会拒绝克隆，防止传错文件")
    p.add_argument("--accuracy", type=float, default=0.7,
                   help="ASR 相似度阈值 0-1，默认 0.7")
    p.add_argument("--language-boost", default="auto",
                   help="小语种/方言增强，默认 auto")
    p.add_argument("--no-watermark", action="store_true",
                   help="关闭 AIGC 音频末尾水印（默认开）")
    args = p.parse_args()

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"录音文件不存在: {audio_path}", file=sys.stderr)
        return 1

    if not audio_path.is_file() or audio_path.suffix.lower() not in {".mp3", ".m4a", ".wav"}:
        p.error("录音必须为 mp3/m4a/wav 文件")
    if audio_path.stat().st_size > 20 * 1024 * 1024:
        p.error("录音不能超过 20 MB")
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.name):
        p.error("音色名仅允许 1–64 位字母、数字、下划线、连字符")
    voice_id = args.voice_id or f"vlo-{uuid.uuid4().hex[:12]}"
    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(exist_ok=True)

    print(f"[1/4] 上传录音 {audio_path.name} ...")
    file_id = mc.upload_file(audio_path, purpose="voice_clone")
    print(f"      file_id = {file_id}")

    print(f"[2/4] 克隆音色 voice_id={voice_id}")
    print(f"      降噪={'开' if not args.no_noise_reduction else '关'}  "
          f"音量归一化={'开' if not args.no_volume_norm else '关'}  "
          f"模型={args.model}")
    result = mc.clone_voice(
        file_id=file_id,
        voice_id=voice_id,
        model=args.model,
        text=args.demo_text,
        noise_reduction=not args.no_noise_reduction,
        volume_normalization=not args.no_volume_norm,
        expected_text=args.expected_text,
        accuracy=args.accuracy,
        language_boost=args.language_boost,
        watermark=not args.no_watermark,
    )

    demo_url = result.get("demo_audio")
    if demo_url:
        demo_path = out_dir / f"demo_{args.name}_{voice_id}.mp3"
        mc.download_audio(demo_url, demo_path)
        print(f"[3/4] 试听音频已保存: {demo_path}")
        print(f"      ⚠️ 这是克隆接口自带的试听（按字符计费，几厘钱），不扣 9.9。")
    else:
        demo_path = None
        print("[3/4] ⚠️ 响应里没有 demo_audio 字段（可能没传 --demo-text）")

    print(f"[4/4] 写入 voices.json（状态: pending，等用户确认后再设为默认）...")
    store.add_voice(
        name=args.name,
        voice_id=voice_id,
        sample_audio=str(audio_path),
        status="pending",
    )
    print()
    print(f"✅ 克隆完成：{args.name} → {voice_id}")
    if demo_path:
        print(f"🎧 试听文件: {demo_path}")
    print()
    print("下一步：把试听发给用户听。用户说'满意/就用这个'后，")
    print("       再用 voices_store.set_default() 设为默认音色，")
    print("       之后第一次正式合成时才会扣 9.9 元解锁费。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
