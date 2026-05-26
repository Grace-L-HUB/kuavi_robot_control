# 内置 ROS 工作空间

本目录包含从 [kuavo-ros-opensource](https://gitee.com/leju-robot/kuavo_opensource) 提取的 **`kuavo_msgs`** 包，供 `robot_control` 在 Atlas 上本地编译，无需再单独克隆整仓控制栈。

## 首次编译

```bash
cd robot_control
bash scripts/build_ros_msgs.sh
```

## 每次运行前

```bash
source robot_control/scripts/setup_ros_env.sh
# 或
source robot_control/ros_ws/devel/setup.bash
```

## 目录说明

| 路径 | 说明 |
|------|------|
| `src/kuavo_msgs/` | Kuavo 消息/服务定义（与官方 control 栈一致） |
| `devel/` | 编译产物（已 gitignore，需在板上生成） |
| `build/` | 编译缓存（已 gitignore） |

IK/FK **节点**仍在机器人下位机运行；此处仅提供 Python 调用服务所需的类型定义。
