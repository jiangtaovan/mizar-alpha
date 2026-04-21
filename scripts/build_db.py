#!/usr/bin/env python3
"""
全量构建向量数据库脚本
初始版本 10*300D日K数据，校验到比较好的效果，建议已这个量为基准 ，适当增加
    建议覆盖不同种类（如：行业、大中小盘 等），且有涨跌周期明显的股票。
 v2 33*300d数据
 v2.1 52*500d
用法:
    python scripts/build_db.py [--config CONFIG_PATH]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from loguru import logger

from data import DataLoader
from features import FeatureEngineer
from utils import setup_logging, load_config
from vector_db import VectorStorage

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent  # mizar 目录
sys.path.insert(0, str(project_root))


def build_database(config: dict):
    """
    构建向量数据库
    
    Args:
        config: 配置字典
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("开始构建向量数据库")
    logger.info("=" * 60)

    import os
    print( "当前工作目录:", os.getcwd() )
    
    try:
        # 1. 加载数据
        logger.info("步骤 1/4: 加载数据...")
        data_loader = DataLoader(config)
        
        # 从配置获取数据路径
        data_path = config.get('data', {}).get('data_path', './datas/raw/*.csv')
        df = data_loader.load_multiple_files(data_path)
        print( "数据模式:", data_path )
        print( "匹配的文件:", list( Path( '.' ).glob( data_path ) ) )
        
        # 计算未来标签
        df = data_loader.calculate_future_labels(df)
        logger.info(f"数据加载完成，共 {len(df)} 条记录")
        
        # 2. 特征工程
        logger.info("步骤 2/4: 特征工程...")
        feature_engineer = FeatureEngineer(config)
        
        # 选择特征
        df_selected = feature_engineer.select_features(df)
        
        # 拟合并转换
        vectors, metadata = feature_engineer.fit_transform(df_selected)
        
        # 保存模型
        feature_engineer.save_models(version="v1")
        logger.info(f"特征工程完成，向量维度：{vectors.shape[1]}")

        # 步骤 3: 构建向量数据库
        logger.info( "步骤 3/4: 构建向量数据库..." )
        vector_storage = VectorStorage( config )
        vector_storage.connect()

        # 重置数据库（删除现有集合，确保使用新维度）
        vector_storage.reset()

        # 创建新集合
        vector_storage.create_collection()
        logger.info( "集合已创建" )
        
        # # 连接并创建集合
        # vector_storage.connect()
        # vector_storage.create_collection()
        
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
        
        # 批量插入向量
        batch_size = config.get('vector_db', {}).get('batch_size', 100)
        vector_storage.add_vectors(
            vectors=vectors,
            metadatas=metadatas,
            ids=doc_ids,
            batch_size=batch_size
        )
        
        # 验证
        record_count = vector_storage.get_count()
        logger.info(f"向量数据库构建完成，总计 {record_count} 条记录")
        
        # 4. 完成
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"✓ 构建成功！耗时：{duration:.2f} 秒")
        logger.info(f"✓ 记录数：{record_count}")
        logger.info(f"✓ 向量维度：{vectors.shape[1]}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"构建失败：{e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='构建市场状态向量数据库')
    parser.add_argument('--config', type=str, default='./config/system_config.yaml',
                       help='配置文件路径')
    
    args = parser.parse_args()
    
    # 加载配置

    config = load_config()
    setup_logging(config)
    
    # 执行构建
    success = build_database(config)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
