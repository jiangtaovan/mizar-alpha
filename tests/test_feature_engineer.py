"""
特征工程测试
"""

import pytest
import pandas as pd
import numpy as np

from features import FeatureEngineer


@pytest.fixture
def sample_config():
    """测试配置"""
    return {
        'features': {
            'config_path': './config/feature_config.yaml',
            'model_path': './tests/test_models'
        }
    }


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    n_samples = 100
    
    data = {
        'date': pd.date_range('2024-01-01', periods=n_samples),
        'symbol': ['000001.SH'] * n_samples,
        'MA_SMA_5': np.random.randn(n_samples) * 10 + 100,
        'MA_SMA_20': np.random.randn(n_samples) * 10 + 98,
        'RSI_RSI_12': np.random.randn(n_samples) * 10 + 50,
        'MACD_macd': np.random.randn(n_samples) * 2,
        'ATR_ATR': np.random.randn(n_samples) * 1 + 3,
        'VOLUME_RATIO': np.random.randn(n_samples) * 0.5 + 1.5,
        'future_ret_1d': np.random.randn(n_samples) * 2,
        'future_label': np.random.choice(['大涨', '小涨', '小跌', '大跌'], n_samples)
    }
    
    return pd.DataFrame(data)


class TestFeatureEngineer:
    """特征工程测试类"""
    
    def test_select_features(self, sample_config, sample_data):
        """测试特征选择"""
        engineer = FeatureEngineer(sample_config)
        
        df_selected = engineer.select_features(sample_data)
        
        # 验证选择了正确的特征
        assert 'MA_SMA_5' in df_selected.columns
        assert 'RSI_RSI_12' in df_selected.columns
        assert 'date' in df_selected.columns  # 元数据应该保留
        assert 'symbol' in df_selected.columns
    
    def test_fit_transform(self, sample_config, sample_data):
        """测试拟合并转换"""
        engineer = FeatureEngineer(sample_config)
        
        # 先选择特征
        df_selected = engineer.select_features(sample_data)
        
        # 拟合并转换
        vectors, metadata = engineer.fit_transform(df_selected)
        
        # 验证输出
        assert isinstance(vectors, np.ndarray)
        assert len(vectors) == len(sample_data)
        assert vectors.shape[1] < len(engineer.selected_features)  # PCA 降维后维度应该更小
        
        # 验证元数据保留
        assert 'date' in metadata.columns
        assert 'future_ret_1d' in metadata.columns
    
    def test_transform_new_data(self, sample_config, sample_data):
        """测试转换新数据"""
        engineer = FeatureEngineer(sample_config)
        
        # 拟合并保存模型
        df_selected = engineer.select_features(sample_data)
        engineer.fit_transform(df_selected)
        engineer.save_models(version="test")
        
        # 创建新数据
        new_data = sample_data.head(5).copy()
        
        # 加载模型并转换
        engineer.load_models(version="test")
        vectors, metadata = engineer.transform(new_data)
        
        assert len(vectors) == 5
        assert vectors.shape[1] == engineer.pca.n_components_
    
    def test_model_persistence(self, sample_config, sample_data):
        """测试模型持久化"""
        engineer = FeatureEngineer(sample_config)
        
        # 拟合并保存
        df_selected = engineer.select_features(sample_data)
        engineer.fit_transform(df_selected)
        engineer.save_models(version="test")
        
        # 创建新的实例并加载
        engineer2 = FeatureEngineer(sample_config)
        engineer2.load_models(version="test")
        
        # 验证加载的模型与原始模型一致
        assert engineer2.selected_features == engineer.selected_features
        assert engineer2.pca.n_components_ == engineer.pca.n_components_


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
