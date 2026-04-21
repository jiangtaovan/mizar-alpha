# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : main.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""Mizar CLI 主入口"""

from .banner import print_banner
from .commands import app
from .backtest import backtest_cmd


def main():
    print_banner()
    app()
    main.add_command( backtest_cmd )


if __name__ == "__main__":
    main()