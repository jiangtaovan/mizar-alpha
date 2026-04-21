# Mizarα API 使用指南

> 详细的API接口文档和使用示例

---

## 📋 概述

Mizarα 提供三种API使用方式：

1. **命令行API** - 通过 `mizar` 命令
2. **Python API** - 通过 `import mizar`
3. **RESTful API** - 通过 HTTP 接口

---

## 🔧 命令行 API

### 基础命令

```bash
# 查看版本
mizar --version

# 查看帮助
mizar --help

# 子命令列表
mizar <command> --help
```

### 数据管理

```bash
# 构建向量数据库
mizar build-db \
  --config config/system_config.yaml \
  --force  # 强制重建

# 增量更新数据
mizar update \
  --date 2026-04-21 \
  --config config/system_config.yaml

# 验证数据
mizar validate data/raw/*.csv --strict
```

### 预测服务

```bash
# 单股预测
mizar predict \
  --stock 000001 \
  --date 2026-04-21 \
  --top-k 10 \
  --weight distance

# 批量预测
mizar batch-predict \
  --stocks 000001,000002,600519 \
  --output predictions.csv
```

### 回测

```bash
# 运行回测
mizar backtest \
  --config config/backtest.yaml \
  --start-date 2025-01-01 \
  --end-date 2026-04-21 \
  --output results/backtest.csv

# 回测分析
mizar analyze-backtest \
  --input results/backtest.csv \
  --report results/analysis.md
```

### 服务部署

```bash
# 启动API服务
mizar serve \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4

# 后台运行
mizar serve --daemon
```

---

## 🐍 Python API

### 核心模块

```python
from mizar import (
    PredictionService,    # 预测服务
    BacktestEngine,       # 回测引擎
    VectorDB,            # 向量数据库
    FeatureEngineer      # 特征工程
)
```

### 预测服务

```python
from mizar import PredictionService

# 初始化
service = PredictionService(
    config_path='config/system_config.yaml'
)

# 单股预测
result = service.predict(
    symbol='000001',
    date='2026-04-21',
    top_k=10,
    weighting_method='distance'
)

# 访问结果
print(f"上涨概率: {result.up_probability:.2%}")
print(f"平均收益: {result.avg_return:.2f}%")
print(f"相似样本数: {result.sample_size}")

# 查看详细相似状态
for state in result.similar_states[:3]:
    print(f"日期: {state.date}, 距离: {state.distance:.4f}")
    print(f"后续收益: {state.future_return:.2f}%")
```

### 批量预测

```python
symbols = ['000001', '000002', '600519']
results = {}

for symbol in symbols:
    results[symbol] = service.predict(
        symbol=symbol,
        date='2026-04-21',
        top_k=10
    )

# 筛选高置信度信号
high_conf = [
    sym for sym, res in results.items()
    if res.up_probability > 0.65
]
```

### 回测引擎

```python
from mizar import BacktestEngine

# 初始化回测引擎
engine = BacktestEngine(
    config_path='config/backtest.yaml'
)

# 运行回测
results = engine.run(
    start_date='2025-01-01',
    end_date='2026-04-21',
    initial_capital=1000000
)

# 查看绩效指标
print(f"总收益率: {results.total_return:.2%}")
print(f"年化收益率: {results.annual_return:.2%}")
print(f"最大回撤: {results.max_drawdown:.2%}")
print(f"夏普比率: {results.sharpe_ratio:.2f}")

# 保存结果
results.to_csv('backtest_results.csv')
results.plot_equity_curve()
```

### 向量数据库

```python
from mizar import VectorDB

# 加载数据库
db = VectorDB('data/chroma_db')

# 查询相似状态
results = db.query(
    features={
        'MA_SMA_5': 10.5,
        'MA_SMA_20': 10.2,
        'RSI_RSI_12': 55.3
    },
    top_k=10
)

# 获取统计信息
stats = db.get_stats()
print(f"总记录数: {stats.total_records}")
print(f"股票数量: {stats.symbol_count}")
print(f"日期范围: {stats.date_range}")
```

### 特征工程

```python
from mizar import FeatureEngineer

# 初始化
engineer = FeatureEngineer(
    config_path='config/feature_config.yaml'
)

# 处理数据
processed = engineer.transform(raw_data)

# 查看选择的特征
print(f"特征数量: {len(engineer.selected_features)}")
print(f"PCA维度: {engineer.pca_components}")
```

