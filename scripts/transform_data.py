#!/usr/bin/env python3
"""
数据转换工具 - 将带前缀的指标列名转换为标准格式，并处理空值

用法:
    python scripts/transform_data.py datas/raw/all_indicators.csv datas/raw/converted_data.csv
"""

import pandas as pd
import sys
from pathlib import Path

# 列名映射规则（前缀 -> 标准名）
COLUMN_MAPPING = {
    # 趋势指标
    'trend_indicators_MACD_macd': 'MACD_macd',
    'trend_indicators_MACD_signal': 'MACD_signal',
    'trend_indicators_MACD_histogram': 'MACD_histogram',
    'trend_indicators_MA_SMA_5': 'MA_SMA_5',
    'trend_indicators_MA_SMA_10': 'MA_SMA_10',
    'trend_indicators_MA_SMA_20': 'MA_SMA_20',
    'trend_indicators_MA_SMA_50': 'MA_SMA_50',
    'trend_indicators_MA_SMA_200': 'MA_SMA_200',
    'trend_indicators_MA_EMA_12': 'MA_EMA_12',
    'trend_indicators_MA_EMA_26': 'MA_EMA_26',
    'trend_indicators_MA_WMA_20': 'MA_WMA_20',
    'trend_indicators_SAR_values': 'SAR',
    'trend_indicators_ADX_values': 'ADX',
    'trend_indicators_TEMA_values': 'TEMA',
    
    # 动量指标
    'momentum_indicators_RSI_RSI_6': 'RSI_RSI_6',
    'momentum_indicators_RSI_RSI_12': 'RSI_RSI_12',
    'momentum_indicators_RSI_RSI_24': 'RSI_RSI_24',
    'momentum_indicators_STOCH_fastK': 'STOCH_fastK',
    'momentum_indicators_STOCH_fastD': 'STOCH_fastD',
    'momentum_indicators_STOCHF_fastK': 'STOCHF_fastK',
    'momentum_indicators_STOCHF_fastD': 'STOCHF_fastD',
    'momentum_indicators_WILLR_values': 'WILLR',
    'momentum_indicators_CCI_values': 'CCI',
    'momentum_indicators_MOM_values': 'MOM',
    'momentum_indicators_ROC_values': 'ROC',
    'momentum_indicators_BIAS_BIAS_6': 'BIAS_BIAS_6',
    'momentum_indicators_BIAS_BIAS_12': 'BIAS_BIAS_12',
    'momentum_indicators_BIAS_BIAS_24': 'BIAS_BIAS_24',
    
    # 波动率指标
    'volatility_indicators_BBANDS_upper': 'BBANDS_upper',
    'volatility_indicators_BBANDS_middle': 'BBANDS_middle',
    'volatility_indicators_BBANDS_lower': 'BBANDS_lower',
    'volatility_indicators_ATR_values': 'ATR_ATR',
    'volatility_indicators_TRANGE_values': 'TRANGE',
    'volatility_indicators_NATR_values': 'NATR',
    
    # 成交量指标
    'volume_indicators_OBV_values': 'OBV',
    'volume_indicators_MFI_values': 'MFI',
    'volume_indicators_CMF_values': 'CMF',
    'volume_indicators_VOLUME_RATIO': 'VOLUME_RATIO',
    
    # 增强指标
    'enhanced_indicators_DMI_PLUS_DI': 'DMI_PLUS_DI',
    'enhanced_indicators_DMI_MINUS_DI': 'DMI_MINUS_DI',
    'enhanced_indicators_DMI_ADX': 'DMI_ADX',
    'enhanced_indicators_DMI_ADXR': 'DMI_ADXR',
    'enhanced_indicators_TRIX': 'TRIX',
    'enhanced_indicators_WILLIAMS_R_MULTI_WILLR_6': 'WILLIAMS_R_MULTI_WILLR_6',
    'enhanced_indicators_WILLIAMS_R_MULTI_WILLR_14': 'WILLIAMS_R_MULTI_WILLR_14',
    'enhanced_indicators_WILLIAMS_R_MULTI_WILLR_28': 'WILLIAMS_R_MULTI_WILLR_28',
    'enhanced_indicators_ROC_MULTI_ROC_6': 'ROC_MULTI_ROC_6',
    'enhanced_indicators_ROC_MULTI_ROC_12': 'ROC_MULTI_ROC_12',
    'enhanced_indicators_ROC_MULTI_ROC_24': 'ROC_MULTI_ROC_24',
    'enhanced_indicators_MOMENTUM_MULTI_MOM_6': 'MOMENTUM_MULTI_MOM_6',
    'enhanced_indicators_MOMENTUM_MULTI_MOM_12': 'MOMENTUM_MULTI_MOM_12',
    'enhanced_indicators_MOMENTUM_MULTI_MOM_24': 'MOMENTUM_MULTI_MOM_24',
    'enhanced_indicators_BOLLINGER_MULTI_BB_10_upper': 'BOLLINGER_MULTI_BB_10_upper',
    'enhanced_indicators_BOLLINGER_MULTI_BB_10_middle': 'BOLLINGER_MULTI_BB_10_middle',
    'enhanced_indicators_BOLLINGER_MULTI_BB_10_lower': 'BOLLINGER_MULTI_BB_10_lower',
    'enhanced_indicators_BOLLINGER_MULTI_BB_20_upper': 'BOLLINGER_MULTI_BB_20_upper',
    'enhanced_indicators_BOLLINGER_MULTI_BB_20_middle': 'BOLLINGER_MULTI_BB_20_middle',
    'enhanced_indicators_BOLLINGER_MULTI_BB_20_lower': 'BOLLINGER_MULTI_BB_20_lower',
    'enhanced_indicators_BOLLINGER_MULTI_BB_50_upper': 'BOLLINGER_MULTI_BB_50_upper',
    'enhanced_indicators_BOLLINGER_MULTI_BB_50_middle': 'BOLLINGER_MULTI_BB_50_middle',
    'enhanced_indicators_BOLLINGER_MULTI_BB_50_lower': 'BOLLINGER_MULTI_BB_50_lower',
    'enhanced_indicators_ATR_MULTI_ATR_7': 'ATR_MULTI_ATR_7',
    'enhanced_indicators_ATR_MULTI_ATR_14': 'ATR_MULTI_ATR_14',
    'enhanced_indicators_ATR_MULTI_ATR_21': 'ATR_MULTI_ATR_21',
    'enhanced_indicators_VR_values': 'VR',
    'enhanced_indicators_VWAP_values': 'VWAP',
    'enhanced_indicators_VOLUME_RATIO_ENHANCED_values': 'VOLUME_RATIO_ENHANCED',
    'enhanced_indicators_AROON_aroon_up': 'AROON_aroon_up',
    'enhanced_indicators_AROON_aroon_down': 'AROON_aroon_down',
    'enhanced_indicators_AROON_aroon_oscillator': 'AROON_aroon_oscillator',
    'enhanced_indicators_CMO': 'CMO',
    'enhanced_indicators_EFFICIENCY_RATIO_values': 'EFFICIENCY_RATIO',
    'enhanced_indicators_IMI_values': 'IMI',
    'enhanced_indicators_KELTNER_CHANNEL_upper': 'KELTNER_CHANNEL_upper',
    'enhanced_indicators_KELTNER_CHANNEL_middle': 'KELTNER_CHANNEL_middle',
    'enhanced_indicators_KELTNER_CHANNEL_lower': 'KELTNER_CHANNEL_lower',
    'enhanced_indicators_DMA_dma_diff': 'DMA_dma_diff',
    'enhanced_indicators_DMA_dma_ama': 'DMA_dma_ama',
    'enhanced_indicators_PRICE_RELATIVE_STRENGTH_PRS_5': 'PRICE_RELATIVE_STRENGTH_PRS_5',
    'enhanced_indicators_PRICE_RELATIVE_STRENGTH_PRS_10': 'PRICE_RELATIVE_STRENGTH_PRS_10',
    'enhanced_indicators_PRICE_RELATIVE_STRENGTH_PRS_20': 'PRICE_RELATIVE_STRENGTH_PRS_20',
    'enhanced_indicators_PRICE_RELATIVE_STRENGTH_PRS_60': 'PRICE_RELATIVE_STRENGTH_PRS_60',
    'enhanced_indicators_VRS_MULTI_VRS_5': 'VRS_MULTI_VRS_5',
    'enhanced_indicators_VRS_MULTI_VRS_20': 'VRS_MULTI_VRS_20',
    'enhanced_indicators_VRS_MULTI_VRS_60': 'VRS_MULTI_VRS_60',
}

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

