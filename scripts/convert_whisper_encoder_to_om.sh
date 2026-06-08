#!/usr/bin/env bash
# Whisper encoder: ONNX → OM（需先有 whisper_encoder.onnx）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODELS="$ROOT/ascend_models"
SOC="${SOC_VERSION:-Ascend310B4}"
ONNX="$MODELS/whisper_encoder.onnx"
OM="$MODELS/whisper_encoder.om"

if [[ ! -f "$ONNX" ]]; then
  echo "未找到 $ONNX"
  echo "请先在 PC 运行: python3 scripts/export_whisper_encoder_onnx.py"
  exit 1
fi

# 读取 tiny 默认 n_audio_ctx=1500, n_mels=80
N_MELS="${WHISPER_N_MELS:-80}"
N_CTX="${WHISPER_N_CTX:-1500}"
INPUT_SHAPE="mel:1,${N_MELS},${N_CTX}"

if [[ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
fi

echo "==> ATC Whisper encoder (soc=$SOC, input=$INPUT_SHAPE)"
atc --model="$ONNX" \
    --framework=5 \
    --output="$MODELS/whisper_encoder" \
    --input_format=ND \
    --input_shape="$INPUT_SHAPE" \
    --soc_version="$SOC" \
    --log=error

mv -f "$MODELS/whisper_encoder.om" "$OM" 2>/dev/null || true
echo "[完成] $OM"
echo "ASR 配置: config/asr_atlas_npu.yaml"
