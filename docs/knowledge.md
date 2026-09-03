# 项目知识与建模约定

## USV 建模约定 V1.0

**冻结日期：** 2026-09-02
**适用范围：** 当前单 USV 二维运动学实体模型

本节记录后续环境、算法和实验共同依赖的基础语义。除非发现明确的建模错误，后续实现应遵守这些约定，避免同一概念在不同模块中出现不同解释。

### 1. 坐标系与航向角

- 使用二维笛卡尔坐标系。
- `x` 轴向右为正方向。
- `y` 轴向上为正方向。
- `psi` 表示 USV 航向角。
- `psi = 0` 表示船首沿 `+x` 方向。
- 航向角逆时针旋转为正，顺时针旋转为负。
- 航向角统一归一化到半开区间 `[-pi, pi)`。

采用半开区间意味着 `pi` 与 `-pi` 表示同一方向时，统一保存为 `-pi`，避免同一航向存在两种数值表示。

### 2. 单位约定

项目统一使用 SI 单位：

| 物理量 | 单位 |
| --- | --- |
| 位置 `x, y` | 米（m） |
| 线速度 `v` | 米每秒（m/s） |
| 角速度 `omega` | 弧度每秒（rad/s） |
| 时间 `dt` | 秒（s） |
| 航向角 `psi` | 弧度（rad） |
| 碰撞半径 | 米（m） |

核心计算中不混用角度制和弧度制。若可视化或用户界面需要显示角度，可以在展示层转换为度，但实体模型与环境内部仍使用弧度。

### 3. 模型定位与假设

当前模型定位为：

> USV-inspired planar kinematic abstraction，即受无人艇任务启发的二维平面运动学抽象模型。

它用于研究路径规划、避障和强化学习决策，不代表真实无人艇水动力学仿真。

V1.0 采用以下假设：

- USV 被抽象为二维平面中的运动实体。
- 底层速度控制器可以理想跟踪目标速度。
- 一个仿真步内，速度指令经过物理限幅后立即生效。
- 暂不模拟船体惯性、推进器动力学、水动力、加速度约束和控制延迟。

因此，后续文档和实验不得把当前模型描述成“真实无人艇动力学模型”。

### 4. 动作语义

单步动作定义为：

```python
action = [v_cmd, omega_cmd]
```

- `v_cmd`：目标线速度，单位为 `m/s`。
- `omega_cmd`：目标角速度，单位为 `rad/s`。

这两个动作量表示速度指令，不表示推力、油门、加速度、电机转矩或舵角。

动作由策略或其他决策模块产生，由环境传递给 `UsvAgent`。`UsvAgent` 对动作进行限幅并执行运动学更新。动作的最终数值范围尚未冻结，后续结合环境尺度和训练稳定性确定。

### 5. Agent 内部状态

`UsvAgent` V1.0 保存以下自身物理状态：

```python
state = [x, y, psi, v, omega]
```

状态顺序和含义固定为：

| 索引 | 名称 | 含义 |
| ---: | --- | --- |
| 0 | `x` | 世界坐标系中的横向位置 |
| 1 | `y` | 世界坐标系中的纵向位置 |
| 2 | `psi` | 当前航向角 |
| 3 | `v` | 当前实际执行的线速度 |
| 4 | `omega` | 当前实际执行的角速度 |

对外返回状态时，建议使用形状为 `(5,)` 的浮点 NumPy 数组，并返回新对象，避免调用方通过修改数组间接破坏 Agent 内部状态。

### 6. Reset 语义

Agent 通过以下接口开始或重新开始一个 Episode：

```python
reset(init_x, init_y, init_psi)
```

重置后：

```text
x = init_x
y = init_y
psi = normalize(init_psi)
v = 0
omega = 0
```

`init_psi` 也必须归一化到 `[-pi, pi)`，保证所有入口的航向角表示一致。

Agent 不保存固定起点。每个 Episode 的初始位置和初始航向由 Environment 生成并传入，Agent 只负责按照传入值初始化自身状态。

### 7. dt 归属

动作执行接口使用：

```python
apply_action(action, dt)
```

`dt` 由 Environment 传入，不作为 Agent 的固定属性。不同环境、训练配置和评估配置可以使用不同的仿真时间步，Agent 不绑定仿真时钟。

职责划分为：

- Environment 决定时间步长并推进仿真时间；
- Agent 接收 `dt`，根据动作和时间跨度更新自身状态；
- Agent 应拒绝 `dt <= 0` 的非法输入。

### 8. 碰撞半径归属

在 V1.0 中，USV 使用标量 `collision_radius` 作为自身几何尺寸的圆形近似。

- `collision_radius` 属于 Agent 的自身几何属性，单位为米（m）；
- Agent 知道自身尺寸，但不判断是否发生碰撞；
- 碰撞计算与碰撞判定属于 Environment；
- Environment 根据 Agent 尺寸、障碍物和其他实体的位置执行碰撞检测。

