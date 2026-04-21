# -*- coding: utf-8 -*-
# @Time    : 2026/3/27 
# @File    : backtest_simple.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""
#!/usr/bin/env python3
"""
简单回测脚本
用法：python scripts/backtest_simple.py --days 200 [--symbol 1INCHBTC] [--threshold 0.6]
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import timedelta
from loguru import logger

from utils import load_config
from features.feature_engineer import FeatureEngineer
from vector_db.storage import VectorStorage
from services.prediction_service import PredictionService


def parse_args():
    parser = argparse.ArgumentParser(description="回测脚本")
    parser.add_argument("--days", type=int, default=200, help="回测天数（从最新日期向前推）")
    parser.add_argument("--symbol", type=str, default=None, help="指定股票/币种，None表示全部")
    parser.add_argument("--threshold", type=float, default=0.6, help="开仓阈值（上涨概率）")
    parser.add_argument("--period", type=int, default=5, help="预测周期（天）")
    parser.add_argument("--top_k", type=int, default=10, help="相似状态数量")
    parser.add_argument("--weighting", type=str, default="distance", help="加权方式")
    return parser.parse_args()


def load_data(data_path: str, symbol: str = None):
    """加载特征数据"""
    files = list(Path(data_path).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"未找到数据文件: {data_path}")
    df_list = []
    for f in files:
        df = pd.read_csv(f)
        df_list.append(df)
    df = pd.concat(df_list, ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    if symbol:
        df = df[df['symbol'] == symbol]
    df = df.sort_values('date').reset_index(drop=True)
    return df


def backtest(df, config, args):
    """执行回测"""
    # 初始化组件（复用已有模型）
    feature_engineer = FeatureEngineer(config)
    vector_storage = VectorStorage(config)
    prediction_service = PredictionService(config)

    # 加载特征工程模型
    feature_engineer.load_models(version="v1")
    logger.info(f"特征数量: {len(feature_engineer.feature_names)}")

    # 连接向量库
    vector_storage.connect()
    vector_storage.create_collection()
    logger.info(f"向量库记录数: {vector_storage.get_count()}")

    # 准备数据
    df = df.dropna(subset=feature_engineer.feature_names + ['close'])
    if len(df) < args.days:
        logger.warning(f"数据不足 {args.days} 天，使用全部 {len(df)} 天")

    # 回测日期范围
    end_date = df['date'].max()
    start_date = end_date - timedelta(days=args.days)
    test_df = df[df['date'] >= start_date].copy()
    test_df = test_df.sort_values('date').reset_index(drop=True)

    logger.info(f"回测区间: {test_df['date'].min().date()} 至 {test_df['date'].max().date()}")
    logger.info(f"共 {len(test_df)} 个交易日")

    # 策略参数
    hold_days = args.period
    position = 0  # 当前持仓方向（0空仓，1多仓）
    entry_date = None
    entry_price = None

    # 记录交易
    trades = []
    daily_returns = []  # 每日收益率（模拟净值）

    # 遍历每个交易日（从最早有足够历史数据开始）
    for i, row in test_df.iterrows():
        current_date = row['date']
        features = {name: row[name] for name in feature_engineer.feature_names}

        # 提取当前特征向量
        features_df = pd.DataFrame([features])
        query_vec, _ = feature_engineer.transform(features_df)

        # 查询相似状态（只使用当前日期之前的数据，避免未来信息）
        where_filter = {'date': {'$lt': current_date.strftime('%Y-%m-%d')}}
        results = vector_storage.query(
            query_vector=query_vec,
            top_k=args.top_k,
            where_filter=where_filter
        )

        if not results['ids']:
            continue  # 无相似状态

        # 计算预测统计
        similar_states = []
        for j in range(len(results['ids'])):
            meta = results['metadatas'][j]
            similar_states.append({
                'future_ret_1d': meta.get('future_ret_1d'),
                'future_ret_5d': meta.get(f'future_ret_{args.period}d'),
                'distance': results['distances'][j]
            })
        prediction = prediction_service.calculate_statistics(
            similar_states,
            weighting_method=args.weighting
        )
        up_prob = prediction.get(f'up_probability_{args.period}d', 0.5)

        # 交易逻辑
        if position == 0:
            # 空仓，判断是否开仓
            if up_prob >= args.threshold:
                position = 1
                entry_date = current_date
                entry_price = row['close']
                logger.debug(f"开仓 {current_date.date()} 价格 {entry_price:.2f}")
        else:
            # 已持仓，判断是否平仓
            if (current_date - entry_date).days >= hold_days:
                # 到期平仓
                exit_price = row['close']
                ret = (exit_price - entry_price) / entry_price
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': ret,
                    'signal': up_prob
                })
                logger.debug(f"平仓 {current_date.date()} 收益 {ret:.2%}")
                position = 0
                entry_date = None
                entry_price = None
            else:
                # 持仓中，记录每日收益率（用于净值计算）
                if i > 0:
                    daily_ret = (row['close'] - test_df.iloc[i-1]['close']) / test_df.iloc[i-1]['close']
                    daily_returns.append(daily_ret)

    # 计算绩效指标
    if trades:
        returns = [t['return'] for t in trades]
        win_rates = [r for r in returns if r > 0]
        loss_rates = [r for r in returns if r <= 0]
        total_return = (1 + np.array(returns)).prod() - 1
        win_rate = len(win_rates) / len(returns) if returns else 0
        avg_win = np.mean(win_rates) if win_rates else 0
        avg_loss = np.mean(loss_rates) if loss_rates else 0
        profit_loss_ratio = -avg_win / avg_loss if avg_loss != 0 else 0
        # 夏普比率（假设无风险利率0）
        if daily_returns:
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
        else:
            sharpe = 0
        # 最大回撤
        cumulative = (1 + np.array(daily_returns)).cumprod() if daily_returns else np.array([1])
        max_drawdown = (np.maximum.accumulate(cumulative) - cumulative).max()

        print("\n" + "="*60)
        print(f"回测结果 - {args.symbol if args.symbol else '全部'}")
        print("="*60)
        print(f"回测区间: {test_df['date'].min().date()} ~ {test_df['date'].max().date()}")
        print(f"开仓阈值: {args.threshold}, 持仓周期: {hold_days}日")
        print(f"交易次数: {len(trades)}")
        print(f"胜率: {win_rate:.2%}")
        print(f"平均盈利: {avg_win:.2%}, 平均亏损: {avg_loss:.2%}")
        print(f"盈亏比: {profit_loss_ratio:.2f}")
        print(f"累计收益率: {total_return:.2%}")
        print(f"夏普比率: {sharpe:.2f}")
        print(f"最大回撤: {max_drawdown:.2%}")
        print("="*60)
    else:
        print("没有产生任何交易。")

    return trades


def main():
    args = parse_args()
    config = load_config()  # 从 config/ 加载配置

    # 数据路径（根据你的实际设置）
    data_path = '/datas/coin/'  # 通常是 ./datas/raw/*.csv
    if isinstance(data_path, str) and '*' in data_path:
        data_path = str(Path(data_path).parent)

    df = load_data(data_path, symbol=args.symbol)
    backtest(df, config, args)


if __name__ == "__main__":
    main()