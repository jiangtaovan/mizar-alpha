
---

### 📄 2. 更新后的 `QUICKSTART.md`

```markdown
# Mizarα 快速开始指南

## 🎯 简介

Mizarα (mizar-alpha) 是一个基于 Python 的量化策略实验框架，核心为市场状态向量数据库系统。本指南帮助您在 5 分钟内完成安装并运行第一个预测查询。

---

## 📦 项目结构速览

```
mizar-alpha/
├── 📁 config/              # 配置文件目录
│   ├── feature_config.yaml    # 特征选择配置（20~50 个指标）
│   └── system_config.yaml     # 系统运行配置
├── 📁 datas/                # 数据目录
│   ├── raw/                   # 放置您的技术指标数据
│   │   └── sample_data.csv    # 示例数据（10 条记录）
│   └── chroma_db/             # ChromaDB 向量库（构建后生成）
├── 📁 models/              # 模型文件目录（构建后生成）
│   ├── scaler.joblib          # 归一化器
│   ├── pca.joblib             # PCA 降维模型
│   └── selected_features.txt  # 特征列表
├── 📁 logs/                # 日志目录（运行后生成）
├── 📁 scripts/             # 工具脚本
│   ├── build_db.py            # 全量构建向量库
│   ├── update_db.py           # 增量更新
│   └── backtest.py            # 回测工具
├── 📁 tests/               # 单元测试
│   ├── test_data_loader.py
│   ├── test_feature_engineer.py
│   ├── test_vector_db.py
│   └── test_prediction_service.py
├── 📁 mizar/   # 核心代码模块
│   ├── data/               # 数据加载模块
│   ├── features/           # 特征工程模块
│   ├── vector_db/          # 向量数据库模块
│   ├── services/           # 预测服务模块
│   ├── api/                # API 接口模块
│   └── main.py             # 主程序入口
├── install.ps1              # Windows 快速安装脚本
├── install.sh               # Linux/macOS快速安装脚本
├── requirements.txt       # Python 依赖
├── Dockerfile            # Docker 镜像配置
├── docker-compose.yml    # Docker Compose 配置
└── README.md             # 详细文档
```

---

## 🚀 三步快速启动

### 1️⃣ 安装依赖

```bash
git clone https://github.com/jiangtaovan/mizar-alpha.git
cd mizar-alpha
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
pip install -r requirements.txt
pip install -e .
```

### 2️⃣ 准备行情数据

将您的日线 CSV 文件（需包含 `date,open,high,low,close,volume` 列，已前复权）放入 `storage/quotes/` 目录。

若暂无数据，可先使用 `mootdx` 在线获取少量数据进行测试。

### 3️⃣ 构建向量库并启动服务

```bash
# 构建向量库（首次运行需较长时间）
#mizar build --market A_share

python scripts/build_db.py


# 启动 API 服务
python main.py
```

服务启动后访问 http://localhost:8000/docs 即可查看交互式 API 文档。

---

## 🎮 命令行交互查询

无需启动 API，直接使用 CLI 工具查询个股预测：

```bash
mizar scan
```

然后输入股票代码（如 `601766`），即可看到预测结果及 Top 5 相似历史状态。

---

## 🧪 运行回测

编辑 `config/backtest_config.yaml` 配置策略参数，然后执行：

```bash
mizar backtest --symbol 601766
```

回测结果（权益曲线、交易记录、绩效指标）将保存在 `storage/backtest_results/`。

---

## 📊 常用命令速查

| 命令 | 用途 |
| :--- | :--- |
| `mizar build` | 全量构建向量库 |
| `mizar scan` | 交互式单点预测查询 |
| `mizar backtest --symbol SYMBOL` | 运行单标的回测 |
| `python main.py` | 启动 FastAPI 服务 |

---

## 🆘 常见问题

### Q1: 提示 `ModuleNotFoundError: No module named 'click.shell_completion'`
**A:** 升级 `click` 即可：`pip install --upgrade click>=8.1.0`

### Q2: 构建向量库时出现 NaT 错误
**A:** 确保行情数据已正确前复权，无缺失日期。可尝试使用 `mootdx` 重新下载。

### Q3: 回测结果异常高（如年化 > 100%）
**A:** 可能存在未来信息泄露。请参考 `docs/DATA_GUIDELINES.md` 中的时间安全规范。

---

## 📖 下一步

- 详细文档：[README.md](README.md)
- 数据使用规范：[docs/DATA_GUIDELINES.md](docs/DATA_GUIDELINES.md)
- 更新日志：[CHANGELOG.md](CHANGELOG.md)

**开发团队**: Mizarα Team  
**初始版本**: 2026-03-25
```
