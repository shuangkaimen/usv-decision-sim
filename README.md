# usv-decision-sim
无人集群智能决策与协同仿真平台

## 安装与测试

项目要求 Python 3.11 或更高版本，采用 `src/` 源码布局。开发和测试前必须在
项目根目录创建或激活虚拟环境，并使用该环境的解释器安装项目及开发依赖：

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

可编辑安装后，普通源码修改直接生效，无需每次重装；修改包结构、依赖声明或
入口点后应重新执行安装命令。IDE / PyCharm 的测试解释器应选择同一个已安装
项目的虚拟环境。pytest 配置只维护在 `pyproject.toml` 中，不额外注入 `src`
到导入路径。当前仓库没有 CI 配置；未来 CI 必须先安装项目，再运行检查。

## 目录职责

| 目录 | 职责 |
| --- | --- |
| `src/usv_decision_sim/` | 可安装、可复用的运行时代码，统一使用 `usv_decision_sim.*` 导入 |
| `tests/` | 测试已安装项目的接口与行为 |
| `scripts/` | 教学、训练、批处理等命令行入口，调用核心库 |
| `experiments/` | 实验编排、评估、统计与运行产物；结果和 checkpoint 不入库 |
| `configs/` | 后续共享的实验输入配置；同一参数以选定配置为准，不再维护另一套默认值 |
| `docs/` | 正式技术文档；模块位置以 [系统架构](docs/architecture.md#模块划分) 为准 |
| `.project_manager/` | 本地项目记忆与执行计划，引用正式文档中的架构事实 |

新增算法和规划实现按需加入核心包，不在顶层创建 `rl`、`planning`、`marl`
等运行时包，也不提前创建空模块。实验专属配置随对应实验组织，只有实际需要
跨实验共享时才放入 `configs/`。

## 依赖管理

`pyproject.toml` 的 `[project]` 中 `dependencies` 字段是运行时依赖的唯一声明来源，
`[project.optional-dependencies].dev` 声明 pytest、Black、Ruff 等开发依赖。
修改依赖声明后，重新执行 `python -m pip install -e ".[dev]"`，并运行测试。
包的构建依赖由 `[build-system]` 独立声明。

当前阶段只维护依赖版本范围，安装时解析兼容版本，不保证不同时间安装的
版本完全相同。开始正式 PPO/MARL 实验前，再选择统一的环境锁定方式
（例如 `uv.lock`），并随实验记录 Python、PyTorch、CUDA 等环境版本。

## 文档

项目文档按“核心技术文档 + 开发实践指南”组织，完整导航见 [`docs/README.md`](docs/README.md)：

- [系统架构](docs/architecture.md)
- [API 与接口契约](docs/api.md)
- [仿真与运动学](docs/simulation.md)
- [算法与决策边界](docs/algorithm.md)
- [测试与验收](docs/testing.md)
- [项目知识与建模约定](docs/knowledge.md)
- [日志与调试指南](docs/guides/logging_and_debugging.md)
