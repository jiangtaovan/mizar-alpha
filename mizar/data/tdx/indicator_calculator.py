# -*- coding: utf-8 -*-
# @Time    : 2026/3/29 
# @File    : indicator_calculator.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
# -*- coding: utf-8 -*-
"""
指标计算模块
使用 TA-Lib 计算技术指标，支持单点最新值和滚动窗口全历史计算（循环方式）
"""
import numpy as np
import pandas as pd
import talib as ta
import yaml
from pathlib import Path
from loguru import logger


def _load_system_config():
    config_path = Path("config/system_config.yaml")
    default = {'data_storage': {'indicator_path': 'datas/indicators', 'format': 'csv'}}
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default, f)
        return default
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class IndicatorCalculator:
    @classmethod
    def load_feature_names(cls, config_path="config/feature_config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        return cfg.get('features', []) + cfg.get('extra_features', [])

    def __init__(self, feature_names=None):
        if feature_names is None:
            feature_names = self.load_feature_names()
        self.feature_names = feature_names
        self._funcs = self._build_funcs()
        sys_cfg = _load_system_config()
        self.save_path = Path(sys_cfg['data_storage']['indicator_path'])
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.fmt = sys_cfg['data_storage']['format']

    def calculate(self, df, trim_before=False, trim_size=60):
        """计算最新一天的指标（df包含完整历史）"""
        if df.empty:
            return None
        # 如果要求trim，只对单次计算有效（但一般在calculate_all中不需要）
        if trim_before and len(df) > trim_size:
            df = df.iloc[trim_size:].copy()
        if len(df) < 60:   # 至少需要60天数据才能计算任何指标
            return None
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        vol = df['volume'].values
        res = {}
        for name, func in self._funcs.items():
            try:
                val = func(close, high, low, vol, df)
                if isinstance(val, (np.ndarray, pd.Series)):
                    val = val[-1] if len(val) > 0 else 0.0
                res[name] = float(val) if not np.isnan(val) else 0.0
                res[name] = round( val, 6 )  # 保留4位小数
            except Exception as e:
                logger.warning(f"{name} 计算失败: {e}")
                res[name] = 0.0
        return res

    def calculate_all(self, df, trim_before_calc=True, trim_size=60):
        """
        滚动窗口计算所有日期的指标（用于回测）
        最终返回的行数 = len(df) - trim_size
        """
        if df.empty:
            return pd.DataFrame()
        # 不预先删除数据，而是跳过前trim_size天
        total = len(df)
        records = []
        # 确保df有symbol列（如果没有，从外部传入）
        symbol = df['symbol'].iloc[1] if 'symbol' in df.columns else 'unknown'
        for i in range(trim_size, total):
            sub = df.iloc[:i+1]
            ind = self.calculate(sub, trim_before=False)
            if ind:
                record = {
                    'date': sub.index[-1],
                    'symbol': symbol,
                    'open': sub['open'].iloc[-1],
                    'close': sub['close'].iloc[-1],
                    **ind
                }
                records.append(record)
            if (i - trim_size + 1) % 100 == 0:
                logger.debug(f"进度: {i - trim_size + 1}/{total - trim_size}")
        result = pd.DataFrame(records)
        if not result.empty:
            result.set_index('date', inplace=True)
        logger.info(f"计算完成 {len(result)} 行（原始 {total} 行，丢弃前 {trim_size} 行无效）")
        return result

    # def save(self, data, symbol, offset=0, full=False):
    #     if data is None or (isinstance(data, pd.DataFrame) and data.empty):
    #         return None
    #     if isinstance(data, pd.DataFrame):
    #         # 全量保存
    #         fname = f"{symbol}_{offset}_indicators_full.{self.fmt}"
    #         path = self.save_path / fname
    #         df = data.copy()
    #         if 'date' not in df.columns and isinstance(df.index, pd.DatetimeIndex):
    #             df.insert(0, 'date', df.index)
    #         if self.fmt == 'parquet':
    #             df.to_parquet(path)
    #         else:
    #             df.to_csv(path, index=False)
    #         logger.info(f"全量保存: {path}")
    #         return path
    #     else:
    #         # 单点保存（一般不会用到全量之外）
    #         rec = data.copy()
    #         rec['symbol'] = symbol
    #         rec['offset'] = offset
    #         df = pd.DataFrame([rec])
    #         date_str = pd.to_datetime(rec.get('date', pd.Timestamp.now())).strftime('%Y%m%d')
    #         fname = f"{symbol}_{offset}_{date_str}_indicators.{self.fmt}"
    #         path = self.save_path / fname
    #         df.to_csv(path, index=False)
    #         return path

    def save(self, data, symbol, offset=0, full=False):
        if data is None:
            return None
        if isinstance( data, pd.DataFrame ):
            if data.empty:
                return None

            # 防御性复制，避免修改原始数据
            df = data.copy()

            # 确保索引为 DatetimeIndex，并移除 NaT
            if not isinstance( df.index, pd.DatetimeIndex ):
                try:
                    df.index = pd.to_datetime( df.index )
                except Exception as e:
                    logger.error( f"索引转换为日期失败: {e}" )
                    return None

            # 移除索引为 NaT 的行
            df = df[~df.index.isna()].copy()
            if df.empty:
                logger.warning( "清洗后无有效数据，跳过保存" )
                return None

            # 插入日期列（如果索引是日期且无'date'列）
            if 'date' not in df.columns:
                df.insert( 0, 'date', df.index )

            fname = f"{symbol}_{offset}_indicators_full.{self.fmt}"
            path = self.save_path / fname
            if self.fmt == 'parquet':
                df.to_parquet( path )
            else:
                df.to_csv( path, index=False )
            logger.info( f"全量保存: {path}" )
            return path
        else:
            # 单点保存逻辑保持不变，但也建议添加 NaT 检查
            rec = data.copy()
            rec['symbol'] = symbol
            rec['offset'] = offset
            df = pd.DataFrame( [rec] )
            # 检查日期有效性
            date_val = rec.get( 'date' )
            if pd.isna( date_val ):
                logger.warning( "记录中的日期为空，使用当前时间替代" )
                date_val = pd.Timestamp.now()
            date_str = pd.to_datetime( date_val ).strftime( '%Y%m%d' )
            fname = f"{symbol}_{offset}_{date_str}_indicators.{self.fmt}"
            path = self.save_path / fname
            df.to_csv( path, index=False )
            return path

    # ---------- 以下 _build_funcs 及自定义指标保持不变（按需增减对应指标） ----------
    def _build_funcs(self):
        f = {}
        # 趋势
        f['SMA_5'] = lambda c, h, l, v, _: ta.SMA(c, 5)
        f['SMA_20'] = lambda c, h, l, v, _: ta.SMA(c, 20)
        f['SMA_50'] = lambda c, h, l, v, _: ta.SMA(c, 50)
        f['EMA_12'] = lambda c, h, l, v, _: ta.EMA(c, 12)
        f['EMA_26'] = lambda c, h, l, v, _: ta.EMA(c, 26)
        f['ADX'] = lambda c, h, l, v, _: ta.ADX(h, l, c, 14)
        f['ADXR'] = lambda c, h, l, v, _: ta.ADXR(h, l, c, 14)
        f['TRIX'] = lambda c, h, l, v, _: ta.TRIX(c, 20)

        for p in [6,12,24]:
            f[f'RSI_{p}'] = lambda c, h, l, v, _, p=p: ta.RSI(c, p)
        def _macd(c, *args):
            m, s, h = ta.MACD(c, 12, 26, 9)
            return m, s, h
        f['macd'] = lambda c, h, l, v, _: _macd(c)[0]
        f['signal'] = lambda c, h, l, v, _: _macd(c)[1]
        f['histogram'] = lambda c, h, l, v, _: _macd(c)[2]
        f['WILLR_14'] = lambda c, h, l, v, _: ta.WILLR(h, l, c, 14)
        f['ROC_12'] = lambda c, h, l, v, _: ta.ROC(c, 12)
        f['MOM_12'] = lambda c, h, l, v, _: ta.MOM(c, 12)
        f['CMO'] = lambda c, h, l, v, _: ta.CMO(c, 14)
        def _stoch(c, h, l, v, _):
            k, d = ta.STOCH(h, l, c, 14, 3, 3)
            return k, d
        f['fastK'] = lambda c, h, l, v, _: _stoch(c, h, l, v, _)[0]
        f['fastD'] = lambda c, h, l, v, _: _stoch(c, h, l, v, _)[1]
        f['BIAS_12'] = lambda c, h, l, v, _: (c - ta.SMA(c, 12)) / ta.SMA(c, 12) * 100

        f['ATR_14'] = lambda c, h, l, v, _: ta.ATR(h, l, c, 14)
        def _bb(c, h, l, v, _):
            u, m, lo = ta.BBANDS(c, 20, 2, 2)
            return u, m, lo
        f['upper'] = lambda c, h, l, v, _: _bb(c, h, l, v, _)[0]
        f['middle'] = lambda c, h, l, v, _: _bb(c, h, l, v, _)[1]
        f['lower'] = lambda c, h, l, v, _: _bb(c, h, l, v, _)[2]

        f['VOLUME_RATIO'] = self._volume_ratio

        f['PLUS_DI'] = lambda c, h, l, v, _: ta.PLUS_DI(h, l, c, 14)
        f['MINUS_DI'] = lambda c, h, l, v, _: ta.MINUS_DI(h, l, c, 14)
        def _aroon(c, h, l, v, _):
            up, down = ta.AROON(h, l, 14)
            return up, down
        f['aroon_up'] = lambda c, h, l, v, _: _aroon(c, h, l, v, _)[0]
        f['aroon_down'] = lambda c, h, l, v, _: _aroon(c, h, l, v, _)[1]
        f['aroon_oscillator'] = lambda c, h, l, v, _: _aroon(c, h, l, v, _)[0] - _aroon(c, h, l, v, _)[1]
        f['PRS_20'] = self._prs(20)
        f['VRS_20'] = self._vrs(20)
        f['WMA_20'] = lambda c, h, l, v, _: ta.WMA(c, 20)

        f['SMA_10'] = lambda c, h, l, v, _: ta.SMA(c, 10)
        f['BIAS_6'] = lambda c, h, l, v, _: (c - ta.SMA(c, 6)) / ta.SMA(c, 6) * 100
        f['BIAS_24'] = lambda c, h, l, v, _: (c - ta.SMA(c, 24)) / ta.SMA(c, 24) * 100
        f['WILLR_6'] = lambda c, h, l, v, _: ta.WILLR(h, l, c, 6)
        f['WILLR_28'] = lambda c, h, l, v, _: ta.WILLR(h, l, c, 28)
        f['ROC_6'] = lambda c, h, l, v, _: ta.ROC(c, 6)
        f['ROC_24'] = lambda c, h, l, v, _: ta.ROC(c, 24)
        f['MOM_6'] = lambda c, h, l, v, _: ta.MOM(c, 6)
        f['MOM_24'] = lambda c, h, l, v, _: ta.MOM(c, 24)
        f['ATR_7'] = lambda c, h, l, v, _: ta.ATR(h, l, c, 7)
        f['ATR_21'] = lambda c, h, l, v, _: ta.ATR(h, l, c, 21)
        f['PRS_5'] = self._prs(5)
        f['PRS_10'] = self._prs(10)
        f['PRS_60'] = self._prs(60)
        f['VRS_5'] = self._vrs(5)
        f['VRS_60'] = self._vrs(60)
        f['dma_diff'] = self._dma_diff
        f['dma_ama'] = self._dma_ama
        return f

    @staticmethod
    def _volume_ratio(c, h, l, v, _):
        vol = pd.Series(v)
        avg5 = vol.rolling(5, min_periods=5).mean().shift(1)
        return (vol / avg5).fillna(0).values

    @staticmethod
    def _prs(period):
        def func(c, h, l, v, _):
            sma = ta.SMA(c, period)
            with np.errstate(divide='ignore', invalid='ignore'):
                return np.where(sma != 0, c / sma * 100, 100.0)
        return func

    @staticmethod
    def _vrs(period):
        def func(c, h, l, v, _):
            vol = pd.Series(v)
            avg = vol.rolling(period, min_periods=period).mean()
            return (vol / avg * 100).fillna(0).values
        return func

    @staticmethod
    def _dma_diff(c, h, l, v, _):
        return ta.SMA(c, 10) - ta.SMA(c, 50)

    @staticmethod
    def _dma_ama(c, h, l, v, _):
        return ta.SMA(c, 10)