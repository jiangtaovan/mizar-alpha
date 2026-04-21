# -*- coding: utf-8 -*-
# @Time    : 2026/4/13 
# @File    : exporter.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
"""
[Optional: Add a more detailed description here]
"""
# mizar/cli/exporter.py
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table


class SessionRecorder:
    """记录交互式查询的会话历史"""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add(self, symbol: str, offset: int, result: Any):
        self.records.append( {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "offset": offset,
            "result": result
        } )

    def clear(self):
        self.records.clear()


class MarkdownExporter:
    """将记录转换为 Markdown 格式"""

    @staticmethod
    def _colorize(text: str, style: str) -> str:
        # 简单映射，可根据需要扩展
        mapping = {
            "cyan": "",
            "success": "✅ ",
            "error": "❌ ",
            "warning": "⚠️ ",
            "gold": "",
            "bold": "**",
        }
        if style in mapping:
            if style == "bold":
                return f"**{text}**"
            return f"{mapping[style]}{text}"
        return text

    @classmethod
    def convert_result_to_md(cls, symbol: str, offset: int, result: Any) -> str:
        """将单个 PredictionResult 转换为 Markdown 区块"""
        lines = []
        lines.append( f"### 查询：{symbol} (偏移 {offset} 交易日)\n" )

        # 基本信息
        lines.append( f"- **次日预期收益**：{result.expected_return_1d:.2%}" )
        lines.append( f"- **5日预期收益**：{result.expected_return_5d:.2%}" )
        lines.append( f"- **上涨概率**：{result.up_probability:.0%}" )
        lines.append( f"- **标签分布**：{result.label_distribution}" )
        lines.append( f"- **相似样本数**：{result.sample_count}" )
        lines.append( f"- **波动率**：{result.volatility:.2%}" )
        lines.append( f"- **夏普比率**：{result.sharpe_ratio:.2f}\n" )

        # 相似样本表格
        lines.append( "**最相似历史状态**\n" )
        if result.similar_samples:
            # 构建 Markdown 表格
            headers = ["日期", "标的", "标签", "次日收益", "距离"]
            table_lines = ["| " + " | ".join( headers ) + " |",
                           "|" + "|".join( ["---"] * len( headers ) ) + "|"]
            for sample in result.similar_samples[:5]:
                row = [
                    sample.date.strftime( "%Y-%m-%d" ),
                    sample.symbol,
                    sample.label,
                    f"{sample.return_1d:.2%}",
                    f"{sample.distance:.4f}"
                ]
                table_lines.append( "| " + " | ".join( row ) + " |" )
            lines.extend( table_lines )
        lines.append( "\n---\n" )
        return "\n".join( lines )

    @classmethod
    def export_session(cls, records: List[Dict], output_path: Path):
        """导出整个会话为 Markdown 文件"""
        md_content = []
        md_content.append( f"# Mizar 交互查询报告\n" )
        md_content.append( f"生成时间：{datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}\n" )
        md_content.append( "---\n" )

        for rec in records:
            md_content.append( cls.convert_result_to_md(
                rec["symbol"], rec["offset"], rec["result"]
            ) )

        output_path.parent.mkdir( parents=True, exist_ok=True )
        output_path.write_text( "\n".join( md_content ), encoding="utf-8" )

