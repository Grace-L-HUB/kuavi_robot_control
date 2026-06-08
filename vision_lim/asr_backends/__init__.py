from .ascend_om import AscendOmBackend
from .base import ASRBackend
from .whisper_local import WhisperLocalBackend

__all__ = ["ASRBackend", "AscendOmBackend", "WhisperLocalBackend"]