未来如改用矩形、椭圆或多边形船体，几何表示可以扩展，但“实体描述自身尺寸、环境负责碰撞判定”的职责边界保持不变。

### 9. 内部 State 与 PPO Observation 的边界

Agent 内部 State 只描述 USV 自身物理状态，不等于强化学习算法接收的 Observation。

未来 PPO Observation 可能包含：

- 目标相对距离；
- 目标相对角度的正弦和余弦；
- 自身线速度与角速度；
- 固定方向的 LiDAR 距离；
- 动态障碍物的相对位置和相对运动信息。

Observation 应优先采用相对量，以增强策略对不同地图和起终点配置的泛化能力。其最终维度、LiDAR 设计和动态障碍物表示方式目前尚未确定。

职责边界冻结如下：

- `UsvAgent` 保存和更新自身物理状态。
- `Environment` 结合 Agent 状态、目标、地图和障碍物构造 Observation。
- `Policy / PPO` 只接收 Observation 并输出 Action。
- `UsvAgent` V1.0 不实现 `get_observation()`，也不依赖 PPO 或 Stable-Baselines3。

### 10. 模块职责

| 模块 | 负责内容 | 不负责内容 |
| --- | --- | --- |
| `UsvAgent` | 自身状态、运动学、动作约束、几何尺寸 | 地图、奖励、碰撞判定、训练 |
| `Environment` | 地图、障碍物、碰撞、奖励、终止、Observation 构造 | PPO 网络结构 |
| `Policy / PPO` | 根据 Observation 输出 Action | 修改地图和 Agent 内部状态 |
| `experiments` | 训练、评估、配置、随机种子、统计 | 改变实体模型语义 |

### 11. 当前已冻结与暂未冻结内容

已冻结：

- 二维坐标系方向；
- 航向角正方向和归一化区间；
- SI 单位；
- 二维运动学抽象的模型定位；
- 动作为 `[v_cmd, omega_cmd]`；
- 内部状态为 `[x, y, psi, v, omega]`；
- State 与 Observation 分离；
- Observation 由 Environment 构造；
- `reset(init_x, init_y, init_psi)` 的重置行为；
- `dt` 由 Environment 传入，不存为 Agent 固定属性；
- V1.0 使用 `collision_radius` 表示自身几何尺寸；
- 碰撞计算和碰撞判定由 Environment 负责；
- Agent、Environment、Policy / PPO、experiments 的职责边界。

暂未冻结：

- `v_cmd` 和 `omega_cmd` 的最终取值范围；
- 最终 Observation 维度；
- LiDAR 具体参数；
- 动态障碍物信息表示；
- 多智能体 Observation 设计；
- 后续是否引入更高保真的动力学模型。

## UsvAgent V1.0 接口契约

本节将建模语义落实为实体类的可执行接口。接口稳定性优先于复杂的继承层次，当前不建立抽象基类，也不让实体类依赖 PPO、Gymnasium 或具体 Environment 实现。

### 1. 构造参数

```python
UsvAgent(
    agent_id,
    v_min=0.0,
    v_max=2.0,
    omega_max=pi / 2,
    collision_radius=1.0,
)
```

其中：

- `agent_id` 是由 Environment 管理的实体标识；
- `v_min`、`v_max`、`omega_max` 和 `collision_radius` 必须是有限数值；
- `v_min <= v_max`；
- `omega_max > 0`；
- `collision_radius > 0`。

上述速度和半径默认值仅用于形成可运行的 V1.0 实体，具体实验参数仍应由配置或 Environment 覆盖，不能视为最终实验结论。

### 2. 状态不变量

任何合法的 Agent 状态都应满足：

- `x`、`y`、`v`、`omega` 为有限浮点数；
- `psi` 为有限浮点数，且始终位于 `[-pi, pi)`；
- 执行动作后，`v` 位于 `[v_min, v_max]`；`reset()` 时按 Episode 初始语义将 `v` 清零；
- `omega` 始终位于 `[-omega_max, omega_max]`；
- `get_state()` 返回的顺序固定为 `[x, y, psi, v, omega]`。

### 3. 方法契约

| 方法 | 输入 | 输出或状态变化 | 约定 |
| --- | --- | --- | --- |
| `reset(init_x, init_y, init_psi)` | 初始位置和航向 | 重置内部状态；速度和角速度清零 | 起点由 Environment 提供；航向归一化 |
| `apply_action(action, dt)` | `[v_cmd, omega_cmd]` 与 `dt` | 限幅并推进一个仿真步 | 使用更新前的 `psi` 更新位置，再更新航向 |
| `get_state()` | 无 | 返回状态副本 | 不暴露内部可变数组；不构造 Observation |
| `get_pos()` | 无 | 返回位置副本 `[x, y]` | 不执行碰撞检测 |
| `_normalize_angle(angle)` | 任意有限角度 | 返回 `[-pi, pi)` 内的角度 | `pi` 统一表示为 `-pi` |

### 4. 错误处理边界

