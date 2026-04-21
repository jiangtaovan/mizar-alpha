# -*- coding: utf-8 -*-
# @Time    : 2026/4/19 
# @File    : predict_service.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00

"""
预测统计服务
基于相似状态计算预测指标

迭代历史：
2026.04 - 初始版本：简单统计（均值、上涨概率）
v0.1.1 - 增加距离加权（1/distance）及时效性加权（temporal）
v0.1.2 - 增加5日收益中位数、VaR、上行潜力等风险指标
v0.2.0 - 修正上涨概率为加权版本，删除未使用的temporal/distance_temporal混合加权
v0.2.1 - 代码清理：仅保留distance加权（默认）和simple（备选），
        - 增加加权上涨概率、风险分位数，删除冗余的夏普比率计算
         - 上涨概率剔除平盘样本，避免系统性低估
         - 增加波动率（加权标准差）和置信度（优化算法）
         - 修复分位数边界越界问题，添加最小样本数阈值
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
                - weighting_method: 默认加权方法，仅支持 'distance' 或 'simple'（默认 'distance'）
                - temporal_decay: （保留，暂未使用）时间衰减因子
        """
        self.config = config
        self.default_weighting = config.get('weighting_method', 'distance')
        # 保留但暂未使用（如需启用时间衰减，可取消 _calculate_weights 中的注释）
        self.temporal_decay = config.get('temporal_decay', 0.1)

    def calculate_statistics(
            self,
            similar_states: List[Dict[str, Any]],
            weighting_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        基于相似状态计算预测统计

        Args:
            similar_states: 相似状态列表，每个元素需包含：
                - future_ret_1d: 次日收益（必须）
                - future_ret_5d: 5日收益（可选）
                - distance: 距离（必须，用于加权）
                - future_label: 标签（可选）
                - date: 日期（可选，用于时间衰减）
            weighting_method: 加权方法，默认 'distance'

        Returns:
            预测结果字典，包含：
                - avg_ret_1d: 加权次日收益均值
                - weighted_up_prob: 加权上涨概率（剔除平盘）
                - std_ret_1d: 加权次日收益波动率
                - confidence: 置信度（基于样本数、方向一致性、距离）
                - avg_ret_5d: 加权5日收益均值
                - median_ret_5d: 5日收益加权中位数
                - var_90: 下行风险（90% VaR，即10%分位数）
                - upside_90: 上行潜力（90%分位数）
                - sample_size: 有效样本数
                - label_distribution: 标签分布（简单计数）
                - weighting_method: 使用的加权方法
        """
        if not similar_states:
            return self._empty_prediction()

        if not isinstance(similar_states, list):
            logger.warning("similar_states 应为列表，已自动转换")
            similar_states = [similar_states]

        method = weighting_method or self.default_weighting
        logger.info(f"基于 {len(similar_states)} 个相似状态，使用 {method} 加权计算预测...")

        # 提取有效数据（仅包含未来1日收益的记录）
        valid_data = []
        for state in similar_states:
            ret1 = state.get('future_ret_1d')
            if ret1 is not None:
                valid_data.append({
                    'ret1': ret1,
                    'ret5': state.get('future_ret_5d'),
                    'label': state.get('future_label'),
                    'distance': state.get('distance', 1.0),
                    'date': state.get('date'),
                })

        if not valid_data:
            return self._empty_prediction()

        # 计算权重（基于距离，可选时间衰减）
        distances = [d['distance'] for d in valid_data]
        dates = [d['date'] for d in valid_data]
        weights = self._calculate_weights(distances, dates, method)

        # 收集加权数据
        ret1_vals = []
        ret1_weights = []
        ret5_vals = []
        ret5_weights = []

        for idx, d in enumerate(valid_data):
            w = weights[idx]
            ret1_vals.append(d['ret1'])
            ret1_weights.append(w)
            if d['ret5'] is not None:
                ret5_vals.append(d['ret5'])
                ret5_weights.append(w)

        n1 = len(ret1_vals)
        n5 = len(ret5_vals)

        # 1. 次日加权均值
        avg_ret_1d = float(np.average(ret1_vals, weights=ret1_weights)) if n1 > 0 else None

        # 2. 加权上涨概率（剔除平盘，即收益为0的样本）
        non_zero_mask = [r != 0 for r in ret1_vals]
        if any(non_zero_mask):
            total_nonzero_weight = sum(w for m, w in zip(non_zero_mask, ret1_weights) if m)
            up_weight = sum(w for r, w in zip(ret1_vals, ret1_weights) if r > 0)
            weighted_up_prob = float(up_weight / total_nonzero_weight) if total_nonzero_weight > 0 else 0.5
        else:
            weighted_up_prob = 0.5  # 全部平盘

        # 3. 波动率（加权标准差）
        if n1 > 1:
            variance = np.average((np.array(ret1_vals) - avg_ret_1d) ** 2, weights=ret1_weights)
            std_ret_1d = float(np.sqrt(variance))
        else:
            std_ret_1d = None

        # 4. 置信度（调用独立方法）
        confidence = self._calculate_confidence(ret1_vals, weights, distances)

        # 5日收益统计
        avg_ret_5d = None
        median_ret_5d = None
        var_90 = None
        upside_90 = None

        if n5 >= 2:  # 允许2个样本，但给出警告
            if n5 < 3:
                logger.warning( f"5日收益样本数仅{n5}，分位数结果参考价值有限" )
            avg_ret_5d = float( np.average( ret5_vals, weights=ret5_weights ) )
            # 加权中位数和分位数
            sorted_idx = np.argsort( ret5_vals )
            sorted_vals = np.array( ret5_vals )[sorted_idx]
            sorted_weights = np.array( ret5_weights )[sorted_idx]
            cum_weights = np.cumsum( sorted_weights )
            cum_norm = cum_weights / cum_weights[-1]
            # 中位数
            median_idx = np.searchsorted( cum_norm, 0.5 )
            median_idx = min( median_idx, len( sorted_vals ) - 1 )
            median_ret_5d = float( sorted_vals[median_idx] )
            # VaR 90% (10%分位数)
            var_idx = np.searchsorted( cum_norm, 0.1 )
            var_idx = min( var_idx, len( sorted_vals ) - 1 )
            var_90 = float( sorted_vals[var_idx] )
            # 上行潜力 (90%分位数)
            upside_idx = np.searchsorted( cum_norm, 0.9 )
            upside_idx = min( upside_idx, len( sorted_vals ) - 1 )
            upside_90 = float( sorted_vals[upside_idx] )
        elif n5 > 0:
            # 只有1个样本，只计算均值
            avg_ret_5d = float( np.average( ret5_vals, weights=ret5_weights ) )
            # 分位数保持 None

        # 标签分布（简单计数，未加权）
        labels = [d['label'] for d in valid_data if d['label'] is not None]
        label_distribution = self._count_labels(labels)

        return {
            'avg_ret_1d': avg_ret_1d,
            'up_probability': weighted_up_prob,
            'std_ret_1d': std_ret_1d,
            'confidence': confidence,
            'avg_ret_5d': avg_ret_5d,
            'median_ret_5d': median_ret_5d,
            'var_90': var_90,
            'upside_90': upside_90,
            'sample_size': n1,
            'label_distribution': label_distribution,
            'weighting_method': method,
        }

    def _calculate_weights(self, distances: List[float], dates: List[Any], method: str) -> np.ndarray:
        """
        计算权重（归一化）

        Args:
            distances: 距离列表
            dates: 日期列表（当前未使用，保留为扩展）
            method: 加权方法，支持 'simple' 和 'distance'

        Returns:
            归一化后的权重数组
        """
        distances = np.array(distances)

        if method == 'simple':
            weights = np.ones(len(distances))
        elif method == 'distance':
            # 指数核：带宽为距离中位数的0.5倍，平滑且避免权重爆炸
            sigma = np.median(distances) * 0.5
            if sigma < 1e-6:
                sigma = 1e-6
            weights = np.exp(-distances / sigma)
        else:
            raise ValueError(f"不支持的加权方法：{method}，仅支持 'distance' 或 'simple'")

        # 归一化
        total = weights.sum()
        if total > 0:
            weights = weights / total
        else:
            weights = np.ones(len(distances)) / len(distances)

        return weights

    def _calculate_confidence(self, returns_1d: List[float], weights: np.ndarray,
                              distances: List[float]) -> float:
        """
        计算置信度（优化版）
        因子：
            - 有效样本数（逆辛普森指数，平滑饱和）
            - 方向一致性 + 收益强度（剔除平盘）
            - 距离衰减（校准至典型距离因子0.85）

        Returns:
            置信度，范围[0,1]
        """
        returns_1d = np.asarray(returns_1d)
        n = len(returns_1d)
        if n == 0:
            return 0.0

        weights_norm = weights / np.sum(weights)

        # 1. 有效样本数因子（平滑曲线）
        effective_n = 1.0 / (np.sum(weights_norm ** 2) + 1e-10)
        tau = 4.0  # 当 effective_n = 4 时因子≈0.63
        n_factor = 1.0 - np.exp(-effective_n / tau)

        # 2. 方向一致性 + 强度因子 + 平盘惩罚
        flat_thresh = 0.0005  # 0.05%
        flat_mask = np.abs(returns_1d) < flat_thresh
        flat_ratio = np.sum(weights[flat_mask]) / np.sum(weights)

        non_flat = ~flat_mask
        if np.any(non_flat):
            w_nonflat = weights[non_flat]
            r_nonflat = returns_1d[non_flat]
            up_prob = np.sum(w_nonflat[r_nonflat > 0]) / np.sum(w_nonflat)
            consistency = 2.0 * abs(up_prob - 0.5)

            # 强度因子：加权收益的均值绝对值 / 标准差
            mean_ret = np.average(r_nonflat, weights=w_nonflat)
            std_ret = np.sqrt(np.average((r_nonflat - mean_ret) ** 2, weights=w_nonflat))
            strength = np.tanh(abs(mean_ret) / (std_ret + 0.005) / 2.0)
            consistency_strength = consistency * (0.5 + 0.5 * strength)

            # 平盘惩罚
            flat_penalty = 1.0 - flat_ratio
            consistency_factor = consistency_strength * flat_penalty
        else:
            consistency_factor = 0.0

        # 3. 距离因子（校准：典型距离下因子=0.85）
        avg_dist = np.mean(distances)
        med_dist = np.median(distances)
        desired_factor_at_med = 0.85
        # 防止除零：若 med_dist 极小，温度也极小，距离因子趋近1
        if med_dist < 1e-8:
            distance_factor = 1.0
        else:
            temperature = -med_dist / np.log(desired_factor_at_med)
            distance_factor = np.exp(-avg_dist / temperature)

        # 4. 组合
        confidence = 0.35 * n_factor + 0.35 * consistency_factor + 0.30 * distance_factor

        # 可选：远距离自适应惩罚（箱线图离群点）
        q75 = np.percentile(distances, 75)
        q25 = np.percentile(distances, 25)
        iqr = q75 - q25
        far_thresh = q75 + 1.5 * iqr
        far_mask = np.array(distances) > far_thresh
        if np.any(far_mask):
            far_ratio = np.sum(weights[far_mask]) / np.sum(weights)
            if far_ratio > 0.2:
                penalty = max(0.6, 1.0 - (far_ratio - 0.2) * 2.0)
                confidence *= penalty

        return float(np.clip(confidence, 0.0, 1.0))

    def _count_labels(self, labels: List[str]) -> Dict[str, int]:
        """统计标签分布（简单计数）"""
        from collections import Counter
        return dict(Counter(labels))

    def _empty_prediction(self) -> Dict[str, Any]:
        """返回空预测结果（字段与正常预测对齐）"""
        return {
            'avg_ret_1d': None,
            'up_probability': None,
            'std_ret_1d': None,
            'confidence': None,
            'avg_ret_5d': None,
            'median_ret_5d': None,
            'var_90': None,
            'upside_90': None,
            'sample_size': 0,
            'label_distribution': {},
            'weighting_method': None,
        }