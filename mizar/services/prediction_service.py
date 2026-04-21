"""
预测统计服务
基于相似状态计算预测指标
tips:
    关于 加权权重
    1. 简单加权（等权）
    优点：计算简单，无额外参数，所有样本一视同仁。
    缺点：忽略相似度与时效性差异，易受噪声样本干扰，对近期/高相似信息不敏感。
    适用：样本质量高、分布均匀，或作为基线对比。

    2. 距离加权（相似度权重）
    优点：高相似样本贡献更大，预测更精准，符合“近朱者赤”直觉。
    缺点：对距离尺度敏感，过陡的权重（如倒数平方）可能导致个别样本主导，易过拟合。
    适用：样本相似度区分明显，希望强调局部匹配。

    3. 时效性加权（时间衰减）
    优点：赋予近期样本更高权重，适应市场风格漂移，避免陈旧规律干扰。
    缺点：需要定义衰减参数（半衰期），若市场无显著漂移反而引入噪声；回测中需避免时间泄露。
    适用：市场非平稳、风格轮动快，且样本时间跨度较大。

    4. 混合加权（距离 × 时效）
    优点：同时兼顾相似度与时效性，理论上最全面，可灵活平衡两者重要性。
    缺点：参数增多（距离平滑方式 + 时间衰减系数），调参复杂，可能过拟合历史；计算量稍大。
    适用：数据充足、追求极致预测精度，且能通过验证集合理配置权重因子。

    建议：在程序模块中提供选项，默认使用距离加权（inverse_linear）作为稳妥起点；用户可根据回测效果或对市场状态认知，自行切换其他方式。
"""

import numpy as np
from typing import List, Dict, Any
from loguru import logger


