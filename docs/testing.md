# 测试与验收

## 测试入口

当前单元测试位于 [`tests/test_usv_agent.py`](../tests/test_usv_agent.py)，覆盖 `UsvAgent` 的接口合法性、状态不变量和二维一阶运动学更新。

在项目根目录运行：

```bash
pytest
```

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
