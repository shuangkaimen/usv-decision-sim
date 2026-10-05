"""PID 与二维航点控制器的最小正确性测试。"""

import math

import numpy as np
import pytest

from usv_decision_sim.control import PidController, WaypointPidController
from usv_decision_sim.environment import UsvAgent


def make_waypoint_controller() -> WaypointPidController:
    """创建使用纯比例增益的确定性测试控制器。"""
    return WaypointPidController(
        distance_pid=PidController(
            kp=1.0,
            ki=0.0,
            kd=0.0,
            output_min=0.0,
            output_max=2.0,
        ),
        heading_pid=PidController(
            kp=1.0,
            ki=0.0,
            kd=0.0,
            output_min=-math.pi / 2.0,
            output_max=math.pi / 2.0,
        ),
    )


def test_pid_controller_computes_and_clips_proportional_output() -> None:
    """验证标量 PID 的比例项和输出限幅可形成最小计算闭环。"""
    controller = PidController(
        kp=2.0,
        ki=0.0,
        kd=0.0,
        output_min=-1.0,
        output_max=1.0,
    )

    output = controller.update(error=0.75, dt=0.1)

    assert output == pytest.approx(1.0)


def test_waypoint_ahead_produces_forward_command() -> None:
    """验证正前方航点产生正线速度和零角速度。"""
    controller = make_waypoint_controller()

    action = controller.compute_action(
        current_pose=(0.0, 0.0, 0.0),
        target_position=(1.0, 0.0),
        dt=0.1,
    )

    np.testing.assert_allclose(action, [1.0, 0.0])


def test_heading_error_wraps_across_pi_boundary() -> None:
    """验证目标方位与当前航向跨越 pi 时采用最短角度误差。"""
    controller = make_waypoint_controller()
    target_bearing = -math.pi + 0.1

    action = controller.compute_action(
        current_pose=(0.0, 0.0, math.pi - 0.1),
        target_position=(math.cos(target_bearing), math.sin(target_bearing)),
        dt=0.1,
    )

    assert action[1] == pytest.approx(0.2)


def test_waypoint_within_position_tolerance_stops_controller() -> None:
    """验证停止容差属于 waypoint controller，并输出零动作。"""
    controller = make_waypoint_controller()

    action = controller.compute_action(
        current_pose=(0.0, 0.0, 1.0),
        target_position=(0.03, 0.04),
        dt=0.1,
    )

    np.testing.assert_allclose(action, [0.0, 0.0])


def test_target_behind_keeps_distance_and_heading_loops_independent() -> None:
    """验证艇后目标不会触发航向门控或强制停止。"""
    controller = make_waypoint_controller()

    action = controller.compute_action(
        current_pose=(0.0, 0.0, 0.0),
        target_position=(-1.0, 0.0),
        dt=0.1,
    )

    assert action[0] > 0.0
    assert action[1] == pytest.approx(-math.pi / 2.0)


def test_waypoint_action_can_drive_usv_agent() -> None:
    """验证控制器输出可直接交给现有 UsvAgent 动作接口。"""
    controller = make_waypoint_controller()
    agent = UsvAgent("pid-integration")
    agent.reset(0.0, 0.0, 0.0)

    action = controller.compute_action(
        current_pose=(agent.x, agent.y, agent.psi),
        target_position=(1.0, 0.0),
        dt=0.5,
    )
    agent.apply_action(action, dt=0.5)

    np.testing.assert_allclose(agent.get_state(), [0.5, 0.0, 0.0, 1.0, 0.0])
