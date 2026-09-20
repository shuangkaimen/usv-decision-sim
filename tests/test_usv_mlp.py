"""USV 控制 MLP 骨架的单元测试。"""

import pytest
import torch

from usv_decision_sim.learning import USV_ACTION_DIM, USV_STATE_DIM, UsvControlMlp


def test_default_forward_outputs_action_shape() -> None:
    """验证默认模型把批量状态映射为批量二维动作。"""
    model = UsvControlMlp()
    states = torch.randn(8, USV_STATE_DIM)

    actions = model(states)

    assert actions.shape == (8, USV_ACTION_DIM)


def test_single_state_forward_outputs_two_actions() -> None:
    """验证单个状态输入仍输出二维动作。"""
    model = UsvControlMlp()
    state = torch.randn(USV_STATE_DIM)

    actions = model(state)

    assert actions.shape == (USV_ACTION_DIM,)


def test_custom_dimensions_and_hidden_sizes() -> None:
    """验证可以自定义输入、输出维度与隐藏层宽度。"""
    model = UsvControlMlp(state_dim=3, action_dim=1, hidden_sizes=(16, 8))

    actions = model(torch.randn(4, 3))

    assert actions.shape == (4, 1)


def test_empty_hidden_sizes_degrades_to_linear_map() -> None:
    """验证空隐藏层退化为线性映射，便于基础回归。"""
    model = UsvControlMlp(hidden_sizes=())

    actions = model(torch.randn(2, USV_STATE_DIM))

    assert actions.shape == (2, USV_ACTION_DIM)


def test_backward_populates_finite_gradients() -> None:
    """验证训练更新链路能够反向传播并产生有限梯度。"""
    model = UsvControlMlp()
    states = torch.randn(8, USV_STATE_DIM)
    targets = torch.randn(8, USV_ACTION_DIM)

    loss = torch.nn.functional.mse_loss(model(states), targets)
    loss.backward()

    gradients = [p.grad for p in model.parameters() if p.requires_grad]
    assert len(gradients) > 0
    assert all(
        gradient is not None and torch.isfinite(gradient).all()
        for gradient in gradients
    )


def test_invalid_dimensions_raise_value_error() -> None:
    """验证非法维度会被拒绝。"""
    with pytest.raises(ValueError):
        UsvControlMlp(state_dim=0)
    with pytest.raises(ValueError):
        UsvControlMlp(action_dim=-1)
    with pytest.raises(ValueError):
        UsvControlMlp(hidden_sizes=(32, 0))
