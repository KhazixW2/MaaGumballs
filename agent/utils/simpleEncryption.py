import hashlib
import platform
import subprocess
import re
import os
import logging
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend
import base64


def get_os_description() -> str:
    """
    与 C# 的 RuntimeInformation.OSDescription 方法完全兼容的 Python 实现。

    :return: 操作系统描述信息。
    """
    system = platform.system()
    if system == "Windows":
        return f"Microsoft Windows {platform.win32_ver()[1]}"
    elif system == "Linux":
        try:
            import distro

            return f"Linux {distro.linux_distribution()[1]} {platform.release()}"
        except ImportError:
            return f"Linux {platform.release()}"
    elif system == "Darwin":
        kernel_detail = subprocess.check_output(
            ["sysctl", "-n", "kern.version"], text=True
        ).strip()

        return f"{platform.system()} {platform.release()} {kernel_detail}"
    else:
        return system


def get_os_architecture() -> str:
    """
    与 C# 的 RuntimeInformation.OSArchitecture 方法完全兼容的 Python 实现。

    :return: 操作系统的架构。
    """
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "X64"
    elif machine in ("aarch64", "arm64"):
        return "Arm64"
    elif machine in ("i386", "x86"):
        return "X86"
    else:
        return machine.upper()


def sha256(src_string: str) -> str:
    """
    与 C# 的 Sha256 方法完全兼容的 Python 实现。

    :param src_string: 原始字符串
    :return: SHA256 哈希值（小写十六进制字符串，无连字符）
    """
    if not src_string:
        return ""

    # 使用 UTF-8 编码
    data = src_string.encode("utf-8")

    # 计算 SHA256 哈希
    hash_bytes = hashlib.sha256(data).digest()

    # 转换为十六进制字符串并去掉连字符
    hash_hex = hash_bytes.hex()

    return hash_hex


# ECB 模式加密（无 IV）
def aes_encrypt(data: str, key: str) -> str:
    """
    AES ECB 模式加密，兼容 C# `AESEncrypt` 方法。

    :param data: 原始明文字符串
    :param key: 32 字符长度的密钥（不足则填充空格，超过则截断）
    :return: Base64 编码的加密结果
    """
    # 确保密钥为 32 字符，不足则填充空格，超过则截断
    key = key.ljust(32)[:32]

    # 使用 UTF-8 编码
    key_bytes = key.encode("utf-8")
    data_bytes = data.encode("utf-8")

    # 使用 PKCS7 填充
    padder = PKCS7(128).padder()
    padded_data = padder.update(data_bytes) + padder.finalize()

    # 创建 AES ECB 加密器
    cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()

    return base64.b64encode(encrypted).decode("utf-8")


# ECB 模式解密（无 IV）
def aes_decrypt(data_b64: str, key: str) -> str:
    """
    AES ECB 模式解密，兼容 C# `AESDecrypt` 方法。

    :param data_b64: Base64 编码的加密字符串
    :param key: 32 字符长度的密钥（不足则填充空格，超过则截断）
    :return: 解密后的原始字符串
    """
    # 确保密钥为 32 字符
    key = key.ljust(32)[:32]

    # 使用 UTF-8 编码
    key_bytes = key.encode("utf-8")
    encrypted_data = base64.b64decode(data_b64)

    # 创建 AES ECB 解密器
    cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

    # 去除 PKCS7 填充
    unpadder = PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()

    return decrypted_data.decode("utf-8").rstrip("\x00")


def get_machine_name() -> str:
    """
    获取机器名称

    :return: 机器名称
    """
    try:
        system = platform.system()
        if system == "Windows":
            return platform.node()
        elif system == "Linux":
            return platform.node().split(".")[0]  # 返回主机名，不包含域名部分
        elif system == "Darwin":
            return platform.node().split(".")[0]
    except Exception as e:
        logging.warning(f"Failed to get machine name: {e}")
    return platform.node()  # 返回主机名，不包含域名部分


def generate():
    os_description = get_os_description()
    os_architecture = get_os_architecture()
    plain_text_specific_id = get_platform_specific_id()
    machine_name = get_machine_name()

    combined_string = (
        f"{os_description}_{os_architecture}_{plain_text_specific_id}_{machine_name}"
    )
    return sha256(combined_string).upper()


def get_platform_specific_id():
    try:
        system = platform.system()

        if system == "Windows":
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        elif system == "Linux":
            try:
                uuid_path = "/sys/class/dmi/id/product_uuid"
                if os.path.exists(uuid_path):
                    with open(uuid_path) as f:
                        return f.read().strip()
            except PermissionError:
                logging.warning(
                    "Permission denied when accessing product_uuid, trying alternative methods"
                )
            except Exception as e:
                logging.warning(f"Failed to read Linux UUID: {e}")

            try:
                machine_id_paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"]
                for path in machine_id_paths:
                    if os.path.exists(path):
                        with open(path) as f:
                            return f.read().strip()
            except Exception as e:
                logging.warning(f"Failed to read Linux machine ID: {e}")

            try:
                for interface in psutil.net_if_addrs().values():
                    for addr in interface:
                        if addr.family == psutil.AF_LINK and addr.address:
                            return addr.address.replace(":", "")
            except Exception as e:
                logging.warning(f"Failed to get Linux MAC address: {e}")
        elif system == "Darwin":
            process = subprocess.Popen(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output, _ = process.communicate()
            output = output.decode()
            match = re.search(r'IOPlatformUUID" = "(.+?)"', output)
            if match:
                return match.group(1)
        else:
            logging.warning("Unsupported OS platform")
    except Exception as e:
        logging.error(e)
    return ""


def get_device_key():
    fingerprint = generate()
    return fingerprint[:32]


def encrypt(plain_text):
    if not plain_text:
        return ""
    key = get_device_key()
    return aes_encrypt(plain_text, key)


def decrypt(encrypted_base64):
    try:
        key = get_device_key()
        return aes_decrypt(encrypted_base64, key)
    except Exception as e:
        logging.warning(e)
        return ""
