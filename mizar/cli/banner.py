# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : banner.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.2.00
"""
Mizar ASCII 艺术体 Logo，集成 TOML 溯源防伪校验。
"""
import hashlib
import os
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

#  cryptography
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False

from .styles import console

# ------------------------------------------------------------
# 1. 从 pyproject.toml 读取元数据（保持不变）
# ------------------------------------------------------------
def _load_mizar_metadata() -> dict:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("tool", {}).get("mizar", {})
    except Exception:
        pass
    return {}

_META = _load_mizar_metadata()

def get_version() -> str:
    try:
        return version("mizar")
    except PackageNotFoundError:
        pass
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        pass
    return "0.2.0-dev"

# ------------------------------------------------------------
# 2. 原始 Banner 文本（请勿修改）
# ------------------------------------------------------------
def _get_raw_banner() -> str:
    return r""" 
       _____  .__                          _____  .__         .__
      /     \ |__|____________ _______    /  _  \ |  | ______ |  |__ _____
     /  \ /  \|  \___   /\__  \\_  __ \  /  /_\  \|  | \____ \|  |  \\__  \
    /    Y    \  |/    /  / __ \|  | \/ /    |    \  |_|  |_> >   Y  \/ __ \_
    \____|__  /__/_____ \(____  /__|    \____|__  /____/   __/|___|  (____  /
            \/         \/     \/                \/     |__|        \/     \/          
         开阳  ·  向量策略   · ·· ··· ✦  ✧
         观往知来 · Mizar    · * ★ * ✧   ✦ """

# ------------------------------------------------------------
# 3. 公钥与签名
# ------------------------------------------------------------
PUBLIC_KEY_BYTES = bytes([
    #  32 个字节值
    79, 118, 204, 101, 35, 231, 228, 253, 27, 101, 200, 94, 10, 62, 26, 246, 96, 236, 139, 241, 7, 246, 206, 113, 45, 79, 1, 83, 46, 72, 87, 43
])

SIGNATURE_BYTES = bytes([
    #  64 个字节值
206, 166, 59, 254, 73, 122, 143, 204, 177, 187, 7, 156, 161, 22, 90, 87, 193, 134, 114, 110, 110, 15, 17, 175, 27, 206, 5, 51, 149, 33, 161, 140, 16, 84, 14, 116, 68, 97, 62, 208, 201, 239, 229, 4, 51, 29, 89, 211, 108, 80, 27, 200, 251, 13, 143, 211, 253, 177, 90, 42, 65, 133, 73, 8
    ])


# ------------------------------------------------------------
# 4. 验证函数：优先 Ed25519，降级哈希
# ------------------------------------------------------------
def _get_message_to_verify() -> bytes:
    """返回用于签名/哈希的消息内容"""
    banner = _get_raw_banner()
    uuid = _META.get("project_uuid", "")
    return f"{banner}||{uuid}".encode('utf-8')

def verify_integrity() -> bool:
    """验证 Banner 与元数据的完整性。支持 Ed25519 和 SHA256 两种模式。"""
    message = _get_message_to_verify()
    # 本地环境 或测试 可以去除验证
    # return True
    # 允许通过环境变量跳过校验
    if os.environ.get( 'MIZAR_SKIP_INTEGRITY_CHECK', '' ).lower() == 'true':
        return True
    # 优先使用 Ed25519 密码学验证
    if _CRYPTO_AVAILABLE and PUBLIC_KEY_BYTES and SIGNATURE_BYTES:
        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(PUBLIC_KEY_BYTES)
            public_key.verify(SIGNATURE_BYTES, message)
            return True
        except InvalidSignature:
            return False
        except Exception:
            pass

    # # 降级方案：SHA256 哈希校验（用于无 cryptography 环境）
    EXPECTED_HASH = "1228ff0c3c9a05ef554ce7ccde488e685192c9e5e4cd3d627dbcbd53f52f2175"
    if not EXPECTED_HASH or EXPECTED_HASH == "1228ff0c3c9a05ef554ce7ccde488e685192c9e5e4cd3d627dbcbd53f52f2175":
        # 未配置哈希值时，默认通过（避免干扰开发环境）
        return True
    current_hash = hashlib.sha256(message).hexdigest()
    return current_hash == EXPECTED_HASH

# ------------------------------------------------------------
# 5. 最终显示（根据验证结果展示不同 Banner）
# ------------------------------------------------------------
def print_banner():
    ver = get_version()
    meta = _META

    # 构建版权信息行
    copyright_info = ""
    if meta.get("copyright_year"):
        copyright_info = f"© {meta['copyright_year']} Chiang Tao"
    if meta.get("license_statement"):
        license_short = meta["license_statement"].split(".")[0] + "."
        copyright_info += f" | {license_short}"

    # 验证通过则显示完整艺术体
    if verify_integrity():
        raw_banner= _get_raw_banner()
        banner = f"""
    [cyan]{raw_banner}[/]
    [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
    [green] Version {ver}[/]   ·   similarity-first quant
    [dim yellow] {copyright_info} [/]
    [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
    """
    else:
        watermark = meta.get("watermark", "MIZAR-ALPHA")
        banner = f"""
    [red]⚠️ 警告：此版本可能已被修改，非官方 Mizarα 发行版。[/]
    [yellow]项目标识: {watermark} | 版本: {ver}[/]
    [dim]官方源码请访问: https://github.com/jiangtaovan/mizar-alpha[/]
    [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
    """
    console.print(banner)
