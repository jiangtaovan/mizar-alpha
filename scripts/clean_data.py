#!/usr/bin/env python3
"""
数据清洗工具 - 删除前期不完整的数据行

用法:
    python scripts/clean_data.py datas/raw/converted_data.csv datas/raw/clean_data.csv
"""

import pandas as pd
import sys
from pathlib import Path

def find_best_start_row(df, required_features):
    """找到最佳的起始行（空值最少）"""
    print("🔍 分析不同起始点的空值情况...")
    print("=" * 60)
    
    results = []
    for start_idx in [0, 50, 100, 150, 200, 250]:
        if start_idx >= len(df):
            break
        
        subset = df.iloc[start_idx:]
        nulls = subset[required_features].isnull().sum().sum()
        total_cells = len(subset) * len(required_features)
        null_rate = (nulls / total_cells * 100) if total_cells > 0 else 0
        
        results.append({
            'start': start_idx,
            'remaining_rows': len(subset),
            'null_count': nulls,
            'null_rate': null_rate
        })
        
        print(f"从第{start_idx:3d}行开始：剩余{len(subset):3d}行，空值{nulls:4d}个，缺失率{null_rate:5.1f}%")
    
    print("=" * 60)
    
    # 找到第一个空值为 0 的位置
    best_result = None
    for r in results:
        if r['null_count'] == 0:
            best_result = r
            break
    
    # 如果没有完全无空值的，找缺失率最低的
    if not best_result:
        best_result = min(results, key=lambda x: x['null_rate'])
    
    return best_result['start']


def clean_data(input_file: str, output_file: str):
    """清洗数据"""
    print(f"正在读取文件：{input_file}")
    df = pd.read_csv(input_file)
    
    # 必需的 45 个指标
    REQUIRED_45 = [
        'MA_SMA_5', 'MA_SMA_20', 'MA_SMA_50', 'MA_SMA_200',
        'MA_EMA_12', 'MA_EMA_26', 'ADX', 'SAR',
        'RSI_RSI_6', 'RSI_RSI_12', 'RSI_RSI_24',
        'MACD_macd', 'MACD_signal', 'MACD_histogram',
        'CCI', 'MOM', 'ROC', 'WILLR',
        'ATR_ATR', 'NATR', 'TRANGE',
        'BBANDS_lower', 'BBANDS_middle', 'BBANDS_upper',
        'VOLUME_RATIO', 'OBV', 'CMF', 'MFI', 'VWAP',
        'patterns_CDL_DOJI', 'patterns_CDL_HAMMER', 'patterns_CDL_ENGULFING',
        'patterns_CDL_MORNINGSTAR', 'patterns_CDL_EVENINGSTAR',
        'patterns_CDL_DARKCLOUDCOVER', 'patterns_CDL_PIERCING',
        'AROON_aroon_up', 'AROON_aroon_down', 'AROON_aroon_oscillator',
        'DMI_ADX', 'DMI_PLUS_DI', 'DMI_MINUS_DI',
        'HISTORICAL_VOLATILITY_HV_20', 'HISTORICAL_VOLATILITY_HV_60',
        'EFFICIENCY_RATIO'
    ]
    
    print(f"\n原始数据：{len(df)} 行")
    
    # 找到最佳起始位置
    best_start = find_best_start_row(df, REQUIRED_45)
    
    print(f"\n💡 建议从第 {best_start} 行开始（后面的数据最完整）")
    
    # 让用户确认
    if best_start > 0:
        confirm = input(f"\n是否删除前 {best_start} 行？(y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 操作已取消")
            return False
    
    # 执行删除
    df_clean = df.iloc[best_start:].reset_index(drop=True)
    
    # 验证
    null_count = df_clean[REQUIRED_45].isnull().sum().sum()
    print(f"\n✅ 清洗完成！")
    print(f"   原始行数：{len(df)}")
    print(f"   清洗后：{len(df_clean)} 行")
    print(f"   删除了：{best_start} 行")
    print(f"   剩余空值：{null_count} 个")
    
    if null_count == 0:
        print(f"\n🎉 完美！所有 45 个指标都无空值！")
    else:
        print(f"\n⚠️  仍有空值，可能需要进一步处理")
        # 显示哪些列还有空值
        null_by_col = df_clean[REQUIRED_45].isnull().sum()
        if null_by_col.sum() > 0:
            print("\n空值分布:")
            for col, count in null_by_col[null_by_col > 0].items():
                print(f"   {col}: {count}个")
    
    # 保存
    df_clean.to_csv(output_file, index=False)
    print(f"\n💾 文件已保存至：{output_file}")
    print(f"文件大小：{Path(output_file).stat().st_size / 1024:.1f} KB")
    
    # 统计信息
    print(f"\n📊 数据统计:")
    print(f"日期范围：{df_clean['date'].min()} ~ {df_clean['date'].max()}")
    print(f"股票数量：{df_clean['symbol'].nunique()}")
    if 'symbol' in df_clean.columns:
        for symbol in df_clean['symbol'].unique()[:3]:
            symbol_df = df_clean[df_clean['symbol'] == symbol]
            print(f"  {symbol}: {len(symbol_df)} 行")
    
    return null_count == 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\n用法：python scripts/clean_data.py <input.csv> <output.csv>")
        print("\n示例:")
        print("  python scripts/clean_data.py datas/raw/converted_data.csv datas/raw/clean_data.csv")
        sys.exit(1)
    
    success = clean_data(sys.argv[1], sys.argv[2])
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 数据清洗成功！可以直接用于构建向量库")
        print("=" * 60)
        print("\n下一步操作:")
        print("  1. 修改 config/system_config.yaml")
        print("     data_path: './datas/raw/clean_data.csv'")
        print("  2. 运行：python scripts/build_db.py")
    else:
        print("\n" + "=" * 60)
        print("⚠️  数据仍有空值，请检查是否需要进一步处理")
        print("=" * 60)
    
    sys.exit(0 if success else 1)
