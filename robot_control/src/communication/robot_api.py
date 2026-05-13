from .websocket_client import WooshWebSocketClient
import logging

logger = logging.getLogger(__name__)

class WooshApi(WooshWebSocketClient):
    def robot_state(self) -> dict:
        """获取机器人状态
        
        Returns:
            dict: 包含机器人状态信息
        """
        try:
            result = self.request("woosh.robot.RobotState")
            if result is None:
                logger.error("Failed to get robot state")
                return None
            return result.get("body", {})
        except Exception as e:
            logger.error(f"Error getting robot state: {e}")
            return None
    
    def robot_pose_speed(self) -> dict:
        """获取机器人位置和速度
        
        Returns:
            dict: 包含 x, y, theta 和线速度、角速度
        """
        try:
            result = self.request("woosh.robot.PoseSpeed")
            if result is None:
                logger.error("Failed to get robot pose and speed")
                return None
            return result.get("body", {})
        except Exception as e:
            logger.error(f"Error getting robot pose and speed: {e}")
            return None
    
    def robot_battery(self) -> dict:
        """获取电池信息
        
        Returns:
            dict: 包含电量百分比、电压、电流等
        """
        try:
            result = self.request("woosh.robot.Battery")
            if result is None:
                logger.error("Failed to get battery info")
                return None
            return result.get("body", {})
        except Exception as e:
            logger.error(f"Error getting battery info: {e}")
            return None
    
    def robot_go_to(self, x: float, y: float, theta: float = 0) -> bool:
        """导航到指定位置（需要先建图）
        
        Args:
            x: 目标 X 坐标（米）
            y: 目标 Y 坐标（米）
            theta: 目标朝向角度（弧度）
        
        Returns:
            bool: 成功返回 True
        """
        try:
            body = {
                "pose": {
                    "x": x,
                    "y": y,
                    "theta": theta
                }
            }
            result = self.request("woosh.robot.PlanNavPath", body)
            if result is None or not result.get("ok", False):
                logger.error("Failed to navigate to position")
                return False
            return True
        except Exception as e:
            logger.error(f"Error navigating to position: {e}")
            return False
    
    def robot_twist(self, linear: float, angular: float) -> bool:
        """速度控制
        
        Args:
            linear: 线速度（米/秒），正数为前进
            angular: 角速度（弧度/秒），正数为左转
        """
        try:
            body = {
                "linear": linear,
                "angular": angular
            }
            result = self.request("woosh.robot.Twist", body)
            if result is None or not result.get("ok", False):
                logger.error("Failed to set robot twist")
                return False
            return True
        except Exception as e:
            logger.error(f"Error setting robot twist: {e}")
            return False
    
    def robot_step_control(self, direction: str, distance: float, speed: float = 0.15) -> bool:
        """单步移动控制
        
        Args:
            direction: 方向，可选 "ahead", "back", "left", "right", "rotate"
            distance: 移动距离（米）或旋转角度（弧度）
            speed: 移动速度（米/秒），最大 0.2
        
        Returns:
            bool: 成功返回 True
        """
        try:
            # 根据方向计算线速度和角速度
            if direction == "ahead":
                linear = speed
                angular = 0
            elif direction == "back":
                linear = -speed
                angular = 0
            elif direction == "left":
                linear = 0
                angular = speed * 2  # 旋转速度
            elif direction == "right":
                linear = 0
                angular = -speed * 2
            elif direction == "rotate":
                linear = 0
                angular = speed * 2 if distance > 0 else -speed * 2
            else:
                logger.error(f"Invalid direction: {direction}")
                return False
            
            # 执行移动
            result = self.robot_twist(linear, angular)
            
            # 根据距离计算移动时间
            if direction in ["ahead", "back"]:
                time = abs(distance) / speed
                import time as time_module
                time_module.sleep(time)
                # 停止移动
                self.robot_twist(0, 0)
            elif direction in ["left", "right", "rotate"]:
                time = abs(distance) / (speed * 2)
                import time as time_module
                time_module.sleep(time)
                # 停止移动
                self.robot_twist(0, 0)
            
            return result
        except Exception as e:
            logger.error(f"Error in step control: {e}")
            return False
    
    def robot_exec_task(self, target: dict, poses: list) -> bool:
        """执行导航任务
        
        Args:
            target: 目标点 {"x": 0, "y": 0, "theta": 0}
            poses: 路径点列表 [{"x": 0, "y": 0, "theta": 0}, ...]
        
        Returns:
            bool: 成功返回 True
        """
        try:
            body = {
                "target": target,
                "poses": poses
            }
            result = self.request("woosh.robot.ExecTask", body)
            if result is None or not result.get("ok", False):
                logger.error("Failed to execute task")
                return False
            return True
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return False
    
    def robot_action_order(self, order: int) -> bool:
        """控制任务执行状态
        
        Args:
            order: 1=开始, 2=暂停, 3=继续, 4=取消
        """
        try:
            body = {"order": order}
            result = self.request("woosh.robot.ActionOrder", body)
            if result is None or not result.get("ok", False):
                logger.error(f"Failed to send action order: {order}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error sending action order: {e}")
            return False
    
    def robot_speak(self, text: str) -> bool:
        """语音播报
        
        Args:
            text: 要播报的文字内容
        """
        try:
            body = {"text": text}
            result = self.request("woosh.robot.Speak", body)
            if result is None or not result.get("ok", False):
                logger.error("Failed to speak")
                return False
            return True
        except Exception as e:
            logger.error(f"Error speaking: {e}")
            return False
    
    def robot_stop(self) -> bool:
        """立即停止机器人移动"""
        try:
            return self.robot_twist(0, 0)
        except Exception as e:
            logger.error(f"Error stopping robot: {e}")
            return False

    def robot_lift_control(self, direction: str, height: float) -> bool:
        """控制升降模组

        Args:
            direction: "up" 或 "down"
            height: 升降高度（米），取绝对值后根据方向设正负

        Returns:
            bool: 成功返回 True
        """
        try:
            height = abs(height)
            if direction == "down":
                height = -height
            elif direction != "up":
                logger.error(f"Invalid lift direction: {direction}. Use 'up' or 'down'")
                return False

            body = {
                "lift_control2": {
                    "height": height,
                    "action": 1
                }
            }
            result = self.request("woosh.ros.CallAction", body)
            if result is None:
                logger.error(f"Failed to control lift: {direction} {abs(height)}m")
                return False
            logger.info(f"Lift control: {direction} {abs(height)}m")
            return True
        except Exception as e:
            logger.error(f"Error controlling lift: {e}")
            return False
