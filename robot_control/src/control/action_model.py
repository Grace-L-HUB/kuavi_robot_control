"""
动作执行器（状态机驱动）

ActionExecutor 是抓取递送系统的核心编排器，通过状态机驱动
各子系统（手臂、夹爪、头部、底盘）协调完成抓取和递送动作。

使用方式：
    executor = ActionExecutor(robot_controller, config)
    executor.execute_pickup((x, y, z))           # 仅抓取
    executor.execute_delivery((x, y, z))          # 仅递送
    executor.execute_pickup_and_deliver(...)       # 完整流程
"""
import time
import logging
from typing import Tuple, Optional, Callable, Dict

from .action_state import (
    ActionState, ActionEvent, ActionContext,
    get_next_state, MAX_RETRIES
)
from .pose_library import PoseLibrary

logger = logging.getLogger(__name__)


class ActionExecutor:
    """状态机驱动的动作执行器"""

    def __init__(self, robot_controller, config: dict = None):
        """初始化动作执行器

        Args:
            robot_controller: RobotController 实例，持有 chassis/arm/gripper/head
            config: 配置字典
        """
        self.robot = robot_controller
        self.config = config or {}
        self.pose_library = PoseLibrary(config)
        self.context: Optional[ActionContext] = None

        # 从配置读取动作参数
        action_config = self.config.get("actions", {})
        self._approach_distance = action_config.get("approach_distance", 0.3)
        self._pre_grasp_height = action_config.get("pre_grasp_height", 0.15)
        self._lift_height = action_config.get("lift_height", 0.20)
        self._grasp_verify_timeout = action_config.get("grasp_verify_timeout", 3.0)
        self._max_retries = action_config.get("max_retries", 2)

        gripper_config = action_config.get("gripper", {})
        self._gripper_close_pos = gripper_config.get("default_close_position", 90)
        self._gripper_velocity = gripper_config.get("default_velocity", 50)
        self._gripper_effort = gripper_config.get("default_effort", 1.5)

        # 状态处理函数映射
        self._handlers: Dict[ActionState, Callable] = {
            ActionState.PREPARE: self._handle_prepare,
            ActionState.APPROACH: self._handle_approach,
            ActionState.ALIGN: self._handle_align,
            ActionState.HEAD_LOOK_DOWN: self._handle_head_look_down,
            ActionState.PRE_GRASP: self._handle_pre_grasp,
            ActionState.OPEN_GRIPPER: self._handle_open_gripper,
            ActionState.GRASP_DESCEND: self._handle_grasp_descend,
            ActionState.CLOSE_GRIPPER: self._handle_close_gripper,
            ActionState.VERIFY_GRASP: self._handle_verify_grasp,
            ActionState.LIFT: self._handle_lift,
            ActionState.TRANSPORT: self._handle_transport,
            ActionState.NAVIGATE: self._handle_navigate,
            ActionState.PRE_PLACE: self._handle_pre_place,
            ActionState.PLACE_DESCEND: self._handle_place_descend,
            ActionState.RELEASE: self._handle_release,
            ActionState.RETRACT: self._handle_retract,
        }

    # ==================== 公共接口 ====================

    def execute_pickup(self, target_pos: Tuple[float, float, float],
                       hand: str = "left",
                       grasp_width: int = None,
                       grasp_effort: float = None) -> bool:
        """执行完整的抓取流程（IDLE -> TRANSPORT）

        Args:
            target_pos: 物体位置 (x, y, z)
            hand: 使用哪只手
            grasp_width: 夹爪闭合位置
            grasp_effort: 夹爪力矩

        Returns:
            bool: 抓取成功返回 True
        """
        self.context = ActionContext(
            target_position=target_pos,
            grasp_hand=hand,
            grasp_width=grasp_width if grasp_width is not None else self._gripper_close_pos,
            grasp_effort=grasp_effort if grasp_effort is not None else self._gripper_effort,
            approach_distance=self._approach_distance,
            pre_grasp_height=self._pre_grasp_height,
            lift_height=self._lift_height,
        )

        logger.info(f"=== Starting PICKUP at {target_pos} with {hand} hand ===")

        # 从 IDLE 开始，运行到 TRANSPORT（抓住物体并保持搬运姿态）
        return self._run_until(
            stop_states={ActionState.TRANSPORT, ActionState.COMPLETE, ActionState.ERROR}
        )

    def execute_delivery(self, delivery_pos: Tuple[float, float, float]) -> bool:
        """执行递送流程（从 TRANSPORT 状态开始 -> COMPLETE）

        必须先执行 execute_pickup 使机器人处于 TRANSPORT 状态。

        Args:
            delivery_pos: 递送位置 (x, y, z)

        Returns:
            bool: 递送成功返回 True
        """
        if self.context is None:
            logger.error("No active context. Call execute_pickup first.")
            return False

        if self.context.current_state != ActionState.TRANSPORT:
            logger.error(f"Cannot start delivery from state {self.context.current_state}. "
                         f"Expected TRANSPORT.")
            return False

        self.context.delivery_position = delivery_pos
        logger.info(f"=== Starting DELIVERY to {delivery_pos} ===")

        # 触发 SUCCESS 事件从 TRANSPORT 转到 NAVIGATE
        return self._run_until(
            stop_states={ActionState.COMPLETE, ActionState.ERROR}
        )

    def execute_pickup_and_deliver(self,
                                    target_pos: Tuple[float, float, float],
                                    delivery_pos: Tuple[float, float, float],
                                    hand: str = "left",
                                    grasp_width: int = None,
                                    grasp_effort: float = None) -> bool:
        """执行完整的抓取-递送流程

        Args:
            target_pos: 物体位置 (x, y, z)
            delivery_pos: 递送位置 (x, y, z)
            hand: 使用哪只手
            grasp_width: 夹爪闭合位置
            grasp_effort: 夹爪力矩

        Returns:
            bool: 全流程成功返回 True
        """
        self.context = ActionContext(
            target_position=target_pos,
            delivery_position=delivery_pos,
            grasp_hand=hand,
            grasp_width=grasp_width if grasp_width is not None else self._gripper_close_pos,
            grasp_effort=grasp_effort if grasp_effort is not None else self._gripper_effort,
            approach_distance=self._approach_distance,
            pre_grasp_height=self._pre_grasp_height,
            lift_height=self._lift_height,
        )

        logger.info(f"=== Starting PICKUP-AND-DELIVER: "
                     f"{target_pos} -> {delivery_pos} ===")

        return self._run_until(
            stop_states={ActionState.COMPLETE, ActionState.ERROR}
        )

    def abort(self):
        """紧急中止当前动作并执行安全恢复"""
        logger.warning("=== ACTION ABORTED ===")
        if self.context:
            self.context.current_state = ActionState.ERROR
            self.context.error_message = "User abort"
        self._execute_error_recovery()

    def get_state(self) -> Optional[ActionState]:
        """获取当前状态"""
        return self.context.current_state if self.context else None

    # ==================== 状态机运行 ====================

    def _run_until(self, stop_states: set) -> bool:
        """运行状态机直到达到指定停止状态

        Args:
            stop_states: 停止状态集合

        Returns:
            bool: 达到非 ERROR 停止状态返回 True
        """
        # 初始转移：IDLE -> PREPARE
        if self.context.current_state == ActionState.IDLE:
            self._transition(ActionEvent.SUCCESS)

        while self.context.current_state not in stop_states:
            state = self.context.current_state

            # 检查状态超时
            if self.context.state_timed_out():
                logger.warning(f"State {state.name} timed out "
                               f"(elapsed={self.context.elapsed_in_state():.1f}s)")
                self._transition(ActionEvent.TIMEOUT)
                continue

            # 查找处理函数
            handler = self._handlers.get(state)
            if handler is None:
                logger.error(f"No handler for state {state.name}")
                self._transition(ActionEvent.FAILURE)
                continue

            # 执行处理函数
            try:
                event = handler()
                logger.debug(f"State {state.name} -> Event {event.name}")
                self._transition(event)
            except Exception as e:
                logger.error(f"Exception in handler for {state.name}: {e}")
                self.context.error_message = str(e)
                self._transition(ActionEvent.FAILURE)

        # 处理最终状态
        final_state = self.context.current_state

        if final_state == ActionState.ERROR:
            logger.error(f"Action failed: {self.context.error_message}")
            self._execute_error_recovery()
            return False

        if final_state == ActionState.COMPLETE:
            elapsed = self.context.total_elapsed()
            logger.info(f"=== Action COMPLETED in {elapsed:.1f}s "
                        f"(retries={self.context.total_retries}) ===")

        return True

    def _transition(self, event: ActionEvent):
        """执行状态转移"""
        current = self.context.current_state
        next_state = get_next_state(current, event)

        # 检查重试限制
        if next_state == current and not self.context.can_retry():
            logger.error(f"Max retries exceeded for state {current.name}")
            next_state = ActionState.ERROR
            self.context.error_message = f"Max retries exceeded in {current.name}"

        logger.info(f"Transition: {current.name} --[{event.name}]--> {next_state.name}")
        self.context.enter_state(next_state)

    # ==================== 状态处理函数 ====================

    def _handle_prepare(self) -> ActionEvent:
        """准备阶段：切换手臂到外部控制模式，头部正视"""
        # 切换手臂控制模式
        if self.robot.arm:
            if not self.robot.arm.set_control_mode(2):
                logger.warning("Failed to set arm control mode, continuing anyway")

        # 头部正视前方
        if self.robot.head:
            self.robot.head.look_forward()

        # 夹爪初始张开
        if self.robot.gripper:
            self.robot.gripper.open()

        return ActionEvent.SUCCESS

    def _handle_approach(self) -> ActionEvent:
        """接近阶段：底盘导航到目标附近"""
        if not self.robot.chassis:
            logger.warning("Chassis not available, skipping approach")
            return ActionEvent.SUCCESS

        x, y, z = self.context.target_position
        result = self.robot.chassis.robot_go_to(x, y)

        if result:
            # 等待导航完成（简化处理：等待一段时间）
            # 实际应轮询 robot_pose_speed() 检查距离
            self._wait(3.0)
            return ActionEvent.SUCCESS
        else:
            return ActionEvent.FAILURE

    def _handle_align(self) -> ActionEvent:
        """对齐阶段：底盘微调对准目标"""
        if not self.robot.chassis:
            return ActionEvent.SUCCESS

        # 微调前进到接近距离
        result = self.robot.chassis.robot_step_control(
            "ahead", self.context.approach_distance, 0.05
        )
        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_head_look_down(self) -> ActionEvent:
        """低头观察抓取区域"""
        if not self.robot.head:
            return ActionEvent.SUCCESS

        result = self.robot.head.look_down(pitch=-20.0)
        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_pre_grasp(self) -> ActionEvent:
        """预抓取：手臂移到物体上方"""
        if not self.robot.arm:
            return ActionEvent.SUCCESS

        x, y, z = self.context.target_position
        pre_z = z + self.context.pre_grasp_height

        # 尝试 IK 笛卡尔控制
        result = self.robot.arm.go_to_cartesian(
            x, y, pre_z,
            hand=self.context.grasp_hand,
            duration=2.0
        )

        if not result:
            # IK 失败，回退到预定义姿态
            logger.warning("IK failed for pre-grasp, falling back to pose library")
            pose = self.pose_library.get("pre_grasp_front")
            if pose:
                result = self.robot.arm.set_target_poses_timed(pose, duration=2.0)
                self._wait(2.5)

        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_open_gripper(self) -> ActionEvent:
        """张开夹爪"""
        if not self.robot.gripper:
            return ActionEvent.SUCCESS

        result = self.robot.gripper.open()
        if result:
            self._wait(0.5)  # 等待夹爪完全张开
        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_grasp_descend(self) -> ActionEvent:
        """下降到抓取高度"""
        if not self.robot.arm:
            return ActionEvent.SUCCESS

        x, y, z = self.context.target_position

        # 使用慢速下降
        arm_config = self.config.get("arm", {})
        slow_duration = arm_config.get("slow_duration", 3.0)

        result = self.robot.arm.go_to_cartesian(
            x, y, z,
            hand=self.context.grasp_hand,
            duration=slow_duration
        )

        if not result:
            # IK 失败，回退到预定义抓取姿态
            logger.warning("IK failed for grasp descent, falling back to pose library")
            pose = self.pose_library.get("grasp_low")
            if pose:
                result = self.robot.arm.set_target_poses_timed(pose, duration=slow_duration)
                self._wait(slow_duration + 0.5)

        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_close_gripper(self) -> ActionEvent:
        """闭合夹爪"""
        if not self.robot.gripper:
            return ActionEvent.SUCCESS

        result = self.robot.gripper.close(
            position=self.context.grasp_width,
            velocity=self._gripper_velocity,
            effort=self.context.grasp_effort
        )
        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_verify_grasp(self) -> ActionEvent:
        """验证抓取：等待夹爪确认抓住物体"""
        if not self.robot.gripper:
            return ActionEvent.GRASP_CONFIRMED

        grasped = self.robot.gripper.wait_for_grasp(
            hand=self.context.grasp_hand,
            timeout=self._grasp_verify_timeout
        )

        if grasped:
            logger.info("Grasp verified successfully")
            return ActionEvent.GRASP_CONFIRMED
        else:
            if self.context.can_retry():
                logger.warning(f"Grasp failed, retry {self.context.retry_count + 1}/"
                               f"{MAX_RETRIES.get(ActionState.VERIFY_GRASP, 0)}")
                return ActionEvent.GRASP_FAILED
            else:
                logger.error("Grasp failed after all retries")
                return ActionEvent.FAILURE

    def _handle_lift(self) -> ActionEvent:
        """抬起手臂"""
        if not self.robot.arm:
            return ActionEvent.SUCCESS

        x, y, z = self.context.target_position
        lift_z = z + self.context.lift_height

        result = self.robot.arm.go_to_cartesian(
            x, y, lift_z,
            hand=self.context.grasp_hand,
            duration=2.0
        )

        if not result:
            # 回退到搬运姿态
            pose = self.pose_library.get("transport")
            if pose:
                result = self.robot.arm.set_target_poses_timed(pose, duration=2.0)
                self._wait(2.5)

        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_transport(self) -> ActionEvent:
        """转到搬运姿态"""
        if not self.robot.arm:
            return ActionEvent.SUCCESS

        # 切到搬运姿态
        pose = self.pose_library.get("transport")
        if pose:
            self.robot.arm.set_target_poses_timed(pose, duration=2.0)
            self._wait(2.5)

        # 头部正视前方
        if self.robot.head:
            self.robot.head.look_forward()

        return ActionEvent.SUCCESS

    def _handle_navigate(self) -> ActionEvent:
        """导航到递送位置"""
        if not self.robot.chassis:
            return ActionEvent.SUCCESS

        if self.context.delivery_position is None:
            logger.error("No delivery position specified")
            return ActionEvent.FAILURE

        x, y, z = self.context.delivery_position
        result = self.robot.chassis.robot_go_to(x, y)

        if result:
            self._wait(3.0)
            return ActionEvent.SUCCESS
        else:
            return ActionEvent.FAILURE

    def _handle_pre_place(self) -> ActionEvent:
        """预放置：手臂移到放置点上方"""
        if not self.robot.arm or self.context.delivery_position is None:
            return ActionEvent.SUCCESS

        x, y, z = self.context.delivery_position
        pre_z = z + self.context.pre_grasp_height

        result = self.robot.arm.go_to_cartesian(
            x, y, pre_z,
            hand=self.context.grasp_hand,
            duration=2.0
        )

        if not result:
            pose = self.pose_library.get("deliver_front")
            if pose:
                result = self.robot.arm.set_target_poses_timed(pose, duration=2.0)
                self._wait(2.5)

        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_place_descend(self) -> ActionEvent:
        """下降到放置高度"""
        if not self.robot.arm or self.context.delivery_position is None:
            return ActionEvent.SUCCESS

        x, y, z = self.context.delivery_position
        arm_config = self.config.get("arm", {})
        slow_duration = arm_config.get("slow_duration", 3.0)

        result = self.robot.arm.go_to_cartesian(
            x, y, z,
            hand=self.context.grasp_hand,
            duration=slow_duration
        )

        if not result:
            pose = self.pose_library.get("grasp_low")
            if pose:
                result = self.robot.arm.set_target_poses_timed(pose, duration=slow_duration)
                self._wait(slow_duration + 0.5)

        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_release(self) -> ActionEvent:
        """释放物体"""
        if not self.robot.gripper:
            return ActionEvent.SUCCESS

        result = self.robot.gripper.open()
        if result:
            self._wait(0.5)
        return ActionEvent.SUCCESS if result else ActionEvent.FAILURE

    def _handle_retract(self) -> ActionEvent:
        """回收手臂到初始位"""
        if self.robot.arm:
            # 先回到 ready 姿态
            ready_pose = self.pose_library.get("ready")
            if ready_pose:
                self.robot.arm.set_target_poses_timed(ready_pose, duration=2.0)
                self._wait(2.5)

            # 再回到 home
            self.robot.arm.home()
            self._wait(2.5)

            # 切回保持模式
            self.robot.arm.set_control_mode(0)

        # 头部正视
        if self.robot.head:
            self.robot.head.look_forward()

        return ActionEvent.SUCCESS

    # ==================== 错误恢复 ====================

    def _execute_error_recovery(self):
        """执行错误恢复流程：安全释放 -> 回收手臂 -> 停止底盘"""
        logger.warning("=== Executing error recovery ===")

        # 1. 安全释放夹爪
        try:
            if self.robot.gripper:
                self.robot.gripper.open()
                self._wait(0.5)
        except Exception as e:
            logger.error(f"Error recovery - gripper open failed: {e}")

        # 2. 回收手臂
        try:
            if self.robot.arm:
                home_pose = self.pose_library.get("home")
                if home_pose:
                    self.robot.arm.set_target_poses_timed(home_pose, duration=3.0)
                    self._wait(3.5)
                self.robot.arm.set_control_mode(0)
        except Exception as e:
            logger.error(f"Error recovery - arm retract failed: {e}")

        # 3. 头部归位
        try:
            if self.robot.head:
                self.robot.head.look_forward()
        except Exception as e:
            logger.error(f"Error recovery - head reset failed: {e}")

        # 4. 停止底盘
        try:
            if self.robot.chassis:
                self.robot.chassis.robot_stop()
        except Exception as e:
            logger.error(f"Error recovery - chassis stop failed: {e}")

        # 重置上下文
        if self.context:
            self.context.current_state = ActionState.IDLE

        logger.warning("=== Error recovery completed ===")

    # ==================== 工具方法 ====================

    @staticmethod
    def _wait(seconds: float):
        """等待指定秒数（兼容 ROS 和非 ROS 环境）"""
        try:
            import rospy
            rospy.sleep(seconds)
        except (ImportError, Exception):
            time.sleep(seconds)
