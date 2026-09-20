"""Day9 最小训练脚本：演示 数据 → 模型 → 损失 → 优化器更新 的完整链路。

本脚本不依赖真实 Environment。它用「朝原点航行的简单规则」生成合成
`(state, action)` 样本，训练 `UsvControlMlp` 回归该规则，用于验证训练
循环和 MLP 骨架可运行。正式环境、奖励和 Observation 属于 Week 5 之后的
内容，本脚本不提前实现。
"""

from __future__ import annotations

import argparse
import math

import numpy as np
import torch
from torch import nn

from usv_decision_sim.learning import USV_ACTION_DIM, USV_STATE_DIM, UsvControlMlp

# V1.0 实体层默认动作约束，仅用于生成演示目标。
V_MAX = 2.0
OMEGA_MAX = math.pi / 2.0


def make_dataset(
    num_samples: int,
    *,
    seed: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """生成合成状态及由「朝原点航行」规则产生的目标动作。

    该规则只用于演示训练链路：线速度随距离衰减，角速度按当前航向与朝向
    原点的目标航向之间的误差进行比例控制，并裁剪到实体层动作范围。
    """
    rng = np.random.default_rng(seed)
    states = np.column_stack(
        [
            rng.uniform(-10.0, 10.0, size=num_samples),  # x
            rng.uniform(-10.0, 10.0, size=num_samples),  # y
            rng.uniform(-math.pi, math.pi, size=num_samples),  # psi
            rng.uniform(0.0, V_MAX, size=num_samples),  # v
            rng.uniform(-OMEGA_MAX, OMEGA_MAX, size=num_samples),  # omega
        ]
    )

    x = states[:, 0]
    y = states[:, 1]
    psi = states[:, 2]

    distance = np.hypot(x, y)
    target_heading = np.arctan2(-y, -x)
    heading_error = (target_heading - psi + math.pi) % (2.0 * math.pi) - math.pi

    v_cmd = V_MAX * np.exp(-distance / 8.0)
    omega_cmd = np.clip(0.8 * heading_error, -OMEGA_MAX, OMEGA_MAX)
    actions = np.column_stack([v_cmd, omega_cmd])

    assert states.shape == (num_samples, USV_STATE_DIM)
    assert actions.shape == (num_samples, USV_ACTION_DIM)

    return (
        torch.from_numpy(states).to(torch.float32),
        torch.from_numpy(actions).to(torch.float32),
    )


def main() -> None:
    """运行一个最小监督式训练循环。"""
    parser = argparse.ArgumentParser(description="训练 USV 控制 MLP 骨架")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # 数据：生成并划分训练集与验证集。
    states, targets = make_dataset(2048, seed=args.seed)
    split_index = int(len(states) * 0.8)
    train_states, val_states = states[:split_index], states[split_index:]
    train_targets, val_targets = targets[:split_index], targets[split_index:]

    # 模型：5 -> 64 -> 64 -> 2。
    model = UsvControlMlp()
    loss_fn = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    initial_loss: float | None = None
    for epoch in range(1, args.epochs + 1):
        # 更新四步：清空梯度 -> 前向 -> 计算损失 -> 反向传播与更新。
        optimizer.zero_grad()
        predictions = model(train_states)
        loss = loss_fn(predictions, train_targets)
        loss.backward()
        optimizer.step()

        if initial_loss is None:
            initial_loss = loss.item()

        if epoch == 1 or epoch % 50 == 0 or epoch == args.epochs:
            model.eval()
            with torch.no_grad():
                val_loss = loss_fn(model(val_states), val_targets).item()
            model.train()
            print(
                f"epoch {epoch:>4}/{args.epochs}  "
                f"train_loss={loss.item():.6f}  val_loss={val_loss:.6f}"
            )

    final_loss = loss.item()
    print(f"训练完成：initial_loss={initial_loss:.6f} -> final_loss={final_loss:.6f}")

    if initial_loss is not None and final_loss >= initial_loss:
        raise SystemExit("训练后损失未下降，请检查学习率或数据生成逻辑。")


if __name__ == "__main__":
    main()
