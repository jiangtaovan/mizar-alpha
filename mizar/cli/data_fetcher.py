# -*- coding: utf-8 -*-
# @Time    : 2026/3/29 
# @File    : data_fetcher.py
# @Project : mizar-alpha
# @Author  : Chiang Tao
# @Version : 0.2.00

"""
数据获取模块
使用 mootdx 获取 A 股日线数据
其他数据接口 请自己实现
"""

import pandas as pd
from mootdx.quotes import Quotes
from loguru import logger
class StockDataFetcher:

    def __init__(self, server: str = "default"):
        self.client = Quotes.factory(server)

    def get_daily_data(self, symbol: str, count: int = 300, start: int = 0) -> pd.DataFrame:
        """
        获取日线数据
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SH"
            count: 获取的数据条数
        Returns:
            DataFrame 包含列: open, high, low, close, volume
        """
        code, market = self._parse_symbol(symbol)

        try:
            data = self.client.bars(
                symbol=code,
                frequency=9,
                start=start,
                offset=count,
                market=market
            )

            # 安全判断返回值
            if data is None:
                logger.error(f"获取 {symbol} 数据失败，返回 None")
                return pd.DataFrame()
            if isinstance(data, pd.DataFrame) and data.empty:
                logger.error(f"获取 {symbol} 数据为空。可能原因：非交易时间、股票代码错误、该股票无数据")
                return pd.DataFrame()
            if isinstance(data, list) and len(data) == 0:
                logger.error(f"获取 {symbol} 数据为空列表")
                return pd.DataFrame()

            # 转换为 DataFrame
            if isinstance(data, pd.DataFrame):
                df = data
            else:
                df = pd.DataFrame(data)

            if df.empty:
                logger.error(f"获取 {symbol} 数据成功但 DataFrame 为空")
                return df

            # 统一列名
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)

            # 处理日期索引
            if 'datetime' in df.columns:
                df['date'] = pd.to_datetime(df['datetime'])
                df.set_index('date', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)

            # 保留所需列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[required_cols]

            df.sort_index(inplace=True)

            logger.info(f"获取 {symbol} 数据成功，共 {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"获取 {symbol} 数据时出错: {e}")
            return pd.DataFrame()

    @staticmethod
    def _parse_symbol(symbol: str):
        """
        解析股票代码，返回 (code, market)
        market: 0 深圳，1 上海
        """
        if '.' in symbol:
            code, exchange = symbol.split('.')
            exchange = exchange.lower()
            if exchange == 'sh':
                market = 1
            elif exchange == 'sz':
                market = 0
            else:
                market = 1   # 默认上海
        else:
            code = symbol
            # 根据代码首位判断市场
            if code.startswith('6'):
                market = 1   # 上海
            elif code.startswith(('0', '3')):
                market = 0   # 深圳
            else:
                market = 1
        return code, market