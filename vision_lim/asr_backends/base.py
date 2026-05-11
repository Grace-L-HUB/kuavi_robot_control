"""ASR 后端抽象：PC 上为 Whisper，后续可在板端替换为昇腾 .om 等实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ASRBackend(ABC):
    @abstractmethod
    def transcribe_file(self, path: str) -> str:
        """输入 wav 等音频文件路径，返回识别文本（trim 后）。"""


class AscendOmBackend(ASRBackend):
    """占位：板端昇腾 whisper.om 推理，后续在此接入 CANN 推理代码。"""

    def transcribe_file(self, path: str) -> str:
        raise NotImplementedError(
            "AscendOmBackend 尚未实现：请在板端接入 ascend_models/whisper.om 推理后实现。"
        )
