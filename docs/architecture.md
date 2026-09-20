# 系统架构

## 项目定位

本项目是一个面向无人集群智能决策与协同仿真的研究型平台。当前仓库处于单 USV 二维平面运动学实体阶段，后续可逐步扩展到环境、障碍物、多智能体和强化学习实验。

当前实体模型的准确定位是 **USV-inspired planar kinematic abstraction**：受无人艇任务启发的二维平面运动学抽象模型，不等同于真实无人艇水动力学仿真。

## 分层职责

```text
experiments / 配置
        │ 训练、评估、随机种子、统计
        ▼
Policy / PPO / 规划算法
        │ Observation → Action
        ▼
Environment
        │ 地图、目标、障碍物、奖励、终止、Observation
        ▼
UsvAgent
        │ 自身状态、动作限幅、运动学推进
        ▼
二维平面状态
```

| 模块 | 负责内容 | 不负责内容 |
| --- | --- | --- |
| `usv_decision_sim.environment.UsvAgent` | 自身状态、二维运动学、动作约束、几何尺寸 | 地图、奖励、碰撞判定、训练、Observation |
| `usv_decision_sim.learning.UsvControlMlp` | 从 State 回归速度动作的教学 MLP 骨架 | 动作限幅、Observation 构造、真实环境交互 |
| `Environment`（逐步建设） | 地图、目标、障碍物、碰撞、奖励、终止、Observation 构造 | PPO 网络结构 |
| `Policy / PPO`（逐步建设） | 根据 Observation 输出 Action | 修改地图和 Agent 内部状态 |
| `experiments`（逐步建设） | 训练、评估、配置、随机种子、统计 | 改变实体模型语义 |

## 状态与数据流

- `UsvAgent` 内部 State 固定为 `[x, y, psi, v, omega]`，只描述自身物理状态。
- `UsvAgent.get_state_tensor()` 将同一内部状态转换为 PyTorch 张量，供后续 DQN/PPO 算法层消费；字段顺序和物理含义与 `get_state()` 完全一致。该方法当前为 Week 1-4 原型，Week 5 冻结环境接口时迁移到 Environment/Observation 构造层。
- `UsvControlMlp` 是 Day9 引入的教学原型，把 5 维 State 映射为 2 维未归一化动作；它不是 Week 3-4 的正式 DQN/PPO Policy，也不负责 Observation 构造或动作限幅。
- Environment 读取 Agent 状态，并结合目标、地图和障碍物构造 Observation。
- Policy/PPO 只消费 Observation 并生成 `[v_cmd, omega_cmd]` Action。
- Environment 决定 `dt`，将 Action 和 `dt` 传给 Agent；Agent 不绑定仿真时钟。
- Agent 知道自身 `collision_radius`，但碰撞计算和 Episode 判定由 Environment 负责。

## 依赖边界

`UsvAgent` 保持轻量、独立的实体层，不依赖 PPO、Gymnasium 或具体 Environment 实现。`get_state_tensor()` 会按需导入 PyTorch，实体层核心仍保持 NumPy 语义；这样可以在没有训练框架的情况下单独运行和测试运动学，同时为算法层提供张量入口。该张量入口为 Week 1-4 原型，Week 5 冻结环境接口时迁移到 Environment/Observation 层。上层环境也可以替换策略实现而不改变实体接口。

`usv_decision_sim.learning` 独立于 `UsvAgent`，顶层直接依赖 PyTorch；它只消费状态张量并输出未归一化动作，不反向访问实体内部状态。

更完整的建模冻结项见 [knowledge.md](knowledge.md)，实体接口见 [api.md](api.md)，仿真步推进规则见 [simulation.md](simulation.md)。开发实践和日志约定见 [guides/logging_and_debugging.md](guides/logging_and_debugging.md)。
