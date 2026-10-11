#!/usr/bin/env python3
"""删除不再需要的克隆音色。

用法：
  python3 delete_voice.py <voice_id>
  python3 delete_voice.py --list   # 列出所有音色
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import minimax_client as mc
import voices_store as store


def list_voices() -> None:
    """列出本地注册的音色。"""
    voices = store.list_voices()
    if not voices:
        print("暂无注册音色")
        return
    print(f"{'音色名':<20} {'voice_id':<30} {'状态':<10}")
    print("-" * 60)
    for name, v in voices.items():
        default = "★" if v["voice_id"] == store.get_default_voice_id() else " "
        print(f"{default}{name:<18} {v['voice_id']:<30} {v.get('status',''):<10}")


def delete_voice(voice_id: str) -> None:
    """调用 API 删除音色，同时清理本地注册。"""
    result = mc._http_post_json("/v1/delete_voice", {
        "voice_id": voice_id,
        "voice_type": "voice_cloning",
    })
    base = result.get("base_resp", {})
    if base.get("status_code", 0) != 0:
        print(f"删除失败: {result}")
        return
    store.remove_voice(voice_id)
    print(f"✅ 已删除音色: {voice_id}")


def main() -> int:
    p = argparse.ArgumentParser(description="删除克隆音色")
    p.add_argument("voice_id", nargs="?", help="要删除的 voice_id")
    p.add_argument("--list", action="store_true", help="列出所有音色")
    args = p.parse_args()

    if args.list:
        list_voices()
        return 0
    if not args.voice_id:
        p.print_help()
        return 1
    delete_voice(args.voice_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
