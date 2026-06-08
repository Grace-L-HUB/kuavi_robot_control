#!/usr/bin/env bash
# ATC 前检查：CANN 不兼容 NumPy 2.0（官方 FAQ）
# https://www.hiascend.com/doc_center/source/zh/mind-sdk/60rc3/mxIndex/mxindexfrug/mxindexfrug_0501.html
set -euo pipefail

_atc_check_numpy() {
  local py="${1:-python3}"
  local ver
  ver="$("$py" -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "missing")"
  if [[ "$ver" == "missing" ]]; then
    echo "[ATC] 警告: $py 未安装 numpy，ATC 可能失败"
    return 0
  fi
  echo "[ATC] $py -> $(which "$py") ($("$py" --version 2>&1))"
  echo "[ATC] $py numpy=$ver"
  if "$py" -c "import numpy as np; import sys; sys.exit(0 if np.__version__.startswith('1.') else 1)" 2>/dev/null; then
    return 0
  fi
  echo ""
  echo "[ATC 错误] NumPy $ver 与 CANN/ATC 不兼容（需 1.26.x，不能用 2.x）"
  echo "  官方方案: pip3 install numpy==1.26.4"
  echo "  建议: 退出 kuavi/conda 虚拟环境后再跑 ATC，并对 ATC 使用的 python3 降级 numpy"
  echo ""
  echo "  deactivate && conda deactivate  # 如有"
  echo "  source /usr/local/Ascend/ascend-toolkit/set_env.sh"
  echo "  pip3 install numpy==1.26.4"
  echo "  python3 -c \"import numpy; print(numpy.__version__)\"  # 应显示 1.26.x"
  return 1
}

_atc_check_tbe_deps() {
  local py="${1:-python3}"
  local missing=()
  for mod in decorator attrs sympy cffi yaml psutil scipy; do
    if ! "$py" -c "import ${mod//-/_}" 2>/dev/null; then
      missing+=("$mod")
    fi
  done
  if ((${#missing[@]} == 0)); then
    return 0
  fi
  echo ""
  echo "[ATC 错误] 缺少 TBE 依赖: ${missing[*]}"
  echo "  当前 python: $(which "$py") ($("$py" --version 2>&1))"
  echo "  常见原因: pip3 装到了别的 Python 版本（如 3.10），ATC 用的是另一个 python3"
  echo "  请执行:"
  echo "    $py -m pip install attrs decorator numpy==1.26.4 cython sympy cffi pyyaml psutil protobuf==3.20.0 scipy requests absl-py"
  echo "  或: bash scripts/atc_install_deps.sh"
  return 1
}

_atc_prepare_env() {
  if [[ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]]; then
    # shellcheck disable=SC1091
    source /usr/local/Ascend/ascend-toolkit/set_env.sh
  fi
  # 优先用未激活 venv 时的 python3（CANN 文档推荐）
  local py="python3"
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo "[ATC] 提示: 当前在 venv ($VIRTUAL_ENV)，NumPy 常为 2.x，易导致 EC0010"
    echo "[ATC] 建议先 deactivate，再单独 source set_env.sh 后执行 atc"
  fi
  _atc_check_numpy "$py"
  _atc_check_tbe_deps "$py"
}

# 被其他脚本 source
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  _atc_prepare_env
fi
