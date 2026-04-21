# -*- coding: utf-8 -*-
# @Time    : 2026/3/25 
# @File    : datas_loader.py
# @Project : mizar-alpha
# @Author  : Chiang Tao
# @Version : 0.1.00

"""
数据导入模块
支持 CSV 和 JSON 格式的技术指标数据导入
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from typing import Union
from loguru import logger


class DataLoader:
    """技术指标数据加载器"""

    def __init__(self, config: dict):
        """
        初始化数据加载器

        Args:
            config: 配置字典，包含数据路径、日期列名等
        """
        self.config = config
        self.date_column = config.get( 'data', {} ).get( 'date_column', 'date' )
        self.symbol_column = config.get( 'data', {} ).get( 'symbol_column', 'symbol' )
        self.close_column = config.get( 'data', {} ).get( 'close_column', 'current_price' )

    def load_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        加载 CSV 文件

        Args:
            file_path: CSV 文件路径

        Returns:
            DataFrame: 加载的数据
        """
        file_path = Path( file_path )
        if not file_path.exists():
            raise FileNotFoundError( f"CSV 文件不存在：{file_path}" )

        logger.info( f"正在加载 CSV 文件：{file_path}" )
        df = pd.read_csv( file_path )
        logger.info( f"成功加载 {len( df )} 条记录" )

        return self._validate_and_preprocess( df )

    def load_json(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        加载 JSON 文件

        Args:
            file_path: JSON 文件路径

        Returns:
            DataFrame: 加载的数据
        """
        file_path = Path( file_path )
        if not file_path.exists():
            raise FileNotFoundError( f"JSON 文件不存在：{file_path}" )

        logger.info( f"正在加载 JSON 文件：{file_path}" )

        with open( file_path, 'r', encoding='utf-8' ) as f:
            data = json.load( f )

        # 支持列表格式和字典格式
        if isinstance( data, list ):
            df = pd.DataFrame( data )
        elif isinstance( data, dict ):
            # 假设是 {"data": [...]} 格式
            if 'data' in data:
                df = pd.DataFrame( data['data'] )
            else:
                # 假设是 {date: {symbol: {...}}} 格式，转换为行格式
                records = []
                for date, symbols in data.items():
                    if isinstance( symbols, dict ):
                        for symbol, values in symbols.items():
                            record = {self.date_column: date, self.symbol_column: symbol}
                            if isinstance( values, dict ):
                                record.update( values )
                            else:
                                record['value'] = values
                            records.append( record )
                    else:
                        records.append( {self.date_column: date, 'value': symbols} )
                df = pd.DataFrame( records )
        else:
            raise ValueError( "不支持的 JSON 数据格式" )

        logger.info( f"成功加载 {len( df )} 条记录" )

        return self._validate_and_preprocess( df )

    def load_multiple_files(self, pattern: str) -> pd.DataFrame:
        """
        加载多个文件（支持通配符）

        Args:
            pattern: 文件路径模式（如 ./datas/raw/*.csv）

        Returns:
            DataFrame: 合并后的数据
        """
        from glob import glob

        files = glob( pattern )
        if not files:
            raise FileNotFoundError( f"未找到匹配的文件：{pattern}" )

        logger.info( f"找到 {len( files )} 个文件" )

        dfs = []
        for file in files:
            try:
                if file.endswith( '.csv' ):
                    df = self.load_csv( file )
                elif file.endswith( '.json' ):
                    df = self.load_json( file )
                else:
                    logger.warning( f"跳过不支持的文件格式：{file}" )
                    continue

                dfs.append( df )
            except Exception as e:
                logger.error( f"加载文件 {file} 失败：{e}" )
                continue

        if not dfs:
            raise ValueError( "未能成功加载任何文件" )

        combined_df = pd.concat( dfs, ignore_index=True )
        # 对合并后的数据重新执行验证和排序
        combined_df = self._validate_and_preprocess( combined_df )
        logger.info( f"合并后总记录数：{len( combined_df )}" )

        return combined_df

    def _validate_and_preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证数据并执行基础预处理

        Args:
            df: 原始数据

        Returns:
            DataFrame: 处理后的数据
        """
        # 检查必需列
        required_columns = [self.date_column, self.symbol_column]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError( f"缺少必需列：{missing_cols}" )

        # 转换日期列为 datetime 类型
        df[self.date_column] = pd.to_datetime( df[self.date_column] )

        # 按日期和代码排序
        df = df.sort_values( [self.date_column, self.symbol_column] )

        # 重置索引
        df = df.reset_index( drop=True )

        logger.info( f"数据验证完成，有效记录：{len( df )} 条" )

        return df

    def calculate_future_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算未来收益标签（修正版）

        - 使用分组内索引赋值，确保标签与原始数据严格对齐
        - 未来5日最大回撤使用未来5个交易日（不含当天），避免使用当天价格影响
        - 分类标签阈值可在此处调整

        Args:
            df: 包含收盘价的数据

        Returns:
            DataFrame: 添加了未来标签的数据
        """
        logger.info( "正在计算未来收益标签..." )

        df = df.copy()

        # 按标的分组，不保留分组键，确保 apply 返回的 DataFrame 索引与原 df 对齐
        grouped = df.groupby( self.symbol_column, group_keys=False )

        def compute_labels(group: pd.DataFrame) -> pd.DataFrame:
            """
            为单个股票分组计算未来标签
            """
            group = group.sort_values( self.date_column )
            close = group[self.close_column].values
            n = len( close )

            # 初始化结果数组
            ret_1d = [np.nan] * n
            ret_5d = [np.nan] * n
            max_dd_5d = [np.nan] * n
            label = [None] * n

            for i in range( n ):
                # 未来 1 日收益率 (%)
                if i < n - 1:
                    ret_1d[i] = (close[i + 1] - close[i]) / close[i] * 100

                # 未来 5 日收益率 (%)
                if i < n - 5:
                    ret_5d[i] = (close[i + 5] - close[i]) / close[i] * 100

                # 未来 5 日最大回撤（不含当天，取未来5个交易日的回撤）
                if i < n - 5:
                    future_window = close[i + 1:i + 6]  # 未来5个收盘价
                    peak = np.maximum.accumulate( future_window )  # 滚动峰值
                    dd = (future_window - peak) / peak * 100  # 回撤率（负值）
                    max_dd_5d[i] = np.min( dd )  # 最大回撤（最负的值）

                # 分类标签（基于未来1日收益）
                if i < n - 1:
                    r = ret_1d[i]
                    # 阈值可根据实际策略调整
                    if r > 2:
                        label[i] = '大涨'
                    elif r >= 0:
                        label[i] = '小涨'
                    elif r >= -2:
                        label[i] = '小跌'
                    else:
                        label[i] = '大跌'

            # 返回与 group 索引对齐的 DataFrame
            return pd.DataFrame( {
                'future_ret_1d': ret_1d,
                'future_ret_5d': ret_5d,
                'future_max_dd_5d': max_dd_5d,
                'future_label': label
            }, index=group.index )

        # 应用分组计算，结果自动按原索引对齐
        results = grouped.apply( compute_labels )

        # 将计算结果赋值到原 DataFrame（列名匹配）
        df[['future_ret_1d', 'future_ret_5d', 'future_max_dd_5d', 'future_label']] = results

        # 删除无法计算未来收益的行（最后一天或最后五天）
        df = df.dropna( subset=['future_ret_1d'] )

        logger.info( f"未来标签计算完成，有效记录：{len( df )} 条" )
        return df