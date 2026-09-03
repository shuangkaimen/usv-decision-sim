"""USV 实体模型与二维一阶运动学的单元测试。"""

import math

import numpy as np
import pytest

from environment.usv_agent import UsvAgent


# =============================================================================
# 基础运动学测试
# =============================================================================


def test_apply_action_moves_along_x_axis() -> None:
    """验证零航向角下，线速度沿 x 轴推进。"""
    # Arrange：从原点、沿 +x 方向开始运动。
    agent = UsvAgent("test-usv")
    agent.reset(0.0, 0.0, 0.0)

    # Act：执行 1 m/s、1 s 的直线动作。
    agent.apply_action([1.0, 0.0], dt=1.0)

    # Assert：位置应前进 1 m，航向角保持不变。
    np.testing.assert_allclose(agent.get_state(), [1.0, 0.0, 0.0, 1.0, 0.0])


def test_apply_action_moves_along_y_axis() -> None:
    """验证航向角为 pi/2 时，线速度沿 y 轴推进。"""
    # Arrange：将 USV 初始航向设置为 +y 方向。
    agent = UsvAgent("test-usv")
    agent.reset(0.0, 0.0, math.pi / 2.0)

    # Act：执行 1 m/s、1 s 的直线动作。
    agent.apply_action([1.0, 0.0], dt=1.0)

    # Assert：x 保持为 0，y 前进 1 m。
    np.testing.assert_allclose(agent.get_pos(), [0.0, 1.0], atol=1e-12)


def test_apply_action_rotates_in_place() -> None:
    """验证线速度为零时，USV 只改变航向而不改变位置。"""
    # Arrange：从原点、零航向开始，准备执行纯旋转动作。
    agent = UsvAgent("test-usv")
    agent.reset(0.0, 0.0, 0.0)

    # Act：线速度为零，角速度为 pi/2，时间步长为 1 s。
    agent.apply_action([0.0, math.pi / 2.0], dt=1.0)

    # Assert：位置保持不变，航向角旋转到 pi/2。
    np.testing.assert_allclose(
        agent.get_state(), [0.0, 0.0, math.pi / 2.0, 0.0, math.pi / 2.0]
    )


def test_heading_is_normalized_after_rotation() -> None:
    """验证旋转后航向角始终位于 [-pi, pi) 区间。"""
    # Arrange：从接近 pi 的航向开始，下一步继续逆时针旋转。
    agent = UsvAgent("test-usv")
    agent.reset(0.0, 0.0, math.pi - 0.1)

    # Act：旋转 0.2 rad，使未归一化角度越过 pi。
    agent.apply_action([0.0, 0.2], dt=1.0)

    # Assert：结果应折返到 -pi 附近，而不是继续超过 pi。
    assert -math.pi <= agent.psi < math.pi
    assert agent.psi == pytest.approx(-math.pi + 0.1)


def test_reset_restores_pose_and_clears_velocity() -> None:
    """验证 reset 恢复传入位姿，并将线速度和角速度清零。"""
    # Arrange：先让 USV 产生位置、航向和速度变化。
    agent = UsvAgent("test-usv")
    agent.reset(0.0, 0.0, 0.0)
    agent.apply_action([1.0, 0.5], dt=1.0)

    # Act：用新的初始位姿重置 Episode，且传入超过 pi 的航向角。
    agent.reset(3.0, -2.0, math.pi + 0.2)

    # Assert：位置使用传入值，航向归一化，速度状态清零。
    np.testing.assert_allclose(
        agent.get_state(),
        [3.0, -2.0, -math.pi + 0.2, 0.0, 0.0],
        atol=1e-12,
    )


