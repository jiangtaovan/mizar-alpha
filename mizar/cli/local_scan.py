# -*- coding: utf-8 -*-
# @Time    : 2026/4/13 
# @File    : local_scan.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""
from services import PredictionService
from utils import load_config

# -*- coding: utf-8 -*-
"""
临时本地交互查询工具（仅供内部使用，不对外发布）
提供与 scan 相同的功能，并自动记录会话，支持保存为 Markdown 报告。
"""

import typer
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.table import Table

from .query_service import QueryService
from .styles import console, PRIMARY_STAR

class LocalSessionRecorder:
    """会话记录器（仅内存）"""
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add(self, symbol: str, offset: int, result: Any):
        self.records.append({
            "timestamp": datetime.now(),
            "symbol": symbol,
            "offset": offset,
            "result": result
        })

    def clear(self):
        self.records.clear()

    def is_empty(self) -> bool:
        return len(self.records) == 0


class MarkdownExporter:
    """将记录导出为 Markdown 文件，保留 Rich 渲染效果（采用 HTML 嵌入）"""

    @staticmethod
    def _result_to_rich_table(result: Any) -> Table:
        """重建 Rich 表格（复用 QueryService 的表格构建逻辑）"""
        table = Table(title=f"{result.symbol} 预测结果", show_header=True, header_style="bold cyan")
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("次日预期收益", f"{result.expected_return_1d:.2%}")
        table.add_row("5日预期收益", f"{result.expected_return_5d:.2%}")
        table.add_row("上涨概率", f"{result.up_probability:.0%}")
        table.add_row("标签分布", str(result.label_distribution))
        table.add_row("相似样本数", str(result.sample_count))
        table.add_row("波动率", f"{result.volatility:.2%}")
        table.add_row("夏普比率", f"{result.sharpe_ratio:.2f}")

        # 相似样本子表
        if result.similar_samples:
            sample_table = Table(show_header=True, header_style="bold yellow")
            sample_table.add_column("日期")
            sample_table.add_column("标的")
            sample_table.add_column("标签")
            sample_table.add_column("次日收益")
            sample_table.add_column("距离")

            for sample in result.similar_samples[:5]:
                sample_table.add_row(
                    sample.date.strftime("%Y-%m-%d"),
                    sample.symbol,
                    sample.label,
                    f"{sample.return_1d:.2%}",
                    f"{sample.distance:.4f}"
                )
            table.add_row("最相似历史状态", sample_table)

        return table

    @classmethod
    def export_to_markdown(cls, records: List[Dict], output_path: Path):
        """导出为 Markdown 文件，使用 Rich 的 HTML 导出功能保留颜色"""
        from io import StringIO
        from rich.console import Console as RichConsole

        md_lines = []
        md_lines.append(f"# Mizar 本地查询报告\n")
        md_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_lines.append("---\n")

        for rec in records:
            symbol = rec["symbol"]
            offset = rec["offset"]
            result = rec["result"]
            timestamp = rec["timestamp"].strftime("%H:%M:%S")

            md_lines.append(f"## 查询：{symbol} (偏移 {offset} 交易日)  [{timestamp}]\n")

            # 使用 Rich 捕获 HTML 输出（完美保留颜色）
            temp_console = RichConsole(record=True)
            table = cls._result_to_rich_table(result)
            temp_console.print(table)

            # 导出为内联样式的 HTML
            html = temp_console.export_html(inline_styles=True)
            # 去除多余的 <html><body> 标签，只保留表格部分
            if "<table" in html:
                start = html.find("<table")
                end = html.rfind("</table>") + 8
                html = html[start:end]
            md_lines.append(html)
            md_lines.append("\n---\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(md_lines), encoding="utf-8")


def get_query_service() -> Optional[QueryService]:
    """获取查询服务实例（复用原有逻辑）"""
    try:

        config = load_config()
        service = PredictionService(config)
        service.initialize()
        return QueryService(service)
    except Exception as e:
        console.print(f"[error]服务初始化失败: {e}[/]")
        return None


def scan_local(
    top_k: int = typer.Option(10, "--k", "-k", help="默认相似样本数"),
):
    """
    [内部使用] 进入交互式查询模式，自动记录会话，退出时提示保存 Markdown 报告。
    """
    qs = get_query_service()
    if not qs or not qs._initialized:
        console.print("[error]服务初始化失败[/]")
        raise typer.Exit(1)

    recorder = LocalSessionRecorder()

    console.print(f"[star]{PRIMARY_STAR}[/] [cyan]进入 Mizar 本地交互查询模式（自动记录）[/]")
    console.print("  格式：[股票代码] [偏移天数-交易日]")
    console.print("  示例：000001.SZ   （查询最新）")
    console.print("        600519 3    （查询3天前）")
    console.print("  命令：[bold]save[/] 立即保存报告，[bold]clear[/] 清空记录，[bold]exit[/]/[bold]quit[/]/[bold]q[/] 退出\n")

    while True:
        try:
            user_input = typer.prompt("查询", default="").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[gold]退出交互模式[/]")
            break

        if user_input.lower() in ("exit", "quit", "q", ""):
            break

        if user_input.lower() == "save":
            if recorder.is_empty():
                console.print("[warning]暂无查询记录可保存[/]")
                continue
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(f"./reports/local_session_{timestamp}.md")
            MarkdownExporter.export_to_markdown(recorder.records, report_path)
            console.print(f"[success]报告已保存至：{report_path}[/]")
            continue

        if user_input.lower() == "clear":
            recorder.clear()
            console.print("[info]会话记录已清空[/]")
            continue

        parts = user_input.split()
        symbol = parts[0]
        offset = 0
        if len(parts) >= 2:
            try:
                offset = int(parts[1])
            except ValueError:
                console.print("[warning]偏移必须为整数，将使用 0[/]")

        # 执行查询
        with console.status(f"[cyan]查询 {symbol} (偏移-交易日={offset}) ...[/]"):
            result = qs.query(symbol, start=offset, top_k=top_k)

        if result:
            qs.print_result(result)
            recorder.add(symbol, offset, result)
        else:
            console.print(f"[error]查询 {symbol} 失败[/]")

    # 退出前询问保存
    if not recorder.is_empty():
        save = typer.confirm("是否保存本次会话报告？", default=True)
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(f"./reports/local_session_{timestamp}.md")
            MarkdownExporter.export_to_markdown(recorder.records, report_path)
            console.print(f"[success]报告已保存至：{report_path}[/]")
        else:
            console.print("[info]报告未保存[/]")

    console.print("[success]再见！[/]")