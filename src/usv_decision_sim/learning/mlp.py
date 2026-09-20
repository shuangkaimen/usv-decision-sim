"""USV 速度控制 MLP 骨架。"""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import nn

# 与 UsvAgent 的内部 State 和动作语义保持一致。
USV_STATE_DIM = 5  # [x, y, psi, v, omega]
USV_ACTION_DIM = 2  # [v_cmd, omega_cmd]

_DEFAULT_HIDDEN_SIZES: tuple[int, ...] = (64, 64)


class UsvControlMlp(nn.Module):
    """将 USV 状态映射为速度控制动作的简单 MLP 骨架。

    当前是 Week 1-4 教学原型：输入是 `UsvAgent` 的 5 维内部 State
    `[x, y, psi, v, omega]`，输出是未归一化的 2 维动作
    `[v_cmd, omega_cmd]`。动作是否限幅由下游的 Environment / UsvAgent
    决定，本模块不负责裁剪。

    Week 5 冻结正式环境接口后，输入应切换为 Environment 构造的
    Observation，输出语义与动作空间以当时的实验配置为准。
    """

    def __init__(
        self,
        state_dim: int = USV_STATE_DIM,
        action_dim: int = USV_ACTION_DIM,
        hidden_sizes: Sequence[int] = _DEFAULT_HIDDEN_SIZES,
    ) -> None:
        """创建一个前馈 MLP。

        参数：
            state_dim: 输入维度，默认与 USV 状态维度一致。
            action_dim: 输出维度，默认与 USV 动作维度一致。
            hidden_sizes: 隐藏层宽度序列；允许为空以退化为线性映射。
        """
        super().__init__()
        state_dim_value = self._as_positive_int(state_dim, "state_dim")
        action_dim_value = self._as_positive_int(action_dim, "action_dim")
        hidden_sizes_value = tuple(
            self._as_positive_int(size, "hidden_sizes") for size in hidden_sizes
        )

        layers: list[nn.Module] = []
        in_features = state_dim_value
        for hidden_size in hidden_sizes_value:
            layers.append(nn.Linear(in_features, hidden_size))
            layers.append(nn.ReLU())
            in_features = hidden_size
        layers.append(nn.Linear(in_features, action_dim_value))
        self.network = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """根据输入状态预测速度动作。

        参数：
            state: 形状为 `(..., state_dim)` 的状态张量。

        返回：
            形状为 `(..., action_dim)` 的未归一化动作张量。
        """
        return self.network(state)

    @staticmethod
    def _as_positive_int(value: int, name: str) -> int:
        """校验正整型参数，并为非法输入提供统一错误。"""
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} 必须是整数")
        if value <= 0:
            raise ValueError(f"{name} 必须是正整数")
        return value


__all__ = [
    "USV_ACTION_DIM",
    "USV_STATE_DIM",
    "UsvControlMlp",
]
