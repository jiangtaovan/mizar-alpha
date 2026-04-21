# -*- coding: utf-8 -*-
# @Time    : 2026/4/16 
# @File    : strategy_pro.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00

"""
策略类重构版（智能平仓 + 动态仓位）：
- 支持多种平仓规则组合：信号消失、固定天数、移动止损、目标止盈、最大持仓天数
- 平仓可配置为部分止盈或全部平仓
- 与现有回测主程序无缝对接，默认行为保持原样
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ExitRule:
    """平仓规则配置"""
    signal_threshold: float          # 信号阈值（用于信号消失平仓）
    fixed_days: Optional[int] = None # 固定持仓天数
    trailing_stop_pct: Optional[float] = None  # 移动止损回撤百分比（如 0.05）
    take_profit_pct: Optional[float] = None    # 目标止盈百分比（如 0.10）
    max_hold_days: Optional[int] = None        # 最大持仓天数（强制平仓）
    partial_exit_pct: float = 1.0              # 部分平仓比例（0~1），1.0表示全平


class Strategy:
    """策略类（开仓过滤 + 灵活平仓 + 仓位管理）"""

    def __init__(
        self,
        threshold: float = 0.55,
        period: int = 5,
        strategy_type: str = 'fixed',
        fee_rate: float = 0.0,
        # 开仓过滤参数
        min_confidence: Optional[float] = None,
        min_ret_5d: Optional[float] = None,
        position_sizing: str = 'full',
        # 平仓规则参数（新增）
        trailing_stop_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        max_hold_days: Optional[int] = None,
        partial_exit_enabled: bool = False,
        # 兼容旧版止损止盈（将被内部映射）
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ):
        """
        参数说明：
            threshold         : 开仓信号阈值
            period            : 固定持仓周期（仅 strategy_type='fixed' 时使用）
            strategy_type     : 'fixed' 或 'signal'
            fee_rate          : 单边手续费率

            min_confidence    : 最低置信度要求（None 表示不过滤）
            min_ret_5d        : 最低5日预期收益（%），如 0.0
            position_sizing   : 'full' 全仓 / 'signal' 按信号强度比例

            trailing_stop_pct : 移动止损回撤比例（例如 0.05 表示从最高点回撤5%止损）
            take_profit_pct   : 固定目标止盈比例（例如 0.10 表示盈利10%止盈）
            max_hold_days     : 最大持仓天数，超过强制平仓
            partial_exit_enabled: 是否启用部分止盈（当 take_profit_pct 触发时只平一部分）
            stop_loss         : 固定止损比例（已弃用，建议使用 trailing_stop_pct）
            take_profit       : 固定止盈比例（已弃用，建议使用 take_profit_pct）
        """
        self.threshold = threshold
        self.period = period
        self.strategy_type = strategy_type
        self.fee_rate = fee_rate

        # 开仓过滤参数
        self.min_confidence = min_confidence
        self.min_ret_5d = min_ret_5d
        self.position_sizing = position_sizing

        # 平仓规则配置
        self.trailing_stop_pct = trailing_stop_pct
        self.take_profit_pct = take_profit_pct
        self.max_hold_days = max_hold_days
        self.partial_exit_enabled = partial_exit_enabled

        # 兼容旧参数：若提供了 stop_loss / take_profit，则映射到新参数（优先级低于新参数）
        if stop_loss is not None and trailing_stop_pct is None:
            self.trailing_stop_pct = stop_loss
        if take_profit is not None and take_profit_pct is None:
            self.take_profit_pct = take_profit

        # 持仓状态
        self.position = 0                     # 0 空仓，1 持仓
        self.current_position_pct = 0.0       # 当前持仓比例（0~1）
        self.entry_date = None
        self.entry_price = None               # 开仓均价
        self.max_price_since_entry = None     # 持仓期间最高价（用于移动止损）
        self.days_held = 0                    # 已持仓天数

        self.trades: List[Dict[str, Any]] = []

    # ---------- 开仓判断 ----------
    def _check_open_conditions(self, prediction: Dict[str, Any]) -> Tuple[bool, float]:
        """检查是否满足开仓条件，返回 (是否开仓, 建议仓位比例)"""
        if self.position > 0:
            return False, 0.0

        prob = prediction.get('up_probability', 0)
        if prob < self.threshold:
            return False, 0.0

        if self.min_confidence is not None:
            if prediction.get('confidence', 0) < self.min_confidence:
                return False, 0.0

        if self.min_ret_5d is not None:
            if prediction.get('avg_ret_5d', 0) < self.min_ret_5d:
                return False, 0.0

        # 计算建议仓位
        if self.position_sizing == 'full':
            pct = 1.0
        else:  # 'signal'
            strength = prob * prediction.get('confidence', 0.5)
            pct = max(0.3, min(1.0, strength * 1.5))

        return True, pct

    # ---------- 平仓判断 ----------
    def _check_exit_conditions(self, up_prob: float, current_price: float) -> Tuple[bool, float]:
        """
        检查平仓条件，返回 (是否触发平仓, 建议平仓比例)
        优先级：移动止损/止盈 > 信号消失/固定天数 > 最大持仓天数
        """
        if self.position == 0:
            return False, 0.0

        # 更新持仓期间最高价
        if self.max_price_since_entry is None or current_price > self.max_price_since_entry:
            self.max_price_since_entry = current_price

        # 1. 移动止损检查（基于最高点回撤）
        if self.trailing_stop_pct is not None and self.max_price_since_entry is not None:
            drawdown_from_peak = (self.max_price_since_entry - current_price) / self.max_price_since_entry
            if drawdown_from_peak >= self.trailing_stop_pct:
                return True, 1.0  # 全平

        # 2. 目标止盈检查
        if self.take_profit_pct is not None:
            profit_pct = (current_price - self.entry_price) / self.entry_price
            if profit_pct >= self.take_profit_pct:
                if self.partial_exit_enabled:
                    # 部分止盈：平掉一半仓位
                    return True, 0.5
                else:
                    return True, 1.0

        # 3. 信号消失或固定天数到期（使用 up_prob 判断）
        if self.strategy_type == 'fixed':
            if self.days_held >= self.period:
                return True, 1.0
        else:  # 'signal'
            if up_prob < self.threshold:
                return True, 1.0

        # 4. 最大持仓天数强制平仓
        if self.max_hold_days is not None and self.days_held >= self.max_hold_days:
            return True, 1.0

        return False, 0.0

    # ---------- 交易执行 ----------
    def step(self, prediction: Dict[str, Any], date, open_price) -> Tuple[float, bool]:
        """
        在 T+1 日开盘时执行策略。
        参数:
            prediction : 完整预测字典，必须包含 'up_probability'
        返回:
            (open_pct, close_flag)
            open_pct   : 开仓比例 (0~1)，0 表示不开仓
            close_flag : 是否有平仓动作 (True/False)，用于手续费计算
        """
        open_pct = 0.0
        close_flag = False
        up_prob = prediction.get('up_probability', 0)

        # ===== 持仓中：先检查平仓 =====
        if self.position == 1:
            should_exit, exit_pct = self._check_exit_conditions(up_prob, open_price)
            if should_exit:
                # 计算本次平仓部分的收益率
                ret = (open_price - self.entry_price) / self.entry_price
                actual_exit_pct = min(exit_pct, self.current_position_pct)

                self.trades.append({
                    'entry_date': self.entry_date,
                    'exit_date': date,
                    'entry_price': self.entry_price,
                    'exit_price': open_price,
                    'return': ret,
                    'position_pct': actual_exit_pct,
                    'exit_reason': self._get_exit_reason(up_prob, open_price)
                })

                # 减少持仓比例
                self.current_position_pct -= actual_exit_pct
                if self.current_position_pct <= 0.001:  # 视为全平
                    self._reset_position()
                    close_flag = True
                else:
                    close_flag = True  # 发生了部分平仓

                # 部分平仓后，不进行开仓判断，直接返回
                return 0.0, close_flag

        # ===== 空仓或仍有仓位：检查是否可以开仓（若全仓则不开） =====
        if self.position == 0:
            can_open, suggested_pct = self._check_open_conditions(prediction)
            if can_open:
                self.entry_date = date
                self.entry_price = open_price
                self.max_price_since_entry = open_price
                self.days_held = 1
                self.position = 1
                self.current_position_pct = suggested_pct
                open_pct = suggested_pct
                return open_pct, False

        # ===== 持仓中未触发平仓：增加持有天数 =====
        if self.position == 1:
            self.days_held += 1

        return 0.0, False

    def _get_exit_reason(self, up_prob: float, current_price: float) -> str:
        """返回平仓原因（用于记录）"""
        if self.trailing_stop_pct and self.max_price_since_entry:
            if (self.max_price_since_entry - current_price) / self.max_price_since_entry >= self.trailing_stop_pct:
                return 'trailing_stop'
        if self.take_profit_pct and (current_price - self.entry_price) / self.entry_price >= self.take_profit_pct:
            return 'take_profit'
        if self.strategy_type == 'fixed' and self.days_held >= self.period:
            return 'fixed_days'
        if self.strategy_type == 'signal' and up_prob < self.threshold:
            return 'signal_lost'
        if self.max_hold_days and self.days_held >= self.max_hold_days:
            return 'max_hold_days'
        return 'unknown'

    def _reset_position(self):
        """重置持仓状态"""
        self.position = 0
        self.current_position_pct = 0.0
        self.entry_date = None
        self.entry_price = None
        self.max_price_since_entry = None
        self.days_held = 0

    # ---------- 强制平仓（用于回测结束时） ----------
    def force_close(self, exit_date, exit_price):
        """以收盘价强制平仓剩余仓位"""
        if self.position == 1 and self.current_position_pct > 0:
            ret = (exit_price - self.entry_price) / self.entry_price
            self.trades.append({
                'entry_date': self.entry_date,
                'exit_date': exit_date,
                'entry_price': self.entry_price,
                'exit_price': exit_price,
                'return': ret,
                'position_pct': self.current_position_pct,
                'exit_reason': 'force_close'
            })
            self._reset_position()