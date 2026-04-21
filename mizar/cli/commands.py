# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : commands.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00

# mizar/cli/commands.py

import typer
import time
import uvicorn
from pathlib import Path

from .styles import console, PRIMARY_STAR
from .query_service import get_query_service

DEFAULT_CONFIG_PATH = Path( __file__ ).parent.parent.parent / "config" / "backtest_config.yaml"

app = typer.Typer(name="mizar", help="Mizar · 相似性检索量化框架")

# 在 commands.py 中，app 定义之后，其他 @app.command() 之前添加

@app.callback( invoke_without_command=True )
def default_callback(ctx: typer.Context):
    """
    当没有提供子命令时自动执行（默认入口优化）
    """
    if ctx.invoked_subcommand is None:
        # 方案一：显示帮助信息（推荐，不改变用户习惯）
        console.print( "[dim]未指定命令，显示帮助信息：[/]\n" )
        ctx.get_help()

        # 方案二：自动进入 scan 交互模式（需要取消上方注释并注释掉方案一）
        # from .commands import scan as scan_cmd
        # scan_cmd(top_k=10)

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload", "-r"),
):
    """启动 Mizar REST API 服务"""

    console.print(f"[cyan]启动 API 服务 {host}:{port}...[/]")
    uvicorn.run(app, host=host, port=port, reload=reload)

@app.command()
def build(
    config: str = typer.Option("config/market_config.yaml", "--config", "-c"),
    market: str = typer.Option("A_share", "--market", "-m"),
):
    """No use"""
    console.print(f"[star]{PRIMARY_STAR}[/] [cyan]正在构建向量库...[/]")
    console.print(f"  配置: {config}")
    console.print(f"  市场: {market}")
    with console.status("[cyan]计算特征并入库...[/]"):
        time.sleep(2)
    console.print("[success]✓ 向量库已就绪[/]")

@app.command()
def query(
    symbol: str = typer.Argument(...),
    date: str = typer.Option(None, "--date", "-d"),
    k: int = typer.Option(10, "--k", "-k"),
):
    """Mizar query demo"""
    console.print(f"[star]{PRIMARY_STAR}[/] [cyan]查询 {symbol} 相似状态[/]")
    from rich.table import Table
    table = Table(title="相似历史状态", title_style="bold cyan")
    table.add_column("日期", style="dim")
    table.add_column("距离", justify="right")
    table.add_column("5日收益", justify="right")
    for i in range(5):
        table.add_row(f"2024-0{i+1}-15", f"{0.12+i*0.03:.3f}", f"[green]+{3.2-i*0.5:.1f}%[/]")
    console.print(table)
    console.print("\n[gold]✦[/] 预测: 上涨概率 58%, 预期收益 +1.8%")


@app.command()
def backtest(
    config: str = typer.Option("config/market_config.yaml", "--config", "-c"),
    start: str = typer.Option(..., "--start", "-s"),
    end: str = typer.Option(..., "--end", "-e"),
):
    """No use"""
    console.print(f"[star]{PRIMARY_STAR}[/] [cyan]回测 {start} → {end}[/]")
    with console.status("[cyan]模拟交易中...[/]"):
        for _ in range(20):
            time.sleep(0.05)
    from rich.table import Table
    table = Table(title="回测报告", title_style="bold cyan")
    table.add_column("指标", style="dim")
    table.add_column("多头", justify="right")
    table.add_column("空头", justify="right")
    table.add_column("合计", justify="right", style="bold")
    table.add_row("收益率", "[green]+32.4%[/]", "[red]+18.7%[/]", "[cyan]+57.2%[/]")
    table.add_row("夏普比率", "1.82", "2.31", "2.05")
    table.add_row("胜率", "53.2%", "60.1%", "56.7%")
    table.add_row("最大回撤", "-12.3%", "-7.8%", "-10.1%")
    console.print(table)
    console.print("[success]✓ 回测完成[/]")


@app.command()
def scan(
    top_k: int = typer.Option(10, "--k", "-k", help="默认相似样本数"),
):
    """进入交互式查询 scan（个股单点预测）"""
    qs = get_query_service()
    if not qs._initialized:
        console.print("[error]服务初始化失败[/]")
        raise typer.Exit(1)

    console.print(f"[star]{PRIMARY_STAR}[/] [cyan]进入 Mizar 交互查询模式[/]")
    console.print("  格式：[股票代码] [偏移天数-交易日]")
    console.print("  示例：000001.SZ   （查询最新）")
    console.print("        600519 3    （查询3天前）")
    console.print("  输入 [bold]exit[/] 或 [bold]quit[/] 退出\n")

    while True:
        try:
            user_input = typer.prompt("查询", default="").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[gold]退出交互模式[/]")
            break

        if user_input.lower() in ("exit", "quit", "q", ""):
            console.print("[gold]退出交互模式[/]")
            break

        parts = user_input.split()
        symbol = parts[0]
        start = 0
        if len(parts) >= 2:
            try:
                start = int(parts[1])
            except ValueError:
                console.print("[warning]偏移必须为整数，将使用 0[/]")

        # 执行查询
        with console.status(f"[cyan]查询 {symbol} (偏移-交易日={start}) ...[/]"):
            result = qs.query(symbol, start=start, top_k=top_k)

        if result:
            qs.print_result(result)
        else:
            console.print(f"[error]查询 {symbol} 失败[/]")

    console.print("[success]再见！[/]")