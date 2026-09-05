# 项目知识与建模约定

本文档记录跨模块共享、需要长期保持一致的建模语义和冻结决策。具体接口、仿真公式、算法边界和测试矩阵分别见：

- [architecture.md](architecture.md)：模块分层、职责和数据流；
- [api.md](api.md)：`UsvAgent` V1.0 接口契约；
- [simulation.md](simulation.md)：坐标、单位、运动学和仿真边界；
- [algorithm.md](algorithm.md)：Observation、PPO 与规划算法边界；
- [testing.md](testing.md)：测试入口和验收矩阵。

## USV 建模约定 V1.0

**冻结日期：** 2026-09-02  
**适用范围：** 当前单 USV 二维运动学实体模型

### 已冻结语义

- 使用二维笛卡尔坐标系：`x` 向右为正、`y` 向上为正。
- `psi=0` 表示船首沿 `+x`，逆时针为正。
- 航向角统一归一化到半开区间 `[-pi, pi)`，`pi` 统一表示为 `-pi`。
- 核心计算统一使用 SI 单位，角度使用弧度。
- 当前模型是受无人艇任务启发的二维平面运动学抽象，不代表真实水动力学仿真。
- 单步动作是 `[v_cmd, omega_cmd]`，表示目标线速度和目标角速度。
- Agent 内部 State 固定为 `[x, y, psi, v, omega]`。
- State 与 Observation 分离；Observation 由 Environment 构造。
- `reset(init_x, init_y, init_psi)` 后位置使用输入值，航向归一化，`v=0`、`omega=0`。
- `dt` 由 Environment 传入，不作为 Agent 固定属性；Agent 拒绝 `dt <= 0`。
- V1.0 使用 `collision_radius` 表示自身圆形几何尺寸。
- Agent 描述自身尺寸，Environment 负责碰撞计算和判定。
- `UsvAgent`、Environment、Policy/PPO、experiments 的职责边界按 [architecture.md](architecture.md) 执行。

### V1.0 假设

- USV 抽象为二维平面中的运动实体。
- 底层速度控制器可以理想跟踪目标速度。
- 一个仿真步内，速度指令经过限幅后立即生效。
- 暂不模拟船体惯性、推进器动力学、水动力、加速度约束和控制延迟。

因此，文档和实验不得将当前模型描述为真实无人艇动力学模型。

## 暂未冻结内容

- `v_cmd` 和 `omega_cmd` 的最终取值范围；
- 最终 Observation 维度、归一化方法和 LiDAR 设计；
- 动态障碍物和多智能体 Observation 表示；
- 奖励函数及 Episode 成功、失败、超时条件；
- 后续是否引入更高保真的动力学模型。

当上述内容被实验验证并形成稳定接口时，应补充冻结日期、适用范围和迁移说明，而不是悄然改变 V1.0 语义。

## 变更原则

1. 跨模块共享的单位、坐标和状态顺序必须先更新本文件，再同步到实现和测试。
2. 改变动作语义、状态布局或更新顺序时，应提高模型版本并补充迁移说明。
3. 新增 Environment 或算法能力时，优先扩展上层职责，不把地图、奖励和 Observation 逻辑塞入 Agent。
