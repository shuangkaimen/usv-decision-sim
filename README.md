# usv-decision-sim
无人集群智能决策与协同仿真平台

## 安装与测试

项目采用 `src/` 源码布局。在项目根目录创建或激活虚拟环境后，执行可编辑安装：

```bash
python -m pip install -e .
pytest
```

运行时代码位于 [`src/usv_decision_sim/`](src/usv_decision_sim/)，测试位于 [`tests/`](tests/)。

## 文档

项目文档按主题组织在 [`docs/`](docs/) 目录：

- [系统架构](docs/architecture.md)
- [API 与接口契约](docs/api.md)
- [仿真与运动学](docs/simulation.md)
- [算法与决策边界](docs/algorithm.md)
- [测试与验收](docs/testing.md)
- [项目知识与建模约定](docs/knowledge.md)
