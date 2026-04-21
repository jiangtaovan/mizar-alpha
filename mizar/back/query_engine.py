# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : query_engine.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00


from ..services import PredictionService
# from ..services.prediction_service import PredictionService
from ..vector_db import VectorStorage


class QueryEngine:
    """封装向量库查询和预测统计"""
    def __init__(self, config):
        self.vector_storage = VectorStorage(config)
        self.vector_storage.connect()
        self.vector_storage.create_collection()
        self.prediction_service = PredictionService(config)


    # query_engine.py 修改部分
    def query(self, query_vec, top_k, period, current_date_str):
        """查询相似状态，返回完整预测字典"""
        results = self.vector_storage.query(
            query_vector=query_vec,
            top_k=top_k,
            where_filter=None
        )
        if not results['ids']:
            return None

        similar_states = []
        for meta, dist in zip( results['metadatas'], results['distances'] ):
            similar_states.append( {
                'date': meta.get( 'date', '' ),
                'symbol': meta.get( 'symbol', '' ),
                'future_ret_1d': meta.get( 'future_ret_1d' ),
                'future_ret_5d': meta.get( 'future_ret_5d' ),
                'future_label': meta.get( 'future_label', '' ),
                'distance': dist,
            } )

        prediction = self.prediction_service.calculate_statistics( similar_states )
        return prediction  # 返回完整字典

# 返回值
#         prediction = {
#             'up_probability': float( weighted_up_prob ),  # 已改为加权概率
#             'avg_ret_1d': float( np.average( returns_1d, weights=weights ) ),
#             'avg_ret_5d': float( avg_ret_5d ),
#             'median_ret_5d': float( median_ret_5d ),
#             'var_5d': float( var_5d ),
#             'upside_5d': float( upside_5d ),
#             'confidence':confidence,
#             'label_distribution': self._count_labels( labels ),
#             'sample_size': len( returns_1d ),
#             'weighting_method': weighting_method,
#             'weighted': weighting_method != 'simple'
#         }