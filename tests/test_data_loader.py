"""
数据加载器测试
"""
import sys

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import json
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from data import DataLoader


@pytest.fixture
def sample_config():
    """测试配置"""
    return {
        'data': {
            'date_column': 'date',
            'symbol_column': 'symbol',
            'close_column': 'current_price'
        }
    }


@pytest.fixture
def sample_csv_data():
    """生成测试 CSV 数据"""
    data = {
        'date': pd.date_range('2024-01-01', periods=10),
        'symbol': ['000001.SH'] * 10,
        'current_price': [10.0 + i * 0.5 for i in range(10)],
        'MA_SMA_5': [9.5 + i * 0.4 for i in range(10)],
        'RSI_RSI_12': [50 + np.random.randn() * 5 for _ in range(10)]
    }
    return pd.DataFrame(data)


class TestDataLoader:
    """数据加载器测试类"""
    
    def test_load_csv(self, sample_config, sample_csv_data):
        """测试 CSV 加载"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_csv_data.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            loader = DataLoader(sample_config)
            df = loader.load_csv(temp_path)
            
            assert len(df) == 10
            assert 'date' in df.columns
            assert 'symbol' in df.columns
            assert df['symbol'].iloc[0] == '000001.SH'
        finally:
            # 清理临时文件
            Path(temp_path).unlink()
    
    def test_load_json(self, sample_config, sample_csv_data):
        """测试 JSON 加载"""
        # 创建临时 JSON 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_data = sample_csv_data.to_dict(orient='records')
            json.dump(json_data, f)
            temp_path = f.name
        
        try:
            loader = DataLoader(sample_config)
            df = loader.load_json(temp_path)
            
            assert len(df) == 10
            assert 'date' in df.columns
        finally:
            Path(temp_path).unlink()
    
    def test_calculate_future_labels(self, sample_config, sample_csv_data):
        """测试未来标签计算"""
        loader = DataLoader(sample_config)
        
        # 添加更多数据以便计算未来标签
        extended_data = pd.concat([sample_csv_data] * 3, ignore_index=True)
        
        df_with_labels = loader.calculate_future_labels(extended_data)
        
        assert 'future_ret_1d' in df_with_labels.columns
        assert 'future_label' in df_with_labels.columns
        assert len(df_with_labels) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
