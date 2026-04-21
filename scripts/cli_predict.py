# -*- coding: utf-8 -*-
# @Time    : 2026/3/29 
# @File    : cli_predict.py
# @Project : mizar-alpha
# @Author  : Chiang Tao
# @Version : 0.1.00
# -*- coding: utf-8 -*-
"""
CLI 交互式预测程序
用户输入股票代码，获取技术指标并预测未来涨跌
"""

import sys
import numpy as np

from utils import load_config
from vector_db import VectorStorage
from features import FeatureEngineer
from services import PredictionService
from cli.data_fetcher import StockDataFetcher
from cli.indicator_calculator import IndicatorCalculator
from loguru import logger

def get_latest_indicators(symbol: str, feature_names: list, start: int = 0) -> dict:
    """
    获取股票指定偏移位置的指标值

    Args:
        symbol: 股票代码
        feature_names: 特征名列表
        start: 偏移天数，0 最新，1 前一天

    Returns:
        特征字典，键为特征名，值为指标值
    """
    # 获取数据  count=60 当前指标最大周期为60，需要60+N才可以有效计算
    fetcher = StockDataFetcher()
    df = fetcher.get_daily_data(symbol, count=60, start=start)

    if df.empty:
        logger.error(f"无法获取 {symbol} 的行情数据")
        return None

    # 计算指标
    calculator = IndicatorCalculator(feature_names)
    indicators = calculator.calculate(df)

    if indicators is None:
        logger.error(f"计算 {symbol} 的指标失败")
        return None

    # 可选：输出当前日期
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    logger.info(f"当前状态日期：{latest_date}")

    return indicators

def main():
    """主程序入口"""
    # 1. 加载配置
    config = load_config()
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # 2. 加载特征工程模型
    logger.info("加载特征工程模型...")
    feature_engineer = FeatureEngineer(config)
    try:
        feature_engineer.load_models()
    except Exception as e:
        logger.error(f"加载模型失败：{e}")
        return

    # 3. 连接向量数据库
    logger.info("连接向量数据库...")
    storage = VectorStorage(config)
    storage.connect()
    storage.create_collection()

    if storage.collection is None:
        logger.error("向量数据库未初始化")
        return

    # 4. 初始化预测服务
    prediction_service = PredictionService(config)

    # 5. CLI 交互循环
    print("\n" + "=" * 60)
    print("市场状态向量预测 CLI")
    print("输入股票代码（如 000001 或 000001.SH），输入 'exit' 退出")
    print("=" * 60)

    while True:
        try:
            symbol = input( "\n请输入股票代码 > " ).strip()
            if symbol.lower() in ('exit', 'quit', 'q'):
                break
            if not symbol:
                continue

            # 获取起始偏移参数
            start_input = input( "请输入起始偏移（0=最新，1=前一天[交易日]，默认为0）> " ).strip()
            try:
                start = int( start_input ) if start_input else 0
            except ValueError:
                print( "偏移必须为整数，将使用默认值0" )
                start = 0

            # 获取指标
            indicators = get_latest_indicators( symbol, feature_engineer.selected_features, start )
            if indicators is None:
                print( f"获取 {symbol} 的指标失败，请检查代码或网络" )
                continue

            # 确保特征顺序与训练一致
            feature_names = feature_engineer.selected_features
            missing = set(feature_names) - set(indicators.keys())
            if missing:
                print(f"缺少特征：{missing}，请检查指标计算")
                continue

            # 构建特征向量（按顺序）
            X = np.array([indicators[name] for name in feature_names], dtype=np.float32).reshape(1, -1)

            # 特征清洗（与训练时保持一致）
            X = np.nan_to_num(X)  # 将 NaN 替换为 0

            # 归一化和降维
            X_norm = feature_engineer.scaler.transform(X)
            X_reduced = feature_engineer.pca.transform(X_norm)

            # 查询相似状态
            logger.info(f"查询 {symbol} 的相似状态...")
            results = storage.query(X_reduced, top_k=10)

            if not results['metadatas']:
                print("未找到相似状态")
                continue

            # 构建 similar_states 列表
            similar_states = []
            for meta, dist in zip(results['metadatas'], results['distances']):
                similar_states.append({
                    'date': meta.get('date', ''),
                    'symbol': meta.get('symbol', ''),
                    'future_ret_1d': meta.get('future_ret_1d'),
                    'future_ret_5d': meta.get('future_ret_5d'),
                    'future_label': meta.get('future_label', ''),
                    'distance': dist,
                })

            # 计算预测统计
            prediction = prediction_service.calculate_statistics(similar_states)

            # 打印结果
            print("\n" + "-" * 60)
            print(f"【{symbol}】预测结果：")
            print(f"  次日预期收益：{prediction['avg_ret_1d']:.2f}%")
            print(f"  5日预期收益：{prediction['avg_ret_5d']:.2f}%")
            print(f"  上涨概率：{prediction['up_probability']*100:.0f}%")
            print(f"  标签分布：{prediction['label_distribution']}")
            # print(f"  当前使用加权方式：{prediction['weighting_method']}" )
            print(f"  相似样本数：{prediction['sample_size']}")
            if prediction['std_ret_1d'] is not None:
                print(f"  波动率：{prediction['std_ret_1d']:.2f}%")
                print(f"  夏普比率：{prediction['sharpe_ratio']:.2f}")

            print("\n最相似状态（前3个）：")
            for state in similar_states[:3]:
                print(f"  {state['date']} {state['symbol']} "
                      f"次日{state['future_label']}({state['future_ret_1d']:.2f}%) "
                      f"距离={state['distance']:.4f}")

        except KeyboardInterrupt:
            print("\n用户中断")
            break
        except Exception as e:
            logger.exception(f"处理过程中出错：{e}")
            continue


if __name__ == "__main__":
    main()