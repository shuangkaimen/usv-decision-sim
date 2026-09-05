# 算法与决策边界

## 当前决策接口

策略模块接收 Environment 构造的 Observation，输出单步速度动作：

```python
action = [v_cmd, omega_cmd]
```

动作表示目标线速度和目标角速度，不表示推力、油门、加速度、电机转矩或舵角。Agent 负责动作合法性检查与限幅，策略不直接修改 Agent 内部状态。

## Observation 与 State

Agent 内部 State 固定为自身物理状态：

```text
[x, y, psi, v, omega]
```

它不等于强化学习算法接收的 Observation。Observation 由 Environment 根据任务上下文构造，候选信息包括：

- 目标相对距离；
- 目标相对角度的正弦和余弦；
- 自身线速度与角速度；
- 固定方向的 LiDAR 距离；
- 动态障碍物的相对位置和相对运动信息。

Observation 应优先采用相对量，以增强策略在不同地图和起终点配置下的泛化能力。最终维度、LiDAR 参数、动态障碍物表示和多智能体 Observation 尚未冻结。

## PPO 与规划算法的职责

- PPO/Policy：学习从 Observation 到 Action 的映射，并维护训练所需的网络、经验和优化过程。
- A*、APF 或其他规划/启发式算法：如后续引入，负责生成路径、航向或动作参考，不改变实体层运动学语义。
- Environment：统一执行状态读取、Observation 构造、奖励与终止判定，并把 Action 交给 Agent。
- UsvAgent：只执行限幅后的速度动作和运动学积分，不依赖 PPO、Stable-Baselines3 或具体规划器。

## 设计约束

1. 算法层不得把 `[v_cmd, omega_cmd]` 解释成推力或加速度。
2. 算法层不得绕过 Environment 直接修改地图、碰撞状态或 Agent 内部状态。
3. 更换 PPO、规则策略或规划算法时，Agent API 和仿真更新顺序保持不变。
4. 如果未来引入动力学模型，应新增并明确版本化的动作语义，不覆盖 V1.0 的运动学约定。

## 后续待冻结项

- `v_cmd`、`omega_cmd` 的实验范围与动作空间定义；
- Observation 的最终维度及归一化方式；
- LiDAR 的射线数量、量程和缺失值处理；
- 动态障碍物及多 USV 的观测编码；
- 奖励函数、成功/失败/超时终止条件。

算法实验配置和评估结果应放在 `experiments/` 或单独实验记录中，不在本文件提前固化尚未验证的结论。
