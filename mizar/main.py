# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : main.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00


"""Mizar CLI 主入口"""

from .cli.banner import print_banner
from .cli.commands import app


def main():
    print_banner()
    app()

if __name__ == "__main__":
    main()