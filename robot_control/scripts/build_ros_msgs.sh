#!/usr/bin/env bash
# 编译内置 ros_ws 中的 kuavo_msgs（仅需 message_generation）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_CONTROL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_WS="${ROBOT_CONTROL_DIR}/ros_ws"

if [ ! -f /opt/ros/noetic/setup.bash ]; then
  echo "ERROR: ROS Noetic not found. Install: ros-noetic-desktop or ros-noetic-ros-base"
  exit 1
fi

# shellcheck source=/dev/null
source /opt/ros/noetic/setup.bash

if ! command -v catkin build >/dev/null 2>&1 && ! command -v catkin_make >/dev/null 2>&1; then
  echo "ERROR: catkin_tools or catkin_make required"
  exit 1
fi

cd "${ROS_WS}"
if command -v catkin build >/dev/null 2>&1; then
  catkin build kuavo_msgs
else
  catkin_make
fi

echo ""
echo "Done. Source before running robot_control:"
echo "  source ${ROS_WS}/devel/setup.bash"
