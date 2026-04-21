# -*- coding: utf-8 -*-
# @Time    : 2026/3/29 
# @File    : indicator_calculator.py
# @Project : mizar-alpha
# @Author  : Chiang Tao
# @Version : 0.2.00
# -*- coding: utf-8 -*-
"""
指标计算模块
使用 TA-Lib 计算技术指标
"""

import numpy as np
import pandas as pd
import talib as ta
from typing import Dict, List, Optional
from loguru import logger


class IndicatorCalculator:
    """技术指标计算器"""

    def __init__(self, feature_names: List[str]):
        """
        初始化
        :param feature_names: 需要计算的特征名列表（与训练时完全一致）
        """
        self.feature_names = feature_names
        # 定义每个特征的计算方法
        self._calculators = self._build_calculators()

    def calculate(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
        """
        根据行情数据计算所有特征的最新值

        Args:
            df: DataFrame，包含 open, high, low, close, volume

        Returns:
            特征字典，键为特征名，值为最新一天的指标值；若计算失败返回 None
        """
        if df.empty:
            logger.error("输入数据为空")
            return None

        # 确保数据足够长（最长指标周期需检查）
        min_required = self._get_min_required_length()
        if len(df) < min_required:
            logger.error(f"数据长度不足，需要至少 {min_required} 条，当前 {len(df)}")
            return None

        # 提取最新一天的数据（用于计算量比等需要当日值的指标）
        latest = df.iloc[-1:].copy()

        # 转换为 TA-Lib 需要的数组格式（全部数据）
        open_arr = df['open'].values.astype(float)
        high_arr = df['high'].values.astype(float)
        low_arr = df['low'].values.astype(float)
        close_arr = df['close'].values.astype(float)
        volume_arr = df['volume'].values.astype(float)

        # 存储计算结果
        results = {}

        # 计算每个特征
        for feature in self.feature_names:
            calc_func = self._calculators.get(feature)
            if calc_func:
                try:
                    # 调用计算函数，返回最新值
                    val = calc_func(close_arr, high_arr, low_arr, volume_arr, df)
                    # 如果是标量，直接赋值；如果是数组，取最后一个值
                    if isinstance(val, (np.ndarray, pd.Series)):
                        if len(val) > 0:
                            results[feature] = val[-1]
                        else:
                            results[feature] = np.nan
                    else:
                        results[feature] = val
                except Exception as e:
                    logger.warning(f"计算 {feature} 失败: {e}")
                    results[feature] = np.nan
            else:
                # 未定义计算方法的特征，设为 NaN
                logger.warning(f"未找到 {feature} 的计算方法，设置为 NaN")
                results[feature] = np.nan

        # 处理 NaN（例如用前值填充或0填充）
        for k, v in results.items():
            if np.isnan(v):
                # 简单处理：用0填充，或可考虑用前向填充
                results[k] = 0.0

        # 确保所有特征都有值
        missing = set(self.feature_names) - set(results.keys())
        if missing:
            logger.error(f"缺少特征: {missing}")
            return None

        return results

    def _build_calculators(self) -> Dict[str, callable]:
        """构建特征 -> 计算函数的映射"""
        calculators = {}

        # ----- 趋势指标 -----
        calculators['SMA_5'] = lambda c, h, l, v, df: ta.SMA(c, timeperiod=5)
        calculators['SMA_20'] = lambda c, h, l, v, df: ta.SMA(c, timeperiod=20)
        calculators['SMA_50'] = lambda c, h, l, v, df: ta.SMA(c, timeperiod=50)
        # calculators['SMA_200'] = lambda c, h, l, v, df: ta.SMA(c, timeperiod=200)
        # 该数据需要获取行情数据太长，忽略按0算
        calculators['SMA_200'] = 0
        calculators['EMA_12'] = lambda c, h, l, v, df: ta.EMA(c, timeperiod=12)
        calculators['EMA_26'] = lambda c, h, l, v, df: ta.EMA(c, timeperiod=26)
        calculators['ADX'] = lambda c, h, l, v, df: ta.ADX(h, l, c, timeperiod=14)
        calculators['ADXR'] = lambda c, h, l, v, df: ta.ADXR(h, l, c, timeperiod=14)
        calculators['TRIX'] = lambda c, h, l, v, df: ta.TRIX(c, timeperiod=30)

        # ----- 动量指标 -----
        calculators['RSI_6'] = lambda c, h, l, v, df: ta.RSI(c, timeperiod=6)
        calculators['RSI_12'] = lambda c, h, l, v, df: ta.RSI(c, timeperiod=12)
        calculators['RSI_24'] = lambda c, h, l, v, df: ta.RSI(c, timeperiod=24)
        # MACD
        calculators['macd'] = lambda c, h, l, v, df: ta.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)[0]
        calculators['signal'] = lambda c, h, l, v, df: ta.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)[1]
        calculators['histogram'] = lambda c, h, l, v, df: ta.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)[2]
        # 威廉指标
        calculators['WILLR_14'] = lambda c, h, l, v, df: ta.WILLR(h, l, c, timeperiod=14)
        # ROC
        calculators['ROC_12'] = lambda c, h, l, v, df: ta.ROC(c, timeperiod=12)
        # MOM
        calculators['MOM_12'] = lambda c, h, l, v, df: ta.MOM(c, timeperiod=12)
        # CMO
        calculators['CMO'] = lambda c, h, l, v, df: ta.CMO(c, timeperiod=14)
        # 随机指标
        def stochastic(c, h, l, v, df):
            fastk, fastd = ta.STOCH(h, l, c, fastk_period=14, slowk_period=3, slowd_period=3)
            return fastk, fastd
        calculators['fastK'] = lambda c, h, l, v, df: stochastic(c, h, l, v, df)[0]
        calculators['fastD'] = lambda c, h, l, v, df: stochastic(c, h, l, v, df)[1]
        # 乖离率（自定义）
        calculators['BIAS_12'] = lambda c, h, l, v, df: (c - ta.SMA(c, 12)) / ta.SMA(c, 12) * 100

        # ----- 波动率指标 -----
        calculators['ATR_14'] = lambda c, h, l, v, df: ta.ATR(h, l, c, timeperiod=14)
        # 布林带
        def bbands(c, h, l, v, df):
            upper, middle, lower = ta.BBANDS(c, timeperiod=20, nbdevup=2, nbdevdn=2)
            return upper, middle, lower
        calculators['upper'] = lambda c, h, l, v, df: bbands(c, h, l, v, df)[0]
        calculators['middle'] = lambda c, h, l, v, df: bbands(c, h, l, v, df)[1]
        calculators['lower'] = lambda c, h, l, v, df: bbands(c, h, l, v, df)[2]

        # ----- 成交量指标 -----
        calculators['VOLUME_RATIO'] = self._volume_ratio

        # ----- 增强指标 -----
        calculators['PLUS_DI'] = lambda c, h, l, v, df: ta.PLUS_DI(h, l, c, timeperiod=14)
        calculators['MINUS_DI'] = lambda c, h, l, v, df: ta.MINUS_DI(h, l, c, timeperiod=14)
        # Aroon
        def aroon(c, h, l, v, df):
            aroon_up, aroon_down = ta.AROON(h, l, timeperiod=14)
            return aroon_up, aroon_down
        calculators['aroon_up'] = lambda c, h, l, v, df: aroon(c, h, l, v, df)[0]
        calculators['aroon_down'] = lambda c, h, l, v, df: aroon(c, h, l, v, df)[1]
        calculators['aroon_oscillator'] = lambda c, h, l, v, df: aroon(c, h, l, v, df)[0] - aroon(c, h, l, v, df)[1]
        # 相对强度（自定义）
        calculators['PRS_20'] = self._price_relative_strength
        calculators['VRS_20'] = self._volume_relative_strength
        # 加权移动平均
        calculators['WMA_20'] = lambda c, h, l, v, df: ta.WMA(c, timeperiod=20)

        # 可选：额外特征（若配置中包含）
        calculators['SMA_10'] = lambda c, h, l, v, df: ta.SMA(c, timeperiod=10)
        calculators['BIAS_6'] = lambda c, h, l, v, df: (c - ta.SMA(c, 6)) / ta.SMA(c, 6) * 100
        calculators['BIAS_24'] = lambda c, h, l, v, df: (c - ta.SMA(c, 24)) / ta.SMA(c, 24) * 100
        calculators['WILLR_6'] = lambda c, h, l, v, df: ta.WILLR(h, l, c, timeperiod=6)
        calculators['WILLR_28'] = lambda c, h, l, v, df: ta.WILLR(h, l, c, timeperiod=28)
        calculators['ROC_6'] = lambda c, h, l, v, df: ta.ROC(c, timeperiod=6)
        calculators['ROC_24'] = lambda c, h, l, v, df: ta.ROC(c, timeperiod=24)
        calculators['MOM_6'] = lambda c, h, l, v, df: ta.MOM(c, timeperiod=6)
        calculators['MOM_24'] = lambda c, h, l, v, df: ta.MOM(c, timeperiod=24)
        calculators['ATR_7'] = lambda c, h, l, v, df: ta.ATR(h, l, c, timeperiod=7)
        calculators['ATR_21'] = lambda c, h, l, v, df: ta.ATR(h, l, c, timeperiod=21)
        calculators['PRS_5'] = self._price_relative_strength_5
        calculators['PRS_10'] = self._price_relative_strength_10
        calculators['PRS_60'] = self._price_relative_strength_60
        calculators['VRS_5'] = self._volume_relative_strength_5
        calculators['VRS_60'] = self._volume_relative_strength_60
        calculators['dma_diff'] = self._dma_diff
        calculators['dma_ama'] = self._dma_ama

        return calculators

    @staticmethod
    def _volume_ratio(close, high, low, volume, df):
        """量比：当日成交量 / 过去5日平均成交量"""
        vol_series = volume
        if len(vol_series) >= 6:
            avg_vol = np.mean(vol_series[-6:-1])  # 前5天平均
            return vol_series[-1] / avg_vol if avg_vol != 0 else 0
        return 0.0

    @staticmethod
    def _price_relative_strength(close, high, low, volume, df):
        """价格相对强度（20日）：当前收盘价 / 20日均价 * 100"""
        sma20 = ta.SMA(close, timeperiod=20)
        if len(sma20) > 0:
            return close[-1] / sma20[-1] * 100
        return 100.0

    @staticmethod
    def _volume_relative_strength(close, high, low, volume, df):
        """成交量相对强度（20日）：当前成交量 / 20日均量 * 100"""
        if len(volume) >= 20:
            avg_vol = np.mean(volume[-20:])
            return volume[-1] / avg_vol * 100 if avg_vol != 0 else 0
        return 0.0

    # 其他周期类似
    @staticmethod
    def _price_relative_strength_5(close, high, low, volume, df):
        sma5 = ta.SMA(close, timeperiod=5)
        return close[-1] / sma5[-1] * 100 if len(sma5) > 0 else 100.0

    @staticmethod
    def _price_relative_strength_10(close, high, low, volume, df):
        sma10 = ta.SMA(close, timeperiod=10)
        return close[-1] / sma10[-1] * 100 if len(sma10) > 0 else 100.0

    @staticmethod
    def _price_relative_strength_60(close, high, low, volume, df):
        sma60 = ta.SMA(close, timeperiod=60)
        return close[-1] / sma60[-1] * 100 if len(sma60) > 0 else 100.0

    @staticmethod
    def _volume_relative_strength_5(close, high, low, volume, df):
        if len(volume) >= 5:
            avg_vol = np.mean(volume[-5:])
            return volume[-1] / avg_vol * 100 if avg_vol != 0 else 0
        return 0.0

    @staticmethod
    def _volume_relative_strength_60(close, high, low, volume, df):
        if len(volume) >= 60:
            avg_vol = np.mean(volume[-60:])
            return volume[-1] / avg_vol * 100 if avg_vol != 0 else 0
        return 0.0

    @staticmethod
    def _dma_diff(close, high, low, volume, df):
        """DMA 差值（短期均线-长期均线）"""
        ama = ta.SMA(close, timeperiod=10)
        dma = ta.SMA(close, timeperiod=50)
        if len(ama) > 0 and len(dma) > 0:
            return ama[-1] - dma[-1]
        return 0.0

    @staticmethod
    def _dma_ama(close, high, low, volume, df):
        """DMA 平滑线（短期均线）"""
        ama = ta.SMA(close, timeperiod=10)
        return ama[-1] if len(ama) > 0 else 0.0

    def _get_min_required_length(self) -> int:
        """获取计算所有指标所需的最小数据长度"""
        # 最长周期是 200 (SMA_200)
        return 60  # 留一点余量