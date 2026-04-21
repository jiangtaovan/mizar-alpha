#!/usr/bin/env python3
"""
基于预计算特征文件和向量库的虚拟币回测脚本
路径写死，直接使用 datas/raw/Binance_AAVEETH_d_features.csv
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from loguru import logger

from utils import load_config
from features.feature_engineer import FeatureEngineer
from vector_db.storage import VectorStorage
from services.prediction_service import PredictionService


def load_features(file_path: str):
    """加载特征文件（已包含所有指标和未来收益标签）"""
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.6, help="开仓阈值")
    parser.add_argument("--period", type=int, default=5, help="持仓周期（天）")
    parser.add_argument("--top_k", type=int, default=10, help="检索数量")
    parser.add_argument("--weighting", type=str, default="distance", help="加权方式")
    args = parser.parse_args()

    # 特征文件路径（写死）
    feat_file = Path("datas/raw/Binance_AAVEETH_d_features.csv")
    if not feat_file.exists():
        logger.error(f"特征文件不存在: {feat_file}")
        sys.exit(1)

    logger.info(f"加载特征数据: {feat_file}")
    df = load_features(str(feat_file))
    logger.info(f"共 {len(df)} 条记录")
    logger.info(f"日期范围: {df['date'].min().date()} ~ {df['date'].max().date()}")

    # 加载系统组件
    config = load_config()
    feature_engineer = FeatureEngineer(config)
    vector_storage = VectorStorage(config)
    prediction_service = PredictionService(config)

    # 加载特征工程模型（归一化器、PCA）
    feature_engineer.load_models(version="v1")

    # 读取特征名称列表（从 models/selected_features.txt）
    model_dir = Path("models")
    with open(model_dir / "selected_features.txt", 'r') as f:
        feature_names = [line.strip() for line in f if line.strip()]
    logger.info(f"特征数量: {len(feature_names)}")

    # 连接向量库
    vector_storage.connect()
    vector_storage.create_collection()
    logger.info(f"向量库记录数: {vector_storage.get_count()}")

    # 回测参数
    min_idx = 50  # 跳过前50行，确保指标有效（SMA_50需要）
    position = 0
    entry_date = None
    entry_price = None
    trades = []
    daily_returns = []

    logger.info("开始回测...")
    for i in range(min_idx, len(df)):
        row = df.iloc[i]
        current_date = row['date']
        current_price = row['close']
        current_timestamp = int(current_date.timestamp())

        # 提取当前特征（按特征列表顺序）
        features = {}
        for name in feature_names:
            if name in row:
                features[name] = row[name]
            else:
                logger.warning(f"特征缺失: {name}，日期 {current_date}")
                features[name] = 0.0

        # 转换为查询向量
        features_df = pd.DataFrame([features])
        query_vec, _ = feature_engineer.transform(features_df)

        # 检索历史相似状态（只使用当前日期之前的数据）
        where_filter = {'date': {'$lt': current_timestamp}}
        results = vector_storage.query(
            query_vector=query_vec,
            top_k=args.top_k,
            where_filter=where_filter
        )

        if not results['ids']:
            continue

        # 构建 similar_states 列表（用于预测）
        similar_states = []
        for j in range(len(results['ids'])):
            meta = results['metadatas'][j]
            ret_key = f'future_ret_{args.period}d'
            if ret_key in meta:
                similar_states.append({
                    ret_key: meta[ret_key],
                    'distance': results['distances'][j]
                })

        if not similar_states:
            continue

        # 计算预测统计
        try:
            prediction = prediction_service.calculate_statistics(
                similar_states,
                weighting_method=args.weighting
            )
            up_prob = prediction.get(f'up_probability_{args.period}d', 0.5)
        except ZeroDivisionError:
            # 权重全零时使用等权平均
            up_prob = 0.5

        # 交易逻辑
        if position == 0:
            if up_prob >= args.threshold:
                position = 1
                entry_date = current_date
                entry_price = current_price
        else:
            if (current_date - entry_date).days >= args.period:
                exit_price = current_price
                ret = (exit_price - entry_price) / entry_price
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': ret,
                    'signal': up_prob
                })
                position = 0
            else:
                # 持仓中，记录每日收益率
                if i > 0:
                    daily_ret = (current_price - df.iloc[i-1]['close']) / df.iloc[i-1]['close']
                    daily_returns.append(daily_ret)

    # 绩效统计
    if trades:
        returns = [t['return'] for t in trades]
        win_rates = [r for r in returns if r > 0]
        loss_rates = [r for r in returns if r <= 0]
        total_return = (1 + np.array(returns)).prod() - 1
        win_rate = len(win_rates) / len(returns) if returns else 0
        avg_win = np.mean(win_rates) if win_rates else 0
        avg_loss = np.mean(loss_rates) if loss_rates else 0
        profit_loss_ratio = -avg_win / avg_loss if avg_loss != 0 else 0

        if daily_returns:
            daily_ret_mean = np.mean(daily_returns)
            daily_ret_std = np.std(daily_returns)
            sharpe = daily_ret_mean / daily_ret_std * np.sqrt(252) if daily_ret_std != 0 else 0
        else:
            sharpe = 0

        cumulative = (1 + np.array(daily_returns)).cumprod() if daily_returns else np.array([1])
        max_drawdown = (np.maximum.accumulate(cumulative) - cumulative).max()

        print("\n" + "="*60)
        print(f"回测结果 - AAVEETH")
        print("="*60)
        print(f"回测区间: {df['date'].min().date()} ~ {df['date'].max().date()}")
        print(f"开仓阈值: {args.threshold}, 持仓周期: {args.period}日")
        print(f"交易次数: {len(trades)}")
        print(f"胜率: {win_rate:.2%}")
        print(f"平均盈利: {avg_win:.2%}, 平均亏损: {avg_loss:.2%}")
        print(f"盈亏比: {profit_loss_ratio:.2f}")
        print(f"累计收益率: {total_return:.2%}")
        print(f"夏普比率: {sharpe:.2f}")
        print(f"最大回撤: {max_drawdown:.2%}")
        print("="*60)

        # 保存交易记录
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('backtest_trades1.csv', index=False)
        print("交易记录已保存到 backtest_trades1.csv")
    else:
        print("没有产生任何交易。")


if __name__ == "__main__":
    main()