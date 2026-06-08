#!/usr/bin/env bash
# YOLOv8n: PT → ONNX（可在 PC 跑）→ OM（在 Atlas 上跑 ATC）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODELS="$ROOT/ascend_models"
SOC="${SOC_VERSION:-Ascend310B4}"

echo "==> [1/3] 导出 ONNX（需 ultralytics + torch）"
if [[ ! -f "$MODELS/yolov8n.onnx" ]]; then
  python3 - <<'PY'
from pathlib import Path
from ultralytics import YOLO
root = Path("ascend_models")
root.mkdir(exist_ok=True)
pt = root / "yolov8n.pt"
if not pt.is_file():
    m = YOLO("yolov8n.pt")
    m.save(str(pt))
model = YOLO(str(pt))
onnx_path = model.export(format="onnx", imgsz=640, opset=12, simplify=True)
from pathlib import Path as P
src = P(onnx_path)
dst = root / "yolov8n.onnx"
if src.resolve() != dst.resolve():
    import shutil
    shutil.copy2(src, dst)
print("ONNX ->", dst)
PY
else
  echo "    已存在 $MODELS/yolov8n.onnx，跳过导出"
fi

echo "==> [2/3] 加载 CANN 环境"
if [[ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
else
  echo "警告: 未找到 set_env.sh，请手动 source CANN 环境"
fi

echo "==> [3/3] ATC: ONNX → OM (soc=$SOC)"
atc --model="$MODELS/yolov8n.onnx" \
    --framework=5 \
    --output="$MODELS/yolov8n" \
    --input_format=NCHW \
    --input_shape="images:1,3,640,640" \
    --soc_version="$SOC" \
    --log=error

echo "[完成] $MODELS/yolov8n.om"
npu-smi info 2>/dev/null || true
