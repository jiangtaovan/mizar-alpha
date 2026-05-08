# -*- coding: utf-8 -*-
"""
集中式日志配置模块

设计原则：
  - 一次初始化，全局生效（configure_logging 幂等）
  - 各模块可通过 add_module_sink() 添加专属日志文件，无需重复调用 setup_logging
  - 所有配置从统一的 yaml 加载，支持通过 system.log_dir / system.log_retention 定制

使用示例：
    from mizar.utils.logging import configure_logging, add_module_sink

    # 全局初始化（在 CLI 回调或进程入口调用一次即可）
    configure_logging(config)

    # 模块级独立日志文件
    add_module_sink("trading", "logs/paper_trading.log", level="DEBUG")
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

_logging_initialized: bool = False
_module_sinks: dict[str, int] = {}


def configure_logging(config: Optional[dict] = None) -> None:
    """全局日志初始化（幂等，仅首次调用生效）。

    配置来源：
      - system.log_level      日志级别，默认 ``INFO``
      - system.log_format     日志格式，``text`` 或 ``json``
      - system.log_dir        日志目录，默认 ``logs``
      - system.log_retention  日志保留天数，默认 ``7 days``

    Args:
        config: 系统配置字典，可为 ``None``（此时使用全默认值）
    """
    global _logging_initialized
    if _logging_initialized:
        return

    cfg = config or {}
    system_cfg = cfg.get("system", {}) if isinstance(cfg, dict) else {}

    log_level = system_cfg.get("log_level", "INFO")
    log_format = system_cfg.get("log_format", "text")
    log_dir = system_cfg.get("log_dir", "logs")
    log_retention = system_cfg.get("log_retention", "7 days")

    # 移除 loguru 默认 stderr sink
    logger.remove()

    # ── 控制台 sink ──
    if log_format == "json":
        logger.add(
            sys.stdout,
            format="{time:ISO8601},{level},{name},{function},{line},{message}",
            level=log_level,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            level=log_level,
            colorize=True,
        )

    # ── 主日志文件 sink（所有模块的输出汇集于此）──
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path / "mizar_{time:YYYY-MM-DD}.log"),
        rotation="00:00",
        retention=log_retention,
        level=log_level,
        encoding="utf-8",
    )

    _logging_initialized = True


def add_module_sink(
    module_name: str,
    file_path: str,
    level: Optional[str] = None,
    rotation: str = "00:00",
    retention: str = "7 days",
) -> None:
    """为指定模块添加独立日志文件 sink（同名模块仅注册一次）。

    新增的日志文件独立于主 ``mizar_*.log``，方便按子系统追踪。

    Args:
        module_name: 模块标识（去重 key），例如 ``"trading"``
        file_path:   日志文件路径，例如 ``"logs/paper_trading.log"``
        level:       文件日志级别，为 ``None`` 时沿用全局级别
        rotation:    日志轮转策略，默认每日零点
        retention:   日志保留时长，默认 7 天
    """
    if module_name in _module_sinks:
        return

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    sink_id = logger.add(
        str(path),
        rotation=rotation,
        retention=retention,
        level=level,
        encoding="utf-8",
    )
    _module_sinks[module_name] = sink_id


def reset_logging() -> None:
    """重置日志状态（仅用于测试）。"""
    global _logging_initialized
    logger.remove()
    _logging_initialized = False
    _module_sinks.clear()
