#!/usr/bin/env bash
# Atlas 200I：先 venv，再 CANN，并确保 acl Python 包在 PYTHONPATH 中
# 用法: source scripts/activate_kuavi_atlas.sh

_KUAVI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1) Python 虚拟环境
if [[ -f "$HOME/kuavi/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/kuavi/bin/activate"
fi

# 2) CANN 工具链 — 官方文档要求每次运行前 source set_env.sh
# 参考: https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/850alpha002/appdevg/acldevg/aclpythondevg_0006.html
if [[ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
else
  echo "[warn] 未找到 /usr/local/Ascend/ascend-toolkit/set_env.sh"
fi

# 3) 官方 set_env 会设置 ASCEND_TOOLKIT_HOME 与 PYTHONPATH；venv 可能覆盖，此处再显式追加
if [[ -n "${ASCEND_TOOLKIT_HOME:-}" ]]; then
  export PYTHONPATH="${ASCEND_TOOLKIT_HOME}/python/site-packages:${ASCEND_TOOLKIT_HOME}/opp/built-in/op_impl/ai_core/tbe:${PYTHONPATH:-}"
  export LD_LIBRARY_PATH="${ASCEND_TOOLKIT_HOME}/lib64:${LD_LIBRARY_PATH:-}"
fi

export PYTHONPATH="$_KUAVI_ROOT:${PYTHONPATH:-}"
cd "$_KUAVI_ROOT" || exit 1

echo "[kuavi-atlas] cwd=$PWD"
echo "[kuavi-atlas] ASCEND_TOOLKIT_HOME=${ASCEND_TOOLKIT_HOME:-未设置}"
echo "[kuavi-atlas] python=$(which python3) version=$(python3 --version 2>&1)"
python3 -c "import acl; print('[kuavi-atlas] import acl OK, soc=', acl.get_soc_name())" 2>/dev/null \
  || echo "[kuavi-atlas] import acl 失败 — 见文档「应用开发环境准备」检查 PYTHONPATH 与 Python 版本"
