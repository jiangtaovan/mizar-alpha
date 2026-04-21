"""
特征工程模块
负责特征选择、归一化、降维
    备注： 当前设计不设置多版本训练留存；理论上可以自行设计不同版本管理，用于针对性训练和使用，如需要自行增加版本管理
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Tuple
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.decomposition import PCA
from loguru import logger


class FeatureEngineer:
    """特征工程处理器"""
    
    def __init__(self, config: dict):
        """
        初始化特征工程
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.feature_config = self._load_feature_config()
        self.model_path = Path(config.get('features', {}).get('model_path', './models'))
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # 模型实例（延迟初始化）
        self.scaler = None
        self.pca = None
        self.selected_features = None
        
    def _load_feature_config(self) -> dict:
        """加载特征配置文件"""
        import yaml
        config_path = Path(self.config.get('features', {}).get(
            'config_path', './config/feature_config.yaml'
        ))
        
        if not config_path.exists():
            raise FileNotFoundError(f"特征配置文件不存在：{config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def select_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        选择特征子集
        
        Args:
            df: 原始数据（包含所有指标）
            
        Returns:
            DataFrame: 只包含选定特征的数据
        """
        logger.info("正在选择特征...")
        
        # 从配置获取特征列表
        feature_list = self.feature_config.get('features', [])
        
        if not feature_list:
            raise ValueError("特征列表为空")
        
        # 检查哪些特征存在于数据中
        available_features = []
        missing_features = []
        
        for feature in feature_list:
            if feature in df.columns:
                available_features.append(feature)
            else:
                missing_features.append(feature)
        
        if missing_features:
            logger.warning(f"以下特征不存在，已跳过：{missing_features}")
        
        if not available_features:
            raise ValueError("没有找到任何可用的特征")
        
        # 添加元数据列（不用于向量化，但需要保留）
        metadata_columns = ['date', 'symbol', 'future_ret_1d', 'future_ret_5d', 
                           'future_max_dd_5d', 'future_label']
        existing_metadata = [col for col in metadata_columns if col in df.columns]
        
        # 选择特征 + 元数据
        selected_columns = available_features + existing_metadata
        df_selected = df[selected_columns].copy()
        
        self.selected_features = available_features
        
        logger.info(f"已选择 {len(available_features)} 个特征")
        logger.debug(f"特征列表：{available_features}")
        
        return df_selected
    
    def fit_transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        拟合并转换特征
        
        Args:
            df: 包含选定特征的数据
            
        Returns:
            Tuple: (转换后的向量数组，保留元数据的 DataFrame)
        """
        logger.info("正在执行特征工程...")
        
        if self.selected_features is None:
            raise ValueError("请先调用 select_features()")
        
        # 提取特征数据
        X = df[self.selected_features].values.astype(np.float32)
        
        # 处理缺失值和无穷值
        X = self._clean_features(X)
        
        # 归一化
        normalization_method = self.feature_config.get('normalization', 'minmax')
        X_normalized = self._normalize(X, method=normalization_method)
        
        # PCA 降维
        pca_config = self.feature_config.get('pca', {})
        n_components = pca_config.get('n_components', 0.95)
        whiten = pca_config.get('whiten', False)
        
        X_reduced = self._reduce_dimension(X_normalized, n_components=n_components, whiten=whiten)
        
        # 保留元数据
        metadata_cols = ['date', 'symbol', 'future_ret_1d', 'future_ret_5d', 
                        'future_max_dd_5d', 'future_label']
        existing_metadata = [col for col in metadata_cols if col in df.columns]
        df_metadata = df[existing_metadata].copy()
        
        logger.info(f"特征工程完成：原始维度 {X.shape[1]} -> 降维后 {X_reduced.shape[1]}")
        
        return X_reduced, df_metadata
    
    def transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        转换新数据（使用已拟合的模型）
        
        Args:
            df: 新数据
            
        Returns:
            Tuple: (转换后的向量数组，元数据 DataFrame)
        """
        logger.info("正在转换新数据...")
        
        if self.scaler is None or self.pca is None:
            raise ValueError("模型未初始化，请先调用 fit_transform() 或 load_models()")
        
        # 确保特征顺序一致
        X = df[self.selected_features].values.astype(np.float32)
        X = self._clean_features(X)
        
        # 归一化
        X_normalized = self.scaler.transform(X)
        
        # PCA 降维
        X_reduced = self.pca.transform(X_normalized)
        
        # 保留元数据
        metadata_cols = ['date', 'symbol', 'future_ret_1d', 'future_ret_5d', 
                        'future_max_dd_5d', 'future_label']
        existing_metadata = [col for col in metadata_cols if col in df.columns]
        df_metadata = df[existing_metadata].copy()
        
        # logger.info(f"新数据转换完成：{X_reduced.shape[0]} 条记录")
        
        return X_reduced, df_metadata
    
    def _clean_features(self, X: np.ndarray) -> np.ndarray:
        """
        清洗特征数据
        
        Args:
            X: 特征数组
            
        Returns:
            np.ndarray: 清洗后的数组
        """
        # 替换无穷值为 NaN
        X = np.where(np.isinf(X), np.nan, X)
        
        # 用列均值填充 NaN
        for col in range(X.shape[1]):
            mask = ~np.isnan(X[:, col])
            if mask.sum() > 0:
                mean_val = X[mask, col].mean()
                X[np.isnan(X[:, col]), col] = mean_val
        
        return X
    
    def _normalize(self, X: np.ndarray, method: str = 'minmax') -> np.ndarray:
        """
        归一化
        
        Args:
            X: 特征数组
            method: 归一化方法 (minmax 或 zscore)
            
        Returns:
            np.ndarray: 归一化后的数组
        """
        logger.info(f"使用 {method} 方法进行归一化...")
        
        if method == 'minmax':
            self.scaler = MinMaxScaler(feature_range=(0, 1))
        elif method == 'zscore':
            self.scaler = StandardScaler()
        else:
            raise ValueError(f"不支持的归一化方法：{method}")
        
        X_normalized = self.scaler.fit_transform(X)
        
        # 保存归一化器
        model_file = self.model_path / 'scaler.joblib'
        joblib.dump(self.scaler, model_file)
        logger.info(f"归一化器已保存至：{model_file}")
        
        return X_normalized
    
    def _reduce_dimension(self, X: np.ndarray, n_components: float = 0.95, 
                         whiten: bool = False) -> np.ndarray:
        """
        PCA 降维
        
        Args:
            X: 归一化后的特征数组
            n_components: 保留方差比例或主成分数量
            whiten: 是否白化
            
        Returns:
            np.ndarray: 降维后的数组
        """
        logger.info(f"执行 PCA 降维（保留方差：{n_components*100:.1f}%）...")
        
        # 如果 n_components 在 0-1 之间，表示保留方差比例
        if 0 < n_components < 1:
            self.pca = PCA(n_components=n_components, whiten=whiten)
        else:
            self.pca = PCA(n_components=int(n_components), whiten=whiten)
        
        X_reduced = self.pca.fit_transform(X)
        
        # 保存 PCA 模型
        model_file = self.model_path / 'pca.joblib'
        joblib.dump(self.pca, model_file)
        logger.info(f"PCA 模型已保存至：{model_file}")
        logger.debug(f"降维后维度：{X_reduced.shape[1]}, 解释方差比：{self.pca.explained_variance_ratio_.sum():.4f}")
        
        return X_reduced
    
    def save_models(self, version: str = "v1"):
        """
        保存模型
        
        Args:
            version: 版本号
        """
        if self.scaler is None or self.pca is None:
            raise ValueError("没有可保存的模型")
        
        # 保存特征列表
        features_file = self.model_path / 'selected_features.txt'
        with open(features_file, 'w', encoding='utf-8') as f:
            for feature in self.selected_features:
                f.write(feature + '\n')
        
        # 保存配置信息
        model_info = {
            'version': version,
            'n_features': len(self.selected_features),
            'n_components': int(self.pca.n_components_),
            'normalization': self.feature_config.get('normalization', 'minmax'),
            'explained_variance_ratio': float(self.pca.explained_variance_ratio_.sum())
        }
        
        info_file = self.model_path / 'model_info.json'
        import json
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"模型信息已保存至：{info_file}")
    
    def load_models(self, version: str = "v1"):
        """
        加载模型
        
        Args:
            version: 版本号
        """
        # 加载归一化器
        scaler_file = self.model_path / 'scaler.joblib'
        if not scaler_file.exists():
            raise FileNotFoundError(f"归一化器文件不存在：{scaler_file}")
        self.scaler = joblib.load(scaler_file)
        
        # 加载 PCA 模型
        pca_file = self.model_path / 'pca.joblib'
        if not pca_file.exists():
            raise FileNotFoundError(f"PCA 模型文件不存在：{pca_file}")
        self.pca = joblib.load(pca_file)
        
        # 加载特征列表
        features_file = self.model_path / 'selected_features.txt'
        if not features_file.exists():
            raise FileNotFoundError(f"特征列表文件不存在：{features_file}")
        
        with open(features_file, 'r', encoding='utf-8') as f:
            self.selected_features = [line.strip() for line in f.readlines()]
        
        logger.info(f"成功加载模型版本：{version}")
        logger.info(f"特征数量：{len(self.selected_features)}, PCA 维度：{self.pca.n_components_}")
