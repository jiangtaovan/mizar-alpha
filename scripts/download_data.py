#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立数据下载模块
从 feature_config.yaml 读取特征列表，下载行情数据并计算技术指标
保存行情和指标，包含必需列: date, symbol, open_price, current_price
"""

import sys
import argparse
import yaml
from pathlib import Path
from loguru import logger

from data.tdx import StockDataFetcher, IndicatorCalculator

def load_feature_names(config_path: str = "config/feature_config.yaml") -> list:
    """从特征配置文件读取需要计算的指标列名"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"特征配置文件不存在: {config_path}")
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    features = config.get('features', [])
    extra = config.get('extra_features', [])
    all_features = features + extra
    logger.info(f"从 {config_path} 加载特征 {len(all_features)} 个")
    return all_features


def download_stock_data(symbol: str, count: int = 800, start_offset: int = 0,
                        save_quote: bool = True, save_indicators: bool = True) -> bool:
    """
    下载股票数据并计算指标，保存到本地
    """
    logger.info(f"开始处理 {symbol} (count={count}, offset={start_offset})")

    # 1. 获取行情数据
    fetcher = StockDataFetcher()
    df = fetcher.get_daily_data(symbol, count=count, start_offset=start_offset)
    if df.empty:
        logger.error(f"获取 {symbol} 行情失败")
        return False

    logger.info(f"行情数据获取成功，共 {len(df)} 条")

    # 2. 保存行情数据（可选）
    if save_quote:
        quote_path = fetcher.save_quote_data(df, symbol, start_offset)
        if quote_path:
            logger.info(f"行情已保存: {quote_path}")
        else:
            logger.warning("行情保存失败")

    # 3. 加载特征列表并计算指标
    try:
        feature_names = load_feature_names()
    except Exception as e:
        logger.error(f"加载特征配置失败: {e}")
        return False

    calculator = IndicatorCalculator(feature_names)
    # indicators = calculator.calculate_all(df, trim_before_calc=True, trim_size=60)
    indicators = calculator.calculate_all( df, trim_before_calc=True, trim_size=60 )

    if save_indicators:
        calculator.save( indicators, symbol=symbol, offset=start_offset, full=True )

    if indicators is None:
        logger.error("指标计算失败")
        return False


def main():
    parser = argparse.ArgumentParser(description="下载股票数据并计算技术指标")
    parser.add_argument("symbol", type=str, help="股票代码，如 000001 或 000001.SH")
    parser.add_argument("--count", "-c", type=int, default=800, help="获取数据条数（默认800）")
    parser.add_argument("--offset", "-o", type=int, default=0, help="起始偏移，0=最新（默认0）")
    parser.add_argument("--no-quote", action="store_true", help="不保存行情数据")
    parser.add_argument("--no-indicators", action="store_true", help="不保存指标数据")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    # 配置日志
    logger.remove()
    level = "DEBUG" if args.verbose else "INFO"
    logger.add(sys.stderr, level=level)

    success = download_stock_data(
        symbol=args.symbol,
        count=args.count,
        start_offset=args.offset,
        save_quote=not args.no_quote,
        save_indicators=not args.no_indicators
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()