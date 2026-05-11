"""语音识别入口：根据配置选择后端（便于后续切换为昇腾）。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from .asr_backends import AscendOmBackend, WhisperLocalBackend

_DEFAULT_CONFIG_NAME = "asr.yaml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_config_path(config_path: Optional[str]) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()
    return _repo_root() / "config" / _DEFAULT_CONFIG_NAME


def _make_backend(cfg: dict):
    asr_cfg = cfg.get("asr") or {}
    backend_name = (asr_cfg.get("backend") or "whisper_local").strip().lower()
    if backend_name == "whisper_local":
        w = asr_cfg.get("whisper") or {}
        return WhisperLocalBackend(
            model_size=str(w.get("model_size") or "tiny"),
            language=w.get("language"),
        )
    if backend_name in ("ascend_om", "ascend"):
        return AscendOmBackend()
    raise ValueError(f"未知的 ASR backend: {backend_name}")


def transcribe_file(
    audio_path: str,
    *,
    config_path: Optional[str] = None,
) -> str:
    """
    将音频文件转为文本。

    Parameters
    ----------
    audio_path : str
        wav 等本地路径（Whisper 常见支持 wav/mp3 等，依 ffmpeg 而定）。
    config_path : str, optional
        覆盖默认的 config/asr.yaml。
    """
    cfg = _load_yaml(_resolve_config_path(config_path))
    backend = _make_backend(cfg)
    return backend.transcribe_file(audio_path)
