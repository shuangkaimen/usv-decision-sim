# 日志与调试

## 目标

为环境、训练和规划模块提供可追踪的运行信息，同时保持日志工具与业务逻辑解耦。日志用于记录上下文和诊断线索，不负责异常恢复、奖励计算或 Episode 判定。

## 日志工具约定

- 使用 Python 标准库 `logging`，不引入额外运行时依赖。
- 默认输出到控制台，格式包含时间、级别、logger 名称和消息。
- 可选写入 UTF-8 日志文件；缺失的父目录自动创建。
- `setup_logger()` 可重复调用，工具自己创建的 handler 会被替换，避免重复输出。
- 公共日志 API 使用英文名称和英文配置错误消息；业务日志可以根据项目用户界面约定使用中文。
- 批量实验可以关闭控制台输出，只保留文件日志，避免终端噪声影响进度观察。

示例：

```python
from usv_decision_sim.utils import setup_logger

logger = setup_logger("usv_decision_sim.environment", level="DEBUG")
logger.debug("step=%d action=%s", step, action)
logger.info("episode started")
logger.exception("environment step failed")
```

## 调试信息边界

后续 Environment 和训练循环应优先记录以下上下文：

- `episode`、`step` 和 `agent_id`；
- 动作输入、动作限幅结果和关键状态摘要；
- 碰撞、越界、终止原因和异常类型；
- 随机种子、地图标识和实验配置版本。

不建议在每一步默认输出完整 Observation 或大数组。详细数组只在 `DEBUG` 级别按需开启，避免日志本身改变实验可读性和运行成本。

## 测试矩阵

| 场景 | 验证内容 |
| --- | --- |
| 控制台输出 | 级别、logger 名称和消息可见 |
| 文件输出 | UTF-8 文本、父目录创建和写入成功 |
| 级别过滤 | 低于配置级别的消息不输出 |
| 重复配置 | 不产生重复 handler 或重复日志 |
| 默认获取 | `get_logger()` 返回同一实例并只初始化一次 |
| 非法配置 | 非法级别立即抛出配置错误（`ValueError` 或 `TypeError`） |
| 关闭控制台 | `console=False` 时仅写文件 |

## 验证命令

```bash
pytest tests/test_logging_and_debugging.py -q
pytest -q
ruff check src tests
black --check src tests
```

对应测试文件为 [`tests/test_logging_and_debugging.py`](../../tests/test_logging_and_debugging.py)。
