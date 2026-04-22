以下是一份**新版回测参数说明与设置指南**，融合了参数全集、行情适配映射、以及预设管理器的使用方法。可直接作为项目文档或 CLI 帮助输出。

---

# Mizar 回测系统参数配置指南 v0.3

## 一、参数速查表

| 参数组 | 参数名（CLI） | 类型 | 默认值 | 作用 | 调大影响 | 调小影响 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **信号过滤** | `--threshold` | float | 0.55 | 开仓所需最低上涨概率 | 信号更少，质量更高 | 信号更多，覆盖更多机会 |
| | `--min_confidence` | float | None | 最低置信度要求 | 剔除不确定性交易 | 允许模型犹豫时开仓 |
| | `--min_ret_5d` | float | None | 最低5日预期收益（%） | 只做短期看涨的票 | 允许左侧摸底 |
| **仓位管理** | `--position_sizing` | str | full | `full` 全仓 / `signal` 按信号强度比例 | 全仓进出 | 按强度动态调仓 |
| **持仓周期** | `--strategy_type` | str | signal | `fixed` 固定持有 / `signal` 信号驱动平仓 | 固定周期持有 | 信号消失即平 |
| | `--period` | int | 2 | 固定持仓天数（仅 `fixed` 有效） | 吃足波段 | 快进快出 |
| **出场规则** | `--trailing_stop_pct` | float | None | 移动止损回撤比例（如 0.05=5%） | 给利润更大空间 | 锁利更紧 |
| | `--take_profit_pct` | float | None | 目标止盈比例 | 容忍更大涨幅 | 落袋更快 |
| | `--stop_loss` | float | None | 固定止损比例（已弃用，建议用移动止损） | — | — |
| | `--take_profit` | float | None | 固定止盈比例（已弃用） | — | — |
| | `--max_hold_days` | int | None | 最大持仓天数（强制平仓） | 允许长线持有 | 强制换手 |
| | `--partial_exit_enabled` | flag | False | 启用部分止盈（触发止盈时平一半） | 让部分仓位继续奔跑 | 一次性全平 |
| **其他** | `--fee_rate` | float | 0.0015 | 单边手续费率（如 0.001=0.1%） | — | — |
| | `--top_k` | int | 10 | 相似检索数量 | 更多样本，更稳健 | 更少样本，更灵敏 |

---

## 二、行情分类与参数调优指南

### 2.1 强趋势单边牛
**特征**：均线多头排列，沿5日线陡峭上行，回调短暂且浅。

| 参数 | 推荐值 | 说明 |
| :--- | :--- | :--- |
| `threshold` | 0.55~0.60 | 中性即可 |
| `min_confidence` | **0.65~0.70** | 高确信开仓，避免回调误入 |
| `min_ret_5d` | 0.0~1.0 | 要求短期预期为正 |
| `strategy_type` | **fixed** | 固定持有，防止盘中震荡洗出 |
| `period` | **5~10** | 覆盖主升浪周期 |
| `trailing_stop_pct` | **0.08~0.12** | 容忍正常回调 |
| `take_profit_pct` | **None** | 不设目标价 |
| `partial_exit_enabled` | **True** | 浮盈后先平一半，剩余奔跑 |
| `position_sizing` | full 或 signal（高仓位） | 重仓参与 |

### 2.2 震荡慢牛
**特征**：均线缓升，通道内“进二退一”，单日波动<2%。

| 参数 | 推荐值 | 说明 |
| :--- | :--- | :--- |
| `threshold` | **0.45~0.50** | 降低门槛，增加机会 |
| `min_confidence` | 0.55~0.60 | 轻微过滤 |
| `strategy_type` | **signal** | 信号消失即走 |
| `period` | 1~2 | 持股极短 |
| `trailing_stop_pct` | **0.03~0.05** | 窄止损 |
| `take_profit_pct` | **0.02~0.04** | 微利止盈 |
| `position_sizing` | signal | 仓位30%~60% |
| `max_hold_days` | **3~5** | 强制换手 |

### 2.3 宽幅震荡/箱体
**特征**：股价在±15%区间反复，假突破频繁。

| 参数 | 推荐值 | 说明 |
| :--- | :--- | :--- |
| `threshold` | **0.60~0.65** | 极高门槛 |
| `min_confidence` | **0.70+** | 双重过滤 |
| `min_ret_5d` | **>1.0** | 要求强动能 |
| `strategy_type` | signal | 信号消失立刻走 |
| `take_profit_pct` | **0.05~0.08** | 箱顶附近止盈 |
| `trailing_stop_pct` | **0.04~0.06** | 较紧止损 |

### 2.4 阴跌熊市
**特征**：均线空头排列，屡创新低。

