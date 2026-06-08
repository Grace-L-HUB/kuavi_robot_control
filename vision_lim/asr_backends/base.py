"""ASR 后端抽象：PC 上为 Whisper，板端为昇腾 encoder.om + CPU decode。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ASRBackend(ABC):
    @abstractmethod
    def transcribe_file(self, path: str) -> str:
        """输入 wav 等音频文件路径，返回识别文本（trim 后）。"""
