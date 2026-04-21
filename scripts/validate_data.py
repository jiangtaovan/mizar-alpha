#!/usr/bin/env python3
"""
数据验证工具 - 快速检查 CSV 数据是否符合要求

用法:
    python scripts/validate_data.py datas/raw/your_data.csv
"""

import sys
import pandas as pd
from pathlib import Path

# 必需的 45 个技术指标
REQUIRED_FEATURES = [
    # 趋势指标 (8)
    'MA_SMA_5', 'MA_SMA_20', 'MA_SMA_50', 'MA_SMA_200',
    'MA_EMA_12', 'MA_EMA_26', 'ADX', 'SAR',
    
    # 动量指标 (10)
    'RSI_RSI_6', 'RSI_RSI_12', 'RSI_RSI_24',
    'MACD_macd', 'MACD_signal', 'MACD_histogram',
    'CCI', 'MOM', 'ROC', 'WILLR',
    
    # 波动率指标 (6)
    'ATR_ATR', 'NATR', 'TRANGE',
    'BBANDS_lower', 'BBANDS_middle', 'BBANDS_upper',
    
    # 成交量指标 (5)
    'VOLUME_RATIO', 'OBV', 'CMF', 'MFI', 'VWAP',
    
    # K 线形态 (7)
    'patterns_CDL_DOJI', 'patterns_CDL_HAMMER', 'patterns_CDL_ENGULFING',
    'patterns_CDL_MORNINGSTAR', 'patterns_CDL_EVENINGSTAR',
    'patterns_CDL_DARKCLOUDCOVER', 'patterns_CDL_PIERCING',
    
    # 增强指标 (9)
    'AROON_aroon_up', 'AROON_aroon_down', 'AROON_aroon_oscillator',
    'DMI_ADX', 'DMI_PLUS_DI', 'DMI_MINUS_DI',
    'HISTORICAL_VOLATILITY_HV_20', 'HISTORICAL_VOLATILITY_HV_60',
    'EFFICIENCY_RATIO'
]

