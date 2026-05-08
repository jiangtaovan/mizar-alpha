# -*- coding: utf-8 -*-
# @Time    : 2026/5/8 
# @File    : volume_utils.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00

# mizar/utils/volume_utils.py
"""A股日内成交量动态修正工具，独立于任何业务模块"""
import hashlib
from datetime import datetime, time
from random import random
from typing import Optional


class VolumeAdjuster:
    """日内成交量乘数计算器，基于U型分布假设，避免误差导致信号失真"""

    # 默认参数（可根据个股/市场微观结构调整）
    TOTAL_MINUTES = 240
    OPEN_MINUTES = 30
    CLOSE_MINUTES = 15           # 尾盘集中放量时间缩短至15分钟，建议[15~20]
    OPEN_RATIO = 0.25
    CLOSE_RATIO = 0.20           # 尾盘总成交占比略低于开盘建议[0.15~0.25]
    MAX_MULTIPLIER = 5.0
    MIN_EFFECTIVE_MINUTE = 5

    @staticmethod
    def get_current_trading_minute(handle_lunch_break: bool = True) -> Optional[int]:
        """
        返回当前 A 股交易分钟序号 (0~239)
        - 0 → 9:30 第一分钟
        - 119 → 上午最后一分钟 (11:29)
        - 120 → 13:00 第一分钟
        - 239 → 下午最后一分钟 (14:59)
        - 非交易时段返回 None (若 handle_lunch_break=True，午休返回119)
        """
        now = datetime.now()
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        current_time = now.time()

        if morning_start <= current_time <= morning_end:
            delta = (now.hour - 9) * 60 + now.minute - 30
            return delta if delta < 120 else 119

        elif current_time < afternoon_start and handle_lunch_break:
            return 119  # 午休期间视为上午最后一分钟

        elif afternoon_start <= current_time <= afternoon_end:
            delta = (now.hour - 13) * 60 + now.minute
            total = 120 + delta
            return total if total < 240 else 239

        return -1

    @staticmethod
    def _base_multiplier(
        t: int,
        total_minutes: int = TOTAL_MINUTES,
        open_minutes: int = OPEN_MINUTES,
        close_minutes: int = CLOSE_MINUTES,
        open_ratio: float = OPEN_RATIO,
        close_ratio: float = CLOSE_RATIO,
        max_multiplier: float = MAX_MULTIPLIER,
        min_effective_minute: int = MIN_EFFECTIVE_MINUTE,
    ) -> float:
        """
        根据当前分钟 t (0-indexed, 9:30=0) 计算成交量乘数 M，
        使得 V_full ≈ V_cum * M
        """
        if t < min_effective_minute:
            return max_multiplier

        mid_ratio = 1.0 - open_ratio - close_ratio
        mid_dur = total_minutes - open_minutes - close_minutes

        if t < open_minutes:
            cum_ratio = t * open_ratio / open_minutes
        elif t < total_minutes - close_minutes:
            cum_ratio = open_ratio + (t - open_minutes) * mid_ratio / mid_dur
        else:
            close_dur_passed = t - (total_minutes - close_minutes)
            cum_ratio = open_ratio + mid_ratio + close_dur_passed * close_ratio / close_minutes

        if cum_ratio < 1.0 / max_multiplier:
            return max_multiplier
        return 1.0 / cum_ratio


    @staticmethod
    def volume_multiplier(
            t: int,
            symbol: str = "",  # 新增：用于生成可复现种子
            trade_date: str = "",  # 新增：日期，格式"YYYY-MM-DD"
            enable_noise: bool = False,  # 新增：是否启用噪声
            noise_range: float = 0.02,  # 噪声幅度 ±2%
            **kwargs  # 兼容原有参数
    ) -> float:
        # 1. 计算基准乘数（原逻辑）
        base_mult =VolumeAdjuster._base_multiplier( t, **kwargs )

        # 2. 如果不启用噪声，直接返回
        if not enable_noise:
            return base_mult

        # 3. 生成基于 symbol+date 的固定种子，确保可复现
        if symbol and trade_date:
            seed_str = f"{symbol}_{trade_date}"
            seed = int( hashlib.md5( seed_str.encode() ).hexdigest(), 16 ) % (2 ** 31)
            random.seed( seed )

        # 4. 乘数上加噪声（相对百分比）
        noise = random.uniform( -noise_range, noise_range )
        adjusted_mult = base_mult * (1.0 + noise)

        # 5. 防止乘数偏离太远
        adjusted_mult = max( 1.0, min( adjusted_mult, kwargs.get( 'max_multiplier', 5.0 ) ) )
        return adjusted_mult