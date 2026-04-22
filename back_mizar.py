# -*- coding: utf-8 -*-
# @Time    : 2026/4/16 
# @File    : back_mizar.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.3.00

"""
回测模块重构版（增强版）：
- 信号在 T 日计算，T+1 日开盘价执行开平仓（彻底消除未来函数）
- 净值计算精确区分延续持仓、开仓、平仓三种情况
- 支持固定周期（fixed）和信号持续（signal）两种策略
- 支持单边手续费设置
- 新增置信度、5日预期收益过滤
- 新增动态仓位管理（全仓 / 信号强度比例仓）
- 绘图时价格曲线与净值起点严格对齐
"""

"""
说明：Mizarα当前 提供当前模块未回测的Demo程序，且指定的了回测的文件路径。
未了保证回测的效率，需要下载行情后同时计算K线指标特征，然后把文件拷贝到对应的目录 进行回测。
因为针对不同个股、或趋势行情，设置不同的参数预期能对回测结果有影响，请自行斟酌。
或参考 docs/technical/Mizarα 回测系统参数配置指南 v0.2.md
后续会考量把回测功能集成到CLI命令中

"""
import argparse
import pandas as pd
from loguru import logger


from mizar.utils import load_config
from mizar.back.data_loader import load_features
from mizar.back.feature_handler import FeatureHandler
from mizar.back.query_engine import QueryEngine
from mizar.back.metrics import calculate_metrics
from mizar.back.strategy_pro import Strategy
from mizar.back.param_presets import ParamPresets, BacktestParams


def run_backtest(
        feature_file,
        threshold=0.5,
        period=5,
        top_k=10,
        strategy_type='fixed',
        fee_rate=0.0,
        min_confidence=None,
        min_ret_5d=None,
        position_sizing='full',
        stop_loss=None,
        take_profit =None,
        trailing_stop_pct=None,
        take_profit_pct=None,
        max_hold_days=None,
        partial_exit_enabled=None
):
    """
    执行回测主流程

    新增参数：
        min_confidence : float, 最低置信度要求，None 表示不过滤
        min_ret_5d    : float, 最低5日预期收益（%），None 表示不过滤
        position_sizing: str, 'full' 全仓 / 'signal' 按信号强度比例
        stop_loss     : float, 止损比例（如 0.05 表示 -5%）
        take_profit   : float, 止盈比例
    """
    # 加载数据（必须包含 open, close, date 列）
    df = load_features( feature_file )
    logger.info( f"数据范围: {df['date'].min().date()} ~ {df['date'].max().date()}, 共 {len( df )} 条" )

    # 初始化组件
    config = load_config()
    feature_handler = FeatureHandler( config )
    query_engine = QueryEngine( config )

    strategy = Strategy(
        threshold=threshold,
        period=period,
        strategy_type=strategy_type,
        fee_rate=fee_rate,
        min_confidence=min_confidence,
        min_ret_5d=min_ret_5d,
        position_sizing=position_sizing,
        trailing_stop_pct=trailing_stop_pct,  # 新
        take_profit_pct=take_profit_pct,  # 新
        max_hold_days=max_hold_days,  # 新
        partial_exit_enabled=partial_exit_enabled  # 新
    )

    # 回测参数：跳过前 min_idx 行（确保技术指标有效，如 SMA_50）
    min_idx = 250
    net_values = [1.0]  # 净值序列（每日收盘后）
    dates = [df['date'].iloc[min_idx - 1]]  # 日期序列（与净值对齐）
    symbol = df['symbol'].iloc[min_idx - 1]  #取得股票代码

    logger.info( "开始回测（延迟执行：信号次日开盘价开平仓）..." )

    # 存储前一天完整预测结果
    prev_prediction = None
    prev_close = df['close'].iloc[min_idx - 1]  # 用于第一天跳空计算

    for i in range( min_idx, len( df ) ):
        row = df.iloc[i]
        current_date = row['date']
        current_open = row['open']
        current_close = row['close']

        # 1. 记录昨日收盘时的持仓状态与仓位比例
        pos_before = strategy.position
        pos_pct_before = strategy.current_position_pct

        # 2. 执行交易（基于前一天的预测）
        open_pct = 0.0
        close_flag = False
        if i > min_idx and prev_prediction is not None:
            open_pct, close_flag = strategy.step( prev_prediction, current_date, current_open )

        # 3. 今日收盘后的持仓状态与仓位比例
        pos_after = strategy.position
        pos_pct_after = strategy.current_position_pct

        # 4. 计算今日收益率（考虑仓位比例）
        if pos_before == 1 and pos_after == 1:
            # 延续持仓：从昨日收盘到今日收盘的涨跌幅 × 昨日仓位
            daily_ret = (current_close - prev_close) / prev_close * pos_pct_before
        elif pos_before == 1 and pos_after == 0:
            # 今日平仓：从昨日收盘到今日开盘的涨跌幅 × 昨日仓位
            daily_ret = (current_open - prev_close) / prev_close * pos_pct_before
        elif pos_before == 0 and pos_after == 1:
            # 今日开仓：从今日开盘到今日收盘的涨跌幅 × 今日开仓比例
            daily_ret = (current_close - current_open) / current_open * open_pct
        else:
            daily_ret = 0.0

        # 5. 扣除手续费（按实际交易比例计算）
        if open_pct > 0 or close_flag:
            # 发生交易时，按实际变动的仓位比例收取单边手续费
            trade_pct = open_pct if open_pct > 0 else pos_pct_before
            daily_ret -= strategy.fee_rate * trade_pct

        # 6. 更新净值
        net_values.append( net_values[-1] * (1 + daily_ret) )
        dates.append( current_date )

        # 7. 更新昨日收盘价
        prev_close = current_close

        # 8. 计算今日信号（用于明天交易）
        features = feature_handler.extract_features( row )
        query_vec, _ = feature_handler.transform( features )
        prediction = query_engine.query( query_vec, top_k, period, current_date.strftime( '%Y-%m-%d' ) )
        # prediction = query_engine.query( query_vec, top_k )

        # 打印关键信息（可注释以减少输出）
        if prediction:
            prob = prediction.get( 'up_probability', 0 )
            conf = prediction.get( 'confidence', 0 )
            ret5 = prediction.get( 'avg_ret_5d', 0 )
            logger.debug(
                f"{current_date.date()} open={current_open:.2f}  close={current_close:.2f}  "
                f"prob={prob:.2%}  conf={conf:.3f}  ret5={ret5:+.2f}%"
            )

        prev_prediction = prediction

    # 回测结束：若有持仓，在最后一天收盘价强制平仓
    if strategy.position == 1:
        exit_price = df['close'].iloc[-1]
        ret = (exit_price - strategy.entry_price) / strategy.entry_price
        strategy.trades.append( {
            'entry_date': strategy.entry_date,
            'exit_date': df['date'].iloc[-1],
            'entry_price': strategy.entry_price,
            'exit_price': exit_price,
            'return': ret,
            'position_pct': strategy.current_position_pct,
        } )

    # 计算绩效指标并绘图
    trades, net_values = calculate_metrics(
        strategy.trades,
        net_values,
        dates,
        df=df,
        plot=True,
        threshold=threshold,
        period=period,
        top_k=top_k,
        strategy_type=strategy_type,
        fee_rate=fee_rate
    )

    # 保存交易记录
    if trades:
        pd.DataFrame( trades ).to_csv( 'storage/out/backtest_trades.csv', index=False )
        print( "交易记录已保存到 backtest_trades.csv" )

    return trades, net_values

