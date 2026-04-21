
---

# Mizarα 数据下载与预处理指南

本脚本 `scripts/download_data.py` 用于获取 A 股日线行情数据并计算技术指标，为 Mizarα 的向量库构建与策略回测提供数据基础。

> ⚠️ **重要声明**：本脚本依赖的 [mootdx](https://github.com/bopo/mootdx) 库采用**非商业使用许可**。Mizarα 项目本身采用 Apache 2.0 协议，但您通过本脚本获取数据时需自行遵守 mootdx 的开源协议要求。**严禁将本脚本用于任何商业用途**。若需商业场景使用，请替换为合法授权的商业数据源（如 Tushare Pro、万得、聚宽等）。

---

## 1. 基本用法

```bash
# 下载最新 800 条数据，计算指标并保存
python scripts/download_data.py 600487

# 指定条数和起始偏移（从 offset=0 开始取 330 条）
python scripts/download_data.py 002149 --count 330 --offset 0

# 只下载行情，不计算指标
python scripts/download_data.py 600036 --no-indicators

# 只计算指标（假设行情已存在）
python scripts/download_data.py 002415 --no-quote

# 详细日志输出
python scripts/download_data.py 600519 -v
```

---

## 2. 文件存储位置

所有存储路径在 `config/system_config.yaml` 中定义，关键配置项如下：

```yaml
data_storage:
  quote_path: ./storage/quotes          # 原始行情数据（CSV/Parquet）
  indicator_path: ./storage/indicators  # 计算后的技术指标数据
  backtests: ./storage/backtest         # 回测专用数据（需用户自行放置）
  out_dir: ./storage/out                # 回测输出图表与报告
  format: "csv"                         # 存储格式（csv / parquet）
```

**文件名格式**：
- 行情数据：`{symbol}_{offset}_{start_date}_{end_date}.{format}`
- 指标数据：`{symbol}_{offset}_indicators_full.{format}`

---

## 3. 数据处理流程图

```
┌─────────────────┐
│  download_data  │  调用 mootdx 获取日线
│     .py         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 行情数据保存    │  → storage/quotes/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 指标计算        │  52 个技术指标（TA-Lib）
│ (IndicatorCalc) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 指标数据保存    │  → storage/indicators/
└─────────────────┘
```

---

## 4. 防止过拟合的数据处理要点

Mizarα 基于向量相似性检索，回测结果的可靠性高度依赖于数据处理的严谨性。请务必遵循以下规范：

### 4.1 严格的时间切分

| 数据用途 | 允许使用的时间范围 | 说明 |
| :--- | :--- | :--- |
| **训练 PCA / Scaler** | **必须早于**回测开始日期 | 用于降维和标准化的模型参数，只能用历史数据拟合，回测期间固定不变 |
| **构建向量库** | 可包含回测开始前的全部历史 | 若回测标的自身数据在库中，必须启用日期过滤或排除自身 |
| **回测数据** | 回测区间内的行情 | 逐日模拟，不得使用当日之后的任何信息 |

**错误示例**：在全部历史数据（含回测期）上拟合 PCA，再用于回测 → **严重过拟合**。

### 4.2 向量库构建时的安全选项

| 场景 | 推荐配置 |
| :--- | :--- |
| 单标的严谨回测 | 构建向量库时**排除该标的的全部数据** |
| 全市场批量回测 | 使用 ChromaDB 的 `where={"date": {"$lt": query_date}}` 动态过滤 |
| 内部快速参数探索 | 可全量构建，但回测收益仅用于相对比较，不可作为绝对预期 |

### 4.3 指标计算的前视偏差防范

- 所有技术指标（MA、RSI、MACD 等）在回测中必须使用 **`shift(1)`** 滞后一期的数据。
- 本脚本计算的指标为**全量历史值**，直接用于回测时需由回测引擎自行处理滞后逻辑。
- 指标计算后自动丢弃前 60 行（避免长周期指标产生 NaN），确保数据有效性。

### 4.4 复权数据的一致性

- 务必使用**前复权（qfq）** 数据，保证价格序列连续可比。
- 复权可能导致数据条数略多于请求的 `count`（通常多 1~3 条），本脚本已做截取处理，不影响后续使用。

### 4.5 训练与测试的物理隔离

建议将数据按用途分目录管理：

```
storage/
├── quotes/           # 原始行情（全量）
├── indicators/       # 计算后的指标（全量）
├── backtest/         # 回测专用数据（时间切分后的子集）
└── out/              # 回测输出（净值图、交易记录）
```

在回测前，从 `indicators/` 中按时间范围提取数据到 `backtest/`，确保回测引擎读取的是已切分的数据。

---

## 5. 批量下载示例

```bash
# Windows PowerShell
@("600519", "000858", "601318", "300750") | ForEach-Object {
    python scripts/download_data.py $_ --count 800
}

# Linux / macOS
for symbol in 600519 000858 601318 300750; do
    python scripts/download_data.py $symbol --count 800
done
```

---

## 6. 配置文件关键项说明

### 6.1 数据配置 (`config/system_config.yaml`)

```yaml
data:
  source_type: csv
  data_path: ./datas/raw/*.csv    # 训练用数据路径（用于构建向量库）
  period_type: day
  periods: [1, 3, 5]              # 计算未来 1/3/5 日收益率标签
  compute_extremes: true          # 是否计算未来最高/最低价
  close_column: close             # 收盘价列名
  validate_on_load: true          # 加载时自动验证数据完整性
```

### 6.2 特征工程配置

```yaml
features:
  config_path: ./config/feature_config.yaml   # 特征选择列表
  model_path: ./models                         # PCA/Scaler 模型保存路径
  auto_retrain: true                           # 是否在数据更新后自动重新训练
```

**注意**：`auto_retrain: true` 仅适用于向量库全量重建场景。在严谨回测中，应手动控制模型训练的时间范围。

---

## 7. 下一步

数据准备完成后：

1. **构建向量库**：`mizar build --market A_share`
2. **交互查询**：`mizar scan`
3. **运行回测**：`mizar backtest --symbol 000001`

详细说明请查阅 [快速入门指南](docs/public/guides/快速入门指南.md)。

---

## 8. 常见问题

### Q1: 提示 `mootdx` 连接超时
**A**: 检查网络是否能访问通达信数据源。若持续失败，可尝试更换网络环境或使用 `--no-quote` 跳过行情下载。

### Q2: 指标计算后行数减少
**A**: 正常现象。计算长周期指标（如 MA200）需要足够的历史数据，脚本会自动丢弃前 60 行无效数据。

### Q3: 如何验证数据是否可用于回测？
**A**: 运行 `mizar backtest --symbol 600519` 前，确保 `storage/backtest/` 中已放入时间切分后的数据，或使用 `mizar build` 时的排除自身功能。

---

**最后更新**：2026-04-21