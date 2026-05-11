"""语音到结构化指令：ASR 文本 -> 规则 NLU（与下游约定的 JSON）。"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Dict, Optional, Tuple

from .audio_record import record_wav_file
from .semantic_parser import parse_instruction
from .speech_recognition import transcribe_file


def normalize_asr_text(text: str) -> str:
    """压缩 Whisper 输出的多余空白，便于规则匹配。"""
    s = text.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def speech_file_to_json(
    audio_path: str,
    *,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    语音文件 -> 任务 JSON（字段与 `parse_instruction` 一致）。

    Parameters
    ----------
    audio_path : str
        wav/mp3 等本地路径。
    config_path : str, optional
        覆盖默认 `config/asr.yaml`。
    """
    raw_text = transcribe_file(audio_path, config_path=config_path)
    text = normalize_asr_text(raw_text)
    return parse_instruction(text)


def transcribe_then_parse(
    audio_path: str,
    *,
    config_path: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    同上，但返回 (识别文本, 任务 JSON)，便于调试或日志。
    """
    raw_text = transcribe_file(audio_path, config_path=config_path)
    text = normalize_asr_text(raw_text)
    return text, parse_instruction(text)


def record_then_parse(
    *,
    duration_sec: float = 5.0,
    wav_path: Optional[str] = None,
    config_path: Optional[str] = None,
    sample_rate: int = 16000,
    device: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    麦克风录制 -> ASR -> NLU，返回 (识别文本, 任务 JSON)。

    wav_path 为 None 时使用临时 wav，识别结束后删除；
    若传入路径则写入该文件并保留。
    """
    cleanup: Optional[str] = None
    path = wav_path
    if path is None:
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        path = tmp
        cleanup = tmp

    try:
        record_wav_file(
            path,
            duration_sec=duration_sec,
            sample_rate=sample_rate,
            device=device,
        )
        return transcribe_then_parse(path, config_path=config_path)
    finally:
        if cleanup and os.path.isfile(cleanup):
            os.unlink(cleanup)


def record_speech_to_json(
    *,
    duration_sec: float = 5.0,
    wav_path: Optional[str] = None,
    config_path: Optional[str] = None,
    sample_rate: int = 16000,
    device: Optional[int] = None,
) -> Dict[str, Any]:
    """麦克风录制 -> 仅返回任务 JSON（与 `speech_file_to_json` 对应）。"""
    _, task = record_then_parse(
        duration_sec=duration_sec,
        wav_path=wav_path,
        config_path=config_path,
        sample_rate=sample_rate,
        device=device,
    )
    return task
