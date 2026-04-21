# -*- coding: utf-8 -*-
# @Time    : 2026/3/28 
# @File    : strategy.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00
"""
策略类扩展版：
- 支持固定周期（fixed）和信号持续（signal）两种基础策略
- 新增止损止盈功能（可选），可与基础策略叠加使用
- 保留原有逻辑，新增参数默认不启用，兼容旧代码
"""


# strategy.py 关键修改
class Strategy:
    def __init__(self, threshold, period, strategy_type='fixed', fee_rate=0.0,
                 stop_loss=None, take_profit=None,
                 min_confidence=None, min_ret_5d=None, position_sizing='full'):
        """
        参数：
            threshold : float   开仓信号阈值（0~1）
            period    : int     持仓周期（仅 fixed 模式使用）
            strategy_type : str 策略类型，'fixed' 固定天数 / 'signal' 信号持续
            fee_rate  : float   单边手续费率（如 0.001 = 0.1%）
            stop_loss : float   止损百分比（如 0.05 = 5%），None 表示不启用
            take_profit : float 止盈百分比，None 表示不启用
        """
        self.threshold = threshold
        self.period = period
        self.strategy_type = strategy_type
        self.fee_rate = fee_rate
        self.stop_loss = stop_loss
        self.take_profit = take_profit

        self.position = 0          # 昨日收盘时的持仓状态
        self.entry_date = None
        self.entry_price = None
        self.days_held = 1         #开仓天数从第一天用1起算
        self.trades = []
        self.min_confidence = min_confidence
        self.min_ret_5d = min_ret_5d
        self.position_sizing = position_sizing  # 'full' 或 'signal'
        self.current_position_pct = 0.0  # 当前持仓比例 (0~1)

    def should_open(self, prediction):
        """基于多维信号判断是否开仓，并返回建议仓位比例"""
        if self.position > 0:
            return 0.0

        prob = prediction.get( 'up_probability', 0 )
        if prob < self.threshold:
            return 0.0

        if self.min_confidence is not None:
            if prediction.get( 'confidence', 0 ) < self.min_confidence:
                return 0.0

        if self.min_ret_5d is not None:
            if prediction.get( 'avg_ret_5d', 0 ) < self.min_ret_5d:
                return 0.0

        # 计算建议仓位比例
        if self.position_sizing == 'full':
            return 1.0
        else:  # 'signal'
            # 基础仓位 = 概率 * 置信度，可映射到 [0.3, 1.0] 区间避免过轻仓
            base = prob * prediction.get( 'confidence', 0.5 )
            # 约束到 0.3 ~ 1.0
            return max( 0.3, min( 1.0, base * 1.5 ) )

    def step(self, prediction, date, open_price):
        """
        在 T+1 日开盘时执行策略。
        prediction: 完整预测字典（包含 up_probability 等）
        返回 (open_pct, close_flag)
            open_pct: 开仓比例 (0~1)，0 表示不开仓
            close_flag: 是否平仓 (True/False)
        """
        open_pct = 0.0
        close_flag = False
        up_prob = prediction.get( 'up_probability', 0 )  # 用于平仓判断

        # 1. 止损止盈检查（基于开盘价和当前持仓比例）
        if self.position == 1:
            if self.should_stop_out( open_price ):
                ret = (open_price - self.entry_price) / self.entry_price
                self.trades.append( {
                    'entry_date': self.entry_date,
                    'exit_date': date,
                    'entry_price': self.entry_price,
                    'exit_price': open_price,
                    'return': ret,
                    'position_pct': self.current_position_pct,
                } )
                self.position = 0
                self.current_position_pct = 0.0
                close_flag = True
                return 0.0, close_flag

        # 2. 常规平仓
        if self.position == 1 and self.should_close_by_signal_or_days( up_prob ):
            ret = (open_price - self.entry_price) / self.entry_price
            self.trades.append( {
                'entry_date': self.entry_date,
                'exit_date': date,
                'entry_price': self.entry_price,
                'exit_price': open_price,
                'return': ret,
                'position_pct': self.current_position_pct,
            } )
            self.position = 0
            self.current_position_pct = 0.0
            close_flag = True
            return 0.0, close_flag

        # 3. 开仓判断（空仓时）
        if self.position == 0:
            suggested_pct = self.should_open( prediction )
            if suggested_pct > 0:
                self.entry_date = date
                self.entry_price = open_price
                self.days_held = 1
                self.position = 1
                self.current_position_pct = suggested_pct
                return suggested_pct, False

        # 4. 持仓中，增加持有天数
        if self.position == 1:
            self.days_held += 1

        return 0.0, close_flag

