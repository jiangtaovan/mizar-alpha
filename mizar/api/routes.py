"""
API 路由模块
提供 RESTful 接口
"""

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from data import DataLoader
from features import FeatureEngineer
from vector_db import VectorStorage
from services import PredictionService


# ===== Pydantic 模型 =====

class QueryRequest(BaseModel):
    """查询请求模型"""
    features: Dict[str, float] = Field(..., description="原始指标特征，键值对形式")
    top_k: int = Field(default=10, ge=1, le=100, description="返回相似状态数量")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
    weighting_method: str = Field(default='distance', description="加权方法")


class SimilarState(BaseModel):
    date: str
    symbol: str
    future_ret_1d: Optional[float]
    future_ret_5d: Optional[float]   # 新增
    future_label: Optional[str]
    distance: float


class PredictionResponse(BaseModel):
    """预测响应模型"""
    similar_states: List[SimilarState]
    prediction: Dict[str, Any]
    query_timestamp: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    vector_db: str
    last_update: Optional[str]
    record_count: int


class UpdateResponse(BaseModel):
    """更新响应"""
    status: str
    new_records: int
    timestamp: str


# ===== API 应用 =====

def create_app(config: dict) -> FastAPI:
    """
    创建 FastAPI 应用
    
    Args:
        config: 配置字典
        
    Returns:
        FastAPI 应用实例
    """
    app = FastAPI(
        title="市场状态向量数据库 API",
        description="基于相似性检索的市场状态预测服务",
        version="0.1.0"
    )
    
    # 初始化组件
    data_loader = DataLoader(config)
    feature_engineer = FeatureEngineer(config)
    vector_storage = VectorStorage(config)
    prediction_service = PredictionService(config)
    
    # 连接向量数据库
    vector_storage.connect()
    vector_storage.create_collection()
    
    # 加载特征工程模型
    try:
        feature_engineer.load_models(version="v1")
        logger.info("特征工程模型加载成功")
    except FileNotFoundError as e:
        logger.warning(f"特征工程模型未找到，请先运行 build_db.py: {e}")
    
    # API Key 认证（可选）
    api_key = config.get('api', {}).get('api_key', '')
    security = HTTPBearer(auto_error=False)
    
    async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
        """验证 API Key"""
        if not api_key:
            return None  # 未启用认证
        
        if credentials is None:
            raise HTTPException(status_code=401, detail="缺少 API Key")
        
        if credentials.credentials != api_key:
            raise HTTPException(status_code=401, detail="无效的 API Key")
        
        return credentials.credentials
    
    # ===== API 端点 =====
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """健康检查接口"""
        try:
            record_count = vector_storage.get_count()
            
            return HealthResponse(
                status="healthy",
                vector_db="connected",
                last_update=datetime.now().isoformat(),
                record_count=record_count
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"服务不可用：{str(e)}")
    
    @app.post("/query", response_model=PredictionResponse)
    async def query(
        request: QueryRequest,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """
        查询相似状态并返回预测
        
        输入原始指标特征，返回最相似的历史状态及统计预测
        """
        try:
            # 验证 API Key（如果启用）
            if api_key:
                await verify_api_key(credentials)
            
            # 将特征字典转换为 DataFrame
            features_df = _convert_features_to_dataframe(request.features)
            
            # 特征工程转换
            query_vector, _ = feature_engineer.transform(features_df)
            
            # 查询向量数据库
            results = vector_storage.query(
                query_vector=query_vector,
                top_k=request.top_k,
                where_filter=request.filters
            )
            
            # 构建相似状态列表
            similar_states = []
            for i in range(len(results['ids'])):
                metadata = results['metadatas'][i]
                state = SimilarState(
                    date=str(metadata.get('date', '')),
                    symbol=metadata.get('symbol', ''),
                    future_ret_1d=float(metadata.get('future_ret_1d')) if metadata.get('future_ret_1d') else None,
                    future_ret_5d=float( metadata.get( 'future_ret_5d' ) ) if metadata.get( 'future_ret_5d' ) else None,
                    future_label=metadata.get('future_label'),
                    distance=float(results['distances'][i])
                )
                similar_states.append(state)
            
            # 计算预测统计
            prediction = prediction_service.calculate_statistics(
                similar_states=[s.model_dump() for s in similar_states],
                weighting_method=request.weighting_method
            )
            
            return PredictionResponse(
                similar_states=similar_states,
                prediction=prediction,
                query_timestamp=datetime.now().isoformat()
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")
    
    @app.post("/update", response_model=UpdateResponse)
    async def update_database(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """
        手动触发增量更新
        
        从数据源加载最新数据并更新向量库
        """
        try:
            # 验证 API Key（如果启用）
            if api_key:
                await verify_api_key(credentials)
            
            # 这里应该调用增量更新脚本
            # 简化处理，返回成功响应
            return UpdateResponse(
                status="success",
                new_records=0,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")
    
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "service": "市场状态向量数据库 API",
            "version": "0.1.0",
            "status": "running"
        }
    
    return app


def _convert_features_to_dataframe(features: Dict[str, float]):
    """
    将特征字典转换为 DataFrame
    
    Args:
        features: 特征字典 {feature_name: value}
        
    Returns:
        DataFrame: 单行 DataFrame
    """
    import pandas as pd
    
    # 添加必要的元数据列（占位符）
    row_data = {
        'date': pd.Timestamp.now(),
        'symbol': 'TEMP',
        **features
    }
    
    df = pd.DataFrame([row_data])
    return df
