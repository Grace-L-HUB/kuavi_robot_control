#!/usr/bin/env bash
# Atlas 200I NPU 环境检查与模型转换入口
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Atlas NPU 环境 ==="
if [[ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
  echo "CANN: OK"
else
  echo "CANN: 未找到 /usr/local/Ascend/ascend-toolkit/set_env.sh"
fi

python3 - <<'PY' || true
try:
    import acl
    print("acl Python: OK")
except ImportError:
    print("acl Python: 不可用（需 source set_env.sh）")
PY

npu-smi info 2>/dev/null | head -5 || echo "npu-smi: 不可用"

echo ""
echo "=== 模型转换 ==="
echo "YOLO:   bash scripts/convert_yolo_to_om.sh"
echo "Whisper encoder ONNX 在 PC: python3 scripts/export_whisper_encoder_onnx.py"
echo "Whisper encoder OM 在板:   bash scripts/convert_whisper_encoder_to_om.sh"
echo ""
echo "=== 运行 NPU 流水线 ==="
echo "export PYTHONPATH=$ROOT"
echo "python3 scripts/atlas_voice_grasp_pipeline.py \\"
echo "  --asr-config config/asr_atlas_npu.yaml \\"
echo "  --vision-config config/vision.yaml \\"
echo "  --device npu \\"
echo "  --audio instance/record5.m4a"