#
# class Strategy:
#     """策略类（固定周期、信号持续、支持止损止盈）"""
#     def __init__(self, threshold, period, strategy_type='fixed', fee_rate=0.0,
#                  stop_loss=None, take_profit=None):
#         """
#         参数：
#             threshold : float   开仓信号阈值（0~1）
#             period    : int     持仓周期（仅 fixed 模式使用）
#             strategy_type : str 策略类型，'fixed' 固定天数 / 'signal' 信号持续
#             fee_rate  : float   单边手续费率（如 0.001 = 0.1%）
#             stop_loss : float   止损百分比（如 0.05 = 5%），None 表示不启用
#             take_profit : float 止盈百分比，None 表示不启用
#         """
#         self.threshold = threshold
#         self.period = period
#         self.strategy_type = strategy_type
#         self.fee_rate = fee_rate
#         self.stop_loss = stop_loss
#         self.take_profit = take_profit
#
#         self.position = 0          # 昨日收盘时的持仓状态
#         self.entry_date = None
#         self.entry_price = None
#         self.days_held = 1         #开仓天数从第一天用1起算
#         self.trades = []
#
    # def should_open(self, up_prob):
    #     """判断是否开仓（基于信号）"""
    #     return self.position == 0 and up_prob >= self.threshold

    def should_close_by_signal_or_days(self, up_prob):
        """判断是否因信号或固定天数平仓（不含止损止盈）"""
        if self.position == 0:
            return False
        if self.strategy_type == 'fixed':
            return self.days_held >= self.period
        else:  # signal
            return up_prob < self.threshold

    def should_stop_out(self, current_price):
        """检查止损止盈条件（基于当前价格与入场价）"""
        if self.position == 0:
            return False
        if self.entry_price is None:
            return False
        pnl = (current_price - self.entry_price) / self.entry_price
        if self.stop_loss is not None and pnl <= -self.stop_loss:
            return True
        if self.take_profit is not None and pnl >= self.take_profit:
            return True
        return False
#
#     def step(self, up_prob, date, open_price):
#         """
#         在 T+1 日开盘时执行策略（基于 T 日的 up_prob）
#         返回 (open_flag, close_flag)
#         优先级：止损止盈 > 信号/天数平仓 > 开仓
#         """
#         open_flag = False
#         close_flag = False
#
#         # 1. 已有持仓，先检查止损止盈（基于当前开盘价）
#         if self.position == 1:
#             if self.should_stop_out(open_price):
#                 ret = (open_price - self.entry_price) / self.entry_price
#                 self.trades.append({
#                     'entry_date': self.entry_date,
#                     'exit_date': date,
#                     'entry_price': self.entry_price,
#                     'exit_price': open_price,
#                     'return': ret,
#                 })
#                 self.position = 0
#                 self.entry_date = None
#                 self.entry_price = None
#                 close_flag = True
#                 # 止损止盈平仓后，本日不再开新仓（避免同一天反复交易）
#                 return open_flag, close_flag
#
#         # 2. 检查常规平仓（信号消失或固定天数到期）
#         if self.position == 1 and self.should_close_by_signal_or_days(up_prob):
#             ret = (open_price - self.entry_price) / self.entry_price
#             self.trades.append({
#                 'entry_date': self.entry_date,
#                 'exit_date': date,
#                 'entry_price': self.entry_price,
#                 'exit_price': open_price,
#                 'return': ret,
#             })
#             self.position = 0
#             self.entry_date = None
#             self.entry_price = None
#             close_flag = True
#             return open_flag, close_flag
#
#         # 3. 开仓（空仓且满足信号）
#         if self.position == 0 and self.should_open(up_prob):
#             self.entry_date = date
#             self.entry_price = open_price
#             self.days_held = 1
#             self.position = 1
#             open_flag = True
#             return open_flag, close_flag
#
#         # 4. 无交易，但持仓中需增加持有天数
#         if self.position == 1:
#             self.days_held += 1
#
#         return open_flag, close_flag