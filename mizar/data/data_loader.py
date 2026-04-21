"""
数据导入模块
支持 CSV 和 JSON 格式的技术指标数据导入
"""

import numpy as np
import pandas as pd
import json
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
        self.date_column = config.get('data', {}).get('date_column', 'date')
        self.symbol_column = config.get('data', {}).get('symbol_column', 'symbol')
        self.open_column = config.get( 'data', {} ).get( 'open_column', 'open' )
        self.close_column = config.get( 'data', {} ).get( 'close_column', 'close' )
        # 旧版本字段规范 current_price
        # self.close_column = config.get('data', {}).get('close_column', 'current_price')
        
    def load_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        加载 CSV 文件
        
        Args:
            file_path: CSV 文件路径
            
        Returns:
            DataFrame: 加载的数据
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"CSV 文件不存在：{file_path}")
        
        logger.info(f"正在加载 CSV 文件：{file_path}")
        df = pd.read_csv(file_path)
        logger.info(f"成功加载 {len(df)} 条记录")
        
        return self._validate_and_preprocess(df)
    
    def load_json(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        加载 JSON 文件
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            DataFrame: 加载的数据
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"JSON 文件不存在：{file_path}")
        
        logger.info(f"正在加载 JSON 文件：{file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持列表格式和字典格式
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # 假设是 {"data": [...]} 格式
            if 'data' in data:
                df = pd.DataFrame(data['data'])
            else:
                # 假设是 {date: {symbol: {...}}} 格式
                df = pd.DataFrame.from_dict(data, orient='index')
        else:
            raise ValueError("不支持的 JSON 数据格式")
        
        logger.info(f"成功加载 {len(df)} 条记录")
        
        return self._validate_and_preprocess(df)
    
    def load_multiple_files(self, pattern: str) -> pd.DataFrame:
        """
        加载多个文件（支持通配符）
        
        Args:
            pattern: 文件路径模式（如 ./datas/raw/*.csv）
            
        Returns:
            DataFrame: 合并后的数据
        """
        from glob import glob
        
        files = glob(pattern)
        if not files:
            raise FileNotFoundError(f"未找到匹配的文件：{pattern}")
        
        logger.info(f"找到 {len(files)} 个文件")
        
        dfs = []
        for file in files:
            try:
                if file.endswith('.csv'):
                    df = self.load_csv(file)
                elif file.endswith('.json'):
                    df = self.load_json(file)
                else:
                    logger.warning(f"跳过不支持的文件格式：{file}")
                    continue
                
                dfs.append(df)
            except Exception as e:
                logger.error(f"加载文件 {file} 失败：{e}")
                continue
        
        if not dfs:
            raise ValueError("未能成功加载任何文件")
        
        combined_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"合并后总记录数：{len(combined_df)}")
        
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
            raise ValueError(f"缺少必需列：{missing_cols}")
        
        # 转换日期列为 datetime 类型
        df[self.date_column] = pd.to_datetime(df[self.date_column])
        
        # 按日期和代码排序
        df = df.sort_values([self.date_column, self.symbol_column])
        
        # 重置索引
        df = df.reset_index(drop=True)
        
        logger.info(f"数据验证完成，有效记录：{len(df)} 条")
        
        return df
    
    def calculate_future_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算未来收益标签
        
        Args:
            df: 包含收盘价的数据
            
        Returns:
            DataFrame: 添加了未来标签的数据
        """
        logger.info("正在计算未来收益标签...")
        
        df = df.copy()
        
        # 按标的分组计算
        grouped = df.groupby(self.symbol_column)
        
        future_ret_1d_list = []
        future_ret_5d_list = []
        future_max_dd_5d_list = []
        future_label_list = []
        
        for name, group in grouped:
            group = group.sort_values(self.date_column)
            close_prices = group[self.close_column].values
            
            # 计算未来 1 日收益率
            ret_1d = []
            for i in range(len(close_prices)):
                if i < len(close_prices) - 1:
                    ret = (close_prices[i+1] - close_prices[i]) / close_prices[i] * 100
                else:
                    ret = 0  # 最后一天无法计算 按0计算
                ret_1d.append(ret)
            
            # 计算未来 5 日收益率
            ret_5d = []
            for i in range(len(close_prices)):
                if i < len(close_prices) - 5:
                    ret = (close_prices[i+5] - close_prices[i]) / close_prices[i] * 100
                else:
                    ret = 0
                ret_5d.append(ret)
            
            # 计算未来 5 日最大回撤
            max_dd_5d = []
            for i in range(len(close_prices)):
                if i < len(close_prices) - 5:
                    window = close_prices[i:i+6]  # 包括当天共 6 天
                    peak = np.maximum.accumulate(window)
                    dd = (window - peak) / peak * 100
                    max_dd = np.min(dd)
                else:
                    max_dd = None
                max_dd_5d.append(max_dd)
            
            # 计算分类标签
            # 计算分类标签
            labels = []
            for ret in ret_1d:
                if ret is None:
                    labels.append( None )
                elif ret >= 3:
                    labels.append( '大涨' )
                elif ret > 0.5:
                    labels.append( '小涨' )
                elif ret >= -0.5:
                    labels.append( '震荡' )
                elif ret >= -3:
                    labels.append( '小跌' )
                else:
                    labels.append( '大跌' )
            
            future_ret_1d_list.extend(ret_1d)
            future_ret_5d_list.extend(ret_5d)
            future_max_dd_5d_list.extend(max_dd_5d)
            future_label_list.extend(labels)
        
        df['future_ret_1d'] = future_ret_1d_list
        df['future_ret_5d'] = future_ret_5d_list
        df['future_max_dd_5d'] = future_max_dd_5d_list
        df['future_label'] = future_label_list
        
        # 删除最后一天的数据（无法计算未来收益）
        df = df.dropna(subset=['future_ret_1d'])
        
        logger.info(f"未来标签计算完成，有效记录：{len(df)} 条")
        
        return df

