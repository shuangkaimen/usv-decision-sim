# API 与接口契约

本文档描述当前已实现的 `UsvAgent` V1.0、PID 与航点控制公共接口。接口稳定性优先于复杂继承层次；当前不建立抽象基类。

## 导入

```python
from usv_decision_sim.environment import UsvAgent
```

## 构造函数

```python
UsvAgent(
    agent_id,
    v_min=0.0,
    v_max=2.0,
    omega_max=pi / 2,
    collision_radius=1.0,
)
```

参数约束：

- `agent_id`：由 Environment 管理的实体标识。
- `v_min`、`v_max`、`omega_max`、`collision_radius`：必须是有限数值。
- `v_min <= v_max`。
- `omega_max > 0`。
- `collision_radius > 0`。

默认速度和半径只是可运行的实体层默认值，实验应通过配置或 Environment 覆盖，不能视为最终实验结论。

## 方法

| 方法 | 输入 | 输出或状态变化 | 约定 |
| --- | --- | --- | --- |
| `reset(init_x, init_y, init_psi)` | 初始位置和航向 | 重置内部状态；速度和角速度清零 | 航向归一化到 `[-pi, pi)` |
| `apply_action(action, dt)` | `[v_cmd, omega_cmd]`、正数 `dt` | 限幅并推进一个仿真步 | 位置使用更新前航向计算 |
| `get_state()` | 无 | 返回 `[x, y, psi, v, omega]` 状态副本 | 不构造 Observation |
| `get_pos()` | 无 | 返回 `[x, y]` 位置副本 | 不执行碰撞检测 |
| `get_state_tensor(device=None, dtype=None)` | 可选 `device`、`dtype` | 返回同样内容的 PyTorch 张量副本 | 状态内容与 `get_state()` 一致，不构造 Observation；Week 1-4 原型，Week 5 迁移到 Environment/Observation 层 |
| `_normalize_angle(angle)` | 有限角度 | 返回 `[-pi, pi)` 内的角度 | `pi` 统一表示为 `-pi` |

## 状态不变量

`UsvAgent` 的状态顺序和字段含义固定如下：

| 索引 | 字段 | 含义 |
| ---: | --- | --- |
| 0 | `x` | 世界坐标系中的横向位置，单位 m |
| 1 | `y` | 世界坐标系中的纵向位置，单位 m |
| 2 | `psi` | 当前航向角，单位 rad |
| 3 | `v` | 当前实际执行的线速度，单位 m/s |
| 4 | `omega` | 当前实际执行的角速度，单位 rad/s |

- `x`、`y`、`v`、`omega` 必须为有限浮点数。
- `psi` 必须始终位于 `[-pi, pi)`。
- 执行动作后，`v ∈ [v_min, v_max]`，`omega ∈ [-omega_max, omega_max]`。
- `reset()` 后 `v = 0`、`omega = 0`。
- `get_state()` 返回数组顺序固定为 `[x, y, psi, v, omega]`，并且是新建的 NumPy 数组。
- `get_state_tensor()` 返回与 `get_state()` 内容一致的新建 PyTorch 张量，供算法层消费；缺省 `dtype` 时按 NumPy 数组推断为 `float64`，上层可按需指定 `float32` 与设备。该方法为 Week 1-4 教学原型，Week 5 冻结正式环境接口时应迁移到 Environment/Observation 层。

## 错误处理

实体层负责自身接口的基本合法性：

- `dt <= 0` 或非有限时抛出 `ValueError`。
- Action 不是形状为 `(2,)` 的有限数值序列时抛出 `ValueError`。
- 构造参数或初始状态不是有限数值时抛出 `ValueError`。

实体层不负责修复地图配置、推断边界规则、计算奖励或决定 Episode 成功与否。

## 最小示例

```python
agent = UsvAgent("test-usv")
agent.reset(1.0, 2.0, 0.0)
agent.apply_action([1.0, 0.0], dt=1.0)

state = agent.get_state()  # [2.0, 2.0, 0.0, 1.0, 0.0]

state_tensor = agent.get_state_tensor(dtype=torch.float32)  # shape (5,)
```

公开类和方法的中文 docstring、关键行内注释以及实现细节位于 [src/usv_decision_sim/environment/usv_agent.py](../src/usv_decision_sim/environment/usv_agent.py)。

## PID 与航点控制器

```python
from usv_decision_sim.control import PidController, WaypointPidController
```

`PidController` 对一个标量误差执行离散 PID 更新。调用方必须显式提供
`kp`、`ki`、`kd`、`output_min` 和 `output_max`，避免在 P-Day11 参数实验前
提前冻结增益。首次更新的微分项为零；`reset()` 清除积分项和上一次误差。

`WaypointPidController` 组合相互独立的距离 PID 与航向 PID：

```python
action = controller.compute_action(
    current_pose=(x, y, psi),
    target_position=(target_x, target_y),
    dt=dt,
)
```

| 名称 | 单位 | 含义 |
| --- | --- | --- |
| `distance_error` | m | 当前位置到目标点的欧氏距离 |
| `heading_error` | rad | `target_bearing - psi`，归一化到 `[-pi, pi)` |
| `linear_velocity_command` / `v_cmd` | m/s | 距离 PID 的限幅输出 |
| `angular_velocity_command` / `omega_cmd` | rad/s | 航向 PID 的限幅输出 |
| `position_tolerance` | m | 航点控制器停止容差，默认 `0.05` |
| `dt` | s | 控制周期，必须为正有限数值 |

返回值为形状 `(2,)` 的 `float64` NumPy 数组 `[v_cmd, omega_cmd]`，可直接传给
`UsvAgent.apply_action()`。控制器侧先按自身配置限幅，`UsvAgent` 继续执行最终
安全限幅；调用方使用自定义 Agent 速度范围时，应同步配置 PID 输出范围。

当 `distance_error <= position_tolerance` 时，控制器重置两个 PID 并返回
`[0.0, 0.0]`。该容差只表示 waypoint controller 的停止条件，不是后续 v0.3
Environment 的任务成功判据，二者是否统一要等环境契约冻结后再决定。

P-Day10 保持距离与航向回路独立：目标位于艇后方时，距离 PID 仍可产生正
`v_cmd`，航向 PID 同时产生 `omega_cmd`。当前不包含航向门控、速度衰减或
“先转向再前进”等启发式规则。

## 学习模块 UsvControlMlp（Day9 原型）

```python
from usv_decision_sim.learning import UsvControlMlp, USV_STATE_DIM, USV_ACTION_DIM
```

`UsvControlMlp` 是一个简单前馈网络，把 5 维 USV 内部 State
`[x, y, psi, v, omega]` 映射为 2 维动作 `[v_cmd, omega_cmd]`。当前只作
训练链路与 MLP 骨架的教学原型，不负责动作限幅、Observation 构造或真实
环境交互。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `state_dim` | `5` | 输入维度，对应 USV 状态 |
| `action_dim` | `2` | 输出维度，对应 USV 动作 |
| `hidden_sizes` | `(64, 64)` | 隐藏层宽度；空元组退化为线性映射 |

- `forward(state)`：输入形状 `(..., state_dim)`，输出形状
  `(..., action_dim)` 的未归一化动作。
- 动作限幅由下游 `Environment` / `UsvAgent` 负责。
- 该模块为 Week 1-4 原型；Week 5 冻结正式 Environment 接口后，输入应切换
  为 Observation，输出语义以实验配置为准。

最小训练脚本见 [scripts/train_usv_mlp.py](../scripts/train_usv_mlp.py)，演示
数据 → 模型 → 损失 → 优化器更新的完整链路。