实体层只对自身接口的基本合法性负责：

- `dt <= 0` 时抛出 `ValueError`；
- Action 不是形状为 `(2,)` 的数值序列时抛出 `ValueError`；
- 参数或初始状态不是有限数值时抛出 `ValueError`。

实体层不负责推断地图规则、修复障碍物配置、计算奖励或判断 Episode 是否成功。

### 5. 代码可读性要求

`UsvAgent` 类、每个公开方法、每个静态辅助方法都必须有中文 docstring。涉及坐标更新、动作限幅、角度归一化和状态副本的关键代码必须有中文行内注释，便于用户脱离 Codex 独立解释和修改。

## 二维一阶运动学 V1.0

### 1. 离散更新公式

对一个长度为 `dt` 的仿真步，使用动作限幅后的实际速度 `v` 和角速度 `omega`：

```text
x(t+1) = x(t) + v * cos(psi(t)) * dt
y(t+1) = y(t) + v * sin(psi(t)) * dt
psi(t+1) = normalize(psi(t) + omega * dt)
```

这里的 `t+1` 表示下一个离散仿真状态，不表示连续时间中的整数秒。

### 2. 固定更新顺序

更新顺序是接口契约的一部分，不可在不同实现中混用：

1. 读取更新前的 `psi(t)`；
2. 使用 `v`、`psi(t)` 和 `dt` 更新 `x`、`y`；
3. 使用 `omega` 和 `dt` 更新 `psi`；
4. 将新的 `psi` 归一化到 `[-pi, pi)`。

例如初始 `psi=0`，同一步执行前进和左转时，位置仍沿旧的 `+x` 方向更新，不能先转向再用新航向计算位移。

### 3. 动作限幅顺序

原始动作先限幅，再进入运动学计算：

```text
v_cmd     -> clip(v_cmd, v_min, v_max)
omega_cmd -> clip(omega_cmd, -omega_max, omega_max)
```

Agent 保存的 `v` 和 `omega` 是实际执行的限幅后数值，而不是未经处理的原始指令。这样可以保证实体状态始终满足速度状态不变量。

### 4. 最低输入检查

- `dt` 必须是大于 0 的有限数值，否则抛出 `ValueError`；
- Action 必须是形状为 `(2,)` 的数值序列 `[v_cmd, omega_cmd]`，否则抛出 `ValueError`；
- Action 中的 `NaN` 或 `Inf` 不得进入运动学计算。

### 5. 运动学范围

本节只定义单个 USV 的状态推进，不定义以下内容：

- 障碍物或其他 USV 的碰撞判定；
- 地图边界和越界处理；
- 奖励函数；
- Episode 成功、失败或超时；
- PPO、A*、APF 或其他策略算法。

### 6. 运动学验收测试矩阵

`tests/test_usv_agent.py` 至少应覆盖以下行为：

| 测试场景 | 验证内容 |
| --- | --- |
| x 轴直线运动 | `psi=0` 时位置沿 x 轴推进 |
| y 轴直线运动 | `psi=pi/2` 时位置沿 y 轴推进 |
| 原地旋转 | `v=0` 时位置不变、航向改变 |
| 先平移后旋转 | 位置使用更新前的 `psi` 计算 |
| 角度归一化 | 航向角不超出 `[-pi, pi)` |
| reset | 位姿恢复、速度和角速度清零 |
| 线速度限幅 | `v_cmd` 被限制到 `[v_min, v_max]` |
| 角速度限幅 | `omega_cmd` 被限制到 `[-omega_max, omega_max]` |
| 非法 `dt` | `dt <= 0` 或非有限时抛出 `ValueError` |
| 非法 Action | Action 不是两个有限数值时抛出 `ValueError` |

## 封装验证实验

### 1. 实验代码

```python
agent = UsvAgent("test-usv")
agent.reset(1, 2, 0)

state = agent.get_state()
state[0] = 999

print(agent.x)
```

预期输出：

```text
1.0
```

### 2. 实验结论

`get_state()` 每次调用都会根据 `x`、`y`、`psi`、`v` 和 `omega` 创建一个新的 NumPy 数组。返回数组与 Agent 内部属性不是同一个可变对象，因此执行 `state[0] = 999` 只会修改外部变量 `state`，不会修改 `agent.x`。

这里保护的是“通过状态返回值间接修改内部状态”的风险。当前 V1.0 的 `x` 等属性仍然是公开属性，调用方在语法上依然可以直接执行 `agent.x = 999`；项目约定外部模块应通过 `reset()` 和 `apply_action()` 改变状态。是否进一步使用私有属性或只读 property 封装，留到出现真实维护需求时再决定，不在 Day 2 提前增加复杂度。

### 3. 自动化验收

对应单元测试为：

```text
test_get_state_returns_independent_array
```

测试同时验证：

- 返回数组确实可以被外部修改；
- 修改返回数组后 `agent.x` 仍为原值；
- 再次调用 `get_state()` 可以获得未被污染的内部状态。
