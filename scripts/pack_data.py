# -*- coding: utf-8 -*-
# @Time    : 2026/3/27 
# @File    : pack_data.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00

#!/usr/bin/env python3
"""
数据打包/解压工具

用于打包预训练向量库、模型文件及示例数据。
支持打包成 zip 或 tar.gz 格式，并解压到指定目录。
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# 默认需要打包的内容（相对于项目根目录）
DEFAULT_PACK_CONTENTS = [
    "datas/chroma_db",           # 向量库完整目录
    "models/scaler.joblib",     # 归一化器
    "models/pca.joblib",        # PCA 降维器
    "models/model_info.json",   # 版本
    "models/selected_features.txt", # 原始维度
    "datas/raw",  # 示例数据（可选）
]

def find_project_root():
    """向上查找包含 .git 或 setup.py 的目录作为项目根目录"""
    current = Path(__file__).parent.resolve()
    while current != current.parent:
        # 根据项目特征判断：有 .git 目录 或 有 main.py 或 有 pyproject.toml
        if (current / ".git").exists() or (current / "main.py").exists() or (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # 兜底：如果找不到，返回脚本所在目录的父目录（即假设 scripts 同级为根）
    return Path(__file__).parent.parent.resolve()

def pack(output_path: str, contents: list = None, format: str = "zip"):
    """
    打包指定内容到压缩文件
    :param output_path: 输出文件路径（不含扩展名）
    :param contents: 要打包的文件/目录列表（相对于项目根目录）
    :param format: 压缩格式，"zip" 或 "tar.gz"
    """
    if contents is None:
        contents = DEFAULT_PACK_CONTENTS

    project_root = find_project_root()
    output_path = Path(output_path).resolve()

    if format == "zip":
        output_file = output_path.with_suffix(".zip")
        shutil.make_archive(
            base_name=str(output_path),
            format="zip",
            root_dir=project_root,
            base_dir=None,
            verbose=True
        )
        # 注意：shutil.make_archive 需要 base_name 不带扩展名，且指定 root_dir 和 base_dir
        # 更简单的方法是手动构建 zip，以便包含相对路径
        # 但这里我们使用 shutil 的标准方式，需要调整参数
        # 下面重新实现手动构建
        import zipfile
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in contents:
                item_path = project_root / item
                if not item_path.exists():
                    print(f"警告: 路径不存在，跳过: {item_path}")
                    continue
                if item_path.is_dir():
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = str(file_path.relative_to(project_root))
                            zipf.write(file_path, arcname)
                else:
                    arcname = item
                    zipf.write(item_path, arcname)
        print(f"打包完成: {output_file}")

    elif format == "tar.gz":
        output_file = output_path.with_suffix(".tar.gz")
        import tarfile
        with tarfile.open(output_file, "w:gz") as tar:
            for item in contents:
                item_path = project_root / item
                if not item_path.exists():
                    print(f"警告: 路径不存在，跳过: {item_path}")
                    continue
                tar.add(item_path, arcname=item)
        print(f"打包完成: {output_file}")

    else:
        raise ValueError(f"不支持的格式: {format}")


def unpack(archive_path: str, target_dir: str = None, overwrite: bool = False):
    """
    解压打包文件到目标目录
    :param archive_path: 压缩文件路径
    :param target_dir: 目标目录（默认为项目根目录）
    :param overwrite: 是否覆盖已存在的文件
    """
    archive_path = Path(archive_path).resolve()
    if not archive_path.exists():
        print(f"错误: 文件不存在: {archive_path}")
        sys.exit(1)

    if target_dir is None:
        target_dir = Path(__file__).parent
    else:
        target_dir = Path(target_dir).resolve()

    # 确保目标目录存在
    target_dir.mkdir(parents=True, exist_ok=True)

    # 根据扩展名选择解压方式
    suffix = archive_path.suffix.lower()
    if suffix == ".zip":
        import zipfile
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            # 检查是否有文件会覆盖
            if not overwrite:
                for member in zipf.namelist():
                    dest = target_dir / member
                    if dest.exists():
                        print(f"文件已存在，跳过 (使用 -f 强制覆盖): {member}")
                        sys.exit(1)
            zipf.extractall(target_dir)
        print(f"解压完成到: {target_dir}")

    elif suffix in (".gz", ".tgz"):
        import tarfile
        with tarfile.open(archive_path, 'r:gz') as tar:
            # 检查覆盖
            if not overwrite:
                for member in tar.getmembers():
                    dest = target_dir / member.name
                    if dest.exists():
                        print(f"文件已存在，跳过 (使用 -f 强制覆盖): {member.name}")
                        sys.exit(1)
            tar.extractall(target_dir)
        print(f"解压完成到: {target_dir}")

    else:
        raise ValueError(f"不支持的文件类型: {suffix}")


def main():
    parser = argparse.ArgumentParser(description="Mizar 数据打包/解压工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # pack 子命令
    pack_parser = subparsers.add_parser("pack", help="打包数据")
    pack_parser.add_argument("-o", "--output", default="mizar_data", help="输出文件名（不含扩展名），默认 mizar_data")
    pack_parser.add_argument("-f", "--format", choices=["zip", "tar.gz"], default="zip", help="压缩格式，默认 zip")
    pack_parser.add_argument("--contents", nargs="+", help="要打包的路径列表（相对于项目根目录），默认使用预定义列表")

    # unpack 子命令
    unpack_parser = subparsers.add_parser("unpack", help="解压数据")
    unpack_parser.add_argument("archive", help="压缩文件路径")
    unpack_parser.add_argument("-t", "--target", help="目标目录（默认项目根目录）")
    unpack_parser.add_argument("-f", "--force", action="store_true", help="强制覆盖已存在的文件")

    args = parser.parse_args()

    if args.command == "pack":
        pack(
            output_path=args.output,
            contents=args.contents,
            format=args.format
        )
    elif args.command == "unpack":
        unpack(
            archive_path=args.archive,
            target_dir=args.target,
            overwrite=args.force
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
#
# # 打包为 zip 格式（默认）
# python scripts/pack_data.py pack -o mizar_data
#
# # 打包为 tar.gz 格式
# python scripts/pack_data.py pack -o mizar_data -f tar.gz
#
# # 自定义打包内容
# python scripts/pack_data.py pack -o mizar_data --contents datas/chroma_db models/scaler.joblib models/pca.joblib
#
# # 解压到项目根目录
# python scripts/pack_data.py unpack mizar_data.zip
#
# # 解压到指定目录
# python scripts/pack_data.py unpack mizar_data.zip -t /path/to/target
#
# # 强制覆盖已存在的文件
# python scripts/pack_data.py unpack mizar_data.zip -f