# install.ps1
$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Mizar Local Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# ---------- 1. Check Python ----------
Write-Host ">>> Checking Python..." -ForegroundColor Yellow
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found. Please install Python 3.13+" -ForegroundColor Red
    exit 1
}
$pyVersion = python -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))"
Write-Host "Python version: $pyVersion"

# ---------- 2. Create virtual environment ----------
$VENV_DIR = "venv"
if (-not (Test-Path $VENV_DIR)) {
    Write-Host ">>> Creating virtual environment $VENV_DIR ..." -ForegroundColor Yellow
    python -m venv $VENV_DIR
} else {
    Write-Host ">>> Virtual environment already exists." -ForegroundColor Yellow
}
& "$VENV_DIR\Scripts\Activate.ps1"
python -m pip install --upgrade pip

# ---------- 3. TA-Lib notice ----------
Write-Host ">>> Checking TA-Lib..." -ForegroundColor Yellow
try {
    python -c "import talib" 2>$null
    Write-Host "TA-Lib Python package already installed." -ForegroundColor Green
} catch {
    Write-Host "==============================================" -ForegroundColor Red
    Write-Host " TA-Lib requires manual installation on Windows." -ForegroundColor Red
    Write-Host " Download appropriate .whl from:" -ForegroundColor Red
    Write-Host " https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib" -ForegroundColor Yellow
    Write-Host " Then install manually: pip install TA_Lib‑xxx.whl" -ForegroundColor Yellow
    Write-Host "==============================================" -ForegroundColor Red
    $continue = Read-Host "Continue installing other dependencies? (y/n)"
    if ($continue -ne "y") { exit 0 }
}

# ---------- 4. Install project (mootdx already removed from pyproject.toml) ----------
Write-Host ">>> Installing Mizar project..." -ForegroundColor Yellow
if (Test-Path "pyproject.toml") {
    pip install -e .
} else {
    Write-Host "ERROR: pyproject.toml not found!" -ForegroundColor Red
    exit 1
}

# ---------- 5. Install mootdx separately (--no-deps) ----------
Write-Host ">>> Installing mootdx (--no-deps)..." -ForegroundColor Yellow
pip install --no-deps mootdx==0.11.7

# Ensure chromadb is correct (should already be installed from project dependencies)
pip install chromadb==1.5.0

# Additional deps for mootdx
pip install websocket-client pytz simplejson

# ---------- 6. Create necessary directories ----------
Write-Host ">>> Creating data directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path data, models, storage, logs | Out-Null

# ---------- 7. Finish ----------
Write-Host "==============================================" -ForegroundColor Green
Write-Host " Installation completed!" -ForegroundColor Green
Write-Host " Activate venv: .\$VENV_DIR\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host " Test CLI: mizar --help" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green