#!/usr/bin/env python3
"""
增量更新向量数据库脚本

用法:
    python scripts/update_db.py [--config CONFIG_PATH]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data import DataLoader
from features import FeatureEngineer
from vector_db import VectorStorage
from loguru import logger


def update_database(config: dict):
    """
    增量更新向量数据库
    
    Args:
        config: 配置字典
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("开始增量更新向量数据库")
    logger.info("=" * 60)
    
    try:
        # 1. 加载已有模型
        logger.info("步骤 1/5: 加载已有模型...")
        feature_engineer = FeatureEngineer(config)
        
        try:
            feature_engineer.load_models(version="v1")
            logger.info("模型加载成功")
        except FileNotFoundError:
            logger.error("未找到已训练的模型，请先运行全量构建脚本 build_db.py")
            return False
        
        # 2. 连接向量数据库
        logger.info("步骤 2/5: 连接向量数据库...")
        vector_storage = VectorStorage(config)
        vector_storage.connect()
        
        if vector_storage.get_count() == 0:
            logger.error("向量库为空，请先运行全量构建脚本 build_db.py")
            return False
        
        # 3. 加载最新数据
        logger.info("步骤 3/5: 加载最新数据...")
        data_loader = DataLoader(config)
        
        # 从配置获取数据路径
        data_path = config.get('data', {}).get('data_path', './datas/update/*.csv')
        df = data_loader.load_multiple_files(data_path)
        
        # 计算未来标签
        df = data_loader.calculate_future_labels(df)
        
        # 获取最后更新日期
        last_date = pd.to_datetime(df['date']).max()
        logger.info(f"最新数据日期：{last_date}")
        
        # 4. 特征工程转换
        logger.info("步骤 4/5: 特征工程转换...")
        df_selected = feature_engineer.select_features(df)
        vectors, metadata = feature_engineer.transform(df_selected)
        
        # 生成文档 ID
        dates = metadata['date'].astype(str).values
        symbols = metadata['symbol'].values
        doc_ids = [f"{date}_{symbol}" for date, symbol in zip(dates, symbols)]
        
        # 准备元数据
        metadatas = []
        for idx, row in metadata.iterrows():
            meta = {
                'date': str(row.get('date', '')),
                'symbol': row.get('symbol', ''),
                'future_ret_1d': float(row.get('future_ret_1d')) if pd.notna(row.get('future_ret_1d')) else None,
                'future_ret_5d': float(row.get('future_ret_5d')) if pd.notna(row.get('future_ret_5d')) else None,
                'future_max_dd_5d': float(row.get('future_max_dd_5d')) if pd.notna(row.get('future_max_dd_5d')) else None,
                'future_label': row.get('future_label', '')
            }
            metadatas.append(meta)
        
        # 5. 更新向量数据库
        logger.info("步骤 5/5: 更新向量数据库...")
        
        # 检查是否已存在（简化处理：先删除再插入）
        existing_count = vector_storage.get_count()
        
        # 批量插入
        batch_size = config.get('vector_db', {}).get('batch_size', 100)
        vector_storage.add_vectors(
            vectors=vectors,
            metadatas=metadatas,
            ids=doc_ids,
            batch_size=batch_size
        )
        
        new_count = vector_storage.get_count()
        new_records = new_count - existing_count
        
        # 完成
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"✓ 更新成功！耗时：{duration:.2f} 秒")
        logger.info(f"✓ 新增记录：{new_records}")
        logger.info(f"✓ 总记录数：{new_count}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"更新失败：{e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='增量更新市场状态向量数据库')
    parser.add_argument('--config', type=str, default='./config/system_config.yaml',
                       help='配置文件路径')
    
    args = parser.parse_args()
    
    # 加载配置
    from utils import load_config, setup_logging
    config = load_config()
    setup_logging(config)
    
    # 执行更新
    success = update_database(config)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