def transform_data(input_file: str, output_file: str):
    """转换数据文件"""
    print(f"正在读取文件：{input_file}")
    df = pd.read_csv(input_file)
    
    print(f"原始数据：{len(df)} 行，{len(df.columns)} 列")
    
    # 重命名列
    new_columns = {}
    unmapped_cols = []
    
    for col in df.columns:
        if col in COLUMN_MAPPING:
            new_columns[col] = COLUMN_MAPPING[col]
        elif col in ['date', 'symbol', 'current_price']:
            new_columns[col] = col
        else:
            unmapped_cols.append(col)
    
    df = df.rename(columns=new_columns)
    df = df.loc[:, ~df.columns.duplicated()]
    
    print(f"\n列名转换完成！")
    print(f"已转换：{len(new_columns) - 3} 个指标列名")
    
    if unmapped_cols:
        print(f"\n未映射的列名 ({len(unmapped_cols)} 个)，将被保留:")
        for col in unmapped_cols[:10]:
            print(f"  - {col}")
        if len(unmapped_cols) > 10:
            print(f"  ... 还有 {len(unmapped_cols) - 10} 个")
    
    # 检查必需指标
    print(f"\n📊 检查必需的 45 个指标...")
    missing_required = []
    for feature in REQUIRED_45:
        if feature not in df.columns:
            missing_required.append(feature)
    
    if missing_required:
        print(f"\n📝 自动补充缺失的 {len(missing_required)} 个指标...")
        
        # K 线形态默认为 0（未出现）
        for pattern in [col for col in missing_required if col.startswith('patterns_')]:
            df[pattern] = 0
            print(f"   ✅ 添加 {pattern} = 0 (未出现)")
        
        # 历史波动率用 ATR 近似
        if 'HISTORICAL_VOLATILITY_HV_20' in missing_required and 'ATR_ATR' in df.columns:
            df['HISTORICAL_VOLATILITY_HV_20'] = df['ATR_ATR'] / df['current_price'] * 100
            print(f"   💡 使用 ATR_ATR 近似替代 HISTORICAL_VOLATILITY_HV_20")
        
        if 'HISTORICAL_VOLATILITY_HV_60' in missing_required and 'HISTORICAL_VOLATILITY_HV_20' in df.columns:
            df['HISTORICAL_VOLATILITY_HV_60'] = df['HISTORICAL_VOLATILITY_HV_20'] * 1.2
            print(f"   💡 使用 HV_20*1.2 近似替代 HISTORICAL_VOLATILITY_HV_60")
    else:
        print(f"✅ 所有 45 个必需指标都存在！")
    
    # 统计空值
    print(f"\n⚠️  空值统计:")
    null_counts = df[REQUIRED_45].isnull().sum()
    total_nulls = null_counts.sum()
    print(f"总空值数：{total_nulls:,}")
    
    if total_nulls > 0:
        print(f"\n空值最多的指标（前 10）:")
        top_nulls = null_counts.sort_values(ascending=False).head(10)
        for col, count in top_nulls.items():
            pct = (count / len(df)) * 100
            print(f"   {col}: {count:,} ({pct:.1f}%)")
    
    # 计算可用行数
    valid_rows = df[df[REQUIRED_45].notnull().all(axis=1)]
    print(f"\n📈 数据可用性:")
    print(f"总行数：{len(df)}")
    print(f"完整行数（45 个指标都非空）: {len(valid_rows)}")
    print(f"可用率：{len(valid_rows) / len(df) * 100:.1f}%")
    
    # 保存
    df.to_csv(output_file, index=False)
    print(f"\n✅ 转换完成！文件已保存至：{output_file}")
    print(f"文件大小：{Path(output_file).stat().st_size / 1024:.1f} KB")
    
    return len(valid_rows) > len(df) * 0.5


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\n用法：python scripts/transform_data.py <input.csv> <output.csv>")
        sys.exit(1)
    
    success = transform_data(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
