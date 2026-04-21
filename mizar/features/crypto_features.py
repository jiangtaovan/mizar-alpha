# -*- coding: utf-8 -*-
# @Time    : 2026/3/27 
# @File    : crypto_features.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
虚拟货币技术指标计算模块
支持币安日线CSV数据转换为Mizar特征格式
使用显式列映射，避免自动检测歧义
"""
import pandas as pd
import numpy as np
import talib
from typing import List, Dict
from pathlib import Path


class CryptoFeatureEngineer:
    """虚拟货币特征计算器"""

    def __init__(self, features_config: dict = None):
        self.default_features = [
            'SMA_5', 'SMA_20', 'SMA_50',
            'EMA_12', 'EMA_26',
            'ADX',
            'MACD_macd', 'MACD_signal', 'MACD_histogram',
            'RSI_12', 'RSI_24',
            'WILLR_14',
            'ROC_12', 'MOM_12',
            'ATR_14',
            'BBANDS_upper', 'BBANDS_middle', 'BBANDS_lower',
            'VOLUME_RATIO',
            'PLUS_DI', 'MINUS_DI'
        ]
        self.features = features_config if features_config else self.default_features

    def add_indicators(self, df: pd.DataFrame, drop_initial_n_rows: int = 60) -> pd.DataFrame:
    # def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # ... 保持不变 ...
        df = df.sort_values('date').reset_index(drop=True)
        open_p = df['open'].values.astype(float)
        high_p = df['high'].values.astype(float)
        low_p = df['low'].values.astype(float)
        close_p = df['close'].values.astype(float)
        volume = df['volume'].values.astype(float)

        df['SMA_5'] = talib.SMA(close_p, timeperiod=5)
        df['SMA_20'] = talib.SMA(close_p, timeperiod=20)
        df['SMA_50'] = talib.SMA(close_p, timeperiod=50)
        df['EMA_12'] = talib.EMA(close_p, timeperiod=12)
        df['EMA_26'] = talib.EMA(close_p, timeperiod=26)
        df['ADX'] = talib.ADX(high_p, low_p, close_p, timeperiod=14)
        macd, signal, hist = talib.MACD(close_p, fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD_macd'] = macd
        df['MACD_signal'] = signal
        df['MACD_histogram'] = hist
        df['RSI_12'] = talib.RSI(close_p, timeperiod=12)
        df['RSI_24'] = talib.RSI(close_p, timeperiod=24)
        df['WILLR_14'] = talib.WILLR(high_p, low_p, close_p, timeperiod=14)
        df['ROC_12'] = talib.ROC(close_p, timeperiod=12)
        df['MOM_12'] = talib.MOM(close_p, timeperiod=12)
        df['ATR_14'] = talib.ATR(high_p, low_p, close_p, timeperiod=14)
        upper, middle, lower = talib.BBANDS(close_p, timeperiod=20, nbdevup=2, nbdevdn=2)
        df['BBANDS_upper'] = upper
        df['BBANDS_middle'] = middle
        df['BBANDS_lower'] = lower
        df['VOLUME_RATIO'] = volume / (talib.SMA(volume, timeperiod=20) + 1e-9)
        df['PLUS_DI'] = talib.PLUS_DI(high_p, low_p, close_p, timeperiod=14)
        df['MINUS_DI'] = talib.MINUS_DI(high_p, low_p, close_p, timeperiod=14)

        df = df.drop_duplicates( subset=['date', 'symbol'], keep='first' )  # 保留第一条

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(method='ffill').fillna(0)
        if drop_initial_n_rows > 0:
            df = df.iloc[drop_initial_n_rows:].reset_index(drop=True)
            print(f"已丢弃前 {drop_initial_n_rows} 行（因指标窗口不足）")
        return df

    def add_future_labels(self, df: pd.DataFrame, periods: List[int] = [1, 3, 5]) -> pd.DataFrame:
        df = df.copy()
        for p in periods:
            df[f'future_ret_{p}d'] = df['close'].shift(-p) / df['close'] - 1
            df[f'up_label_{p}d'] = (df[f'future_ret_{p}d'] > 0).astype(int)
        return df


def process_crypto_file(
    input_path: str,
    output_path: str = None,
    periods: List[int] = [1, 3, 5],
    column_mapping: Dict[str, str] = None
) -> pd.DataFrame:
    """
    处理单个虚拟货币CSV文件，生成特征数据并保存

    :param input_path: 原始CSV文件路径
    :param output_path: 输出路径（可选，默认为 raw 目录下同名文件加 _features）
    :param periods: 需要计算的未来周期列表
    :param column_mapping: 原始列名到标准列名的映射，必须包含以下键：
                           open, high, low, close, volume, symbol
                           日期列至少提供一种（Unix 或 Date），映射为 'date'
    :return: 处理后的DataFrame
    """
    if column_mapping is None:
        raise ValueError("必须提供 column_mapping 参数，指定原始列名到标准列名的映射")

    # 读取原始数据
    df = pd.read_csv(input_path)

    # 应用列名映射（先重命名，后面再处理重复）
    df = df.rename(columns=column_mapping)

    # 检查是否有重复列名（例如多个源列映射到同一目标，如 'Unix' 和 'Date' 都映射到 'date'）
    duplicate_cols = df.columns[df.columns.duplicated()].tolist()
    if duplicate_cols:
        # 保留第一个出现的列，删除后续重复的列
        df = df.loc[:, ~df.columns.duplicated()]
        print(f"警告: 发现重复列名 {duplicate_cols}，已去重，保留第一个")

    # 检查必要列是否存在
    required = ['open', 'high', 'low', 'close', 'volume', 'symbol']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"映射后缺少必要列: {missing}。当前列: {list(df.columns)}")

    # 处理日期列：优先使用 'date' 列，否则尝试自动查找
    if 'date' in df.columns:
        date_col = df['date']
    else:
        # 尝试从可能的日期列自动创建（如果映射中没有提供）
        if 'Unix' in df.columns:
            date_col = df['Unix']
        elif 'Date' in df.columns:
            date_col = df['Date']
        else:
            raise ValueError("无法找到日期列，请在映射中包含 'date' 列")

    # 智能转换日期格式
    if date_col.dtype == 'int64' or date_col.dtype == 'float64':
        # 假设是毫秒时间戳
        df['date'] = pd.to_datetime(date_col, unit='ms').dt.strftime('%Y-%m-%d')
    else:
        # 尝试解析字符串日期
        df['date'] = pd.to_datetime(date_col).dt.strftime('%Y-%m-%d')

    # 按日期排序
    df = df.sort_values('date').reset_index(drop=True)

    # 计算技术指标
    engineer = CryptoFeatureEngineer()
    df = engineer.add_indicators(df)

    # 添加未来收益标签
    df = engineer.add_future_labels(df, periods=periods)

    # 添加 current_price 列
    df['current_price'] = df['close']

    # 确定输出路径
    if output_path is None:
        input_path = Path(input_path)
        output_path = input_path.parent.parent / 'raw' / f"{input_path.stem}_features.csv"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"处理完成: {output_path}")

    return df

#
# if __name__ == '__main__':
#     # BTCUSDT 映射（仅映射一个日期列，避免重复）
#     mapping_1inch = {
#         'Unix': 'date',          # 使用 Unix 时间戳作为日期
#         'Symbol': 'symbol',
#         'Open': 'open',
#         'High': 'high',
#         'Low': 'low',
#         'Close': 'close',
#         'Volume USDT': 'volume'
#     }
#     process_crypto_file(
#         'datas/coin/Binance_BTCUSDT_d.csv',
#         column_mapping=mapping_1inch
#     )
#
#     # ETCUSDT 映射
#     mapping_aave = {
#         'Unix': 'date',
#         'Symbol': 'symbol',
#         'Open': 'open',
#         'High': 'high',
#         'Low': 'low',
#         'Close': 'close',
#         'Volume USDT': 'volume'
#     }
#     process_crypto_file(
#         'datas/coin/Binance_ETCUSDT_d.csv',
#         column_mapping=mapping_aave
#     )