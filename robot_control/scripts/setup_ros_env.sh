#!/usr/bin/env bash
# 加载 ROS Noetic + 本仓库内置 kuavo_msgs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_CONTROL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_WS="${ROBOT_CONTROL_DIR}/ros_ws"

if [ -f /opt/ros/noetic/setup.bash ]; then
  # shellcheck source=/dev/null
  source /opt/ros/noetic/setup.bash
else
  echo "WARN: /opt/ros/noetic/setup.bash not found"
fi

if [ -f "${ROS_WS}/devel/setup.bash" ]; then
  # shellcheck source=/dev/null
  source "${ROS_WS}/devel/setup.bash"
  echo "Sourced ${ROS_WS}/devel/setup.bash (kuavo_msgs)"
else
  echo "WARN: kuavo_msgs not built. Run: bash robot_control/scripts/build_ros_msgs.sh"
fi

# 默认 Master（可在环境中覆盖）
export ROS_MASTER_URI="${ROS_MASTER_URI:-http://169.254.128.2:11311}"
