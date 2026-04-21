# -*- coding: utf-8 -*-
# @Time    : 2026/3/27 
# @File    : batch_compute_features.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""
from pathlib import Path
from features.crypto_features import process_crypto_file

def main():
    coin_dir = Path('datas/coin')
    for file_path in coin_dir.glob('*.csv'):
        print(f"处理 {file_path.name}...")
        # 根据文件名选择映射（示例）
        if 'AAVEETH' in file_path.name:
            mapping = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close',
                'Volume AAVE': 'volume', 'Date': 'date', 'Symbol': 'symbol'
            }
        elif '1INCHBTC' in file_path.name:
            mapping = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close',
                'Volume 1INCH': 'volume', 'Date': 'date', 'Symbol': 'symbol'
            }
        else:
            mapping = None  # 使用自动映射
        try:
            process_crypto_file(str(file_path), column_mapping=mapping)
        except Exception as e:
            print(f"  错误: {e}")

if __name__ == '__main__':
    main()