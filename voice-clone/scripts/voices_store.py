"""voices.json 状态读写。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent / "voices.json"


def _load() -> dict:
    if not STORE_PATH.exists():
        return {"default_voice_id": None, "voices": {}}
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    STORE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_voice(
    name: str,
    voice_id: str,
    sample_audio: str | None = None,
    status: str = "pending",
) -> None:
    data = _load()
    data["voices"][name] = {
        "voice_id": voice_id,
        "provider": "minimax",
        "sample_audio": sample_audio,
        "status": status,  # pending=试听阶段未扣9.9; active=用户确认已正式启用
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    # pending 音色不自动设为默认，等用户确认后再调 set_default
    _save(data)


def set_default(name: str) -> None:
    data = _load()
    if name not in data["voices"]:
        raise RuntimeError(f"未找到音色: {name}")
    data["default_voice_id"] = data["voices"][name]["voice_id"]
    _save(data)


def get_default_voice_id() -> str | None:
    return _load().get("default_voice_id")


def get_voice_id(name: str) -> str | None:
    return _load()["voices"].get(name, {}).get("voice_id")


def list_voices() -> dict:
    return _load()["voices"]


def current_name() -> str | None:
    data = _load()
    default_id = data.get("default_voice_id")
    for name, info in data["voices"].items():
        if info["voice_id"] == default_id:
            return name
    return None


def remove_voice(voice_id: str) -> None:
    data = _load()
    to_remove = None
    for name, info in data["voices"].items():
        if info["voice_id"] == voice_id:
            to_remove = name
            break
    if to_remove:
        del data["voices"][to_remove]
    if data.get("default_voice_id") == voice_id:
        data["default_voice_id"] = None
    _save(data)