class PredictionService:
    """预测统计服务"""
    
    def __init__(self, config: dict):
        """
        初始化预测服务
        
        Args:
            config: 配置字典
        """
        self.config = config

    def calculate_statistics(self, similar_states: List[Dict[str, Any]],
                             weighting_method: str = 'simple') -> Dict[str, Any]:
        """
        基于相似状态计算预测统计

        Args:
            similar_states: 相似状态列表（包含 future_ret_1d, future_label 等）
            weighting_method: 加权方法 ('simple', 'distance', 'temporal')

        Returns:
            Dict: 预测统计结果
        """
        if not similar_states:
            return self._empty_prediction()

        logger.debug( f"基于 {len( similar_states )} 个相似状态计算预测..." )

        # 提取收益率和标签
        returns_1d = []
        returns_5d = []
        labels = []
        distances = []
        dates = []

        for state in similar_states:
            if state.get( 'future_ret_1d' ) is not None:
                returns_1d.append( state['future_ret_1d'] )
                labels.append( state.get( 'future_label', 'unknown' ) )
                distances.append( state.get( 'distance', 1.0 ) )
                dates.append( state.get( 'date', '' ) )

            if state.get( 'future_ret_5d' ) is not None:
                returns_5d.append( state['future_ret_5d'] )

        # 计算权重
        weighting_method = self.config.get('weighting_method','simple')
        weights = self._calculate_weights( distances, weighting_method )

        # --- 修复点：上涨概率也使用权重计算 ---
        is_up = np.array( returns_1d ) > 0
        total_weight = np.sum( weights )
        if total_weight > 0:
            weighted_up_prob = np.sum( weights[is_up] ) / total_weight
        else:
            weighted_up_prob = 0.5  # 回退值

        # ------------------------------------

        # median_ret_5d = self.weighted_median( returns_5d, weights )
        # var_5d_5pct = self.weighted_quantile( returns_5d, weights, 0.05 )
        # up_5d_95pct = self.weighted_upside_quantile( returns_5d, weights, 0.95)

        # # 均值：自动缩尾
        # avg_ret_5d = RobustStats.weighted_mean( returns_5d, weights, winsorize=True )
        #
        # # 中位数：自动缩尾（中位数本身稳健，缩尾影响极小）
        # median_ret_5d = RobustStats.weighted_quantile( returns_5d, weights, 0.50, winsorize=True )
        #
        # # 下行风险
        # var_5d = RobustStats.weighted_quantile( returns_5d, weights, 0.05, winsorize=True )
        #
        # # 上行潜力
        # upside_5d = RobustStats.weighted_quantile( returns_5d, weights, 0.95, winsorize=True )

        # # ========== 强制调试输出：请观察控制台 ==========
        # print( "\n!!! DEBUG: returns_5d 完整数组 !!!" )
        # for i, (ret, w) in enumerate( zip( returns_5d, weights ) ):
        #     print( f"样本{i:2d}: 5日收益 = {ret:+.2f}%, 权重 = {w:.4f}" )
        # print( "!!! DEBUG END !!!\n" )
        # # =============================================

        avg_ret_5d, median_ret_5d, var_5d, upside_5d = self.compute_robust_stats(
            returns_5d, weights,
            q_down=0.10, q_up=0.90,
            winsorize=False,  # 保留原始极端值
            use_interp=True  # 启用插值平滑
        )

        # 计算置信度
        confidence = self._calculate_confidence( returns_1d, weights, distances )

        # 计算统计指标
        prediction = {
            'up_probability': float( weighted_up_prob ),  # 已改为加权概率
            'avg_ret_1d': float( np.average( returns_1d, weights=weights ) ),
            'avg_ret_5d': float( avg_ret_5d ),
            'median_ret_5d': float( median_ret_5d ),
            'var_5d': float( var_5d ),
            'upside_5d': float( upside_5d ),
            'confidence':confidence,
            'label_distribution': self._count_labels( labels ),
            'sample_size': len( returns_1d ),
            'weighting_method': weighting_method,
            'weighted': weighting_method != 'simple'
        }

        # 计算标准差（风险指标）
        if len( returns_1d ) > 1:
            prediction['std_ret_1d'] = float( np.std( returns_1d, ddof=1 ) )
            prediction['sharpe_ratio'] = float(
                prediction['avg_ret_1d'] / prediction['std_ret_1d'] * np.sqrt( 252 )
            ) if prediction['std_ret_1d'] > 0 else None
        else:
            prediction['std_ret_1d'] = None
            prediction['sharpe_ratio'] = None
        # # 用于调试的 代码
        # print( f"DEBUG: weights = {weights}" )
        # print( f"DEBUG: is_up = {is_up}" )
        # print( f"DEBUG: weighted_up_prob = {weighted_up_prob}" )

        return prediction

    def _calculate_weights(self, distances: List[float], method: str) -> np.ndarray:
        """
        计算权重（自适应常数版）
        """
        distances = np.array( distances )

        if method == 'simple':
            weights = np.ones( len( distances ) )

        elif method == 'distance':
            # 自适应常数：基于距离中位数的比例
            med_dist = np.median( distances )
            # 当距离极小时，c 也不应过小，设置下限 0.005
            c = max( 0.005, med_dist * 0.5 )
            # 可选：对距离进行开方压缩
            d_adj = np.sqrt( distances )
            weights = 1.0 / (d_adj + c)

        elif method == 'temporal':
            n = len( distances )
            weights = np.arange( n, 0, -1 )

        elif method == 'distance_temporal':
            med_dist = np.median( distances )
            c = max( 0.005, med_dist * 0.5 )
            d_adj = np.sqrt( distances )
            distance_weights = 1.0 / (d_adj + c)
            n = len( distances )
            temporal_weights = np.arange( n, 0, -1 )
            weights = distance_weights * temporal_weights

        else:
            raise ValueError( f"不支持的加权方法：{method}" )

        weights = weights / weights.sum()
        return weights
    
    # def _calculate_weights(self, distances: List[float], method: str) -> np.ndarray:
    #     """
    #     计算权重
    #
    #     Args:
    #         distances: 距离列表
    #         method: 加权方法
    #
    #     Returns:
    #         np.ndarray: 权重数组
    #     """
    #     distances = np.array(distances)
    #
    #     if method == 'simple':
    #         # 简单平均
    #         weights = np.ones(len(distances))
    #
    #     elif method == 'distance':
    #         # 距离加权（距离越小权重越大）
    #         # 加一个小值避免除零 inverse 当d极小时权重极大
    #         # weights = 1.0 / (distances + 1e-6)
    #         # inverse_linear 1/(1+d)，权重最大为1，无爆炸风险
    #         weights = 1.0 / (0.1 + distances)
    #
    #     elif method == 'temporal':
    #         # 时效性加权（这里简化处理，假设数据已按时间排序，近期数据权重高）
    #         n = len(distances)
    #         weights = np.arange(n, 0, -1)  # 越近的数据权重越高
    #
    #     elif method == 'distance_temporal':
    #         # 距离 + 时效性混合加权
    #         distance_weights = 1.0 / (distances + 1e-6)
    #         n = len(distances)
    #         temporal_weights = np.arange(n, 0, -1)
    #         weights = distance_weights * temporal_weights
    #
    #     else:
    #         raise ValueError(f"不支持的加权方法：{method}")
    #
    #     # 归一化权重
    #     weights = weights / weights.sum()
    #
    #     return weights

    # def _calculate_confidence(self, returns_1d: List[float], weights: np.ndarray,
    #                           distances: List[float]) -> float:
    #     """
    #     计算预测置信度（0~1，越高越可信）
    #
    #     综合考虑：
    #     - 权重集中度（有效样本数）：避免仅个别样本主导
    #     - 正负样本一致性：加权上涨概率远离0.5时更可信
    #     - 平均相似距离：距离越小越可信
    #     """
    #     n = len( returns_1d )
    #     if n == 0:
    #         return 0.0
    #
    #     # 1. 权重集中度 -> 有效样本比例 (熵归一化)
    #     weights_norm = weights / np.sum( weights )
    #     entropy = -np.sum( weights_norm * np.log( weights_norm + 1e-10 ) )
    #     max_entropy = np.log( n )
    #     concentration = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
    #     # concentration 越高表示权重越集中（由少数样本主导），此时置信度应降低，所以用 1 - concentration
    #     effective_factor = 1.0 - concentration  # 权重分散时因子高
    #
    #     # 2. 正负一致性：加权上涨概率偏离0.5的程度
    #     is_up = np.array( returns_1d ) > 0
    #     up_weight = np.sum( weights[is_up] )
    #     total_weight = np.sum( weights )
    #     if total_weight > 0:
    #         up_prob = up_weight / total_weight
    #     else:
    #         up_prob = 0.5
    #     consistency = 2.0 * abs( up_prob - 0.5 )  # 范围 [0,1]
    #
    #     # 3. 平均相似距离（归一化到[0,1]区间，假设最大距离为1.0，可根据实际调整）
    #     avg_dist = np.mean( distances ) if distances else 0.05
    #     # 距离越小置信度越高，使用指数衰减
    #     distance_factor = np.exp( -avg_dist * 20.0 )  # 距离0->1, 距离1->0.135
    #
    #     # 综合得分（可调整权重）
    #     confidence = 0.2 * effective_factor + 0.4 * consistency + 0.4 * distance_factor
    #     return round(np.clip(confidence, 0.0, 1.0), 3)

    # def _calculate_confidence(self, returns_1d: List[float], weights: np.ndarray,
    #                           distances: List[float]) -> float:
    #     n = len( returns_1d )
    #     if n == 0:
    #         return 0.0
    #
    #     weights_norm = weights / np.sum( weights )
    #
    #     # 1. 有效样本数因子（逆辛普森指数）
    #     effective_n = 1.0 / (np.sum( weights_norm ** 2 ) + 1e-10)
    #     n_factor = min( 1.0, effective_n / 5.0 )
    #
    #     # 2. 对称一致性
    #     is_up = np.array( returns_1d ) > 0
    #     up_prob = np.sum( weights[is_up] ) / np.sum( weights )
    #     consistency = 2.0 * abs( up_prob - 0.5 )
    #
    #     # 3. 自适应距离因子
    #     avg_dist = np.mean( distances )
    #     med_dist = np.median( distances )
    #     temperature = max( 0.005, med_dist * 1.5 )
    #     distance_factor = np.exp( -avg_dist / temperature )
    #
    #     # 4. 基础置信度
    #     confidence = 0.35 * n_factor + 0.35 * consistency + 0.30 * distance_factor
    #
    #     # # ==== 新增：远距离样本惩罚，按需使用 ====
    #     # # 计算距离 >0.08 的样本权重占比
    #     # far_mask = np.array( distances ) > 0.08
    #     # far_ratio = np.sum( weights[far_mask] ) / np.sum( weights )
    #     # # 若占比超过30%，线性惩罚至最低0.5倍
    #     # if far_ratio > 0.3:
    #     #     penalty = max( 0.5, 1.0 - (far_ratio - 0.3) * 1.5 )
    #     #     confidence *= penalty
    #
    #     return round( np.clip( confidence, 0.0, 1.0 ), 3 )

    def _calculate_confidence(self, returns_1d, weights, distances):

        returns_1d = np.asarray( returns_1d )
        n = len( returns_1d )
        if n == 0:
            return 0.0
        weights_norm = weights / np.sum( weights )
        # 1. 有效样本数因子（平滑版本）
        effective_n = 1.0 / (np.sum( weights_norm ** 2 ) + 1e-10)
        tau = 4.0  # 当 effective_n=4 时因子约0.63，=8时0.86
        n_factor = 1.0 - np.exp( -effective_n / tau )

        # 2. 方向一致性 + 强度因子
        flat_thresh = 0.0005  # 0.05%
        flat_mask = np.abs( returns_1d ) < flat_thresh
        flat_ratio = np.sum( weights[flat_mask] ) / np.sum( weights )
        non_flat = ~flat_mask
        if np.any( non_flat ):
            w_nonflat = weights[non_flat]
            r_nonflat = returns_1d[non_flat]
            up_prob = np.sum( w_nonflat[r_nonflat > 0] ) / np.sum( w_nonflat )
            consistency = 2.0 * abs( up_prob - 0.5 )
            # 强度因子：加权收益的均值绝对值 / 标准差
            mean_ret = np.average( r_nonflat, weights=w_nonflat )
            std_ret = np.sqrt( np.average( (r_nonflat - mean_ret) ** 2, weights=w_nonflat ) )
            strength = np.tanh( abs( mean_ret ) / (std_ret + 0.005) / 2.0 )
            consistency_strength = consistency * (0.5 + 0.5 * strength)
            # 平盘惩罚
            flat_penalty = 1.0 - flat_ratio
            consistency_factor = consistency_strength * flat_penalty
        else:
            consistency_factor = 0.0

        # 3. 距离因子（校准至典型距离因子0.85）
        avg_dist = np.mean( distances )
        med_dist = np.median( distances )
        desired_factor_at_med = 0.85
        temperature = -med_dist / np.log( desired_factor_at_med )
        distance_factor = np.exp( -avg_dist / temperature )

        # 4. 组合
        # [0.35 0.35 0.30]为泛用设定，实际需结合大盘趋势，标的波动性评估设置不同的参数
        confidence = 0.35 * n_factor + 0.35 * consistency_factor + 0.30 * distance_factor
        # 5. 远距离自适应惩罚（可选）
        q75 = np.percentile( distances, 75 )
        q25 = np.percentile( distances, 25 )
        iqr = q75 - q25
        far_thresh = q75 + 1.5 * iqr
        far_mask = np.array( distances ) > far_thresh
        if np.any( far_mask ):
            far_ratio = np.sum( weights[far_mask] ) / np.sum( weights )
            if far_ratio > 0.2:
                penalty = max( 0.6, 1.0 - (far_ratio - 0.2) * 2.0 )
                confidence *= penalty
        return round( np.clip( confidence, 0.0, 1.0 ), 3 )


    @staticmethod
    def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
        """计算加权中位数 (50%分位数)"""
        if len( values ) == 0 or np.sum( weights ) == 0:
            return float( np.median( values ) ) if len( values ) > 0 else 0.0
        sorted_idx = np.argsort( values )
        cum_weights = np.cumsum( weights[sorted_idx] )
        median_idx = np.searchsorted( cum_weights, 0.5 * np.sum( weights ) )
        return float( values[sorted_idx[median_idx]] )

    @staticmethod
    def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
        """计算加权 q 分位数 (q∈[0,1])"""
        if len( values ) == 0 or np.sum( weights ) == 0:
            return float( np.quantile( values, q ) ) if len( values ) > 0 else 0.0
        sorted_idx = np.argsort( values )
        cum_weights = np.cumsum( weights[sorted_idx] )
        target = q * np.sum( weights )
        idx = np.searchsorted( cum_weights, target )
        return float( values[sorted_idx[idx]] )

    # @staticmethod
    # def weighted_upside_quantile(values: np.ndarray, weights: np.ndarray, q: float = 0.95) -> float:
    #     """
    #     计算加权上行分位数（默认 95% 分位，即只有 5% 概率超过此收益）
    #     完全对称于 weighted_quantile 的下行计算（q=0.05）
    #     """
    #     if len( values ) == 0 or np.sum( weights ) == 0:
    #         return float( np.quantile( values, q ) ) if len( values ) > 0 else 0.0
    #     sorted_idx = np.argsort( values )
    #     cum_weights = np.cumsum( weights[sorted_idx] )
    #     target = q * np.sum( weights )
    #     idx = np.searchsorted( cum_weights, target )
    #     return float( values[sorted_idx[idx]] )

    @staticmethod
    def weighted_upside_quantile(values: np.ndarray, weights: np.ndarray, q: float=0.95) -> float:
        """
        稳健加权分位数（基于加权秩次插值）
        - 不依赖任何外部参数
        - 自动抑制单一极端值对分位数的污染
        """
        if len( values ) == 0 or np.sum( weights ) == 0:
            return float( np.quantile( values, q ) ) if len( values ) > 0 else 0.0

        # 按值排序
        sorted_idx = np.argsort( values )
        sorted_w = weights[sorted_idx]
        cum_w = np.cumsum( sorted_w )
        total_w = cum_w[-1]

        # 计算每个样本的加权百分位排名（中点规则）
        rank_pct = (cum_w - 0.5 * sorted_w) / total_w

        # 线性插值求目标分位
        if q <= rank_pct[0]:
            return float( values[sorted_idx[0]] )
        if q >= rank_pct[-1]:
            return float( values[sorted_idx[-1]] )

        idx = np.searchsorted( rank_pct, q )
        x0, x1 = rank_pct[idx - 1], rank_pct[idx]
        y0, y1 = values[sorted_idx[idx - 1]], values[sorted_idx[idx]]
        t = (q - x0) / (x1 - x0)
        return float( y0 + t * (y1 - y0) )


    @staticmethod
    def weighted_expected_shortfall(values, weights, q=0.05):
        # 转换为 numpy 数组并扁平化
        values = np.asarray( values ).ravel()
        weights = np.asarray( weights ).ravel()

        if len( values ) == 0:
            return 0.0
        if len( values ) != len( weights ):
            raise ValueError( "values and weights must have the same length" )
        total_weight = np.sum( weights )
        if total_weight == 0:
            return float( np.mean( values ) )

        # 按值排序
        sorted_idx = np.argsort( values )
        sorted_values = values[sorted_idx]
        sorted_weights = weights[sorted_idx]

        cum_weights = np.cumsum( sorted_weights )
        target_weight = q * total_weight

        # 查找分位点索引，确保返回整数
        var_idx = int( np.searchsorted( cum_weights, target_weight ) )
        var_idx = min( var_idx, len( sorted_values ) - 1 )
        var_value = sorted_values[var_idx]

        # 计算尾部平均
        tail_mask = values <= var_value
        if not np.any( tail_mask ):
            return float( var_value )

        tail_values = values[tail_mask]
        tail_weights = weights[tail_mask]
        expected_shortfall = np.average( tail_values, weights=tail_weights )

        return float( expected_shortfall )


    @staticmethod
    def trimmed_weighted_mean(values: np.ndarray, weights: np.ndarray, trim_ratio: float = 0.1) -> float:
        """计算截尾加权平均（剔除两端 trim_ratio 比例的权重）"""
        if len( values ) == 0 or np.sum( weights ) == 0:
            return float( np.mean( values ) ) if len( values ) > 0 else 0.0
        sorted_idx = np.argsort( values )
        sorted_w = weights[sorted_idx]
        cum_w = np.cumsum( sorted_w ) / np.sum( sorted_w )
        start = np.searchsorted( cum_w, trim_ratio )
        end = np.searchsorted( cum_w, 1.0 - trim_ratio )
        trimmed_values = values[sorted_idx][start:end]
        trimmed_weights = sorted_w[start:end]
        if len( trimmed_values ) == 0:
            return float( np.median( values ) )
        return float( np.average( trimmed_values, weights=trimmed_weights ) )


    def _count_labels(self, labels: List[str]) -> Dict[str, int]:
        """
        统计标签分布
        
        Args:
            labels: 标签列表
            
        Returns:
            Dict: 标签计数
        """
        from collections import Counter
        counter = Counter(labels)
        return dict(counter)
    
    def _empty_prediction(self) -> Dict[str, Any]:
        """
        返回空预测结果
        
        Returns:
            Dict: 空预测
        """
        return {
            'avg_ret_1d': None,
            'avg_ret_5d': None,
            'up_probability': None,
            'label_distribution': {},
            'sample_size': 0,
            'weighted': False,
            'std_ret_1d': None,
            'sharpe_ratio': None
        }

    @staticmethod
    def compute_robust_stats(returns_5d, weights,
                             q_down=0.10, q_up=0.90,
                             winsorize=False,
                             use_interp=True):
        """
        计算稳健加权统计量：均值、中位数、下行分位数、上行分位数

        Args:
            returns_5d: 5日收益数组
            weights: 权重数组
            q_down: 下行分位点（默认 0.10）
            q_up:   上行分位点（默认 0.90）
            winsorize: 是否对收益进行缩尾裁剪（默认 False，保留极端值）
            use_interp: 分位数是否使用线性插值（默认 True，推荐）

        Returns:
            (mean, median, var_down, upside_up)
        """
        # 类型转换
        returns = np.asarray( returns_5d, dtype=float )
        w = np.asarray( weights, dtype=float )

        if len( returns ) == 0 or np.sum( w ) == 0:
            return 0.0, 0.0, 0.0, 0.0

        # 可选缩尾
        if winsorize:
            sorted_idx = np.argsort( returns )
            sorted_w = w[sorted_idx]
            cum_w = np.cumsum( sorted_w )
            total_w = cum_w[-1]
            q1 = returns[sorted_idx[np.searchsorted( cum_w, 0.25 * total_w )]]
            q3 = returns[sorted_idx[np.searchsorted( cum_w, 0.75 * total_w )]]
            iqr = q3 - q1
            if iqr == 0:
                iqr = np.abs( np.mean( returns ) ) * 0.1 if np.mean( returns ) != 0 else 1.0
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            returns = np.clip( returns, lower, upper )

        # ---------- 加权均值 ----------
        mean_val = np.average( returns, weights=w )

        # ---------- 加权分位数插值函数 ----------
        def wquantile(values, weights, q):
            if len( values ) == 0 or np.sum( weights ) == 0:
                return 0.0
            sorter = np.argsort( values )
            v_sorted = values[sorter]
            w_sorted = weights[sorter]
            cum_w = np.cumsum( w_sorted )
            total_w = cum_w[-1]
            target = q * total_w

            if not use_interp:
                # 直接取跨越点
                idx = np.searchsorted( cum_w, target )
                return float( v_sorted[min( idx, len( v_sorted ) - 1 )] )

            # 线性插值
            # 计算每个样本的累积概率（中点规则）
            p = (cum_w - 0.5 * w_sorted) / total_w
            if q <= p[0]:
                return float( v_sorted[0] )
            if q >= p[-1]:
                return float( v_sorted[-1] )
            idx = np.searchsorted( p, q )
            x0, x1 = p[idx - 1], p[idx]
            y0, y1 = v_sorted[idx - 1], v_sorted[idx]
            t = (q - x0) / (x1 - x0)
            return float( y0 + t * (y1 - y0) )

        # 计算所需统计量
        median = wquantile( returns, w, 0.50 )
        var_down = wquantile( returns, w, q_down )
        upside_up = wquantile( returns, w, q_up )

        return float( mean_val ), float( median ), float( var_down ), float( upside_up )

