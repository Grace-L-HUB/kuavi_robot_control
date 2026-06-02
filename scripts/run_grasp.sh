#!/bin/bash
# 在下位机运行抓取脚本前自动 source ROS + Kuavo 工作空间
set -e

ROS_SETUP="${ROS_SETUP:-/opt/ros/noetic/setup.bash}"
KUAVO_WS_SETUP="${KUAVO_WS_SETUP:-}"

if [ -f "$ROS_SETUP" ]; then
  # shellcheck source=/dev/null
  source "$ROS_SETUP"
else
  echo "未找到 ROS: $ROS_SETUP"
  exit 1
fi

if [ -n "$KUAVO_WS_SETUP" ] && [ -f "$KUAVO_WS_SETUP" ]; then
  # shellcheck source=/dev/null
  source "$KUAVO_WS_SETUP"
else
  SCRIPT_DIR_EARLY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for cand in \
    "$SCRIPT_DIR_EARLY/../devel/setup.bash" \
    "/home/lab/kuavo-ros-control/devel/setup.bash" \
    "$HOME/kuavo-ros-control/devel/setup.bash" \
    "/home/lab/kuavo_ros_control/devel/setup.bash"; do
    if [ -f "$cand" ]; then
      # shellcheck source=/dev/null
      source "$cand"
      echo "已 source: $cand"
      break
    fi
  done
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 脚本在 opensource/scripts 时，工作目录用 scripts 本身即可（单文件脚本无仓库依赖）
cd "$SCRIPT_DIR"

echo "PYTHONPATH=${PYTHONPATH:-<empty>}"
python3 -c "import kuavo_sdk; import motion_capture_ik; print('kuavo_sdk OK:', kuavo_sdk.__file__)" \
  || {
    echo ""
    echo "仍无法 import kuavo_sdk，请设置 Kuavo 工作空间后重试，例如："
    echo "  export KUAVO_WS_SETUP=/home/lab/kuavo-ros-control/devel/setup.bash"
    echo "  bash scripts/run_grasp.sh --hand right"
    exit 1
  }

exec python3 "$SCRIPT_DIR/grasp_from_offline_vision.py" "$@"
