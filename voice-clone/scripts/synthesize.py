#!/usr/bin/env python3
"""用默认克隆音色合成一段语音。

用法：
  python3 synthesize.py --text "要读的文字" [--emotion happy] [--out output/xxx.mp3]

情绪识别：不传 --emotion 时，根据文案里的关键词自动映射；识别不到则让模型自动判断。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import minimax_client as mc
import voices_store as store

# 情绪关键词 → 统一情绪枚举
EMOTION_KEYWORDS: list[tuple[list[str], str]] = [
    (["开心", "高兴", "笑", "兴奋", "太好了", "棒", "喜悦", "哈哈"], "happy"),
    (["伤心", "悲伤", "难过", "哭", "遗憾", "失落", "唉", "呜呜"], "sad"),
    (["生气", "愤怒", "气死", "吼", "火大", "可恶", "混账"], "angry"),
    (["害怕", "紧张", "担心", "恐惧", "吓人", "哆嗦"], "fearful"),
    (["恶心", "讨厌", "嫌弃", "反胃", "烦死"], "disgusted"),
    (["惊讶", "震惊", "居然", "没想到", "天哪", "不会吧"], "surprised"),
    (["平静", "冷静", "淡定", "从容", "安详"], "calm"),
    (["小声", "耳语", "悄悄", "低声", "嘀咕"], "whisper"),
]


def detect_emotion(text: str) -> str | None:
    for keywords, emo in EMOTION_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return emo
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True, help="要合成的文字")
    p.add_argument("--voice-id", help="指定 voice_id；不传则用默认")
    p.add_argument("--emotion", help="强制指定情绪：happy/sad/angry/fearful/disgusted/surprised/calm/whisper")
    p.add_argument("--model", default="speech-2.8-turbo")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--vol", type=float, default=1.0, help="音量 0-10，默认 1.0")
    p.add_argument("--modify-pitch", type=int, default=0,
                   help="声音亮度 -100~100，默认 0")
    p.add_argument("--modify-timbre", type=int, default=0,
                   help="音色 -100~100，+清脆 -浑厚")
    p.add_argument("--modify-intensity", type=int, default=0,
                   help="语气强度 -100~100，+刚劲 -轻柔")
    p.add_argument("--language-boost", default=None,
                   help="多语言/方言增强：auto（自动识别）/ Chinese / English / Japanese 等")
    p.add_argument("--pronunciation", default=None,
                   help="发音字典，格式：'重:(zhong4),行长:(hang2)(zhang3)'，纠正多音字")
    p.add_argument("--watermark", action="store_true",
                   help="开启 AIGC 水印（结尾滴滴声），默认关闭")
    p.add_argument("--out", help="输出 mp3 路径，默认 output/<时间戳>.mp3")
    args = p.parse_args()

    voice_id = args.voice_id or store.get_default_voice_id()
    if not voice_id:
        print("未找到默认音色。请先运行 clone_voice.py 克隆一段录音。", file=sys.stderr)
        return 1

    emotion = args.emotion or detect_emotion(args.text)
    if emotion:
        print(f"情绪识别: {emotion}")
    else:
        print("情绪识别: 自动（由模型判断）")

    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(exist_ok=True)
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        from datetime import datetime

        out_path = out_dir / f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

    print(f"合成中... voice_id={voice_id}")

    # 长文本提示
    if len(args.text) > 2000:
        print(f"⚠️ 文案 {len(args.text)} 字，超过 2000 字建议用异步接口（t2a_async_v2）")

    # 发音字典解析
    pronunciation = None
    if args.pronunciation:
        words = []
        for pair in args.pronunciation.split(","):
            if ":" in pair:
                w, p = pair.split(":", 1)
                words.append(f"{w.strip()}/{p.strip()}")
        if words:
            pronunciation = {"tone": words}

    audio = mc.synthesize(
        voice_id=voice_id,
        text=args.text,
        model=args.model,
        emotion=emotion,
        speed=args.speed,
        vol=args.vol,
        voice_modify={
            "pitch": args.modify_pitch,
            "timbre": args.modify_timbre,
            "intensity": args.modify_intensity,
        },
        watermark=args.watermark,
        language_boost=args.language_boost,
        pronunciation_dict=pronunciation,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    print(f"✅ 已保存: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
