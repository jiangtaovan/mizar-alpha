# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : data_preparer.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
数据准备模块：加载数据、计算未来标签、特征工程
支持多周期收益、最大回撤、价格极值等标签
"""

import pandas as pd
import numpy as np
from loguru import logger

from .data_loader import DataLoader
from features.feature_engineer import FeatureEngineer


class DataPreparer:
    """
    数据准备器：负责原始数据加载、未来标签计算、特征工程
    """
    def __init__(self, config):
        self.config = config
        self.data_loader = DataLoader(config)
        self.feature_engineer = FeatureEngineer(config)
        self.periods = config.get('data', {}).get('periods', [1, 3, 5])  # 支持多周期
        self.compute_extremes = config.get('data', {}).get('compute_extremes', True)  # 是否计算价格极值

    def load_and_prepare(self, data_path: str = None):
        """
        加载数据、计算未来标签、特征工程
        Returns:
            vectors: np.ndarray, 特征向量
            metadata: pd.DataFrame, 元数据（含日期、代码、未来标签等）
        """
        # 1. 加载数据
        if data_path is None:
            data_path = self.config.get('data', {}).get('data_path', './datas/raw/*.csv')
        logger.info(f"加载数据: {data_path}")
        df = self.data_loader.load_multiple_files(data_path)
        logger.info(f"原始数据行数: {len(df)}")

        # 2. 计算未来标签
        logger.info("计算未来标签...")
        df = self._compute_future_labels(df)

        # 3. 特征工程
        logger.info("特征工程...")
        df_selected = self.feature_engineer.select_features(df)
        vectors, metadata = self.feature_engineer.fit_transform(df_selected)

        # 保存模型
        self.feature_engineer.save_models(version=self.config.get('features', {}).get('model_version', 'v1'))

        logger.info(f"特征工程完成，向量维度: {vectors.shape[1]}")
        return vectors, metadata

    def _compute_future_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算未来标签，按股票分组（假设数据已按时间排序）
        添加列：
            future_ret_{p}d: 未来 p 个交易日收益率
            future_max_dd_{p}d: 未来 p 个交易日最大回撤
            future_high_1d: 未来1个交易日最高价 / 当前收盘价
            future_low_1d:  未来1个交易日最低价 / 当前收盘价
        """
        df = df.copy()
        # 确保按股票和日期排序
        df = df.sort_values(['symbol', 'date'])

        for period in self.periods:
            # 收益率
            ret_col = f'future_ret_{period}d'
            df[ret_col] = df.groupby('symbol')['close'].transform(
                lambda x: x.shift(-period) / x - 1
            )

            # 最大回撤（未来 period 天内的最大回撤）
            dd_col = f'future_max_dd_{period}d'
            def max_dd(series):
                # 滚动窗口内最大回撤
                # 注意：这里需要未来 period 天的数据，用 rolling 不好做，用自定义函数
                # 简单实现：对每个分组，计算未来窗口内的回撤
                # 由于数据量不大，使用 apply 效率尚可
                pass
            # 更高效：使用 groupby + rolling
            # 因为需要未来数据，我们直接对每个股票计算
            df[dd_col] = np.nan
            for symbol, group in df.groupby('symbol'):
                group = group.reset_index(drop=True)
                closes = group['close'].values
                for i in range(len(group)):
                    end = min(i + period, len(group))
                    if end > i:
                        window = closes[i:end+1]
                        peak = window[0]
                        max_dd_val = 0
                        for price in window[1:]:
                            dd = (peak - price) / peak
                            if dd > max_dd_val:
                                max_dd_val = dd
                        df.loc[group.index[i], dd_col] = max_dd_val

        # 价格极值（仅1d，可以扩展）
        if self.compute_extremes:
            # 未来1天最高价 / 当前收盘价
            df['future_high_1d'] = df.groupby('symbol')['high'].transform(
                lambda x: x.shift(-1) / x
            )
            # 未来1天最低价 / 当前收盘价
            df['future_low_1d'] = df.groupby('symbol')['low'].transform(
                lambda x: x.shift(-1) / x
            )

        # 移除最后几行（因为未来标签缺失）
        # 但实际构建向量库时，需要保留所有有标签的行，缺失值在入库时会处理
        # 这里不再删除，后续插入时忽略NaN

        logger.info(f"未来标签计算完成，新增列: {[c for c in df.columns if c.startswith('future_')]}")
        return df