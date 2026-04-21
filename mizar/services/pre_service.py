"""
预测统计服务
基于相似状态计算预测指标
2026.03.26 修正版本
    增加 temporal_decay
"""

import numpy as np
from typing import List, Dict, Any, Optional
from loguru import logger


class PredictionService:
    """预测统计服务"""

    def __init__(self, config: dict):
        """
        初始化预测服务

        Args:
            config: 配置字典，可包含以下键：
                - weighting_method: 默认加权方法 (str)
                - temporal_decay: 时间衰减因子 (float)
        """
        self.config = config
        self.default_weighting = config.get('weighting_method', 'distance')
        self.temporal_decay = config.get('temporal_decay', 0.1)  # 时间衰减因子

    def calculate_statistics(
            self,
            similar_states: List[Dict[str, Any]],
            weighting_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        基于相似状态计算预测统计
        """
        if not similar_states:
            return self._empty_prediction()

        # 输入验证·
        if not isinstance(similar_states, list):
            logger.warning("similar_states 应为列表，已自动转换")
            similar_states = [similar_states]

        method = weighting_method or self.default_weighting
        # logger.info( f"基于 {len( similar_states )} 个相似状态，使用 {method} 加权计算预测..." )
        logger.info(f"基于 {len(similar_states)} 个相似状态，使用 {method} 加权计算预测...")

        # 提取有效数据（仅包含未来1日收益的记录）
        valid_data = []
        for state in similar_states:
            ret1 = state.get('future_ret_1d')
            if ret1 is not None:
                valid_data.append({
                    'ret1': ret1,
                    'ret5': state.get('future_ret_5d'),  # 可为None
                    'label': state.get('future_label'),
                    'distance': state.get('distance', 1.0),
                    'date': state.get('date'),
                })

        if not valid_data:
            return self._empty_prediction()

        # 提取距离和日期列表（用于权重计算）
        distances = [d['distance'] for d in valid_data]
        dates = [d['date'] for d in valid_data]

        # 计算权重（基于所有有效样本）
        weights = self._calculate_weights(distances, dates, method)

        # 收集各项数据及对应权重
        ret1_vals = []
        ret1_weights = []
        ret5_vals = []
        ret5_weights = []
        labels = []

        for idx, d in enumerate(valid_data):
            w = weights[idx]
            ret1_vals.append(d['ret1'])
            ret1_weights.append(w)

            if d['ret5'] is not None:
                ret5_vals.append(d['ret5'])
                ret5_weights.append(w)

            if d['label'] is not None:
                labels.append(d['label'])

        # 计算加权平均
        avg_ret_1d = float(np.average(ret1_vals, weights=ret1_weights)) if ret1_vals else None
        avg_ret_5d = float(np.average(ret5_vals, weights=ret5_weights)) if ret5_vals else None

        # 上涨概率（简单计数，也可加权）
        up_probability = float(np.sum(np.array(ret1_vals) > 0) / len(ret1_vals)) if ret1_vals else None

        # 标签分布
        label_distribution = self._count_labels(labels)

        prediction = {
            'avg_ret_1d': avg_ret_1d,
            'avg_ret_5d': avg_ret_5d,
            'up_probability': up_probability,
            'label_distribution': label_distribution,
            'sample_size': len(ret1_vals),
            'weighted': method != 'simple',
            'weighting_method': method,
        }

        # 风险指标
        if len(ret1_vals) > 1:
            std_ret_1d = float(np.std(ret1_vals, ddof=1))
            prediction['std_ret_1d'] = std_ret_1d
            if std_ret_1d > 0 and avg_ret_1d is not None:
                prediction['sharpe_ratio'] = float(avg_ret_1d / std_ret_1d * np.sqrt(252))
            else:
                prediction['sharpe_ratio'] = None
        else:
            prediction['std_ret_1d'] = None
            prediction['sharpe_ratio'] = None

        return prediction

    def _calculate_weights(self, distances: List[float], dates: List[Any], method: str) -> np.ndarray:
        """
        计算权重

        Args:
            distances: 距离列表
            dates: 日期列表（可能包含 None 或不可解析的值）
            method: 加权方法

        Returns:
            np.ndarray: 权重数组
        """
        distances = np.array(distances)

        if method == 'simple':
            weights = np.ones(len(distances))

        elif method == 'distance':
            # 距离加权（距离越小权重越大）
            weights = 1.0 / (distances + 1e-6)

        elif method == 'temporal':
            # 时效性加权：基于日期，越近的日期权重越大
            weights = self._temporal_weights(dates)

        elif method == 'distance_temporal':
            # 距离 + 时效性混合加权
            distance_weights = 1.0 / (distances + 1e-6)
            temporal_weights = self._temporal_weights(dates)
            weights = distance_weights * temporal_weights

        else:
            raise ValueError(f"不支持的加权方法：{method}")

        # 归一化权重
        total = weights.sum()
        if total > 0:
            weights = weights / total
        else:
            weights = np.ones(len(distances)) / len(distances)

        return weights

    def _temporal_weights(self, dates: List[Any]) -> np.ndarray:
        """
        计算时效性权重（基于日期，越近权重越大）

        Args:
            dates: 日期列表

        Returns:
            np.ndarray: 时效性权重（未归一化）
        """
        n = len(dates)

        # 尝试将日期转换为时间戳（天数）
        timestamps = []
        for d in dates:
            if d is None:
                timestamps.append(0)
            elif isinstance(d, (int, float)):
                timestamps.append(d)  # 假设已经是天数
            elif hasattr(d, 'timestamp'):  # datetime-like
                timestamps.append(d.timestamp() / (24 * 3600))
            else:
                # 尝试字符串解析
                try:
                    from datetime import datetime
                    if isinstance(d, str):
                        dt = datetime.fromisoformat(d.replace(' ', 'T'))
                        timestamps.append(dt.timestamp() / (24 * 3600))
                    else:
                        timestamps.append(0)
                except Exception:
                    timestamps.append(0)

        timestamps = np.array(timestamps)
        current_time = np.max(timestamps)

        # 指数衰减：权重 = exp(-decay * (current_time - timestamp))
        weights = np.exp(-self.temporal_decay * (current_time - timestamps))

        # 如果所有日期都无效，则使用简单倒序权重
        if np.all(weights == 1.0):
            weights = np.arange(n, 0, -1)

        return weights

    def _count_labels(self, labels: List[str]) -> Dict[str, int]:
        """统计标签分布"""
        from collections import Counter
        return dict(Counter(labels))

    def _empty_prediction(self) -> Dict[str, Any]:
        """返回空预测结果"""
        return {
            'avg_ret_1d': None,
            'avg_ret_5d': None,
            'up_probability': None,
            'label_distribution': {},
            'sample_size': 0,
            'weighted': False,
            'weighting_method': None,
            'std_ret_1d': None,
            'sharpe_ratio': None,
        }