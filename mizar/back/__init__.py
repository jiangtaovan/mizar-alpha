# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : __init__.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00

"""
回测功能：
- 该模块针对币市BTC/ETC 进行过优化，默认不屁股股票市场 ，因参数不一致，且数据格式不一致
- 回测数据后可以保存开仓清单csv，以及净值曲线 单/双线，以及是否 净值1.0双侧对齐 可按需选择
"""

from .data_loader import load_features
from .feature_handler import FeatureHandler
from .query_engine import QueryEngine
from .metrics import calculate_metrics
from .strategy import Strategy


__all__ = ['load_features','FeatureHandler','QueryEngine','calculate_metrics','Strategy']
