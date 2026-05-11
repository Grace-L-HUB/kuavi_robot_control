"""麦克风录制为 WAV（16kHz 单声道 int16，便于 Whisper 与板端格式对齐）。"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Optional

import numpy as np


def record_wav_file(
    out_path: str,
    *,
    duration_sec: float = 5.0,
    sample_rate: int = 16000,
    device: Optional[int] = None,
) -> str:
    """
    从默认（或指定）麦克风录制单声道 WAV。

    Parameters
    ----------
    out_path : str
        输出 .wav 路径（父目录不存在时会创建）。
    duration_sec : float
        录制时长（秒）。
    sample_rate : int
        采样率，默认 16000。
    device : int, optional
        sounddevice 输入设备编号；默认 None 为系统默认麦克风。
        可用 `python -m sounddevice` 查看设备列表。

    Returns
    -------
    str
        写入文件的绝对路径字符串。
    """
    try:
        import sounddevice as sd  # type: ignore
    except ImportError as e:
        raise ImportError(
            "录制需要安装 sounddevice：pip install sounddevice numpy"
        ) from e

    frames = int(duration_sec * sample_rate)
    kwargs = dict(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    if device is not None:
        kwargs["device"] = device

    recording = sd.rec(frames, **kwargs)
    sd.wait()

    audio = np.asarray(recording, dtype=np.float32).reshape(-1)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)

    path = Path(out_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

    return str(path)
