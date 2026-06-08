"""昇腾 NPU Whisper：encoder.om 在 NPU，decoder 在 CPU（openai-whisper）。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import numpy as np

from ..ascend.om_infer import OmModel, default_om_path, is_ascend_available
from .base import ASRBackend

logger = logging.getLogger(__name__)

_encoder_cache: dict = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class AscendOmBackend(ASRBackend):
    """
    Whisper 混合推理：
    - 梅尔谱 + tokenizer 解码：CPU（轻量）
    - Audio Encoder：昇腾 NPU（whisper_encoder.om）
    """

    def __init__(
        self,
        encoder_om_path: Optional[str] = None,
        model_size: str = "tiny",
        language: Optional[str] = "zh",
        device_id: int = 0,
    ):
        default_enc = default_om_path("whisper_encoder.om")
        self.encoder_om_path = str(
            Path(encoder_om_path or default_enc).expanduser().resolve()
        )
        self.model_size = model_size
        self.language = language
        self.device_id = device_id
        self._whisper_model: Any = None
        self._encoder_om: Optional[OmModel] = None

    def _ensure_whisper_cpu(self) -> Any:
        if self._whisper_model is not None:
            return self._whisper_model
        try:
            import whisper  # type: ignore
        except ImportError as e:
            raise ImportError(
                "NPU ASR 仍需 openai-whisper 做解码：pip install openai-whisper"
            ) from e
        self._whisper_model = whisper.load_model(self.model_size, device="cpu")
        return self._whisper_model

    def _ensure_encoder_om(self) -> OmModel:
        if not is_ascend_available():
            raise RuntimeError(
                "未检测到 acl 模块（NPU 不可用）。请先执行:\n"
                "  source scripts/activate_kuavi_atlas.sh\n"
                "或:\n"
                "  source /usr/local/Ascend/ascend-toolkit/set_env.sh\n"
                "  export PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:$PYTHONPATH"
            )
        if not Path(self.encoder_om_path).is_file():
            raise FileNotFoundError(
                f"Whisper encoder OM 不存在: {self.encoder_om_path}\n"
                "请运行: bash scripts/convert_whisper_encoder_to_om.sh"
            )
        key = (self.encoder_om_path, self.device_id)
        if key not in _encoder_cache:
            om = OmModel(self.encoder_om_path, device_id=self.device_id)
            om.load()
            _encoder_cache[key] = om
        return _encoder_cache[key]

    def transcribe_file(self, path: str) -> str:
        import torch
        import whisper  # type: ignore
        from whisper.decoding import DecodingOptions, decode

        model = self._ensure_whisper_cpu()
        om = self._ensure_encoder_om()

        from whisper.audio import N_FRAMES

        audio = whisper.load_audio(path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels)
        mel = whisper.pad_or_trim(mel, N_FRAMES)
        mel_batch = mel.unsqueeze(0).numpy().astype(np.float32)

        features_np = om.infer([mel_batch])[0]
        if not isinstance(features_np, np.ndarray):
            raise TypeError(
                f"Whisper encoder NPU 输出类型错误: {type(features_np)!r}，期望 numpy.ndarray"
            )
        logger.info("Whisper encoder NPU out shape=%s", features_np.shape)
        features = torch.from_numpy(np.ascontiguousarray(features_np))
        if features.ndim == 2:
            features = features.unsqueeze(0)

        class _NpuEncoder(torch.nn.Module):
            def __init__(self, feat: torch.Tensor):
                super().__init__()
                self.register_buffer("_feat", feat)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return self._feat

        model.encoder = _NpuEncoder(features.to(torch.float32))

        lang = self.language if self.language else None
        options = DecodingOptions(language=lang)
        result = decode(model, mel, options)
        text = (result.text or "").strip()
        logger.info("Ascend Whisper (encoder NPU): %r", text)
        return text
