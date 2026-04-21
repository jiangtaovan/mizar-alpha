"""
预测服务测试
"""

import pytest

from services import PredictionService


@pytest.fixture
def sample_config():
    """测试配置"""
    return {}


@pytest.fixture
def sample_similar_states():
    """生成相似状态测试数据"""
    return [
        {
            'date': '2024-01-01',
            'symbol': '000001.SH',
            'future_ret_1d': 1.5,
            'future_label': '小涨',
            'distance': 0.1
        },
        {
            'date': '2024-01-02',
            'symbol': '000001.SH',
            'future_ret_1d': 2.5,
            'future_label': '大涨',
            'distance': 0.2
        },
        {
            'date': '2024-01-03',
            'symbol': '000001.SH',
            'future_ret_1d': -1.0,
            'future_label': '小跌',
            'distance': 0.3
        },
        {
            'date': '2024-01-04',
            'symbol': '000001.SH',
            'future_ret_1d': -3.0,
            'future_label': '大跌',
            'distance': 0.4
        },
        {
            'date': '2024-01-05',
            'symbol': '000001.SH',
            'future_ret_1d': 0.5,
            'future_label': '小涨',
            'distance': 0.5
        }
    ]


class TestPredictionService:
    """预测服务测试类"""
    
    def test_calculate_statistics_simple(self, sample_config, sample_similar_states):
        """测试基础统计计算"""
        service = PredictionService(sample_config)
        
        prediction = service.calculate_statistics(
            similar_states=sample_similar_states,
            weighting_method='simple'
        )
        
        # 验证基本字段
        assert 'avg_ret_1d' in prediction
        assert 'up_probability' in prediction
        assert 'label_distribution' in prediction
        
        # 验证上涨概率（3 个上涨 / 5 个总样本）
        assert prediction['up_probability'] == 0.6
        
        # 验证标签分布
        assert prediction['label_distribution']['小涨'] == 2
        assert prediction['label_distribution']['大涨'] == 1
        assert prediction['label_distribution']['小跌'] == 1
        assert prediction['label_distribution']['大跌'] == 1
    
    def test_distance_weighting(self, sample_config, sample_similar_states):
        """测试距离加权"""
        service = PredictionService(sample_config)
        
        prediction = service.calculate_statistics(
            similar_states=sample_similar_states,
            weighting_method='distance'
        )
        
        # 距离加权应该更接近距离小的样本
        # 第一个样本距离最小 (0.1)，收益率 1.5
        # 加权平均应该接近 1.5
        assert prediction['avg_ret_1d'] > 0  # 应该是正的
        assert prediction['weighted'] is True
    
    def test_empty_states(self, sample_config):
        """测试空状态"""
        service = PredictionService(sample_config)
        
        prediction = service.calculate_statistics(
            similar_states=[],
            weighting_method='simple'
        )
        
        # 验证返回空预测
        assert prediction['sample_size'] == 0
        assert prediction['avg_ret_1d'] is None
        assert prediction['up_probability'] is None
    
    def test_label_distribution(self, sample_config, sample_similar_states):
        """测试标签分布统计"""
        service = PredictionService(sample_config)
        
        prediction = service.calculate_statistics(
            similar_states=sample_similar_states,
            weighting_method='simple'
        )
        
        # 验证分布总和等于样本数
        total = sum(prediction['label_distribution'].values())
        assert total == len(sample_similar_states)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
