#!/usr/bin/env python3
"""长文本异步合成（有声书/长视频口播用）。

适用：文案 > 2000 字时。同步接口上限 10000 字符，异步接口上限 100 万字符。
异步接口直接传整段，内部自动处理断句和韵律，不需要手动拆分。

用法：
  python3 synthesize_long.py --text "很长的文案..." --out output/book.mp3
  python3 synthesize_long.py --file book.txt --out output/book.mp3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import minimax_client as mc
import voices_store as store


def create_async_task(
    voice_id: str,
    text: str,
    model: str = "speech-2.8-turbo",
    speed: float = 1.2,
    emotion: str | None = None,
    watermark: bool = False,
) -> str:
    """创建异步合成任务，返回 task_id。"""
    voice_setting = {
        "voice_id": voice_id,
        "speed": speed,
    }
    if emotion:
        voice_setting["emotion"] = emotion

    payload = {
        "model": model,
        "text": text,
        "voice_setting": voice_setting,
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
        "aigc_watermark": watermark,
    }
    result = mc._http_post_json("/v1/t2a_async_v2", payload)
    base = result.get("base_resp", {})
    if base.get("status_code", 0) != 0:
        raise RuntimeError(f"创建异步任务失败: {result}")
    task_id = result.get("task_id")
    if not task_id:
        raise RuntimeError(f"未返回 task_id: {result}")
    return task_id


def poll_task(task_id: str, interval: int = 5, timeout: int = 600) -> dict:
    """轮询任务状态，完成后返回结果。"""
    start = time.time()
    while time.time() - start < timeout:
        result = mc._http_get_json(
            f"/v1/query/t2a_async_query_v2?task_id={task_id}"
        )
        if result.get("base_resp", {}).get("status_code", 0) != 0:
            raise RuntimeError("查询异步任务失败")
        status = result.get("status", "").lower()
        print(f"  任务状态: {status} ({int(time.time()-start)}s)")
        if status == "success":
            return result
        if status in ("failed", "expired"):
            raise RuntimeError(f"任务失败: {result}")
        time.sleep(interval)
    raise TimeoutError(f"任务超时（{timeout}s）")


def download_result(file_id: str, out_path: Path) -> None:
    """根据 file_id 下载合成结果。"""
    url = f"{mc._api_base()}/v1/files/retrieve_content?file_id={file_id}"
    req = mc.urllib.request.Request(url, headers=mc._headers())
    with mc.urllib.request.urlopen(req, timeout=120) as resp:
        out_path.write_bytes(resp.read())


def main() -> int:
    p = argparse.ArgumentParser(description="长文本异步合成")
    p.add_argument("--text", help="要合成的文字（和 --file 二选一）")
    p.add_argument("--file", help="从文件读取长文案")
    p.add_argument("--voice-id", help="指定 voice_id；不传用默认")
    p.add_argument("--speed", type=float, default=1.2)
    p.add_argument("--emotion", default=None)
    p.add_argument("--watermark", action="store_true")
    p.add_argument("--out", required=True, help="输出 mp3 路径")
    args = p.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        p.error("必须传 --text 或 --file")

    voice_id = args.voice_id or store.get_default_voice_id()
    if not voice_id:
        print("未找到默认音色，请先克隆", file=sys.stderr)
        return 1

    print(f"文案长度: {len(text)} 字")
    print(f"创建异步任务...")
    task_id = create_async_task(
        voice_id=voice_id,
        text=text,
        speed=args.speed,
        emotion=args.emotion,
        watermark=args.watermark,
    )
    print(f"任务已创建: {task_id}")

    print("轮询中...")
    result = poll_task(task_id)
    file_id = result.get("file_id")
    if not file_id:
        raise RuntimeError(f"结果里没有 file_id: {result}")

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    download_result(file_id, out_path)
    print(f"✅ 完成: {out_path} ({out_path.stat().st_size//1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
