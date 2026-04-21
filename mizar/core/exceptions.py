# -*- coding: utf-8 -*-
# @Time    : 2026/4/16 
# @File    : exceptions.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00

"""
Mizar 统一异常体系
所有自定义异常继承自 MizarError，便于上层统一捕获。
"""
from typing import Optional, Dict, Any


class MizarError(Exception):
    """所有 Mizar 异常的基类"""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            message: 人类可读的错误描述
            code: 错误码（如 "DATA_001"），便于 API 映射
            details: 额外上下文（如缺失的列名、文件路径）
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 API 返回 JSON"""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


# ==================== 配置异常 ====================
class ConfigurationError(MizarError):
    """配置加载或解析失败"""
    pass


# ==================== 数据异常 ====================
class DataError(MizarError):
    """数据相关异常的基类"""
    pass


class DataLoadError(DataError):
    """数据加载失败（文件不存在、格式不支持等）"""
    pass


class DataValidationError(DataError):
    """数据验证失败（缺少必需列、数据类型错误）"""
    pass


class LabelCalculationError(DataError):
    """未来标签计算失败"""
    pass


# ==================== 特征工程异常 ====================
class FeatureError(MizarError):
    """特征工程相关异常基类"""
    pass


class FeatureNotFoundError(FeatureError):
    """请求的特征在数据中不存在"""
    pass


class FeatureTransformError(FeatureError):
    """归一化或 PCA 转换失败"""
    pass


class ModelNotFittedError(FeatureError):
    """尝试 transform 但尚未调用 fit"""
    pass


# ==================== 向量数据库异常 ====================
class VectorDBError(MizarError):
    """向量数据库操作异常基类"""
    pass


class VectorDBConnectionError(VectorDBError):
    """连接向量数据库失败"""
    pass


class CollectionNotFoundError(VectorDBError):
    """集合不存在"""
    pass


class VectorInsertError(VectorDBError):
    """插入向量失败"""
    pass


# ==================== 预测异常 ====================
class PredictionError(MizarError):
    """预测计算相关异常"""
    pass


class InvalidWeightingMethodError(PredictionError):
    """不支持的加权方法"""
    pass


# ==================== 流水线异常 ====================
class PipelineError(MizarError):
    """流水线执行异常基类"""
    pass


class BuildError(PipelineError):
    """全量构建失败"""
    pass


class UpdateError(PipelineError):
    """增量更新失败"""
    pass


# ==================== 版本管理异常 ====================
class VersionError(MizarError):
    """版本管理异常基类"""
    pass


class VersionNotFoundError(VersionError):
    """请求的版本不存在"""
    pass


class VersionConflictError(VersionError):
    """版本冲突（如覆盖已有版本时未指定 force）"""
    pass


class ModelLoadError(VersionError):
    """模型文件加载失败（文件损坏、格式错误）"""
    pass


# ==================== 外部依赖异常 ====================
class ExternalDependencyError(MizarError):
    """缺少必需的外部依赖（如 TA-Lib）"""
    pass