class RobustStats:
    """稳健加权统计工具箱，自动抑制极端值影响。"""

    @staticmethod
    def _weighted_quartiles(values: np.ndarray, weights: np.ndarray):
        """计算加权 Q1、Q3 和 IQR。"""
        if len(values) == 0 or np.sum(weights) == 0:
            return 0.0, 0.0, 0.0
        sorted_idx = np.argsort(values)
        sorted_w = weights[sorted_idx]
        cum_w = np.cumsum(sorted_w)
        total = cum_w[-1]
        q1_idx = np.searchsorted(cum_w, 0.25 * total)
        q3_idx = np.searchsorted(cum_w, 0.75 * total)
        q1 = float(values[sorted_idx[q1_idx]])
        q3 = float(values[sorted_idx[q3_idx]])
        iqr = q3 - q1
        return q1, q3, iqr

    @staticmethod
    def weighted_mean(values: np.ndarray, weights: np.ndarray,
                      winsorize: bool = True) -> float:
        """
        加权均值（可选自动缩尾）。
        当 winsorize=True 时，自动将超出 [Q1-1.5*IQR, Q3+1.5*IQR] 的值裁剪到边界。
        """
        if len(values) == 0 or np.sum(weights) == 0:
            return 0.0
        if not winsorize:
            return np.average(values, weights=weights)
        q1, q3, iqr = RobustStats._weighted_quartiles(values, weights)
        if iqr == 0:
            iqr = np.abs(np.mean(values)) * 0.1 if np.mean(values) != 0 else 1.0
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        clipped = np.clip(values, lower, upper)
        return np.average(clipped, weights=weights)

    @staticmethod
    def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float,
                          winsorize: bool = True) -> float:
        """
        加权分位数（可选自动缩尾）。
        """
        if len(values) == 0 or np.sum(weights) == 0:
            return float(np.quantile(values, q)) if len(values) > 0 else 0.0
        if not winsorize:
            sorted_idx = np.argsort(values)
            cum_w = np.cumsum(weights[sorted_idx])
            target = q * np.sum(weights)
            idx = np.searchsorted(cum_w, target)
            return float(values[sorted_idx[idx]])
        # 先缩尾再计算分位数
        q1, q3, iqr = RobustStats._weighted_quartiles(values, weights)
        if iqr == 0:
            iqr = np.abs(np.mean(values)) * 0.1 if np.mean(values) != 0 else 1.0
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        clipped = np.clip(values, lower, upper)
        sorted_idx = np.argsort(clipped)
        cum_w = np.cumsum(weights[sorted_idx])
        target = q * np.sum(weights)
        idx = np.searchsorted(cum_w, target)
        return float(clipped[sorted_idx[idx]])