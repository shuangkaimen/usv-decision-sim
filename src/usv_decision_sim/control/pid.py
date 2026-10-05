"""PID 控制器与二维航点控制组合器。"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


class PidController:
    """对单个标量误差执行离散 PID 控制。"""

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        *,
        output_min: float,
        output_max: float,
    ) -> None:
        """创建具有显式输出范围的 PID 控制器。"""
        self.kp = self._as_finite_float(kp, "kp")
        self.ki = self._as_finite_float(ki, "ki")
        self.kd = self._as_finite_float(kd, "kd")
        self.output_min = self._as_finite_float(output_min, "output_min")
        self.output_max = self._as_finite_float(output_max, "output_max")

        if self.output_min > self.output_max:
            raise ValueError("output_min 不能大于 output_max")

        self._integral = 0.0
        self._previous_error: float | None = None

    def update(self, error: float, dt: float) -> float:
        """根据当前误差和控制周期计算一次限幅后的控制量。"""
        error_value = self._as_finite_float(error, "error")
        dt_value = self._as_finite_float(dt, "dt")
        if dt_value <= 0.0:
            raise ValueError("dt 必须是大于 0 的有限数值")

        self._integral += error_value * dt_value
        derivative = 0.0
        if self._previous_error is not None:
            derivative = (error_value - self._previous_error) / dt_value

        raw_output = (
            self.kp * error_value + self.ki * self._integral + self.kd * derivative
        )
        self._previous_error = error_value
        return float(np.clip(raw_output, self.output_min, self.output_max))

    def reset(self) -> None:
        """清除积分项和上一次误差。"""
        self._integral = 0.0
        self._previous_error = None

    @staticmethod
    def _as_finite_float(value: float, name: str) -> float:
        """将输入转换为有限浮点数。"""
        try:
            value_float = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} 必须是数值") from exc

        if not math.isfinite(value_float):
            raise ValueError(f"{name} 必须是有限数值")
        return value_float


class WaypointPidController:
    """将二维航点误差转换为 USV 线速度和角速度指令。"""

    def __init__(
        self,
        distance_pid: PidController,
        heading_pid: PidController,
        *,
        position_tolerance: float = 0.05,
    ) -> None:
        """组合相互独立的距离 PID 和航向 PID。"""
        if distance_pid is heading_pid:
            raise ValueError("distance_pid 和 heading_pid 必须是不同实例")

        tolerance = PidController._as_finite_float(
            position_tolerance,
            "position_tolerance",
        )
        if tolerance < 0.0:
            raise ValueError("position_tolerance 不能小于 0")

        self.distance_pid = distance_pid
        self.heading_pid = heading_pid
        self.position_tolerance = tolerance

    def compute_action(
        self,
        current_pose: Sequence[float] | np.ndarray,
        target_position: Sequence[float] | np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """返回动作 ``[v_cmd, omega_cmd]``。

        ``position_tolerance`` 只表示航点控制器的停止容差，不表示未来
        Environment 的任务成功判据。距离和航向控制回路彼此独立，本方法
        不根据航向误差衰减或关闭线速度指令。
        """
        dt_value = PidController._as_finite_float(dt, "dt")
        if dt_value <= 0.0:
            raise ValueError("dt 必须是大于 0 的有限数值")

        pose = self._as_finite_vector(current_pose, 3, "current_pose")
        target = self._as_finite_vector(target_position, 2, "target_position")

        delta_x = target[0] - pose[0]
        delta_y = target[1] - pose[1]
        distance_error = math.hypot(delta_x, delta_y)

        if distance_error <= self.position_tolerance:
            # 到达航点后清除历史项，避免切换到新目标时继承旧误差。
            self.reset()
            return np.zeros(2, dtype=np.float64)

        target_bearing = math.atan2(delta_y, delta_x)
        heading_error = self._normalize_angle(target_bearing - pose[2])

        linear_velocity_command = self.distance_pid.update(distance_error, dt_value)
        angular_velocity_command = self.heading_pid.update(heading_error, dt_value)
        return np.array(
            [linear_velocity_command, angular_velocity_command],
            dtype=np.float64,
        )

    def reset(self) -> None:
        """重置距离和航向 PID 的内部状态。"""
        self.distance_pid.reset()
        self.heading_pid.reset()

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """将角度归一化到半开区间 ``[-pi, pi)``。"""
        angle_value = PidController._as_finite_float(angle, "angle")
        return (angle_value + math.pi) % (2.0 * math.pi) - math.pi

    @staticmethod
    def _as_finite_vector(
        value: Sequence[float] | np.ndarray,
        expected_size: int,
        name: str,
    ) -> np.ndarray:
        """将输入转换为指定长度的有限一维数组。"""
        try:
            vector = np.asarray(value, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} 必须是数值序列") from exc

        if vector.shape != (expected_size,):
            raise ValueError(f"{name} 必须是一维且包含 {expected_size} 个元素")
        if not np.all(np.isfinite(vector)):
            raise ValueError(f"{name} 不能包含 NaN 或 Inf")
        return vector


__all__ = ["PidController", "WaypointPidController"]
