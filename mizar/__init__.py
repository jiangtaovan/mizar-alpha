# -*- coding: utf-8 -*-
# @Time    : 2026/4/22
# @File    : __init__.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00
"""
Mizarα (mizar-alpha) — 基于向量相似性检索的量化策略框架

Mizarα 将市场技术指标编码为高维向量，通过向量数据库检索历史上最相似的“市场状态”，
并基于相似状态的未来走势生成可解释的预测信号。与黑盒模型不同，每一次决策都能找到
真实的历史参照。

核心特性：
    - 端到端流程：数据加载 → 50+ 个技术指标计算 → PCA 降维 → ChromaDB 向量存储
      → 相似检索 → 预测统计
    - 交互式 CLI：`mizar scan` 实时查询个股预测，直观展示相似历史状态
    - RESTful API：FastAPI 提供查询与健康检查接口
    - 模块化设计：特征工程、向量库、回测、服务层解耦，易于扩展

主要模块：
    - mizar.cli        : 命令行入口（mizar 命令）
    - mizar.back       : 回测引擎封装
    - mizar.api        : FastAPI 服务 预留
    - mizar.data       : 行情获取与处理

使用示例：
    import mizar
    print(mizar.__version__)

    # CLI 交互查询
    # $ mizar scan

项目主页：https://github.com/jiangtaovan/mizar-alpha
许可证：Apache License 2.0
"""


# Copyright 2026 Chiang Tao
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


__version__ = "0.2.0.dev1"
__author__ = "Chiang Tao"
__project_uuid__ = "25da688b-5e73-58ce-83f0-d9f4387632b2"