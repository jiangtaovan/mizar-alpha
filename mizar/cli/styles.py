# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : styles.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: 颜色主题与视觉常量]
"""
# # mizar/cli/styles.py
# """Mizar CLI 视觉风格定义"""
#
from rich.style import Style
from rich.console import Console
from rich.theme import Theme
#
# 主色：青蓝（科技感）
MIZAR_CYAN = "#00B4D8"
# 辅色：星芒黄
MIZAR_GOLD = "#FFD166"
# 背景：深空黑
MIZAR_BG = "#0D1117"
# 错误红
MIZAR_RED = "#E5484D"
# 成功绿
MIZAR_GREEN = "#2EA043"
# 警告橙
MIZAR_ORANGE = "#F0883E"

# Rich 主题配置
MIZAR_THEME = Theme({
    "mizar.cyan": Style(color=MIZAR_CYAN),
    "mizar.gold": Style(color=MIZAR_GOLD),
    "mizar.success": Style(color=MIZAR_GREEN),
    "mizar.error": Style(color=MIZAR_RED),
    "mizar.warning": Style(color=MIZAR_ORANGE),
    "mizar.star": Style(color=MIZAR_GOLD, bold=True),
    "mizar.path": Style(color=MIZAR_CYAN, italic=True),
    "mizar.metric": Style(color=MIZAR_CYAN, bold=True),
})


MIZAR_THEME = Theme({
    "star": "bold cyan",
    "cyan": "cyan",
    "gold": "yellow",
    "success": "green",
    "error": "red",
})
# # 星图符号
STAR_SYMBOLS = ["·", "✧", "✦", "*", "★"]
PRIMARY_STAR = "✧"
SECONDARY_STAR = "✦"

# 创建控制台，显式启用标记解析，不强制终端
console = Console(theme=MIZAR_THEME, markup=True)