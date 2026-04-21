# -*- coding: utf-8 -*-
# @Time    : 2026/3/29 
# @File    : config_loader.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00

# utils/config_loader.py

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from loguru import logger
import sys

def load_config() -> Dict[str, Any]:
    """加载系统配置，按以下优先级查找配置文件：
    1. 环境变量 MIZAR_CONFIG_DIR 指定的目录
    2. 当前工作目录下的 config 目录
    3. 包安装目录的父目录下的 config 目录（用于 pip install 后的场景）
    """
    config_dir = os.environ.get( "MIZAR_CONFIG_DIR" )

    if config_dir:
        config_path = Path( config_dir ) / "system_config.yaml"
        if config_path.exists():
            with open( config_path, "r", encoding="utf-8" ) as f:
                return yaml.safe_load( f )
        else:
            raise FileNotFoundError( f"环境变量 MIZAR_CONFIG_DIR 指定的配置文件不存在: {config_path}" )

    # 尝试当前工作目录下的 config
    cwd_config = Path.cwd() / "config" / "system_config.yaml"
    if cwd_config.exists():
        with open( cwd_config, "r", encoding="utf-8" ) as f:
            return yaml.safe_load( f )

    # 尝试包所在目录的父目录下的 config（适用于 pip install 后）
    # try:
    #     import mizar
    #     pkg_dir = Path( mizar.__file__ ).parent
    #     parent_config = pkg_dir.parent / "config" / "system_config.yaml"
    #     if parent_config.exists():
    #         with open( parent_config, "r", encoding="utf-8" ) as f:
    #             return yaml.safe_load( f )
    # except ImportError:
    #     pass

    raise FileNotFoundError(
        "无法找到配置文件 system_config.yaml。请确保：\n"
        "1. 设置环境变量 MIZAR_CONFIG_DIR 指向正确的 config 目录\n"
        "2. 或在当前工作目录下存在 config/system_config.yaml\n"
        "3. 或项目根目录下存在 config/system_config.yaml"
    )
def setup_logging(config: dict):
    """配置日志"""
    log_level = config.get( 'system', {} ).get( 'log_level', 'INFO' )
    log_format = config.get( 'system', {} ).get( 'log_format', 'text' )

    if log_format == 'json':
        # JSON 格式日志
        logger.remove()
        logger.add(
            sys.stdout,
            format="{time:ISO8601},{level},{name},{function},{line},{message}",
            level=log_level,
            serialize=True
        )
    else:
        # 文本格式日志
        logger.remove()
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )

    # 同时输出到文件
    logger.add(
        "logs/mizar_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level=log_level,
        encoding='utf-8'
    )
