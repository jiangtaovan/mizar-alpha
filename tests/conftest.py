"""
测试配置
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试配置
TEST_CONFIG = {
    'data': {
        'date_column': 'date',
        'symbol_column': 'symbol',
        'close_column': 'current_price'
    },
    'features': {
        'config_path': './config/feature_config.yaml',
        'model_path': './tests/test_models'
    },
    'vector_db': {
        'persist_directory': './tests/test_chroma',
        'collection_name': 'test_collection',
        'distance_metric': 'cosine',
        'batch_size': 10
    }
}


def pytest_configure(config):
    """pytest 配置钩子"""
    config.TEST_CONFIG = TEST_CONFIG
