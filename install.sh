#!/bin/bash
set -e  # 遇到错误立即停止

echo "=============================================="
echo " Mizar 本地环境安装脚本 (Linux/macOS)"
echo "=============================================="

# ---------- 1. 检查 Python ----------
echo ">>> 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 python3，请先安装 Python 3.13+"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python 版本: $PYTHON_VERSION"

# ---------- 2. 创建虚拟环境 ----------
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo ">>> 创建虚拟环境 $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
else
    echo ">>> 虚拟环境已存在，跳过创建。"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

# ---------- 3. 安装 TA-Lib C 库 ----------
install_talib_c() {
    echo ">>> 安装 TA-Lib C 库..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ta-lib
        else
            echo "错误：请先安装 Homebrew (https://brew.sh) 或手动安装 TA-Lib。"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux (Debian/Ubuntu)
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y build-essential wget
            wget https://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
            tar -xzf ta-lib-0.4.0-src.tar.gz
            cd ta-lib/
            ./configure --prefix=/usr
            make
            sudo make install
            cd ..
            rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
        else
            echo "警告：未检测到 apt-get，请手动安装 TA-Lib C 库。"
        fi
    else
        echo "警告：未知操作系统，请手动安装 TA-Lib C 库。"
    fi
}

# 检查 TA-Lib 是否已安装
if ! ldconfig -p 2>/dev/null | grep -q libta_lib && ! brew list ta-lib &>/dev/null; then
    install_talib_c
else
    echo ">>> TA-Lib C 库已安装，跳过。"
fi

# ---------- 4. 安装 Python TA-Lib ----------
pip install TA-Lib

# ---------- 5. 安装项目依赖（mootdx 已从 pyproject.toml 中移除）----------
echo ">>> 安装 Mizar 项目..."
if [ -f "pyproject.toml" ]; then
    pip install -e .
else
    echo "错误：未找到 pyproject.toml！"
    exit 1
fi

# ---------- 6. 单独安装 mootdx（绕过依赖冲突）----------
echo ">>> 单独安装 mootdx (--no-deps)..."
pip install --no-deps mootdx>=0.11.7

# 确保 chromadb 正确
pip install chromadb==1.5.0

# 补装 mootdx 可能需要的额外包
pip install websocket-client pytz simplejson

# ---------- 7. 创建必要目录 ----------
echo ">>> 创建数据目录..."
mkdir -p data models storage logs

# ---------- 8. 完成 ----------
echo "=============================================="
echo " 安装完成！"
echo " 激活虚拟环境: source $VENV_DIR/bin/activate"
echo " 运行 CLI 测试: mizar --help"
echo "=============================================="