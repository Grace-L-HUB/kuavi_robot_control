# 第三方代码来源

以下目录内容来自乐聚 **kuavo-ros-opensource**（Kuavo 机器人开源控制栈），仅保留 `robot_control` 运行所需部分：

| 本仓库路径 | 上游 |
|------------|------|
| `robot_control/ros_ws/src/kuavo_msgs/` | `kuavo-ros-opensource/src/kuavo_msgs` |
| `robot_control/vendor/kuavo_sdk_reference/` | `kuavo-ros-opensource/src/kuavo_sdk`（示例脚本子集） |

未包含 `humanoid_controllers`、`motion_capture_ik` 等重型包；IK 服务仍在机器人下位机运行。

请根据你使用的上游版本同步更新，并保持与实机固件版本一致。
