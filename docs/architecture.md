# 系统架构

## 项目定位

本项目是一个面向无人集群智能决策与协同仿真的研究型平台。当前仓库处于单 USV 二维平面运动学实体阶段，后续可逐步扩展到环境、障碍物、多智能体和强化学习实验。

当前实体模型的准确定位是 **USV-inspired planar kinematic abstraction**：受无人艇任务启发的二维平面运动学抽象模型，不等同于真实无人艇水动力学仿真。

## 模块划分

本节是模块位置与实现状态的唯一文档事实来源，项目记忆和计划引用本节，
不另行维护位置表。运行时代码统一放在 `src/usv_decision_sim/` 下，通过
`pyproject.toml` 打包；测试和实验入口通过 `usv_decision_sim.*` 导入核心库。

| 模块 | 位置 | 状态与职责 |
| --- | --- | --- |
| `usv_decision_sim.environment` | `src/usv_decision_sim/environment/` | 已实现单艇 `UsvAgent`；完整 Environment 后续建设 |
| `usv_decision_sim.control` | `src/usv_decision_sim/control/` | 已实现标量 PID 与航点控制基线 |
| `usv_decision_sim.learning` | `src/usv_decision_sim/learning/` | 已实现教学型控制 MLP，不代表正式 DQN/PPO |
| `usv_decision_sim.utils` | `src/usv_decision_sim/utils/` | 已实现日志等通用基础设施 |
| `usv_decision_sim.rl` | `src/usv_decision_sim/rl/`（规划位置，尚未创建） | V1 强化学习策略与可复用算法组件 |
| `usv_decision_sim.planning` | `src/usv_decision_sim/planning/`（规划位置，尚未创建） | V1 A*、APF 等传统规划实现 |
| MARL 相关模块 | 核心包内，具体子包边界待多艇阶段确定 | V1 多艇环境与协同算法，按实际职责划分 |
| LLM / Agent 相关模块 | V2 启动后确定 | V1 阶段不创建占位模块 |
| 实验与配置 | `experiments/`、`configs/` | 实验编排、评估、统计和配置输入，调用核心库 |
| 命令行脚本 | `scripts/` | 教学、训练和批处理入口，调用核心库 |
| 测试 | `tests/` | 测试已安装的项目 |
| 正式文档 | `docs/` | 模块、接口、建模与验证约定 |
| 项目记忆与计划 | `.project_manager/` | 当前状态、计划与交接，引用正式技术文档 |

尚未实现的模块按需创建，不预先建立空包。核心库不反向依赖实验或一次性
脚本。可复用的策略、rollout 和算法组件放入核心包，训练参数、运行编排、
checkpoint 和结果统计归实验侧。共享实验配置按需放入 `configs/`，专属配置
随实验保存，同一参数不在多个地方手工维护。

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
| `usv_decision_sim.control` | 标量 PID、航点距离/航向控制、控制器侧输出限幅 | 修改 Agent 状态、任务成功判定、路径规划、RL 训练 |
| `usv_decision_sim.learning.UsvControlMlp` | 从 State 回归速度动作的教学 MLP 骨架 | 动作限幅、Observation 构造、真实环境交互 |
| `Environment`（逐步建设） | 地图、目标、障碍物、碰撞、奖励、终止、Observation 构造 | PPO 网络结构 |
| `Policy / PPO`（逐步建设） | 根据 Observation 输出 Action | 修改地图和 Agent 内部状态 |
| `experiments`（逐步建设） | 训练、评估、配置、随机种子、统计 | 改变实体模型语义 |

## 状态与数据流

- `UsvAgent` 内部 State 固定为 `[x, y, psi, v, omega]`，只描述自身物理状态。
- `UsvAgent.get_state_tensor()` 将同一内部状态转换为 PyTorch 张量，供后续 DQN/PPO 算法层消费；字段顺序和物理含义与 `get_state()` 完全一致。该方法当前为 Week 1-4 原型，Week 5 冻结环境接口时迁移到 Environment/Observation 构造层。
- `UsvControlMlp` 是 Day9 引入的教学原型，把 5 维 State 映射为 2 维未归一化动作；它不是 Week 3-4 的正式 DQN/PPO Policy，也不负责 Observation 构造或动作限幅。
- Environment 读取 Agent 状态，并结合目标、地图和障碍物构造 Observation。
- PID waypoint controller 接收当前位姿、目标点和 `dt`，输出与 Agent 一致的 `[v_cmd, omega_cmd]`，但不持有或修改 Agent。
- Policy/PPO 只消费 Observation 并生成 `[v_cmd, omega_cmd]` Action。
- Environment 决定 `dt`，将 Action 和 `dt` 传给 Agent；Agent 不绑定仿真时钟。
- Agent 知道自身 `collision_radius`，但碰撞计算和 Episode 判定由 Environment 负责。

## 依赖边界

`UsvAgent` 保持轻量、独立的实体层，不依赖 PPO、Gymnasium 或具体 Environment 实现。`get_state_tensor()` 会按需导入 PyTorch，实体层核心仍保持 NumPy 语义；这样可以在没有训练框架的情况下单独运行和测试运动学，同时为算法层提供张量入口。该张量入口为 Week 1-4 原型，Week 5 冻结环境接口时迁移到 Environment/Observation 层。上层环境也可以替换策略实现而不改变实体接口。

`usv_decision_sim.learning` 独立于 `UsvAgent`，顶层直接依赖 PyTorch；它只消费状态张量并输出未归一化动作，不反向访问实体内部状态。

`usv_decision_sim.control` 同样独立于 `UsvAgent`。航点控制器只消费普通数值
位姿、目标点和控制周期，返回 NumPy 动作数组。控制器的
`position_tolerance` 仅用于停止 waypoint controller，不替代未来 Environment
定义的任务成功条件。

更完整的建模冻结项见 [knowledge.md](knowledge.md)，实体接口见 [api.md](api.md)，仿真步推进规则见 [simulation.md](simulation.md)。开发实践和日志约定见 [guides/logging_and_debugging.md](guides/logging_and_debugging.md)。
