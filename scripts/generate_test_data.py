#!/usr/bin/env python3
"""
生成模拟测试数据
如果无法获得真实有效数据，可以使用模拟数据
但为了验证有效性，请严格按真实行情计算好数据 用来导入

用法:
    python scripts/generate_test_data.py --days 250 --output datas/raw/test_data.csv
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_test_data(days: int = 250, symbols: list = None, output: str = None):
    """
    生成模拟技术指标数据
    
    Args:
        days: 交易日天数
        symbols: 股票代码列表
        output: 输出文件路径
    """
    if symbols is None:
        symbols = ['000001.SH', '000002.SZ', '399001.SZ']
    
    print(f"正在生成 {len(symbols)} 个标的，每个 {days} 天的模拟数据...")
    
    # 生成日期序列（跳过周末）
    end_date = datetime(2026, 3, 24)
    dates = []
    current = end_date
    while len(dates) < days:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current)
        current -= timedelta(days=1)
    
    dates = sorted(dates)
    
    # 生成数据
    all_data = []
    
    for symbol in symbols:
        base_price = np.random.uniform(10, 100)
        
        for i, date in enumerate(dates):
            # 生成价格数据
            price_change = np.random.randn() * 0.02
            current_price = base_price * (1 + price_change)
            
            # 生成技术指标（随机但合理）
            ma5 = current_price * (1 + np.random.randn() * 0.01)
            ma20 = current_price * (1 + np.random.randn() * 0.02)
            ma50 = current_price * (1 + np.random.randn() * 0.03)
            ma200 = current_price * (1 + np.random.randn() * 0.05)
            
            ema12 = current_price * (1 + np.random.randn() * 0.008)
            ema26 = current_price * (1 + np.random.randn() * 0.015)
            
            adx = np.random.uniform(15, 45)
            sar = current_price * (1 + np.random.uniform(-0.05, 0.05))
            
            # RSI (0-100)
            rsi6 = np.random.uniform(30, 70)
            rsi12 = np.random.uniform(35, 65)
            rsi24 = np.random.uniform(40, 60)
            
            # MACD
            macd_macd = np.random.randn() * 0.5
            macd_signal = np.random.randn() * 0.3
            macd_hist = macd_macd - macd_signal
            
            # CCI
            cci = np.random.uniform(-150, 150)
            
            # MOM, ROC
            mom = np.random.randn() * 2
            roc = np.random.randn() * 5
            
            # WILLR (-100 to 0)
            willr = np.random.uniform(-100, 0)
            
            # ATR
            atr = current_price * np.random.uniform(0.02, 0.05)
            natr = atr / current_price * 100
            trange = atr * np.random.uniform(0.8, 1.2)
            
            # BOLLINGER
            bb_lower = current_price * (1 - np.random.uniform(0.02, 0.05))
            bb_middle = current_price
            bb_upper = current_price * (1 + np.random.uniform(0.02, 0.05))
            
            # Volume indicators
            volume_ratio = np.random.uniform(0.5, 3.0)
            obv = np.random.randint(1000000, 10000000)
            cmf = np.random.uniform(-0.5, 0.5)
            mfi = np.random.uniform(30, 70)
            vwap = current_price * (1 + np.random.uniform(-0.01, 0.01))
            
            # Candlestick patterns (0 or 1)
            cdl_doji = np.random.choice([0, 1], p=[0.9, 0.1])
            cdl_hammer = np.random.choice([0, 1], p=[0.85, 0.15])
            cdl_engulfing = np.random.choice([0, 1], p=[0.8, 0.2])
            cdl_morning = np.random.choice([0, 1], p=[0.9, 0.1])
            cdl_evening = np.random.choice([0, 1], p=[0.9, 0.1])
            cdl_dark = np.random.choice([0, 1], p=[0.85, 0.15])
            cdl_piercing = np.random.choice([0, 1], p=[0.85, 0.15])
            
            # Enhanced indicators
            aroon_up = np.random.uniform(0, 100)
            aroon_down = np.random.uniform(0, 100)
            aroon_osc = aroon_up - aroon_down
            
            dmi_adx = adx
            dmi_plus_di = np.random.uniform(10, 40)
            dmi_minus_di = np.random.uniform(10, 40)
            
            hv20 = np.random.uniform(0.2, 0.5)
            hv60 = np.random.uniform(0.25, 0.45)
            efficiency = np.random.uniform(0.3, 0.8)
            
            row = {
                'date': date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'MA_SMA_5': round(ma5, 2),
                'MA_SMA_20': round(ma20, 2),
                'MA_SMA_50': round(ma50, 2),
                'MA_SMA_200': round(ma200, 2),
                'MA_EMA_12': round(ema12, 2),
                'MA_EMA_26': round(ema26, 2),
                'ADX': round(adx, 2),
                'SAR': round(sar, 2),
                'RSI_RSI_6': round(rsi6, 2),
                'RSI_RSI_12': round(rsi12, 2),
                'RSI_RSI_24': round(rsi24, 2),
                'MACD_macd': round(macd_macd, 3),
                'MACD_signal': round(macd_signal, 3),
                'MACD_histogram': round(macd_hist, 3),
                'CCI': round(cci, 2),
                'MOM': round(mom, 2),
                'ROC': round(roc, 2),
                'WILLR': round(willr, 2),
                'ATR_ATR': round(atr, 2),
                'NATR': round(natr, 2),
                'TRANGE': round(trange, 2),
                'BBANDS_lower': round(bb_lower, 2),
                'BBANDS_middle': round(bb_middle, 2),
                'BBANDS_upper': round(bb_upper, 2),
                'VOLUME_RATIO': round(volume_ratio, 2),
                'OBV': obv,
                'CMF': round(cmf, 3),
                'MFI': round(mfi, 2),
                'VWAP': round(vwap, 2),
                'patterns_CDL_DOJI': cdl_doji,
                'patterns_CDL_HAMMER': cdl_hammer,
                'patterns_CDL_ENGULFING': cdl_engulfing,
                'patterns_CDL_MORNINGSTAR': cdl_morning,
                'patterns_CDL_EVENINGSTAR': cdl_evening,
                'patterns_CDL_DARKCLOUDCOVER': cdl_dark,
                'patterns_CDL_PIERCING': cdl_piercing,
                'AROON_aroon_up': round(aroon_up, 2),
                'AROON_aroon_down': round(aroon_down, 2),
                'AROON_aroon_oscillator': round(aroon_osc, 2),
                'DMI_ADX': round(dmi_adx, 2),
                'DMI_PLUS_DI': round(dmi_plus_di, 2),
                'DMI_MINUS_DI': round(dmi_minus_di, 2),
                'HISTORICAL_VOLATILITY_HV_20': round(hv20, 3),
                'HISTORICAL_VOLATILITY_HV_60': round(hv60, 3),
                'EFFICIENCY_RATIO': round(efficiency, 2)
            }
            
            all_data.append(row)
            base_price = current_price
    
    # 创建 DataFrame
    df = pd.DataFrame(all_data)
    
    # 保存
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✓ 数据已保存至：{output_path}")
        print(f"  - 总计 {len(df)} 条记录")
        print(f"  - 标的数量：{len(symbols)}")
        print(f"  - 时间范围：{df['date'].min()} 至 {df['date'].max()}")
    else:
        print(df.head())
        print(f"\n总计 {len(df)} 条记录")
    
    return df


def main():
    parser = argparse.ArgumentParser(description='生成模拟测试数据')
    parser.add_argument('--days', type=int, default=250, help='交易日天数')
    parser.add_argument('--symbols', type=str, nargs='+', default=None, 
                       help='股票代码列表')
    parser.add_argument('--output', type=str, default=None, 
                       help='输出文件路径')
    
    args = parser.parse_args()
    
    generate_test_data(days=args.days, symbols=args.symbols, output=args.output)


if __name__ == "__main__":
    main()
