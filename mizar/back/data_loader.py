# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : data_loader.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""
import pandas as pd

def load_features(file_path: str):
    """加载特征文件，返回排序后的 DataFrame"""
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df