def test_position_uses_heading_before_rotation() -> None:
    """验证同一步中先用旧航向更新位置，再更新航向角。"""
    # Arrange：初始沿 +x，动作同时包含前进和逆时针旋转。
    agent = UsvAgent("test-usv")
    agent.reset(0.0, 0.0, 0.0)

    # Act：一个时间步内前进 1 m 并旋转 pi/2。
    agent.apply_action([1.0, math.pi / 2.0], dt=1.0)

    # Assert：位置使用旧 psi=0，因此落在 (1, 0)，航向才变为 pi/2。
    np.testing.assert_allclose(
        agent.get_state(), [1.0, 0.0, math.pi / 2.0, 1.0, math.pi / 2.0]
    )


def test_action_is_clipped_before_kinematics() -> None:
    """验证线速度和角速度在运动学计算前分别受到上下限约束。"""
    # Arrange：设置较小的速度约束，便于观察限幅结果。
    agent = UsvAgent(
        "test-usv",
        v_min=0.5,
        v_max=1.0,
        omega_max=0.25,
    )
    agent.reset(0.0, 0.0, 0.0)

    # Act：输入超过上限的线速度和角速度。
    agent.apply_action([3.0, 2.0], dt=1.0)

    # Assert：保存的实际执行值应为限幅后的值，位置也按限幅后的 v 推进。
    np.testing.assert_allclose(agent.get_state(), [1.0, 0.0, 0.25, 1.0, 0.25])

    # Act：输入低于线速度下限以及超过负角速度下限的动作。
    agent.apply_action([-2.0, -2.0], dt=1.0)

    # Assert：速度分别被裁剪为 v_min 和 -omega_max。
    assert agent.v == pytest.approx(0.5)
    assert agent.omega == pytest.approx(-0.25)


# =============================================================================
# 面向对象封装性测试
# =============================================================================


def test_get_state_returns_independent_array() -> None:
    """验证修改 get_state 返回值不会破坏 Agent 内部状态。"""
    # Arrange：将 Agent 重置到一个便于识别的位置。
    agent = UsvAgent("test-usv")
    agent.reset(1.0, 2.0, 0.0)

    # Act：取得状态数组后，故意修改其中的 x 值。
    state = agent.get_state()
    state[0] = 999.0

    # Assert：外部数组已改变，但 Agent 内部保存的 x 仍然是 1。
    assert state[0] == pytest.approx(999.0)
    assert agent.x == pytest.approx(1.0)
    np.testing.assert_allclose(agent.get_state(), [1.0, 2.0, 0.0, 0.0, 0.0])


# =============================================================================
# 非法输入测试
# =============================================================================


def test_non_positive_dt_raises_value_error() -> None:
    """验证 dt 必须是大于零的有限数值。"""
    # Arrange：创建一个可执行动作的 USV。
    agent = UsvAgent("test-usv")

    # Assert：零和负时间步都必须被拒绝。
    with pytest.raises(ValueError, match="dt"):
        agent.apply_action([1.0, 0.0], dt=0.0)
    with pytest.raises(ValueError, match="dt"):
        agent.apply_action([1.0, 0.0], dt=-1.0)


def test_action_must_contain_exactly_two_elements() -> None:
    """验证动作必须严格是 [v_cmd, omega_cmd] 两个元素。"""
    # Arrange：创建一个可执行动作的 USV。
    agent = UsvAgent("test-usv")

    # Assert：长度不足、长度过长和二维数组都必须被拒绝。
    with pytest.raises(ValueError, match="action"):
        agent.apply_action([1.0], dt=1.0)
    with pytest.raises(ValueError, match="action"):
        agent.apply_action([1.0, 0.0, 0.0], dt=1.0)
    with pytest.raises(ValueError, match="action"):
        agent.apply_action([[1.0, 0.0]], dt=1.0)


def test_kinematics_rejects_non_finite_inputs() -> None:
    """验证 dt 和动作中的 NaN/Inf 不会进入运动学计算。"""
    # Arrange：创建一个可执行动作的 USV。
    agent = UsvAgent("test-usv")

    # Assert：所有非有限输入都应抛出 ValueError。
    with pytest.raises(ValueError):
        agent.apply_action([1.0, 0.0], dt=math.nan)
    with pytest.raises(ValueError):
        agent.apply_action([math.inf, 0.0], dt=1.0)