---

## 🌐 RESTful API

### 启动服务

```bash
mizar serve --port 8000
```

API文档: http://localhost:8000/docs

### 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/query` | POST | 查询相似状态 |
| `/predict` | POST | 执行预测 |
| `/backtest` | POST | 运行回测 |
| `/stats` | GET | 数据库统计 |

### 健康检查

```bash
curl http://localhost:8000/health
```

响应:
```json
{
  "status": "healthy",
  "db_size": 125000,
  "version": "1.0.0"
}
```

### 查询相似状态

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "MA_SMA_5": 10.5,
      "MA_SMA_20": 10.2,
      "RSI_RSI_12": 55.3,
      "MACD_macd": 0.15,
      "ATR_ATR": 2.5
    },
    "top_k": 10,
    "weighting_method": "distance"
  }'
```

响应:
```json
{
  "similar_states": [
    {
      "date": "2026-03-15",
      "symbol": "000001",
      "future_ret_1d": 1.2,
      "future_label": "小涨",
      "distance": 0.15
    },
    // ... 更多结果
  ],
  "prediction": {
    "avg_ret_1d": 0.8,
    "up_probability": 0.7,
    "label_distribution": {
      "大涨": 2,
      "小涨": 5,
      "小跌": 2,
      "大跌": 1
    },
    "sample_size": 10
  }
}
```

### 执行预测

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001",
    "date": "2026-04-21",
    "top_k": 10
  }'
```

### 运行回测

```bash
curl -X POST "http://localhost:8000/backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2026-04-21",
    "initial_capital": 1000000,
    "strategy_config": {
      "threshold": 0.65,
      "position_size": 0.1
    }
  }'
```

---

## 📊 使用示例

### 示例1: 基础预测流程

```python
from mizar import PredictionService

# 1. 初始化服务
service = PredictionService()

# 2. 执行预测
result = service.predict('000001', '2026-04-21')

# 3. 根据信号决策
if result.up_probability > 0.65:
    print("买入信号")
elif result.up_probability < 0.35:
    print("卖出信号")
else:
    print("持有观望")
```

### 示例2: 选股策略

```python
# 扫描多只股票
universe = ['000001', '000002', '600519', '601318']
candidates = []

for symbol in universe:
    result = service.predict(symbol, '2026-04-21')
    if result.up_probability > 0.7:
        candidates.append({
            'symbol': symbol,
            'probability': result.up_probability,
            'expected_return': result.avg_return
        })

# 按预期收益排序
candidates.sort(key=lambda x: x['expected_return'], reverse=True)
print("推荐标的:", candidates[:3])
```

### 示例3: 动态置信度调整

```python
# 根据市场状态调整阈值
def get_threshold(market_regime):
    thresholds = {
        'bull': 0.60,    # 牛市降低阈值
        'bear': 0.70,    # 熊市提高阈值
        'neutral': 0.65  # 震荡市标准阈值
    }
    return thresholds.get(market_regime, 0.65)

# 使用动态阈值
threshold = get_threshold(current_regime)
if result.up_probability > threshold:
    execute_trade()
```

---

## ⚠️ 注意事项

### 数据一致性

- 确保查询时的特征顺序与训练时一致
- 定期更新向量数据库以保持预测准确性
- 备份 `data/chroma_db/` 和 `models/` 目录

### 性能优化

```python
# 批量查询优于循环单次查询
symbols = ['000001', '000002', ...]  # 100+ stocks
results = service.batch_predict(symbols, date='2026-04-21')
```

### 错误处理

```python
try:
    result = service.predict('000001', '2026-04-21')
except ValueError as e:
    print(f"数据错误: {e}")
except ConnectionError as e:
    print(f"数据库连接失败: {e}")
```

---

## 🔍 调试技巧

### 启用日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看详细的检索过程
service.predict('000001', '2026-04-21', verbose=True)
```

### 检查数据质量

```bash
# 验证数据
mizar validate data/raw/*.csv --strict

# 查看数据库统计
curl http://localhost:8000/stats
```

---

## 📚 相关资源

- [快速入门指南](快速入门指南.md)
- [策略配置指南](策略配置指南.md)
- [技术架构说明](../technical/技术架构说明.md)

---

**版本**: v1.0  
**最后更新**: 2026-04-21
