"""
服务模块入口
pre_service 增加 temporal_decay: 时间衰减因子 (float)
prediction 多周期【1-3-5】信号，符合权重调优模块


"""
# from .prediction_service import PredictionService
# from .pre_service import PredictionService as Service_pro
# from .prediction import PredictionService as Service_plus

from .predict_service import PredictionService
__all__ = ['PredictionService']
