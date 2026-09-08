"""项目日志工具及 Day4 调试约定测试。"""

from __future__ import annotations

import logging

import pytest

from usv_decision_sim.utils.logger import get_logger, setup_logger


def _managed_handlers(logger: logging.Logger) -> list[logging.Handler]:
    """测试只统计工具自有 handler，避免把调用方扩展误判为重复配置。"""
    return [
        handler
        for handler in logger.handlers
        if getattr(handler, "_usv_decision_sim_handler", False)
    ]


def test_setup_logger_emits_level_and_message_to_console(capsys) -> None:
    """控制台日志必须保留定位问题所需的级别、来源和消息。"""
    logger = setup_logger("test.logging.console", level="INFO")

    logger.info("episode started")

    captured = capsys.readouterr()
    assert "INFO" in captured.err
    assert "test.logging.console" in captured.err
    assert "episode started" in captured.err


def test_setup_logger_writes_utf8_messages_to_file(tmp_path) -> None:
    """实验日志需要支持中文业务信息，并允许直接使用尚未创建的运行目录。"""
    log_path = tmp_path / "nested" / "run.log"
    logger = setup_logger("test.logging.file", log_file=log_path, console=False)

    logger.warning("碰撞检测告警")

    content = log_path.read_text(encoding="utf-8")
    assert "WARNING" in content
    assert "碰撞检测告警" in content


def test_setup_logger_filters_messages_below_configured_level(capsys) -> None:
    """级别过滤应在开发诊断能力与正式运行噪声之间提供明确边界。"""
    logger = setup_logger("test.logging.level", level=logging.WARNING)

    logger.info("hidden")
    logger.error("visible")

    captured = capsys.readouterr()
    assert "hidden" not in captured.err
    assert "visible" in captured.err


def test_setup_logger_is_idempotent_for_managed_handlers(tmp_path) -> None:
    """重复初始化常见于测试和脚本入口，不应造成日志重复或继续写旧文件。"""
    log_path = tmp_path / "first.log"
    logger = setup_logger("test.logging.idempotent", log_file=log_path)
    setup_logger("test.logging.idempotent", log_file=tmp_path / "second.log")

    assert len(_managed_handlers(logger)) == 2
    logger.info("only once")
    assert "only once" not in log_path.read_text(encoding="utf-8")
    assert "only once" in (tmp_path / "second.log").read_text(encoding="utf-8")


def test_get_logger_configures_default_logger_only_when_needed() -> None:
    """模块可反复获取同名 logger，但默认日志出口只能初始化一次。"""
    first = get_logger("test.logging.default")
    second = get_logger("test.logging.default")

    assert first is second
    assert len(_managed_handlers(first)) == 1


@pytest.mark.parametrize("level", ["NOT_A_LEVEL", True, 1.5])
def test_setup_logger_rejects_invalid_level(level) -> None:
    """非法级别应在配置阶段失败，避免运行过程中静默丢失日志。"""
    with pytest.raises((ValueError, TypeError), match="level"):
        setup_logger("test.logging.invalid", level=level)


def test_setup_logger_can_disable_console_output(capsys, tmp_path) -> None:
    """批量实验可关闭控制台输出，以免大量运行日志干扰终端进度信息。"""
    logger = setup_logger(
        "test.logging.no_console",
        log_file=tmp_path / "run.log",
        console=False,
    )

    logger.info("file only")

    assert capsys.readouterr().err == ""
    assert "file only" in (tmp_path / "run.log").read_text(encoding="utf-8")
