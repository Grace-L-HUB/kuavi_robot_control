"""视觉与语言推理模块（语音、检测、坐标变换等）。"""

from .semantic_parser import parse_instruction
from .speech_recognition import transcribe_file

__all__ = ["parse_instruction", "transcribe_file"]
