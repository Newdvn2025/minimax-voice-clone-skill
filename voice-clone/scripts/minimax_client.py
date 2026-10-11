"""MiniMax 语音克隆与合成客户端（仅用标准库）。

环境变量：
  MINIMAX_API_KEY   必填，在 platform.minimaxi.com → 账户管理 → 接口密钥 创建
  MINIMAX_GROUP_ID  选填，部分老接口需要；新版 Bearer 鉴权可不填
  MINIMAX_API_BASE  选填，默认 https://api.minimax.cn（国内站）
"""
from __future__ import annotations

import json
import os
import uuid
import urllib.request
import urllib.error
from pathlib import Path


def _api_base() -> str:
    return os.environ.get("MINIMAX_API_BASE", "https://api.minimax.cn").rstrip("/")


def _headers() -> dict:
    key = os.environ.get("MINIMAX_API_KEY")
    if not key:
        raise RuntimeError("未设置环境变量 MINIMAX_API_KEY")
    return {
        "Authorization": f"Bearer {key}",
    }


def _url(path: str) -> str:
    url = f"{_api_base()}{path}"
    gid = os.environ.get("MINIMAX_GROUP_ID")
    if gid and "?" not in url:
        url += f"?GroupId={gid}"
    return url


def _http_get_json(path: str) -> dict:
    req = urllib.request.Request(_url(path), headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _url(path),
        data=data,
        method="POST",
        headers={**_headers(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _http_post_multipart(path: str, field_name: str, file_path: Path, purpose: str) -> dict:
    """multipart/form-data 上传文件。"""
    boundary = "----MMXBoundary" + uuid.uuid4().hex
    filename = file_path.name
    file_bytes = file_path.read_bytes()

    body = b""
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="purpose"\r\n\r\n'.encode()
    body += f"{purpose}\r\n".encode()
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
    )
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += file_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        _url(path),
        data=body,
        method="POST",
        headers={
            **_headers(),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_file(file_path: Path, purpose: str = "voice_clone") -> str:
    """上传音频文件，返回 file_id。

    purpose:
      voice_clone  待克隆音频（10秒–5分钟，mp3/m4a/wav，<20MB）
      prompt_audio 参考音频（<8秒，可选，增强克隆效果）
    """
    result = _http_post_multipart("/v1/files/upload", "file", file_path, purpose)
    file_id = result.get("file", {}).get("file_id")
    if not file_id:
        raise RuntimeError(f"上传失败: {result}")
    return file_id


def clone_voice(
    file_id: str,
    voice_id: str,
    model: str = "speech-2.8-hd",
    text: str = "你好，这是我的克隆音色试听。",
    prompt_audio_id: str | None = None,
    prompt_text: str | None = None,
    noise_reduction: bool = True,
    volume_normalization: bool = True,
    expected_text: str | None = None,
    accuracy: float = 0.7,
    language_boost: str = "auto",
    watermark: bool = False,
) -> dict:
    """发起音色克隆。voice_id 由调用方自定义（8-256字符，字母开头）。

    - noise_reduction: 降噪（录音有背景噪时建议 true）
    - volume_normalization: 音量归一化
    - expected_text: 录音里实际说的话（≤200字符），提供后做 ASR 校验防传错文件
    - accuracy: ASR 相似度阈值 0-1，默认 0.7
    - language_boost: 小语种/方言增强，默认 auto
    - watermark: 是否在试听末尾加 AIGC 节奏标识，默认 false
    返回完整响应 JSON；demo_audio 字段是试听音频 URL（按字符计费，不扣 9.9）。
    """
    payload: dict = {
        "file_id": file_id,
        "voice_id": voice_id,
        "text": text,
        "model": model,
        "need_noise_reduction": noise_reduction,
        "need_volume_normalization": volume_normalization,
        "accuracy": accuracy,
        "language_boost": language_boost,
        "aigc_watermark": watermark,
    }
    if expected_text:
        payload["text_validation"] = expected_text
    if prompt_audio_id:
        payload["clone_prompt"] = {
            "prompt_audio": prompt_audio_id,
            "prompt_text": prompt_text or text,
        }
    result = _http_post_json("/v1/voice_clone", payload)
    base = result.get("base_resp", {})
    if base.get("status_code", 0) != 0:
        raise RuntimeError(f"克隆失败: {result}")
    return result


def download_audio(url: str, out_path: Path) -> None:
    """下载试听音频 URL 到本地。"""
    req = urllib.request.Request(url, headers={"User-Agent": "voice-clone-skill/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out_path.write_bytes(resp.read())


# 统一情绪枚举 → MiniMax emotion 值
EMOTION_MAP = {
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "fearful": "fearful",
    "disgusted": "disgusted",
    "surprised": "surprised",
    "calm": "calm",
    "neutral": "neutral",
    "fluent": "fluent",
    "whisper": "whisper",
}


def synthesize(
    voice_id: str,
    text: str,
    model: str = "speech-2.8-turbo",
    emotion: str | None = None,
    speed: float = 1.0,
    vol: float = 1.0,
    pitch: int = 0,
    voice_modify: dict | None = None,
    watermark: bool = False,
    language_boost: str | None = None,
    pronunciation_dict: dict | None = None,
) -> bytes:
    """用克隆音色合成语音，返回 mp3 字节。

    emotion 不传时让模型自动判断。
    voice_modify: {pitch: int, intensity: int, timbre: int, sound_effects: str}
      pitch: [-100,100] +亮 -沉；intensity: +刚劲 -轻柔；timbre: +清脆 -浑厚
    watermark: 是否加 AIGC 末尾"滴滴"声，默认 False（关闭）
    language_boost: 多语言/方言增强，传 "auto" 自动识别，或指定 "Chinese"/"English" 等
    """
    voice_setting: dict = {
        "voice_id": voice_id,
        "speed": speed,
        "vol": vol,
        "pitch": pitch,
    }
    if emotion and emotion in EMOTION_MAP:
        voice_setting["emotion"] = EMOTION_MAP[emotion]

    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": voice_setting,
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
        "aigc_watermark": watermark,
    }
    if language_boost:
        payload["language_boost"] = language_boost
    if pronunciation_dict:
        payload["pronunciation_dict"] = pronunciation_dict
    # voice_modify 独立字段，不在 voice_setting 里
    if voice_modify:
        payload["voice_modify"] = voice_modify

    result = _http_post_json("/v1/t2a_v2", payload)
    base = result.get("base_resp", {})
    if base.get("status_code", 0) != 0:
        raise RuntimeError(f"合成失败: {result}")
    audio_b64 = result.get("data", {}).get("audio")
    if not audio_b64:
        raise RuntimeError(f"未返回音频: {result}")
    import base64

    # MiniMax 返回的 audio 字段是 hex 字符串（如 "494433..." = ID3 mp3头），
    # 不是标准 base64。优先尝试 hex 解码；失败再 fallback 到 base64。
    try:
        return bytes.fromhex(audio_b64)
    except ValueError:
        return base64.b64decode(audio_b64)
