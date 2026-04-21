# -*- coding: utf-8 -*-
# @Time    : 2026/3/29 
# @File    : data_fetcher.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00
# -*- coding: utf-8 -*-
"""
数据获取模块
使用 mootdx 获取 A 股日线数据，支持行情数据存储
    v：2 adjust="adjust",
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Tuple, Optional
from mootdx.quotes import Quotes
from loguru import logger


def _load_system_config():
    """加载系统配置，若文件不存在则创建默认配置"""
    config_path = Path("config/system_config.yaml")
    default_config = {
        'data_storage': {
            'quote_path': 'storage/quotes',
            'indicator_path': 'storage/indicators',
            'format': 'parquet'  # 可选 'csv' 或 'parquet'
        }
    }
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True)
        return default_config
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class StockDataFetcher:
    """股票数据获取器（支持本地缓存）"""

    def __init__(self, server: str = "std"):
        """
        初始化
        :param server: mootdx 服务器配置，可选 'std' 或 'ext'
        """
        self.client = Quotes.factory(server)
        # 加载存储配置
        sys_config = _load_system_config()
        storage_cfg = sys_config.get('data_storage', {})
        self.quote_path = Path(storage_cfg.get('quote_path', 'datas/quotes'))
        self.storage_format = storage_cfg.get('format', 'parquet')
        # 确保目录存在
        self.quote_path.mkdir(parents=True, exist_ok=True)

    def get_daily_data(self, symbol: str, count: int = 300, start_offset: int = 0) -> pd.DataFrame:
        """
        获取日线数据（优先从缓存读取，若不存在则从网络获取）

        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SH"
            count: 获取的数据条数（至少需要大于最长指标周期）
            start_offset: 起始偏移，0 表示最新一天，1 表示前一天，以此类推

        Returns:
            DataFrame 包含列: open, high, low, close, volume（以日期为索引）
        """
        # 先尝试从缓存加载
        df_cached = self._load_quote_data_from_cache(symbol, start_offset)
        if not df_cached.empty:
            logger.info(f"从缓存加载 {symbol} 行情数据成功，共 {len(df_cached)} 条")
            # 确保数据量足够
            if len(df_cached) >= count:
                return df_cached
            else:
                logger.warning(f"缓存数据不足（{len(df_cached)} < {count}），将重新获取")

        # 缓存不存在或不足，从网络获取
        code, market = self._parse_symbol(symbol)

        try:
            data = self.client.bars(
                symbol=code,
                frequency=9,          # 日线
                start=start_offset,   # 偏移量：0=最新一天，1=前一天...
                offset=count,         # 获取 count 条（向后取）
                market=market,
                adjust="qfq",
                retry=True,
                timestamp=False
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

            # 统一列名（mootdx 返回的列名通常是英文）
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True, errors='ignore')

            # 处理日期列
            if 'datetime' in df.columns:
                df['date'] = pd.to_datetime(df['datetime'])
                df.set_index('date', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            else:
                # 若无日期列，尝试使用索引
                if not isinstance(df.index, pd.DatetimeIndex):
                    logger.error("无法识别日期列，返回空DataFrame")
                    return pd.DataFrame()

            df['symbol'] = symbol  # 关键行
            # 确保所需列存在
            required_cols = ['symbol','open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"缺少必要的列，实际列名：{list(df.columns)}")
                return pd.DataFrame()

            df = df[required_cols]
            df.sort_index(inplace=True)

            logger.info(f"获取 {symbol} 数据成功，共 {len(df)} 条（起始偏移 {start_offset}）")

            # 保存到缓存
            self.save_quote_data(df, symbol, start_offset)
            return df

        except Exception as e:
            logger.error(f"获取 {symbol} 数据时出错: {e}")
            return pd.DataFrame()

    def save_quote_data(self, df: pd.DataFrame, symbol: str, start_offset: int = 0) -> Optional[Path]:
        """
        保存行情数据到本地文件

        Args:
            df: 行情DataFrame (需包含日期索引及 open,high,low,close,volume)
            symbol: 股票代码
            start_offset: 起始偏移，用于文件名区分

        Returns:
            保存的文件路径，失败返回 None
        """
        if df.empty:
            logger.warning(f"数据为空，跳过保存 {symbol}")
            return None

        # 确保索引是 DatetimeIndex，并移除 NaT
        if not isinstance( df.index, pd.DatetimeIndex ):
            try:
                df.index = pd.to_datetime( df.index )
            except:
                logger.error( "无法将索引转换为日期时间格式" )
                return None

        # 删除索引为 NaT 的行
        df = df[~df.index.isna()]
        if df.empty:
            logger.warning( "清洗后无有效数据，跳过保存" )
            return None

        # 文件名: {symbol}_{start_offset}_{起始日期}_{结束日期}.{format}
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        filename = f"{symbol}_{start_offset}_{start_date}_{end_date}.{self.storage_format}"
        filepath = self.quote_path / filename

        try:
            if self.storage_format == 'parquet':
                df.to_parquet(filepath)
            else:
                df.to_csv(filepath)
            logger.info(f"行情数据已保存至 {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存行情数据失败: {e}")
            return None

    def _load_quote_data_from_cache(self, symbol: str, start_offset: int = 0) -> pd.DataFrame:
        """
        从本地缓存加载行情数据（根据命名规则查找最新的文件）
        """
        pattern = f"{symbol}_{start_offset}_*.{self.storage_format}"
        files = list(self.quote_path.glob(pattern))
        if not files:
            return pd.DataFrame()
        # 按修改时间取最新的
        latest_file = max(files, key=lambda p: p.stat().st_mtime)
        try:
            if self.storage_format == 'parquet':
                df = pd.read_parquet(latest_file)
            else:
                df = pd.read_csv(latest_file, index_col=0, parse_dates=True)
            logger.info(f"从缓存加载行情数据: {latest_file}")
            return df
        except Exception as e:
            logger.warning(f"读取缓存文件失败 {latest_file}: {e}")
            return pd.DataFrame()

    @staticmethod
    def _parse_symbol(symbol: str) -> Tuple[str, int]:
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