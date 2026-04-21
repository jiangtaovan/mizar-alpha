# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : feature_handler.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""
from pathlib import Path

import pandas as pd
from ..features.feature_engineer import FeatureEngineer

class FeatureHandler:
    """封装特征工程模型，提供特征提取和转换"""
    def __init__(self, config):
        self.engineer = FeatureEngineer(config)
        self.engineer.load_models(version="v1")
        with open(Path("models") / "selected_features.txt", 'r') as f:
            self.feature_names = [line.strip() for line in f if line.strip()]

    def extract_features(self, row):
        """从 DataFrame 的一行中提取特征字典"""
        features = {name: row[name] for name in self.feature_names if name in row}
        # 补全缺失特征
        for name in self.feature_names:
            if name not in features:
                features[name] = 0.0
        return features

    def transform(self, features_dict):
        """将特征字典转换为查询向量"""
        df = pd.DataFrame([features_dict])
        return self.engineer.transform(df)