def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def validate_data(file_path: str):
    """验证数据文件"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"\n❌ 文件不存在：{file_path}")
        return False
    
    print_section("📥 数据加载")
    print(f"文件路径：{file_path}")
    
    try:
        df = pd.read_csv(file_path)
        print(f"✅ 成功读取 CSV 文件")
        print(f"   文件大小：{file_path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"❌ 读取失败：{e}")
        return False
    
    # 基本信息
    print_section("📊 基本信息")
    print(f"总行数：{len(df):,}")
    print(f"总列数：{len(df.columns)}")
    print(f"\n所有列名:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    # 必需列检查
    print_section("✅ 必需列验证")
    all_required = REQUIRED_FEATURES + ['date', 'symbol', 'current_price']
    missing_cols = [col for col in all_required if col not in df.columns]
    extra_cols = [col for col in df.columns if col not in all_required + ['date', 'symbol', 'current_price']]
    
    if missing_cols:
        print(f"❌ 缺少 {len(missing_cols)} 个必需列:")
        for col in missing_cols:
            print(f"   - {col}")
        success = False
    else:
        print(f"✅ 所有 {len(all_required)} 个必需列都存在")
        success = True
    
    if extra_cols:
        print(f"\nℹ️  额外列 ({len(extra_cols)} 个，将被忽略):")
        for col in extra_cols[:10]:  # 只显示前 10 个
            print(f"   - {col}")
        if len(extra_cols) > 10:
            print(f"   ... 还有 {len(extra_cols) - 10} 个")
    
    # 空值检查
    print_section("⚠️  空值检查")
    null_counts = df[all_required].isnull().sum()
    total_nulls = null_counts.sum()
    
    if total_nulls == 0:
        print(f"✅ 无空值")
    else:
        print(f"⚠️  发现 {total_nulls:,} 个空值")
        print("\n空值分布（前 10 列）:")
        problematic = null_counts[null_counts > 0].sort_values(ascending=False)
        for col, count in problematic.head(10).items():
            pct = (count / len(df)) * 100
            print(f"   {col}: {count:,} ({pct:.1f}%)")
        
        if total_nulls > len(df) * 0.1:
            print(f"\n⚠️  警告：空值超过 10%，建议先清洗数据")
    
    # 数据类型和范围检查
    print_section("🔍 数据合理性检查")
    
    # 日期格式
    try:
        dates = pd.to_datetime(df['date'])
        print(f"✅ 日期格式正确")
        print(f"   日期范围：{dates.min().strftime('%Y-%m-%d')} ~ {dates.max().strftime('%Y-%m-%d')}")
        trading_days = (dates.max() - dates.min()).days
        print(f"   时间跨度：{trading_days} 天")
    except Exception as e:
        print(f"❌ 日期格式错误：{e}")
    
    # 股票代码
    if 'symbol' in df.columns:
        symbols = df['symbol'].unique()
        print(f"✅ 股票代码数量：{len(symbols)}")
        print(f"   示例：{', '.join(symbols[:5])}")
    
    # 价格范围
    if 'current_price' in df.columns:
        prices = df['current_price'].dropna()
        if len(prices) > 0:
            print(f"✅ 价格范围：¥{prices.min():.2f} ~ ¥{prices.max():.2f}")
            if prices.min() <= 0:
                print(f"⚠️  警告：发现非正价格")
    
    # 技术指标范围抽样检查
    print_section("📈 技术指标抽样检查")
    sample_features = ['MA_SMA_5', 'RSI_RSI_12', 'MACD_macd', 'ATR_ATR']
    for feature in sample_features:
        if feature in df.columns:
            values = df[feature].dropna()
            if len(values) > 0:
                print(f"{feature}:")
                print(f"   范围：[{values.min():.4f}, {values.max():.4f}]")
                print(f"   均值：{values.mean():.4f}")
                print(f"   标准差：{values.std():.4f}")
    
    # 数据统计
    print_section("📊 数据统计")
    unique_dates = df['date'].nunique() if 'date' in df.columns else 0
    unique_symbols = df['symbol'].nunique() if 'symbol' in df.columns else 0
    valid_records = len(df) - total_nulls
    
    print(f"唯一日期数：{unique_dates}")
    print(f"股票数量：{unique_symbols}")
    print(f"有效记录：{valid_records:,}")
    
    # 最终建议
    print_section("💡 建议")
    
    recommendations = []
    
    if len(df) < 100:
        recommendations.append("⚠️  数据量较少（< 100 条），建议增加至 500+ 条")
    
    if total_nulls > 0:
        recommendations.append("⚠️  存在空值，建议使用 fillna() 或删除含空值的行")
    
    if unique_symbols == 1 and unique_dates < 200:
        recommendations.append("ℹ️  单只股票数据，建议增加更多标的或更长时间跨度")
    
    if len(df) >= 500 and total_nulls == 0:
        recommendations.append("✅ 数据质量良好，可以直接使用")
    
    if not recommendations:
        recommendations.append("✅ 数据基本符合要求，可以继续下一步")
    
    for rec in recommendations:
        print(rec)
    
    print_section("验证完成")
    if success and total_nulls == 0:
        print("✅ 验证通过！数据可以用于构建向量库")
        print("\n下一步操作:")
        print("  1. 将文件放入 datas/raw/ 目录")
        print("  2. 修改 config/system_config.yaml 中的 data_path")
        print("  3. 运行：python scripts/build_db.py")
    elif success:
        print("⚠️  基本结构正确，但需要处理空值")
    else:
        print("❌ 验证未通过，请先修复缺少的列")
    
    print()
    
    return success and total_nulls == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n用法：python scripts/validate_data.py <csv_file_path>")
        print("\n示例:")
        print("  python scripts/validate_data.py datas/raw/sample_data.csv")
        print("  python scripts/validate_data.py datas/raw/real_data.csv")
        sys.exit(1)
    
    success = validate_data(sys.argv[1])
    sys.exit(0 if success else 1)
