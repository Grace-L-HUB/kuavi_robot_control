"""视觉与语言推理模块（语音、检测、坐标变换等）。"""

from .audio_record import record_wav_file
from .semantic_parser import parse_instruction
from .speech_recognition import transcribe_file
from .voice_pipeline import (
    normalize_asr_text,
    record_speech_to_json,
    record_then_parse,
    speech_file_to_json,
    transcribe_then_parse,
)

__all__ = [
    "normalize_asr_text",
    "parse_instruction",
    "record_speech_to_json",
    "record_then_parse",
    "record_wav_file",
    "speech_file_to_json",
    "transcribe_file",
    "transcribe_then_parse",
]
