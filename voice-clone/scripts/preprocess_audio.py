#!/usr/bin/env python3
"""音频预处理：降噪 + 切频 + 音量归一化。

在克隆前先跑一遍，把用户录音处理干净，试听满意后再拿处理后的文件去克隆。

用法：
  python3 preprocess_audio.py <输入录音> [--out output/clean.wav]

处理链：
  1. afftdn  FFT 域降噪（温和强度，避免发闷/回响）
  2. highpass=70  切掉 70Hz 以下低频轰鸣（空调/桌面震动）
  3. lowpass=16000  保留到 16kHz，避免声音发闷
  4. loudnorm  EBU R128 音量归一化
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def preprocess(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg 滤镜链：温和降噪 + 保留高频 + 音量归一化
    # afftdn nr=8 温和降噪，nf=-28 噪声基底稍宽
    filter_chain = (
        "afftdn=nr=8:nf=-28,"
        "highpass=f=70,"
        "lowpass=f=16000,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-af", filter_chain,
        "-ar", "32000",   # 克隆要求 32kHz 即可
        "-ac", "1",       # 单声道
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output_path),
    ]
    print(f"运行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg 报错:", result.stderr[-500:], file=sys.stderr)
        sys.exit(1)
    print(f"✅ 预处理完成: {output_path} ({output_path.stat().st_size//1024} KB)")
    return output_path


def main() -> int:
    p = argparse.ArgumentParser(description="克隆前的音频降噪预处理")
    p.add_argument("input", help="原始录音路径")
    p.add_argument("--out", help="输出路径，默认 output/clean_<原名>.mp3")
    args = p.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    if not in_path.exists():
        print(f"文件不存在: {in_path}", file=sys.stderr)
        return 1

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        out_dir = Path(__file__).resolve().parent.parent / "output"
        out_path = out_dir / f"clean_{in_path.stem}.mp3"

    preprocess(in_path, out_path)
    print()
    print("下一步：把处理后的音频发给用户试听。")
    print("用户满意后，用这个 clean 文件去跑 clone_voice.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
