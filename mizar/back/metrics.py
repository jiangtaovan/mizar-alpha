# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : metrics.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.3.00

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime


def plot_net_value_with_price(net_values, dates, df, trades=None, save_path='net_value.png', text_info=None):
    """
    绘制净值曲线与价格曲线（双轴），并可选标记开仓点
    trades : list of dict, 交易记录，每个元素包含 'entry_date', 'entry_price' 等
    """
    fig, ax1 = plt.subplots(figsize=(12, 8))

    # 左轴：净值
    ax1.plot(dates, net_values, color='blue', linewidth=1.5, label='Net Value')
    ax1.axhline(y=1.0, color='gray', linestyle='--', alpha=0.7)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Net Value', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.legend(loc='upper left')

    # 右轴：价格（归一化）
    if df is not None:
        # 统一转换为日期对象（忽略时间）
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.date
        price_dict = dict(zip(df['date'], df['close']))

        # 将 dates 列表转换为纯 date 对象
        dates_dt = []
        for d in dates:
            if isinstance(d, (pd.Timestamp, datetime)):
                dates_dt.append(d.date())
            elif isinstance(d, str):
                dates_dt.append(pd.to_datetime(d).date())
            else:
                dates_dt.append(d)

        # 提取对应日期的价格
        prices = [price_dict.get(d, np.nan) for d in dates_dt]

        # 调试输出
        print(f"净值起点日期: {dates_dt[0]}")
        print(f"价格基准日期: {dates_dt[0]}")
        print(f"价格基准值: {prices[0] if prices else 'None'}")
        print(f"price_dict 中是否有该日期: {dates_dt[0] in price_dict}")

        # 处理缺失值
        if any(np.isnan(prices)):
            print("警告：部分日期在价格数据中缺失，将使用前向填充")
            prices_series = pd.Series(prices)
            prices_series = prices_series.fillna(method='ffill').fillna(method='bfill')
            prices = prices_series.tolist()

        # 归一化：以第一个日期的价格为基准
        start_price = prices[0] if prices else 1.0
        normalized_prices = [p / start_price for p in prices]

        ax2 = ax1.twinx()
        ax2.plot(dates_dt, normalized_prices, color='orange', linewidth=1.0, alpha=0.7, label='Price (norm)')
        ax2.set_ylabel('Normalized Price', color='orange')
        ax2.tick_params(axis='y', labelcolor='orange')
        ax2.legend(loc='upper right')

        # 标记开仓点
        if trades is not None and len(trades) > 0:
            # 提取开仓日期和价格
            entry_dates = []
            entry_prices_norm = []
            for t in trades:
                entry_date = t['entry_date']
                entry_price = t['entry_price']
                # 将 entry_date 转换为纯 date 对象
                if isinstance(entry_date, (pd.Timestamp, datetime)):
                    entry_date = entry_date.date()
                elif isinstance(entry_date, str):
                    entry_date = pd.to_datetime(entry_date).date()
                # 检查该日期是否在 dates_dt 中，且价格字典中有对应价格
                if entry_date in price_dict:
                    # 开仓价格归一化
                    norm_price = entry_price / start_price
                    entry_dates.append(entry_date)
                    entry_prices_norm.append(norm_price)
            if entry_dates:
                ax2.scatter(entry_dates, entry_prices_norm, color='red', s=20, marker='o',
                            label='Entry Points', zorder=5 ,alpha=0.6)
                ax2.legend(loc='upper right')

    plt.title('Backtest Net Value vs Price')
    if text_info:
        if isinstance(text_info, dict):
            text_str = '\n'.join([f"{k}: {v}" for k, v in text_info.items()])
        else:
            text_str = str(text_info)
        fig.text(0.02, 0.98, text_str, fontsize=9, verticalalignment='top',
                 bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    plt.grid(True, alpha=0.3)
    fig.tight_layout()
    plt.savefig(f"storage/out/{save_path}", dpi=150)
    plt.close()
    print(f"净值/价格曲线已保存至 {save_path}")

def plot_net_value_with_price_single(net_values, dates, df, trades=None, save_path='net_value_single.png', text_info=None):
    """
    绘制净值曲线与价格曲线（单轴），确保1.0对齐。
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    # 净值曲线
    ax.plot(dates, net_values, color='blue', linewidth=1.5, label='Net Value')
    # 价格曲线（归一化）
    if df is not None:
        # 准备价格数据
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.date
        price_dict = dict(zip(df['date'], df['close']))

        # 将 dates 转换为纯日期列表
        dates_dt = []
        for d in dates:
            if isinstance(d, (pd.Timestamp, datetime)):
                dates_dt.append(d.date())
            elif isinstance(d, str):
                dates_dt.append(pd.to_datetime(d).date())
            else:
                dates_dt.append(d)

        # 提取价格
        prices = [price_dict.get(d, np.nan) for d in dates_dt]
        # 处理缺失值
        if any(np.isnan(prices)):
            prices_series = pd.Series(prices)
            prices_series = prices_series.fillna(method='ffill').fillna(method='bfill')
            prices = prices_series.tolist()

        start_price = prices[0] if prices else 1.0
        normalized_prices = [p / start_price for p in prices]

        ax.plot(dates_dt, normalized_prices, color='orange', linewidth=1.0, alpha=0.7, label='Price (norm)')

        # 标记开仓点
        if trades is not None and len(trades) > 0:
            entry_dates = []
            entry_prices_norm = []
            for t in trades:
                entry_date = t['entry_date']
                entry_price = t['entry_price']
                if isinstance(entry_date, (pd.Timestamp, datetime)):
                    entry_date = entry_date.date()
                elif isinstance(entry_date, str):
                    entry_date = pd.to_datetime(entry_date).date()
                if entry_date in price_dict:
                    norm_price = entry_price / start_price
                    entry_dates.append(entry_date)
                    entry_prices_norm.append(norm_price)
            if entry_dates:
                ax.scatter(entry_dates, entry_prices_norm, color='red', s=20, marker='o',
                           label='Entry Points', zorder=5, alpha=0.6)

    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.7)
    ax.set_xlabel('Date')
    ax.set_ylabel('Normalized Value (Start = 1)')
    ax.legend(loc='upper left')
    ax.set_title('Backtest Net Value vs Price')
    ax.grid(True, alpha=0.3)

    if text_info:
        if isinstance(text_info, dict):
            text_str = '\n'.join([f"{k}: {v}" for k, v in text_info.items()])
        else:
            text_str = str(text_info)
        fig.text(0.02, 0.98, text_str, fontsize=9, verticalalignment='top',
                 bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    fig.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"净值/价格曲线已保存至 {save_path}")


def calculate_metrics(trades, net_values, dates, df, plot=True, **kwargs):
    """
    计算绩效指标，并可选绘制曲线（携带参数信息）
    df: 原始数据，用于绘图（必须包含 'date' 和 'close'）
    """
    net_values = np.array(net_values)
    daily_returns = net_values[1:] / net_values[:-1] - 1

    total_return = net_values[-1] - 1
    trading_days = len(daily_returns)
    if trading_days > 0:
        annual_return = (1 + total_return) ** (252 / trading_days) - 1
    else:
        annual_return = 0

    if daily_returns.std() != 0:
        sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
    else:
        sharpe = 0

    peak = np.maximum.accumulate(net_values)
    drawdown = (peak - net_values) / peak
    max_drawdown = drawdown.max() if len(drawdown) > 0 else 0

    if trades:
        returns = [t['return'] for t in trades]
        win_rates = [r for r in returns if r > 0]
        loss_rates = [r for r in returns if r <= 0]
        win_rate = len(win_rates) / len(returns)
        avg_win = np.mean(win_rates) if win_rates else 0
        avg_loss = np.mean(loss_rates) if loss_rates else 0
        profit_loss_ratio = -avg_win / avg_loss if avg_loss != 0 else 0
        trade_count = len(trades)
    else:
        win_rate = avg_win = avg_loss = profit_loss_ratio = trade_count = 0

    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    print(f"回测区间: {dates[0].date()} ~ {dates[-1].date()}")
    print(f"交易次数: {trade_count}")
    print(f"胜率: {win_rate:.2%}")
    print(f"平均盈利: {avg_win:.2%}, 平均亏损: {avg_loss:.2%}")
    print(f"盈亏比: {profit_loss_ratio:.2f}")
    print(f"累计收益率: {total_return:.2%}")
    print(f"年化收益率: {annual_return:.2%}")
    print(f"夏普比率: {sharpe:.2f}")
    print(f"最大回撤: {max_drawdown:.2%}")
    print("="*60)

    if plot:
        text_info = {
            "Threshold": kwargs.get('threshold', 'N/A'),
            "Period": kwargs.get('period', 'N/A'),
            "Top K": kwargs.get('top_k', 'N/A'),
            "Strategy": kwargs.get('strategy_type', 'N/A'),
            "Fee Rate": f"{kwargs.get('fee_rate', 0):.2%}",
            "Trades": trade_count,
            "Win Rate": f"{win_rate:.2%}",
            "Total Return": f"{total_return:.2%}",
            "Sharpe": f"{sharpe:.2f}",
            "Max DD": f"{max_drawdown:.2%}"
        }
        # 将 trades 传入绘图函数
        plot_net_value_with_price(net_values, dates, df, trades=trades, save_path='net_value.png', text_info=text_info)


    return trades, net_values.tolist()