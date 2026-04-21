# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : query_service.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00

# mizar/cli/query_service.py
"""独立的股票相似性查询服务，可脱离 CLI 复用"""

import numpy as np
from typing import Dict, Optional, Any

import pandas as pd
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import sys

from ..utils import load_config
from ..vector_db import VectorStorage
from ..features import FeatureEngineer
from ..services import PredictionService
from .data_fetcher import StockDataFetcher
from .indicator_calculator import IndicatorCalculator
from .styles import MIZAR_THEME

# 强制使用 UTF-8，避免宽度计算异常
console = Console(
    theme=MIZAR_THEME,
    force_terminal=True,
    color_system="auto",
    width=120,               # 固定宽度，避免容器环境检测失败
    legacy_windows=False,    # 禁用 Windows 旧版模式
)

class QueryService:
    """股票相似性检索预测服务"""

    def __init__(self):
        self.config = None
        self.feature_engineer: Optional[FeatureEngineer] = None
        self.storage: Optional[VectorStorage] = None
        self.prediction_service: Optional[PredictionService] = None
        self._initialized = False

    def initialize(self) -> bool:
        """加载模型、连接向量库（仅执行一次）"""
        if self._initialized:
            return True

        try:
            self.config = load_config()
        except Exception as e:
            console.print(f"[error]加载配置失败：{e}[/]")
            return False

        logger.remove()
        logger.add(sys.stderr, level="INFO")

        # 加载特征工程模型
        console.print("[cyan]加载特征工程模型...[/]")
        self.feature_engineer = FeatureEngineer(self.config)
        try:
            self.feature_engineer.load_models()
        except Exception as e:
            console.print(f"[error]加载模型失败：{e}[/]")
            return False

        # 连接向量数据库
        console.print("[cyan]连接向量数据库...[/]")
        self.storage = VectorStorage(self.config)
        self.storage.connect()
        self.storage.create_collection()

        if self.storage.collection is None:
            console.print("[error]向量数据库未初始化[/]")
            return False

        # 预测服务
        self.prediction_service = PredictionService(self.config)

        self._initialized = True
        console.print("[success]✓ 初始化完成[/]\n")
        return True

    def get_indicators(self, symbol: str, start: int = 0) -> Optional[Dict[str, float]]:
        """
        获取指定股票指定偏移日的指标值

        Args:
            symbol: 股票代码
            start: 偏移天数，0 为最新，1 为前一个交易日

        Returns:
            特征名 -> 指标值的字典，包含 'date' 字段，失败返回 None
        """
        if not self._initialized:
            console.print( "[error]服务未初始化[/]" )
            return None

        fetcher = StockDataFetcher()
        df = fetcher.get_daily_data( symbol, count=60, start=start )

        if df.empty:
            console.print( f"[error]无法获取 {symbol} 的行情数据[/]" )
            return None

        # ---- 提取查询日期 ----
        query_date = ''
        # 假设 df 索引为日期（DatetimeIndex）或包含 'date' 列
        if isinstance( df.index, pd.DatetimeIndex ):
            # 取最后一行（偏移后的最新数据）的日期
            target_date = df.index[-1]
            query_date = target_date.strftime( '%Y-%m-%d' )
        elif 'date' in df.columns:
            dates = pd.to_datetime( df['date'] )
            target_date = dates.iloc[-1]
            query_date = target_date.strftime( '%Y-%m-%d' )
        else:
            # 若无日期信息，则留空
            query_date = ''

        calculator = IndicatorCalculator( self.feature_engineer.selected_features )
        indicators = calculator.calculate( df )

        if indicators is None:
            console.print( f"[error]计算 {symbol} 的指标失败[/]" )
            return None

        # 将日期插入指标字典
        indicators['date'] = query_date

        return indicators

    def query(self, symbol: str, start: int = 0, top_k: int = 10) -> Optional[Dict[str, Any]]:
        """
        执行一次完整查询：获取指标 → 向量检索 → 预测统计

        Args:
            symbol: 股票代码
            start: 偏移天数
            top_k: 相似样本数

        Returns:
            包含预测结果和相似样本的字典，失败返回 None
        """
        # 1. 获取指标
        indicators = self.get_indicators(symbol, start)
        if indicators is None:
            return None

        # 2. 构建特征向量（按训练顺序）
        feature_names = self.feature_engineer.selected_features
        missing = set(feature_names) - set(indicators.keys())
        if missing:
            console.print(f"[error]缺少特征：{missing}[/]")
            return None

        X = np.array([indicators[name] for name in feature_names], dtype=np.float32).reshape(1, -1)
        X = np.nan_to_num(X)  # 替换 NaN 为 0

        # 3. 归一化 + 降维
        X_norm = self.feature_engineer.scaler.transform(X)
        X_reduced = self.feature_engineer.pca.transform(X_norm)

        # 4. 向量检索
        results = self.storage.query(X_reduced, top_k=top_k)
        if not results['metadatas']:
            console.print("[warning]未找到相似状态[/]")
            return None

        # 5. 构建相似状态列表
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

        # 6. 预测统计
        prediction = self.prediction_service.calculate_statistics(similar_states)
        query_date = indicators.get('date', '' )

        return {
            'query_date':query_date,
            'symbol': symbol,
            'start': start,
            'top_k': top_k,
            'prediction': prediction,
            'similar_states': similar_states,
        }


    def print_result(self, result: Dict[str, Any]):
        """以 Rich 结构化布局打印查询结果（紧凑优化版）"""
        try:
            pred = result['prediction']
            similar = result.get( 'similar_states', [] )

            console.print()

            # ========== 顶部信息汇总面板（原辅助信息提升至此） ==========
            sample_size = pred.get( 'sample_size', 0 )
            weight_method = pred.get( 'weighting_method', 'default' )
            label_dist = pred.get( 'label_distribution', {} )
            label_str = " ".join( [f"{k}:{v}" for k, v in label_dist.items()] ) if label_dist else "无"

            info_lines = [
                f"时间: {result['query_date']}   参数: top_k={sample_size}   加权: {weight_method}",
                f"样本分布: {label_str}"
            ]
            info_text = "\n".join( info_lines )
            info_panel = Panel( info_text, title=f"代码 {result['symbol']}", border_style="dim", padding=(0, 2) )
            # 注意：这个面板后续会放入统一容器中，所以不需要直接打印

            # ========== 核心信号面板（两列布局） ==========
            prob = pred.get( 'up_probability', 0 )
            ret1 = pred.get( 'avg_ret_1d', 0 )
            volatility = pred.get( 'std_ret_1d', 0 )
            confidence = pred.get( 'confidence', 0 )

            # 颜色逻辑
            if prob < 0.35:
                prob_color = "grey"
            elif prob < 0.50:
                prob_color = "yellow"
            elif prob < 0.60:
                prob_color = "orange1"
            else:
                prob_color = "green"
            prob_display = f"[{prob_color}]{prob * 100:.2f}%[/]"

            ret1_color = "green" if ret1 > 0 else "red" if ret1 < 0 else "white"
            ret1_display = f"[{ret1_color}]{ret1:+.2f}%[/]"

            core_grid = Table.grid( padding=(0, 2) )
            core_grid.add_column( style="cyan", justify="left" )
            core_grid.add_column( justify="right" )
            core_grid.add_column( style="cyan", justify="left" )
            core_grid.add_column( justify="right" )
            core_grid.add_row(
                "上涨概率", prob_display,
                "次日收益", ret1_display
            )
            core_grid.add_row(
                "波动率", f"{volatility:.2f}%",
                "置信度", f"{confidence:.3f}"
            )

            core_panel = Panel( core_grid, title="[bold]核心信号[/]", border_style="cyan", expand=False )

            # ========== 5日展望面板 ==========
            ret5_mean = pred.get( 'avg_ret_5d', 0 )
            ret5_median = pred.get( 'median_ret_5d', 0 )
            var_down = pred.get( 'var_90', 0 )
            upside_up = pred.get( 'upside_90', 0 )

            mean_color = "green" if ret5_mean > 0 else "red" if ret5_mean < 0 else "white"
            median_color = "green" if ret5_median > 0 else "red" if ret5_median < 0 else "white"

            mid_grid = Table.grid( padding=(0, 2) )
            mid_grid.add_column( style="cyan", justify="left" )
            mid_grid.add_column( justify="right" )
            mid_grid.add_column( style="cyan", justify="left" )
            mid_grid.add_column( justify="right" )
            mid_grid.add_row(
                "收益（均值）", f"[{mean_color}]{ret5_mean:+.2f}%[/]",
                "收益（中位数）", f"[{median_color}]{ret5_median:+.2f}%[/]"
            )
            mid_grid.add_row(
                "下行风险 (VaR 90%)", f"[bold red]{var_down:+.2f}%[/]",
                "上行潜力 (90%分位)", f"[bold green]{upside_up:+.2f}%[/]"
            )

            mid_panel = Panel( mid_grid, title="[bold]5日预期收益|风险|潜力[/]", border_style="magenta", expand=False )

            # ========== 相似表格 ==========
            if not similar:
                console.print( "[warning]无相似状态详情[/]" )
                console.print()
                return

            table = Table( title="向量相似 Top 5", title_style="bold cyan" )
            table.add_column( "日期", style="dim" )
            table.add_column( "标的", style="dim" )
            table.add_column( "标签", justify="center" )
            table.add_column( "次日收益", justify="right" )
            table.add_column( "5日收益", justify="right" )
            table.add_column( "距离", justify="right" )

            for state in similar[:5]:
                date = str( state.get( 'date', '' ).split()[0] )
                symbol = str( state.get( 'symbol', '' ) )
                label = str( state.get( 'future_label', '' ) )
                ret_1d = state.get( 'future_ret_1d' )
                ret_5d = state.get( 'future_ret_5d' )
                distance = state.get( 'distance' )

                ret_str = f"{ret_1d:+.2f}%" if ret_1d is not None else "N/A"
                ret5_str = f"{ret_5d:+.2f}%" if ret_5d is not None else "N/A"
                dist_str = f"{distance:.4f}" if distance is not None else "N/A"

                if label in ("涨", "小涨", "大涨"):
                    label_style = "green"
                elif label in ("跌", "小跌", "大跌"):
                    label_style = "red"
                else:
                    label_style = "yellow"

                table.add_row( date, symbol, f"[{label_style}]{label}[/]", ret_str, ret5_str, dist_str )

            # ========== 统一布局容器 ==========
            layout = Table.grid( padding=(0, 0) )
            layout.add_column()  # 单列，宽度由最宽的行（表格）决定

            layout.add_row( info_panel )
            layout.add_row( core_panel )
            layout.add_row( mid_panel )
            layout.add_row( table )

            console.print( layout )
            console.print()

        except Exception as e:
            console.print( "[error]格式化输出时出错，降级显示原始数据：[/]" )
            console.print( result )
            logger.exception( "print_result 异常" )


# 全局单例（可选）
_query_service_instance: Optional[QueryService] = None


def get_query_service() -> QueryService:
    """获取全局查询服务单例"""
    global _query_service_instance
    if _query_service_instance is None:
        _query_service_instance = QueryService()
        _query_service_instance.initialize()
    return _query_service_instance