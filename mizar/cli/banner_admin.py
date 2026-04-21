# -*- coding: utf-8 -*-
# @Time    : 2026/4/9 
# @File    : banner.py
# @Project : Mizar
# @Author  : Chiang Tao
# @Version : 0.1.00
# -*- coding: utf-8 -*-
# banner.py （已集成 Ed25519 签名验证）
import hashlib
import os
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

# 尝试导入 cryptography，若失败则降级为哈希校验
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
    # ... 保持原有实现 ...
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
    return r"""   _____  .__                              
  /     \ |__|____________ _______        
 /  \ /  \|  \___   /\__  \\_  __ \       
/    Y    \  |/    /  / __ \|  | \/       
\____|__  /__/_____ \(____  /__|          
        \/         \/     \/               
     开阳  ·  向量策略   · ·· ··· ✦  ✧
     观往知来 · Mizar   · * ★ * ✧    ✦"""

# ------------------------------------------------------------
# 3. Ed25519 公钥与签名（由 generate_signature.py 生成）
# ------------------------------------------------------------
PUBLIC_KEY_BYTES = bytes([
    # 请替换为实际生成的 32 个字节值
    # 例如: 215, 79, 98, ...
])

SIGNATURE_BYTES = bytes([
    # 请替换为实际生成的 64 个字节值
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

    # 优先使用 Ed25519 密码学验证
    if _CRYPTO_AVAILABLE and PUBLIC_KEY_BYTES and SIGNATURE_BYTES:
        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(PUBLIC_KEY_BYTES)
            public_key.verify(SIGNATURE_BYTES, message)
            return True
        except InvalidSignature:
            return False
        except Exception:
            # 若 cryptography 出错，降级为哈希
            pass

    # 降级方案：SHA256 哈希校验（用于无 cryptography 环境）
    EXPECTED_HASH = "请填入之前生成的 SHA256 哈希值，或留空以跳过校验"
    if not EXPECTED_HASH or EXPECTED_HASH == "请填入之前生成的 SHA256 哈希值，或留空以跳过校验":
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

    # 验证通过则显示完整艺术体，否则显示简化警告版
    if verify_integrity():
        banner = f"""
    [cyan]   _____  .__                              [/]
    [cyan]  /     \\ |__|____________ _______        [/]
    [cyan] /  \\ /  \\|  \\___   /\\__  \\\\_  __ \\ [/]
    [cyan]/    Y    \\  |/    /  / __ \\|  | \\/     [/]
    [cyan]\\____|__  /__/_____ \\(____  /__|         [/]
    [cyan]        \\/         \\/     \\/            [/]
    [cyan]      [bold]开阳  ·  向量策略  [/][star]· ·· ··· ✦  ✧[/]
    [cyan]      [dim yellow]观往知来[/][bold] · Mizar[/]   [star]· * ★ * ✧    ✦[/]
    [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
    [green] Version {ver}[/]   ·   similarity-first quant
    [dim] {copyright_info} [/]
    [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
    """
    else:
        # 警告模式：显示简化文字，但保留关键溯源信息
        watermark = meta.get("watermark", "MIZAR")
        banner = f"""
    [red]⚠️ 警告：此版本可能已被篡改，非官方 Mizar 发行版。[/]
    [yellow]项目标识: {watermark} | 版本: {ver}[/]
    [dim]官方源码请访问: https://github.com/jiangtaovan/mizar[/]
    [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
    """
    console.print(banner)
