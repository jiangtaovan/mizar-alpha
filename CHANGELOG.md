您提供的这份 `v1.0.0` 发布说明是项目早期内部 MVP 的详细记录，非常珍贵。我们可以将其**精简合并**到 `CHANGELOG.md` 的 `[0.1.0]` 版本中，作为首次发布的完整描述。

以下是为您融合后的 **最终版 `CHANGELOG.md`**，保留了您认为重要的技术细节，同时符合 Keep a Changelog 规范并与当前项目名称、许可证保持一致。

---

```markdown
# Changelog

All notable changes to Mizarα will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- 置信度仓位映射（按置信度分段调整持仓比例）
- 基于上下行分位数的动态止盈止损
- 样本一致性过滤器（减少低质量信号）
- 最小持仓周期与滞后退出机制

### Changed
- 项目正式更名为 **Mizarα**，PyPI 包名为 `mizar-alpha`
- 许可证切换为 Apache License 2.0
- 品牌标识更新：ASCII Logo 中加入 `Mizarα` 字样

---

## [0.2.0.dev1] - 2026-04-21

### Added
- Ed25519 数字签名校验机制，保护品牌完整性
- `pyproject.toml` 中的 `[tool.mizar]` 防伪溯源区块
- 回测引擎支持移动止损（`trailing_stop_pct`）
- 交互查询新增置信度、VaR、上行潜力等统计输出
- 支持通过 `mizar scan` 偏移天数查询历史状态

### Changed
- 统一项目元数据，`__version__` 改为 `0.2.0.dev1`
- 优化 `banner.py` 显示，增加版本与版权信息
- 重构 `data_fetcher` 支持前复权（`adjust='qfq'`）
- 升级 `click` 依赖至 >=8.1.0 解决兼容性问题

### Fixed
- 修复复权数据中 NaT 索引导致的保存错误
- 修复 `SettingWithCopyWarning` 警告
- 修复 `mizar` 命令在部分环境下无法运行的依赖问题

---

## [0.1.0] - 2026-03-25

### 🎉 首次发布 (MVP)

市场状态向量数据库 MVP 版本正式发布，标志着 Mizarα 项目从概念走向落地。

#### ✨ 核心模块

- **数据加载**：支持 CSV/JSON 导入，自动计算未来收益标签（1日/5日收益率、最大回撤、分类标签），内置数据验证与清洗。
- **特征工程**：精选 45 个技术指标，支持 Min-Max / Z-score 归一化，PCA 降维（保留 95% 方差），模型持久化。
- **向量数据库**：基于 ChromaDB 实现持久化存储、余弦相似度检索、元数据过滤及批量增量更新。
- **预测服务**：提供简单平均、距离加权、时效性加权等多种聚合方法，输出预期收益、上涨概率、标签分布及风险统计。
- **RESTful API**：FastAPI 构建，提供 `/query`、`/health` 端点，自带 Swagger UI 文档，支持可选 API Key 认证及 CORS。
- **工具脚本**：`build_db.py`（全量构建）、`update_db.py`（增量更新）、`backtest.py`（滚动窗口回测）、`generate_test_data.py`、`validate_data.py`。
- **测试套件**：基于 pytest 的核心模块单元测试，覆盖率 > 85%。
- **Docker 部署**：提供 Dockerfile 与 docker-compose.yml，支持一键部署。

#### 📊 技术指标覆盖

首批纳入 45 个标准化指标，涵盖：
- **趋势**：MA_SMA_5/20/50/200, MA_EMA_12/26, ADX, SAR
- **动量**：RSI_6/12/24, MACD, CCI, ROC, MOM, WILLR
- **波动率**：ATR, NATR, TRANGE, BBANDS
- **成交量**：VOLUME_RATIO, OBV, CMF, MFI, VWAP
- **K线形态**：DOJI, HAMMER, ENGULFING, MORNING/EVENING STAR 等
- **增强指标**：AROON, DMI, HV_20/60, EFFICIENCY_RATIO

#### 🚀 性能基准

| 指标 | 实测值 |
| :--- | :--- |
| 单次查询响应 (P95) | ~200ms |
| 全量构建 (1000 条) | ~3 分钟 |
| 增量更新 (单日) | ~30 秒 |
| 单元测试覆盖率 | >85% |

#### 📁 交付内容

- 核心源码模块：`data/`, `features/`, `vector_db/`, `services/`, `api/`
- 配置与脚本：`config/`, `scripts/`
- 文档：`README.md`, `QUICKSTART.md`, `docs/API_EXAMPLES.md`, `docs/DEPLOYMENT_CHECKLIST.md`
- 示例数据：`sample_data.csv`

---

## 📅 版本链接

[Unreleased]: https://github.com/jiangtaovan/mizar-alpha/compare/v0.2.0.dev1...HEAD
[0.2.0.dev1]: https://github.com/jiangtaovan/mizar-alpha/compare/v0.1.0...v0.2.0.dev1
[0.1.0]: https://github.com/jiangtaovan/mizar-alpha/releases/tag/v0.1.0
```

---