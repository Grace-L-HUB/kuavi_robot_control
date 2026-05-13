"""
动作状态机定义

定义抓取递送动作的状态枚举、事件枚举、状态转移表和动作上下文。
纯数据文件，无硬件依赖，可独立测试。
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Tuple, Optional
import time


class ActionState(Enum):
    """动作状态枚举"""
    IDLE = auto()             # 空闲
    PREPARE = auto()          # 准备：切换手臂外部控制模式，头部归位
    APPROACH = auto()         # 接近：底盘导航到目标附近
    ALIGN = auto()            # 对齐：底盘微调对准物体
    HEAD_LOOK_DOWN = auto()   # 低头：头部低头观察抓取区域
    PRE_GRASP = auto()        # 预抓取：手臂移到物体上方
    OPEN_GRIPPER = auto()     # 张开夹爪
    GRASP_DESCEND = auto()    # 下降抓取：手臂下降到抓取高度
    CLOSE_GRIPPER = auto()    # 闭合夹爪
    VERIFY_GRASP = auto()     # 验证抓取：等待夹爪状态确认
    LIFT = auto()             # 抬起：抬起手臂
    TRANSPORT = auto()        # 搬运：手臂转到搬运姿态
    NAVIGATE = auto()         # 导航：底盘导航到递送位置
    PRE_PLACE = auto()        # 预放置：手臂移到放置点上方
    PLACE_DESCEND = auto()    # 下降放置：手臂下降到放置高度
    RELEASE = auto()          # 释放：张开夹爪释放物体
    RETRACT = auto()          # 回收：手臂回到初始位
    COMPLETE = auto()         # 完成
    ERROR = auto()            # 错误


class ActionEvent(Enum):
    """动作事件枚举"""
    SUCCESS = auto()          # 当前步骤成功完成
    FAILURE = auto()          # 当前步骤失败
    TIMEOUT = auto()          # 当前步骤超时
    GRASP_CONFIRMED = auto()  # 夹爪状态确认抓取 (state=3)
    GRASP_FAILED = auto()     # 夹爪抓取失败 (state=-1 或超时)
    ABORT = auto()            # 外部中止请求


# 状态转移表: (当前状态, 事件) -> 下一个状态
TRANSITIONS = {
    # 正常流程：抓取阶段
    (ActionState.IDLE, ActionEvent.SUCCESS): ActionState.PREPARE,
    (ActionState.PREPARE, ActionEvent.SUCCESS): ActionState.APPROACH,
    (ActionState.APPROACH, ActionEvent.SUCCESS): ActionState.ALIGN,
    (ActionState.ALIGN, ActionEvent.SUCCESS): ActionState.HEAD_LOOK_DOWN,
    (ActionState.HEAD_LOOK_DOWN, ActionEvent.SUCCESS): ActionState.PRE_GRASP,
    (ActionState.PRE_GRASP, ActionEvent.SUCCESS): ActionState.OPEN_GRIPPER,
    (ActionState.OPEN_GRIPPER, ActionEvent.SUCCESS): ActionState.GRASP_DESCEND,
    (ActionState.GRASP_DESCEND, ActionEvent.SUCCESS): ActionState.CLOSE_GRIPPER,
    (ActionState.CLOSE_GRIPPER, ActionEvent.SUCCESS): ActionState.VERIFY_GRASP,

    # 抓取验证分支
    (ActionState.VERIFY_GRASP, ActionEvent.GRASP_CONFIRMED): ActionState.LIFT,
    (ActionState.VERIFY_GRASP, ActionEvent.GRASP_FAILED): ActionState.OPEN_GRIPPER,  # 重试

    # 正常流程：搬运和递送阶段
    (ActionState.LIFT, ActionEvent.SUCCESS): ActionState.TRANSPORT,
    (ActionState.TRANSPORT, ActionEvent.SUCCESS): ActionState.NAVIGATE,
    (ActionState.NAVIGATE, ActionEvent.SUCCESS): ActionState.PRE_PLACE,
    (ActionState.PRE_PLACE, ActionEvent.SUCCESS): ActionState.PLACE_DESCEND,
    (ActionState.PLACE_DESCEND, ActionEvent.SUCCESS): ActionState.RELEASE,
    (ActionState.RELEASE, ActionEvent.SUCCESS): ActionState.RETRACT,
    (ActionState.RETRACT, ActionEvent.SUCCESS): ActionState.COMPLETE,

    # 超时处理：与失败相同进入错误状态
    (ActionState.APPROACH, ActionEvent.TIMEOUT): ActionState.ERROR,
    (ActionState.NAVIGATE, ActionEvent.TIMEOUT): ActionState.ERROR,
}

# 每个状态的默认超时时间（秒）
STATE_TIMEOUTS = {
    ActionState.PREPARE: 5.0,
    ActionState.APPROACH: 60.0,
    ActionState.ALIGN: 10.0,
    ActionState.HEAD_LOOK_DOWN: 3.0,
    ActionState.PRE_GRASP: 10.0,
    ActionState.OPEN_GRIPPER: 5.0,
    ActionState.GRASP_DESCEND: 10.0,
    ActionState.CLOSE_GRIPPER: 5.0,
    ActionState.VERIFY_GRASP: 5.0,
    ActionState.LIFT: 10.0,
    ActionState.TRANSPORT: 5.0,
    ActionState.NAVIGATE: 60.0,
    ActionState.PRE_PLACE: 10.0,
    ActionState.PLACE_DESCEND: 10.0,
    ActionState.RELEASE: 5.0,
    ActionState.RETRACT: 10.0,
}

# 每个状态的最大重试次数
MAX_RETRIES = {
    ActionState.VERIFY_GRASP: 2,  # 抓取验证允许重试2次
    ActionState.PRE_GRASP: 1,
    ActionState.GRASP_DESCEND: 1,
}


def get_next_state(current: ActionState, event: ActionEvent) -> ActionState:
    """根据当前状态和事件获取下一个状态

    Args:
        current: 当前状态
        event: 触发的事件

    Returns:
        下一个状态。ABORT 事件始终进入 ERROR；
        未定义的转移在 FAILURE 事件时进入 ERROR。
    """
    if event == ActionEvent.ABORT:
        return ActionState.ERROR

    next_state = TRANSITIONS.get((current, event))
    if next_state is not None:
        return next_state

    # 未定义的转移：FAILURE/TIMEOUT 进入 ERROR
    if event in (ActionEvent.FAILURE, ActionEvent.TIMEOUT):
        return ActionState.ERROR

    return ActionState.ERROR


@dataclass
class ActionContext:
    """动作执行上下文，携带整个动作生命周期的参数和状态"""

    # 目标位置
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 物体 (x, y, z)
    delivery_position: Optional[Tuple[float, float, float]] = None  # 递送位置

    # 抓取参数
    grasp_hand: str = "left"          # 使用哪只手: "left" / "right"
    grasp_width: int = 90             # 夹爪闭合位置 0-100
    grasp_velocity: int = 50          # 夹爪速度 0-100
    grasp_effort: float = 1.5         # 夹爪力矩 1.0-2.0A

    # 运动参数
    approach_distance: float = 0.3    # 接近距离 (m)
    pre_grasp_height: float = 0.15    # 预抓取高度偏移 (m)
    lift_height: float = 0.20         # 抬起高度偏移 (m)

    # 状态机运行时数据
    current_state: ActionState = ActionState.IDLE
    retry_count: int = 0
    total_retries: int = 0
    error_message: Optional[str] = None

    # 时间戳
    start_time: float = field(default_factory=time.time)
    state_entry_time: float = field(default_factory=time.time)

    def enter_state(self, state: ActionState):
        """进入新状态，更新时间戳和重试计数"""
        if state == self.current_state:
            # 重试同一状态
            self.retry_count += 1
            self.total_retries += 1
        else:
            self.retry_count = 0
        self.current_state = state
        self.state_entry_time = time.time()
        self.error_message = None

    def can_retry(self) -> bool:
        """检查当前状态是否还能重试"""
        max_retry = MAX_RETRIES.get(self.current_state, 0)
        return self.retry_count < max_retry

    def elapsed_in_state(self) -> float:
        """当前状态已经过的时间（秒）"""
        return time.time() - self.state_entry_time

    def total_elapsed(self) -> float:
        """动作启动以来的总时间（秒）"""
        return time.time() - self.start_time

    def state_timed_out(self) -> bool:
        """检查当前状态是否超时"""
        timeout = STATE_TIMEOUTS.get(self.current_state, 10.0)
        return self.elapsed_in_state() > timeout
