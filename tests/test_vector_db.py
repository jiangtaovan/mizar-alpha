"""
向量数据库测试
"""

import pytest
import numpy as np

from vector_db import VectorStorage


@pytest.fixture
def sample_config():
    """测试配置"""
    return {
        'vector_db': {
            'persist_directory': './tests/test_chroma',
            'collection_name': 'test_collection',
            'distance_metric': 'cosine',
            'batch_size': 10
        }
    }


class TestVectorStorage:
    """向量存储测试类"""
    
    def test_connect_and_create(self, sample_config):
        """测试连接和创建集合"""
        storage = VectorStorage(sample_config)
        
        # 连接
        storage.connect()
        assert storage.client is not None
        
        # 创建集合
        storage.create_collection()
        assert storage.collection is not None
    
    def test_add_vectors(self, sample_config):
        """测试添加向量"""
        storage = VectorStorage(sample_config)
        storage.connect()
        storage.create_collection()
        
        # 准备测试数据
        n_vectors = 20
        n_dimensions = 10
        
        vectors = np.random.randn(n_vectors, n_dimensions).astype(np.float32)
        metadatas = [{'label': f'label_{i}'} for i in range(n_vectors)]
        ids = [f'id_{i}' for i in range(n_vectors)]
        
        # 添加向量
        storage.add_vectors(vectors, metadatas, ids, batch_size=10)
        
        # 验证数量
        count = storage.get_count()
        assert count == n_vectors
    
    def test_query(self, sample_config):
        """测试查询"""
        storage = VectorStorage(sample_config)
        storage.connect()
        storage.create_collection()
        
        # 添加测试向量
        n_vectors = 20
        vectors = np.random.randn(n_vectors, 10).astype(np.float32)
        metadatas = [{'label': f'label_{i}', 'category': i % 3} for i in range(n_vectors)]
        ids = [f'id_{i}' for i in range(n_vectors)]
        
        storage.add_vectors(vectors, metadatas, ids)
        
        # 查询
        query_vector = vectors[0].reshape(1, -1)
        results = storage.query(query_vector, top_k=5)
        
        # 验证结果
        assert len(results['ids']) == 5
        assert len(results['distances']) == 5
        assert len(results['metadatas']) == 5
        
        # 第一个结果应该是查询向量本身（距离接近 0）
        assert results['ids'][0] == 'id_0'
        assert results['distances'][0] < 0.1
    
    def test_query_with_filter(self, sample_config):
        """测试带过滤的查询"""
        storage = VectorStorage(sample_config)
        storage.connect()
        storage.create_collection()
        
        # 添加带 category 的向量
        n_vectors = 30
        vectors = np.random.randn(n_vectors, 10).astype(np.float32)
        metadatas = [{'label': f'label_{i}', 'category': i % 3} for i in range(n_vectors)]
        ids = [f'id_{i}' for i in range(n_vectors)]
        
        storage.add_vectors(vectors, metadatas, ids)
        
        # 带过滤查询
        query_vector = vectors[0].reshape(1, -1)
        results = storage.query(
            query_vector,
            top_k=5,
            where_filter={'category': 0}
        )
        
        # 验证所有结果的 category 都是 0
        for meta in results['metadatas']:
            assert meta['category'] == 0
    
    def test_delete_by_ids(self, sample_config):
        """测试删除"""
        storage = VectorStorage(sample_config)
        storage.connect()
        storage.create_collection()
        
        # 添加向量
        n_vectors = 20
        vectors = np.random.randn(n_vectors, 10).astype(np.float32)
        metadatas = [{'label': f'label_{i}'} for i in range(n_vectors)]
        ids = [f'id_{i}' for i in range(n_vectors)]
        
        storage.add_vectors(vectors, metadatas, ids)
        
        # 删除部分向量
        delete_ids = ['id_0', 'id_1', 'id_2']
        storage.delete_by_ids(delete_ids)
        
        # 验证剩余数量
        count = storage.get_count()
        assert count == n_vectors - len(delete_ids)
    
    def teardown_method(self, method, sample_config):
        """测试后清理"""
        try:
            storage = VectorStorage(sample_config)
            storage.connect()
            storage.reset()
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
