
# -*- coding: utf-8 -*-
# @Time    : 2026/04/16
# @File    : param_presets.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
股票分类参数预设管理器
根据股票活跃度和市值规模提供默认回测参数组合
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class ActivityLevel(Enum):
    """活跃度分类"""
    LOW = "low"          # 低波动、低换手（如银行、公用事业）
    MEDIUM = "medium"    # 中等波动（如沪深300成分股）
    HIGH = "high"        # 高波动、高换手（如题材股、科创板次新）
    EXTREME = "extreme"  # 极端波动（如妖股、量化密集标的）


class CapSize(Enum):
    """市值规模分类"""
    LARGE = "large"      # 大盘股（>500亿）
    MID = "mid"          # 中盘股（100-500亿）
    SMALL = "small"      # 小盘股（<100亿）


@dataclass
class BacktestParams:
    """回测参数容器"""
    # 核心参数
    threshold: float = 0.55
    period: int = 2
    top_k: int = 10
    strategy_type: str = "signal"
    fee_rate: float = 0.0015

    # 过滤参数
    min_confidence: Optional[float] = 0.4
    min_ret_5d: Optional[float] = 0.0

    # 仓位管理
    position_sizing: str = "signal"
    stop_loss: Optional[float] = 0.03
    take_profit: Optional[float] = None

    # 动态出场
    trailing_stop_pct: Optional[float] = 0.05
    take_profit_pct: Optional[float] = 0.10
    max_hold_days: Optional[int] = None
    partial_exit_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，方便 **kwargs 传递"""
        return {
            'threshold': self.threshold,
            'period': self.period,
            'top_k': self.top_k,
            'strategy_type': self.strategy_type,
            'fee_rate': self.fee_rate,
            'min_confidence': self.min_confidence,
            'min_ret_5d': self.min_ret_5d,
            'position_sizing': self.position_sizing,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'trailing_stop_pct': self.trailing_stop_pct,
            'take_profit_pct': self.take_profit_pct,
            'max_hold_days': self.max_hold_days,
            'partial_exit_enabled': self.partial_exit_enabled,
        }


class ParamPresets:
    """
    参数预设管理器
    使用方式：
        params = ParamPresets.get_preset(ActivityLevel.HIGH, CapSize.MID)
        run_backtest(**params.to_dict())
    """

    # ========== 预设定义 ==========
    # 格式: (活跃度, 市值) -> BacktestParams

    @classmethod
    def get_preset(cls, activity: ActivityLevel, cap: CapSize) -> BacktestParams:
        """根据活跃度和市值获取预设参数"""
        key = (activity, cap)

        # ----- 低活跃度（蓝筹、公用事业）-----
        if activity == ActivityLevel.LOW:
            if cap == CapSize.LARGE:
                return BacktestParams(
                    threshold=0.45,           # 降低门槛，增加交易机会
                    period=3,                 # 慢牛中可持股稍长
                    strategy_type="fixed",    # 固定周期，避免频繁进出
                    min_confidence=0.50,
                    position_sizing="full",   # 低波动下可全仓
                    trailing_stop_pct=0.03,   # 窄止损
                    take_profit_pct=0.04,     # 微利即走
                    max_hold_days=5,
                )
            elif cap == CapSize.MID:
                return BacktestParams(
                    threshold=0.45,
                    period=2,
                    strategy_type="signal",
                    min_confidence=0.50,
                    position_sizing="signal",
                    trailing_stop_pct=0.03,
                    take_profit_pct=0.04,
                    max_hold_days=5,
                )
            else:  # SMALL
                return BacktestParams(
                    threshold=0.50,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.55,
                    position_sizing="signal",
                    trailing_stop_pct=0.04,
                    take_profit_pct=0.05,
                    max_hold_days=3,
                )

        # ----- 中等活跃度（主流成分股）-----
        elif activity == ActivityLevel.MEDIUM:
            if cap == CapSize.LARGE:
                return BacktestParams(
                    threshold=0.55,
                    period=2,
                    strategy_type="signal",
                    min_confidence=0.55,
                    position_sizing="signal",
                    trailing_stop_pct=0.04,
                    take_profit_pct=0.06,
                    max_hold_days=7,
                )
            elif cap == CapSize.MID:
                return BacktestParams(
                    threshold=0.55,
                    period=2,
                    strategy_type="signal",
                    min_confidence=0.55,
                    position_sizing="signal",
                    trailing_stop_pct=0.05,
                    take_profit_pct=0.08,
                    partial_exit_enabled=True,   # 中等波动下分批止盈
                )
            else:  # SMALL
                return BacktestParams(
                    threshold=0.58,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.60,
                    position_sizing="signal",
                    trailing_stop_pct=0.05,
                    take_profit_pct=0.10,
                    partial_exit_enabled=True,
                )

        # ----- 高活跃度（题材、科创）-----
        elif activity == ActivityLevel.HIGH:
            if cap == CapSize.LARGE:
                return BacktestParams(
                    threshold=0.58,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.60,
                    position_sizing="signal",
                    trailing_stop_pct=0.06,
                    take_profit_pct=0.12,
                    partial_exit_enabled=True,
                )
            elif cap == CapSize.MID:
                return BacktestParams(
                    threshold=0.60,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.65,
                    min_ret_5d=0.5,              # 要求短期预期为正
                    position_sizing="signal",
                    trailing_stop_pct=0.07,
                    take_profit_pct=0.15,
                    partial_exit_enabled=True,
                    max_hold_days=10,
                )
            else:  # SMALL
                return BacktestParams(
                    threshold=0.62,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.65,
                    min_ret_5d=0.5,
                    position_sizing="signal",
                    trailing_stop_pct=0.08,
                    take_profit_pct=0.18,
                    partial_exit_enabled=True,
                    max_hold_days=12,
                )

        # ----- 极端活跃度（妖股、量化密集）-----
        else:  # ActivityLevel.EXTREME
            if cap == CapSize.SMALL:
                return BacktestParams(
                    threshold=0.65,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.70,
                    min_ret_5d=1.0,
                    position_sizing="signal",
                    trailing_stop_pct=0.10,       # 放宽止损，容忍巨震
                    take_profit_pct=0.20,
                    partial_exit_enabled=True,
                    max_hold_days=15,
                )
            else:
                # 极端活跃但非小盘较少见，按高活跃处理
                return BacktestParams(
                    threshold=0.60,
                    period=1,
                    strategy_type="signal",
                    min_confidence=0.65,
                    position_sizing="signal",
                    trailing_stop_pct=0.08,
                    take_profit_pct=0.15,
                    partial_exit_enabled=True,
                )

    # ========== 便捷别名 ==========
    @classmethod
    def blue_chip(cls) -> BacktestParams:
        """大盘蓝筹股（低活跃，大盘）"""
        return cls.get_preset(ActivityLevel.LOW, CapSize.LARGE)

    @classmethod
    def growth_mid(cls) -> BacktestParams:
        """成长中盘股（中等活跃，中盘）"""
        return cls.get_preset(ActivityLevel.MEDIUM, CapSize.MID)

    @classmethod
    def tech_small(cls) -> BacktestParams:
        """科技小盘股（高活跃，小盘）"""
        return cls.get_preset(ActivityLevel.HIGH, CapSize.SMALL)

    @classmethod
    def quant_active(cls) -> BacktestParams:
        """量化活跃标的（极端活跃，小盘）"""
        return cls.get_preset(ActivityLevel.EXTREME, CapSize.SMALL)

    @classmethod
    def default(cls) -> BacktestParams:
        """通用默认参数（中等活跃、中盘）"""
        return cls.get_preset(ActivityLevel.MEDIUM, CapSize.MID)

    @classmethod
    def list_all_presets(cls) -> Dict[str, BacktestParams]:
        """返回所有预设的字典，便于遍历测试"""
        presets = {}
        for act in ActivityLevel:
            for cap in CapSize:
                name = f"{act.value}_{cap.value}"
                presets[name] = cls.get_preset(act, cap)
        presets['blue_chip'] = cls.blue_chip()
        presets['growth_mid'] = cls.growth_mid()
        presets['tech_small'] = cls.tech_small()
        presets['quant_active'] = cls.quant_active()
        presets['default'] = cls.default()
        return presets