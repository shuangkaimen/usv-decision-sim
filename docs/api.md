# API 与接口契约

本文档描述当前已实现的 `UsvAgent` V1.0 公共接口。接口稳定性优先于复杂继承层次；当前不建立抽象基类。

## 导入

```python
from environment.usv_agent import UsvAgent
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
```

公开类和方法的中文 docstring、关键行内注释以及实现细节位于 [environment/usv_agent.py](../environment/usv_agent.py)。
