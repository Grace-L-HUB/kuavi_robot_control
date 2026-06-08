#!/usr/bin/env python3
"""导出 Whisper tiny encoder 为 ONNX（固定输入 1×80×n_audio_ctx）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "ascend_models"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Whisper encoder to ONNX")
    parser.add_argument("--model-size", default="tiny", choices=["tiny", "base", "small"])
    parser.add_argument(
        "--output",
        default=str(OUT_DIR / "whisper_encoder.onnx"),
        help="输出 ONNX 路径",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=14,
        help="ONNX opset（Whisper 含 scaled_dot_product_attention，至少 14）",
    )
    args = parser.parse_args()

    try:
        import torch
        import whisper
    except ImportError as e:
        print("需要: pip install openai-whisper torch", file=sys.stderr)
        return 1

    from whisper.audio import N_FRAMES

    model = whisper.load_model(args.model_size, device="cpu")
    n_mels = model.dims.n_mels
    # Encoder 输入 mel 时间维为 N_FRAMES(3000)，非 n_audio_ctx(1500)。
    # conv2 stride=2 后才是 n_audio_ctx 帧，与 positional_embedding 对齐。
    mel_frames = N_FRAMES
    dummy = torch.randn(1, n_mels, mel_frames, dtype=torch.float32)
    with torch.no_grad():
        model.encoder(dummy)  # 导出前校验 shape

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model.encoder,
        dummy,
        str(out_path),
        input_names=["mel"],
        output_names=["audio_features"],
        opset_version=args.opset,
        dynamic_axes=None,
        do_constant_folding=True,
    )
    print(f"[OK] encoder ONNX: {out_path}")
    print(f"     opset: {args.opset}")
    print(f"     input shape: (1, {n_mels}, {mel_frames})  (ATC: mel:1,{n_mels},{mel_frames})")
    print(f"     encoder output ctx: {model.dims.n_audio_ctx}")
    print("下一步在 Atlas 上运行: bash scripts/convert_whisper_encoder_to_om.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
