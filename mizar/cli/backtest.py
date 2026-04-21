# -*- coding: utf-8 -*-
# @Time    : 2026/4/10 
# @File    : backtest.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""

# mizar/cli/backtest.py
import click
from pathlib import Path
from ..back.runners.single import run_single_backtest

DEFAULT_CONFIG_PATH = Path( __file__ ).parent.parent.parent / "config" / "backtest_config.yaml"


@click.command( name="backtest" )
@click.option( "--config", "-c", default=None, help="配置文件路径（默认使用项目内置配置）" )
@click.option( "--symbol", "-s", required=True, help="股票代码（如 000001）" )
@click.option( "--output", "-o", help="输出目录（覆盖配置文件中的设置）" )
def backtest_cmd(config, symbol, output):
    """运行单标的回测"""
    if config is None:
        config = str( DEFAULT_CONFIG_PATH )
        if not Path( config ).exists():
            raise click.ClickException( f"默认配置文件不存在: {config}\n请通过 --config 指定配置文件" )
        click.echo( f"使用默认配置: {config}" )

    run_single_backtest( config, symbol, output )