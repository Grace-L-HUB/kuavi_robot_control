"""PC 开发阶段：openai-whisper 本地推理（CPU/GPU）。"""

from __future__ import annotations

from typing import Any, Optional

from .base import ASRBackend


class WhisperLocalBackend(ASRBackend):
    def __init__(self, model_size: str = "tiny", language: Optional[str] = "zh"):
        self._model_size = model_size
        self._language = language
        self._model: Any = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            import whisper  # type: ignore
        except ImportError as e:
            raise ImportError(
                "未安装 openai-whisper。请先安装: pip install -r requirements-asr.txt"
            ) from e
        self._model = whisper.load_model(self._model_size)

    def transcribe_file(self, path: str) -> str:
        self._ensure_model()
        kwargs = {}
        if self._language:
            kwargs["language"] = self._language
        result = self._model.transcribe(path, **kwargs)
        text = (result.get("text") or "").strip()
        return text
