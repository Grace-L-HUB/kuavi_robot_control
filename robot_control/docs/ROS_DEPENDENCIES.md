# ROS 依赖说明

`robot_control` 已内置 **`ros_ws/src/kuavo_msgs`**（来自 kuavo-ros-opensource），无需再把整仓 opensource 拷到 Atlas。

## 一次性编译（Atlas / 开发机）

```bash
cd robot_control
bash scripts/build_ros_msgs.sh
```

需要：ROS Noetic、`catkin build` 或 `catkin_make`。

## 每次运行前

```bash
source robot_control/scripts/setup_ros_env.sh
export ROS_MASTER_URI=http://169.254.128.2:11311   # 可按实机修改

python3 -c "from kuavo_msgs.srv import changeArmCtrlMode; print('ok')"
python3 scripts/test_arm.py
```

## 目录结构

```text
robot_control/
  ros_ws/src/kuavo_msgs/     # 消息/服务定义（已纳入 git）
  ros_ws/devel/              # 编译输出（gitignore，本地生成）
  vendor/kuavo_sdk_reference/  # 官方示例脚本（只读对照）
  src/utils/kuavo_ros_types.py # 统一 import kuavo_msgs
```

## 仍在机器人上运行的部分

| 组件 | 位置 |
|------|------|
| IK/FK 节点 `/ik/*` | 下位机 kuavo-ros-control |
| 手臂/夹爪执行 | 下位机主程序 |

Atlas 只需 **消息类型** + **发布 Topic / 调用 Service**。

## 与上游同步

更新 `kuavo_msgs` 时，从同版本 `kuavo-ros-opensource` 覆盖 `ros_ws/src/kuavo_msgs/` 后重新 `build_ros_msgs.sh`。详见 `vendor/ATTRIBUTION.md`。
