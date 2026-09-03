"""USV 单体实体模型。

本模块只负责单艘 USV 的自身状态、二维运动学和动作约束，
不负责地图、奖励、碰撞判定、Observation 构造或强化学习训练。
"""

from __future__ import annotations

import math
from typing import Sequence, Union

import numpy as np


class UsvAgent:
    """表示一艘采用二维一阶运动学抽象的 USV。

    V1.0 将动作解释为目标线速度和目标角速度。底层速度控制器被假设为
    可以在一个仿真步内理想跟踪限幅后的速度指令，因此本类不模拟惯性、
    水动力、推进器动力学或控制延迟。
    """

    def __init__(
        self,
        agent_id: Union[str, int],
        *,
        v_min: float = 0.0,
        v_max: float = 2.0,
        omega_max: float = math.pi / 2.0,
        collision_radius: float = 1.0,
    ) -> None:
        """创建 USV 实体并设置可覆盖的 V1.0 默认约束。

        参数：
            agent_id: 当前 USV 的唯一标识，由上层 Environment 管理。
            v_min: 线速度下限，单位为 m/s；V1.0 默认不允许倒车。
            v_max: 线速度上限，单位为 m/s。
            omega_max: 角速度绝对值上限，单位为 rad/s。
            collision_radius: USV 的圆形几何近似半径，单位为 m。

        注意：具体速度范围尚未作为实验全局配置冻结，这里的默认值只是
        可运行的实体层默认值，后续可以由 Environment 或配置文件覆盖。
        """
        v_min_value = self._as_finite_float(v_min, "v_min")
        v_max_value = self._as_finite_float(v_max, "v_max")
        omega_max_value = self._as_finite_float(omega_max, "omega_max")
        collision_radius_value = self._as_finite_float(
            collision_radius,
            "collision_radius",
        )

        if v_min_value > v_max_value:
            raise ValueError("v_min 不能大于 v_max")
        if omega_max_value <= 0.0:
            raise ValueError("omega_max 必须大于 0")
        if collision_radius_value <= 0.0:
            raise ValueError("collision_radius 必须大于 0")

        self.agent_id = agent_id
        self.v_min = v_min_value
        self.v_max = v_max_value
        self.omega_max = omega_max_value
        self.collision_radius = collision_radius_value

        # 实体初始状态统一设为原点、零航向和零速度；Episode 开始时由 reset 重置。
        self.x = 0.0
        self.y = 0.0
        self.psi = 0.0
        self.v = 0.0
        self.omega = 0.0

    def reset(self, init_x: float, init_y: float, init_psi: float) -> None:
        """根据 Environment 提供的初始位姿重置一个 Episode。

        重置后位置使用传入的 `init_x` 和 `init_y`，航向角会被归一化到
        `[-pi, pi)`，线速度和角速度均清零。Agent 不保存固定起点。
        """
        # 入口状态必须是有限数值，避免非法状态进入后续运动学计算。
        self.x = self._as_finite_float(init_x, "init_x")
        self.y = self._as_finite_float(init_y, "init_y")
        self.psi = self._normalize_angle(init_psi)
        self.v = 0.0
        self.omega = 0.0

    def apply_action(
        self,
        action: Union[Sequence[float], np.ndarray],
        dt: float,
    ) -> None:
        """执行一个仿真步的速度动作并更新自身运动状态。

        参数：
            action: 长度为 2 的动作 `[v_cmd, omega_cmd]`。
            dt: 本次仿真步的时间跨度，单位为 s，由 Environment 传入。

        计算顺序固定为：先使用更新前的航向角计算位置，再使用角速度更新
        航向角。动作会先经过速度约束，Agent 不负责判断碰撞或计算奖励。
        """
        dt_value = self._as_finite_float(dt, "dt")
        if dt_value <= 0.0:
            raise ValueError("dt 必须是大于 0 的有限数值")

        try:
            action_array = np.asarray(action, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError("action 必须是包含两个数值的序列") from exc

        if action_array.shape != (2,):
            raise ValueError("action 必须是一维且恰好包含 [v_cmd, omega_cmd] 两个元素")
        if not np.all(np.isfinite(action_array)):
            raise ValueError("action 中不能包含 NaN 或 Inf")

        v_cmd, omega_cmd = action_array

        # 先执行动作限幅，保存的 v 和 omega 表示实际执行值而非原始指令值。
        self.v = float(np.clip(v_cmd, self.v_min, self.v_max))
        self.omega = float(np.clip(omega_cmd, -self.omega_max, self.omega_max))

        # 将已限幅的速度指令交给运动学积分函数，保持动作处理与状态更新分层。
        self._integrate_kinematics(dt_value)

    def get_state(self) -> np.ndarray:
        """返回自身状态 `[x, y, psi, v, omega]` 的独立副本。

        返回新数组可以避免调用方修改返回值时意外改变 Agent 的内部状态。
        该状态是实体内部 State，不是 PPO 使用的 Observation。
        """
        return np.array(
            [self.x, self.y, self.psi, self.v, self.omega],
            dtype=np.float64,
        )

    def get_pos(self) -> np.ndarray:
        """返回当前位置 `[x, y]` 的独立副本。

        该方法只提供几何位置，不执行碰撞检测；碰撞判定由 Environment 负责。
        """
        return np.array([self.x, self.y], dtype=np.float64)

    def _integrate_kinematics(self, dt: float) -> None:
        """按照 V1.0 一阶二维运动学推进一个时间步。

        该方法使用当前已经限幅的 `v` 和 `omega` 更新状态。
        先使用更新前的 `psi` 计算位置，再使用角速度更新 `psi`，最后将航向角
        归一化到 `[-pi, pi)`。本方法不负责动作限幅、碰撞判定或奖励计算。
        """
        # 该私有方法也保留基本时间步检查，避免被其他内部调用传入非法 dt。
        dt_value = self._as_finite_float(dt, "dt")
        if dt_value <= 0.0:
            raise ValueError("dt 必须是大于 0 的有限数值")

        # 必须缓存更新前的航向角，确保位置使用旧航向而不是新航向计算。
        current_psi = self.psi
        delta_x = self.v * math.cos(current_psi) * dt_value
        delta_y = self.v * math.sin(current_psi) * dt_value
        delta_psi = self.omega * dt_value

        # 先更新位置，再更新航向角，严格遵守 V1.0 离散化约定。
        self.x += delta_x
        self.y += delta_y
        self.psi = self._normalize_angle(current_psi + delta_psi)

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """将航向角归一化到半开区间 `[-pi, pi)`。

        使用模运算统一处理超过一个完整周期的输入，并将 `pi` 归一化为
        `-pi`，从而避免同一方向出现两种数值表示。
        """
        angle_value = UsvAgent._as_finite_float(angle, "angle")
        return (angle_value + math.pi) % (2.0 * math.pi) - math.pi

    @staticmethod
    def _as_finite_float(value: float, name: str) -> float:
        """将输入转换为有限浮点数，并为非法输入提供统一错误。

        该辅助方法只负责数值入口校验，不承担动作限幅、碰撞判定或奖励计算。
        """
        try:
            value_float = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} 必须是数值") from exc

        if not math.isfinite(value_float):
            raise ValueError(f"{name} 必须是有限数值")
        return value_float


__all__ = ["UsvAgent"]
