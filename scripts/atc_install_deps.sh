#!/usr/bin/env bash
# 安装 CANN/ATC 模型转换所需的 Python 第三方库
# 官方: https://www.hiascend.com/document/detail/zh/canncommercial/82RC1/softwareinst/instg/instg_0094.html
# ATC 常见报错 decorator/te: 按提示 pip 安装缺失包
set -euo pipefail

echo "==> 加载 CANN 环境"
if [[ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
fi

echo "==> 当前 python3: $(which python3) $(python3 --version 2>&1)"

# root 用户不加 --user；NumPy 用 1.26.x（CANN 不支持 2.x，见 MindSDK FAQ）
echo "==> 安装 ATC/TBE 依赖（decorator、scipy、psutil 等）"
pip3 install \
  numpy==1.26.4 \
  decorator \
  attrs \
  cython \
  sympy \
  cffi \
  pyyaml \
  psutil \
  "protobuf==3.20.0" \
  scipy \
  requests \
  absl-py

# pathlib2 仅 Python<3.4 需要，Atlas 可跳过
python3 - <<'PY'
import importlib
mods = [
    "numpy", "decorator", "attrs", "sympy", "cffi", "yaml",
    "psutil", "google.protobuf", "scipy", "requests", "absl",
]
ok = True
for m in mods:
    try:
        importlib.import_module(m)
        print(f"  OK  {m}")
    except ImportError as e:
        print(f"  FAIL {m}: {e}")
        ok = False
import numpy as np
print(f"  numpy version: {np.__version__}")
if not np.__version__.startswith("1."):
    print("  WARN: numpy 应为 1.x，当前为", np.__version__)
    ok = False
raise SystemExit(0 if ok else 1)
PY

echo ""
echo "[完成] 请在本 shell 中执行 atc（勿切换 venv）:"
echo "  atc --model=ascend_models/yolov8n.onnx --framework=5 \\"
echo "      --output=ascend_models/yolov8n --input_format=NCHW \\"
echo "      --input_shape=\"images:1,3,640,640\" --soc_version=Ascend310B4"
