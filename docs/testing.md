# 测试与验收

## 测试入口

当前测试按职责拆分：

- [`tests/test_usv_agent.py`](../tests/test_usv_agent.py)：覆盖 `UsvAgent` 的接口合法性、状态不变量和二维一阶运动学更新；
- [`tests/test_pid_controller.py`](../tests/test_pid_controller.py)：覆盖 P-Day10 PID 计算、航点误差、停止容差和 Agent 接口连接；
- [`tests/test_usv_mlp.py`](../tests/test_usv_mlp.py)：覆盖教学型 MLP 的输入输出、参数和梯度；
- [`tests/test_logging_and_debugging.py`](../tests/test_logging_and_debugging.py)：覆盖日志级别、控制台输出、文件输出、重复配置和参数校验。

项目采用 `src/` 布局。开发和测试前必须在选定的虚拟环境中安装项目及开发
依赖，然后在项目根目录运行测试：

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

pytest 配置统一位于 `pyproject.toml`，不设置 `pythonpath = src`。IDE / PyCharm
运行单测时也应使用上述环境的解释器。可编辑安装后，普通源码修改无需重装；
修改包结构、依赖声明或入口点后重新安装。当前仓库没有 CI 配置，未来 CI
应执行相同的先安装、后测试流程。

日常开发使用可编辑安装验证接口与行为；它不能单独证明 wheel 的内容完整。
发布或源码布局变更时，还应构建 wheel，在仓库外的独立环境中安装并验证
导入和测试，避免仓库路径掩盖遗漏。依赖声明与安装见
[README 的依赖说明](../README.md#依赖管理)。

## 运动学验收矩阵

| 测试场景 | 验证内容 |
| --- | --- |
| x 轴直线运动 | `psi=0` 时位置沿 x 轴推进 |
| y 轴直线运动 | `psi=pi/2` 时位置沿 y 轴推进 |
| 原地旋转 | `v=0` 时位置不变、航向改变 |
| 先平移后旋转 | 位置使用更新前的 `psi` 计算 |
| 角度归一化 | 航向角始终位于 `[-pi, pi)` |
| reset | 位姿恢复、速度和角速度清零 |
| 线速度限幅 | `v_cmd` 被限制到 `[v_min, v_max]` |
| 角速度限幅 | `omega_cmd` 被限制到 `[-omega_max, omega_max]` |

## 接口与封装验收矩阵

| 测试场景 | 验证内容 |
| --- | --- |
| 独立状态副本 | 修改 `get_state()` 返回数组不会改变 Agent 内部状态 |
| 位置副本 | `get_pos()` 返回独立的二维位置数组 |
| 非法 `dt` | `dt <= 0` 或非有限时抛出 `ValueError` |
| 非法 Action | Action 不是两个有限数值时抛出 `ValueError` |
| 非法构造参数 | 速度范围、角速度上限和碰撞半径违反约束时抛出 `ValueError` |
| 非法初始状态 | `reset()` 的位置或航向不是有限数值时抛出 `ValueError` |

## P-Day10 PID 最小验收矩阵

| 测试场景 | 验证内容 |
| --- | --- |
| 标量 PID | 纯比例输出和控制器侧限幅正确 |
| 正前方航点 | 输出正 `v_cmd` 和零 `omega_cmd` |
| 跨越 `pi` | 航向误差采用 `[-pi, pi)` 内的最短角度 |
| 停止容差 | 距离不大于 `0.05 m` 时输出 `[0.0, 0.0]` |
| 艇后目标 | 距离与航向回路独立，不执行速度门控 |
| Agent 集成 | 输出可直接传给 `UsvAgent.apply_action()` 推进状态 |

完整零误差、饱和、异常输入组合测试和 2–3 组参数实验属于 P-Day11，不在
P-Day10 最小验收中提前扩展。

## 封装验证示例

```python
agent = UsvAgent("test-usv")
agent.reset(1, 2, 0)

state = agent.get_state()
state[0] = 999

assert agent.x == 1.0
```

`get_state()` 每次创建新的 NumPy 数组，因此外部修改只影响返回值，不会污染 Agent 内部状态。当前 `x`、`y` 等属性仍是公开属性；项目约定外部模块通过 `reset()` 和 `apply_action()` 改变状态，是否进一步封装为私有属性留待真实维护需求出现后再决定。

## 测试扩展方向

Environment 实现后，应补充地图边界、障碍物碰撞、奖励、终止条件和 Observation 维度测试；多智能体与动态障碍物应增加确定性种子下的回归测试。算法实验则应单独验证动作空间、Observation 归一化和训练/评估流程，不把训练结果测试混入实体层单元测试。

日志相关测试保持在工具层，重点验证配置行为和输出边界；业务模块只需验证是否在关键状态转换和异常路径上写入了必要上下文，不应把日志文本格式作为业务算法测试的核心断言。
