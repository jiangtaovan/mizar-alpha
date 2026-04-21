"""
向量数据库存储模块
使用 ChromaDB 作为向量存储引擎
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger
import numpy as np


class VectorStorage:
    """向量数据库存储管理器"""
    
    def __init__(self, config: dict):
        """
        初始化向量存储
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.persist_directory = Path(config.get('vector_db', {}).get(
            'persist_directory', './datas/chroma_db'
        ))
        self.collection_name = config.get('vector_db', {}).get(
            'collection_name', 'market_state_vectors'
        )
        
        # 确保目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # 初始化 ChromaDB 客户端
        self.client = None
        self.collection = None
        
    def connect(self):
        """连接到向量数据库"""
        logger.info(f"正在连接 ChromaDB，路径：{self.persist_directory}")
        
        # 创建持久化客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        logger.info("ChromaDB 连接成功")
    
    def create_collection(self, metadata: Optional[Dict] = None):
        """
        创建集合
        
        Args:
            metadata: 集合元数据
        """
        if self.client is None:
            raise RuntimeError("请先调用 connect()")
        
        # 获取或创建集合
        # ChromaDB 会自动创建不存在的集合
        distance_metric = self.config.get('vector_db', {}).get(
            'distance_metric', 'cosine'
        )
        
        # 映射距离度量到 ChromaDB 空间
        space_map = {
            'cosine': 'cosine',
            'euclidean': 'l2',
            'ip': 'ip'
        }
        space = space_map.get(distance_metric, 'cosine')
        
        try:
            # 尝试获取现有集合
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            logger.info(f"使用已存在的集合：{self.collection_name}")
        except Exception:
            # 集合不存在，创建新的
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": space}
            )
            logger.info(f"创建新集合：{self.collection_name}, 距离度量：{space}")
    
    def add_vectors(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]], 
                   ids: List[str], batch_size: int = 100):
        """
        批量添加向量
        
        Args:
            vectors: 向量数组 (n_samples, n_dimensions)
            metadatas: 元数据列表
            ids: ID 列表
            batch_size: 批量大小
        """
        if self.collection is None:
            raise RuntimeError("集合未初始化")
        
        if len(vectors) != len(metadatas) or len(vectors) != len(ids):
            raise ValueError("vectors, metadatas, ids 长度必须一致")
        
        logger.info(f"正在添加 {len(vectors)} 个向量...")
        
        # 转换为列表格式
        vectors_list = vectors.tolist()
        
        # 分批插入
        n_batches = len(vectors) // batch_size + 1
        
        for i in range(n_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(vectors))
            
            batch_vectors = vectors_list[start_idx:end_idx]
            batch_metadatas = metadatas[start_idx:end_idx]
            batch_ids = ids[start_idx:end_idx]
            
            # 过滤掉 None 值的 metadata
            valid_data = []
            for vec, meta, id_ in zip(batch_vectors, batch_metadatas, batch_ids):
                # 确保 metadata 中的值都是 JSON 可序列化的，且不为 None
                clean_meta = {}
                for k, v in meta.items():
                    # 跳过 None 值
                    if v is None:
                        continue
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif isinstance(v, (np.integer, np.floating)):
                        clean_meta[k] = float(v) if isinstance(v, np.floating) else int(v)
                    else:
                        clean_meta[k] = str(v)  # 其他类型转为字符串
                
                # 跳过包含 NaN 的向量
                if not any(np.isnan(x) for x in vec):
                    valid_data.append((vec, clean_meta, id_))
            
            if valid_data:
                vecs, metas, ids_ = zip(*valid_data)
                
                self.collection.add(
                    embeddings=list(vecs),
                    metadatas=list(metas),
                    ids=list(ids_)
                )
            
            if (i + 1) % 10 == 0:
                logger.info(f"已添加 {min(end_idx, len(valid_data))} / {len(vectors)} 个向量")
        
        logger.info(f"向量添加完成，总计 {len(vectors)} 条")
    
    def query(self, query_vector: np.ndarray, top_k: int = 10, 
             where_filter: Optional[Dict] = None) -> Dict[str, Any]:
        """
        查询相似向量
        
        Args:
            query_vector: 查询向量 (1, n_dimensions) 或 (n_dimensions,)
            top_k: 返回数量
            where_filter: 过滤条件（如 {"volatility_level": "high"}）
            
        Returns:
            Dict: 查询结果，包含 ids, distances, metadatas
        """
        if self.collection is None:
            raise RuntimeError("集合未初始化")
        
        # 确保是 2D 数组
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        query_vec_list = query_vector.tolist()
        
        # 构建查询条件
        kwargs = {
            'query_embeddings': query_vec_list,
            'n_results': top_k,
            'include': ['metadatas', 'distances']
        }
        
        if where_filter:
            kwargs['where'] = where_filter
        
        results = self.collection.query(**kwargs)
        
        # 格式化结果
        formatted_results = {
            'ids': results['ids'][0],
            'distances': results['distances'][0],
            'metadatas': results['metadatas'][0]
        }
        
        return formatted_results
    
    def delete_by_ids(self, ids: List[str]):
        """
        根据 ID 删除向量
        
        Args:
            ids: 要删除的 ID 列表
        """
        if self.collection is None:
            raise RuntimeError("集合未初始化")
        
        logger.info(f"正在删除 {len(ids)} 个向量...")
        self.collection.delete(ids=ids)
        logger.info("删除完成")
    
    def get_count(self) -> int:
        """
        获取集合中向量数量
        
        Returns:
            int: 向量数量
        """
        if self.collection is None:
            raise RuntimeError("集合未初始化")
        
        return self.collection.count()
    
    def reset(self):
        """重置数据库（删除所有数据）"""
        logger.warning("正在重置向量数据库...")
        
        if self.client:
            try:
                self.client.delete_collection(self.collection_name)
                logger.info("已删除所有数据")
            except Exception as e:
                logger.error(f"删除失败：{e}")
    
    def close(self):
        """关闭连接"""
        logger.info("关闭 ChromaDB 连接")
        # ChromaDB PersistentClient 不需要显式关闭
        self.client = None
        self.collection = None