def main():
    parser = argparse.ArgumentParser( description="Mizar 回测系统" )
    parser.add_argument( "--file", default="./storage/backtest/601778_0_indicators_full.csv", help="特征文件路径" )

    # 新增预设参数组
    parser.add_argument( "--preset", type=str, default=None,
                         choices=["blue_chip", "growth_mid", "tech_small", "quant_active", "default",
                                  "low_large", "low_mid", "low_small",
                                  "medium_large", "medium_mid", "medium_small",
                                  "high_large", "high_mid", "high_small",
                                  "extreme_large", "extreme_mid", "extreme_small"],
                         help="使用预设参数组，会覆盖后续单独指定的参数" )

    # 原有参数（若指定了 preset，则默认值将被预设覆盖，但命令行传入的值优先级更高）
    parser.add_argument( "--threshold", type=float, default=0.50, help="开仓阈值" )
    parser.add_argument( "--period", type=int, default=None, help="持仓周期" )
    parser.add_argument( "--top_k", type=int, default=10, help="相似检索数量" )
    parser.add_argument( "--strategy_type", default=None, choices=["fixed", "signal"], help="策略类型" )
    parser.add_argument( "--fee_rate", type=float, default=0.0015, help="单边手续费率" )
    parser.add_argument( "--min_confidence", type=float, default=None, help="最低置信度过滤" )
    parser.add_argument( "--min_ret_5d", type=float, default=None, help="最低5日预期收益" )
    parser.add_argument( "--position_sizing", default="full", choices=["full", "signal"], help="仓位模式" )
    parser.add_argument( "--stop_loss", type=float, default=None, help="止损比例" )
    parser.add_argument( "--take_profit", type=float, default=None, help="止盈比例" )
    parser.add_argument( "--trailing_stop_pct", type=float, default=None, help="移动止损回撤比例" )
    parser.add_argument( "--take_profit_pct", type=float, default=None, help="目标止盈比例" )
    parser.add_argument( "--max_hold_days", type=int, default=None, help="最大持仓天数" )
    parser.add_argument( "--partial_exit_enabled", action="store_true", default=None, help="启用部分止盈" )

    args = parser.parse_args()

    # 确定最终参数：优先使用命令行传入值，其次使用预设值，最后使用硬编码默认值
    if args.preset:
        preset_map = ParamPresets.list_all_presets()
        base_params = preset_map.get( args.preset, ParamPresets.default() )
    else:
        base_params = BacktestParams()  # 使用 dataclass 默认值

    # 用命令行参数覆盖预设
    final_params = base_params.to_dict()
    for key in final_params.keys():
        if hasattr( args, key ):
            arg_val = getattr( args, key )
            if arg_val is not None:
                final_params[key] = arg_val

    run_backtest(
        feature_file=args.file,
        **final_params
    )

if __name__ == "__main__":
    main()