| 参数 | 推荐值 | 说明 |
| :--- | :--- | :--- |
| **全局** | **启用大盘过滤器** | 指数<20日线时空仓 |
| `threshold` | 0.65+ | 极少开仓 |
| `position_sizing` | signal，且限制20%仓位 | 极轻仓试探 |
| `trailing_stop_pct` | 0.02~0.03 | 极窄止损 |
| `max_hold_days` | 1~2 | 超短线 |

### 2.5 高波动题材/量化活跃股
**特征**：日内振幅>5%，常有“早盘砸、午盘拉”走势。

| 参数 | 推荐值 | 说明 |
| :--- | :--- | :--- |
| `threshold` | 0.55~0.60 | 正常门槛 |
| `min_confidence` | 0.60~0.65 | 适度过滤 |
| `trailing_stop_pct` | **0.05~0.07** | 放宽止损 |
| `take_profit_pct` | **0.08~0.12** | 目标收益提高 |
| `partial_exit_enabled` | **True** | 强烈建议分批止盈 |
| **执行优化** | 启用日内智能挂单 | 等待盘中回踩买入 |

---

## 三、预设参数管理器使用指南

我们提供了 `ParamPresets` 类，可根据股票的**活跃度**和**市值规模**自动加载最优默认参数，大幅简化命令行操作。

### 3.1 可用预设列表

| 预设名 | 活跃度 | 市值 | 适用标的示例 |
| :--- | :--- | :--- | :--- |
| `blue_chip` | 低 | 大盘 | 工商银行、长江电力 |
| `growth_mid` | 中 | 中盘 | 汇川技术、中际旭创 |
| `tech_small` | 高 | 小盘 | 寒武纪、科创次新 |
| `quant_active` | 极端 | 小盘 | 量化密集标的 |
| `default` | 中 | 中盘 | 通用默认 |

也可直接使用底层组合，如 `low_large`、`high_small` 等。

### 3.2 命令行用法

```bash
# 直接使用预设（所有参数自动填充）
python back_mizar.py --file ./data/688256.csv --preset tech_small

python back_mizar.py --preset tech_small

# 使用预设，并微调单个参数（例如将移动止损改为6%）
python back_mizar.py --file ./data/688256.csv --preset tech_small --trailing_stop_pct 0.06

# 不使用预设，完全手动指定
python back_mizar.py --file ./data/xxx.csv --threshold 0.60 --min_confidence 0.65 --position_sizing signal
```

### 3.3 在 Python 脚本中调用

```python
from mizar.back.param_presets import ParamPresets, ActivityLevel, CapSize

# 方式1：通过枚举
params = ParamPresets.get_preset(ActivityLevel.HIGH, CapSize.SMALL)

# 方式2：便捷别名
params = ParamPresets.tech_small()

# 传入回测函数
run_backtest("data.csv", **params.to_dict())
```

---

## 四、参数优化 SOP（标准操作流程）

1. **划分行情片段**  
   将回测数据按趋势划分为：上涨段、下跌段、震荡段。

2. **单参数网格搜索**  
   固定其他参数，对核心参数（如 `threshold`、`min_confidence`）在合理区间内步进搜索。

3. **观察关键指标**  
   - 提高 `threshold` → 交易次数 ↓，胜率 ↑，收益可能先升后降  
   - 加入 `min_confidence` → 回撤 ↓，夏普 ↑  
   - 延长 `period` → 单笔盈利 ↑，胜率可能 ↓  
   - 收紧 `trailing_stop_pct` → 回撤 ↓，易错失大波段

4. **选择帕累托最优**  
   以**夏普比率**和**最大回撤**为主优化目标，累计收益为次要目标，选取稳定区域参数。

5. **样本外验证**  
   将选定参数应用于其他时间段或标的，确认非过拟合。

---

## 五、进阶：行情自适应参数切换

若需在回测中根据实时行情自动切换参数组，可引入行情识别器：

```python
def get_market_regime(df, lookback=20):
    close = df['close']
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    vol = close.pct_change().rolling(20).std()
    if close.iloc[-1] > ma20.iloc[-1] and ma20.iloc[-1] > ma60.iloc[-1]:
        return 'bull'
    elif close.iloc[-1] < ma20.iloc[-1] and ma20.iloc[-1] < ma60.iloc[-1]:
        return 'bear'
    else:
        return 'range'
```

然后在策略循环中动态加载 `params_map` 中的对应参数组（需扩展 `Strategy` 支持运行时更新参数，或每次切换时重新初始化策略对象）。

---

此文档涵盖了从入门到高阶的全部参数设置知识，可作为团队内部回测操作的标准化手册。