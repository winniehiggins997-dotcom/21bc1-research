# -*- coding: utf-8 -*-
"""
21 Bitcoin Computer - 本地钱包与离线交易示例脚本
该脚本展示了如何在不依赖已失效的 21.co 云端服务的情况下，
在本地使用 two1 库进行 HD 钱包管理与基本的比特币交易构造。
"""

import sys

def test_imports():
    print("[1/3] 正在检测 two1 库导入...")
    try:
        from two1.wallet import Wallet
        # 以下两个模块在本函数中并不直接使用，但作为关键依赖进行导入测试，
        # 确认 two1 库的 bitcoin 子模块（txn/crypto）均可正常加载。
        from two1.bitcoin.txn import Transaction      # noqa: F401
        from two1.bitcoin.crypto import HDPrivateKey, HDPublicKey  # noqa: F401
        print(" -> [成功] two1 库核心模块导入成功！")
        return True
    except ImportError as e:
        print(" -> [失败] 无法导入 two1 库。请确保已安装该库。")
        print("    错误详情: {}".format(e))
        print("\n    提示：您可以尝试在终端运行以下命令安装（需要 Python 3.5 环境较佳）：")
        print("    pip install two1")
        return False

def demo_wallet_usage():
    print("\n[2/3] 正在尝试初始化本地 HD 钱包...")
    from two1.wallet import Wallet
    
    try:
        # 初始化本地钱包（默认读取本地配置文件，如 ~/.two1/two1.json）
        # 如果是第一次在树莓派上运行，可能会提示配置
        wallet = Wallet()
        
        # 1. 获取当前接收地址
        address = wallet.current_address
        print(" -> 钱包当前比特币接收地址 (Address): {}".format(address))
        
        # 2. 查看钱包余额 (单位是 Satoshis 聪，1 BTC = 10^8 Satoshis)
        balance = wallet.confirmed_balance()
        print(" -> 钱包已确认余额 (Balance): {} satoshis (约 {} BTC)".format(balance, balance / 10**8))
        
        # 3. 获取钱包的主公钥
        master_pubkey = wallet.w._master_key.public_key.to_b58check(wallet.w.testnet)
        print(" -> 钱包主公钥 (Master Public Key): {}".format(master_pubkey))
        
    except Exception as e:
        print(" -> [提示] 钱包初始化失败，可能原因为未进行 initial setup。")
        print("    错误详情: {}".format(e))
        print("    如果您是在标准 PC 上测试，可以使用 two1 的底层 crypto 库手动生成临时钱包，请看下一步。")

def demo_crypto_fallback():
    print("\n[3/3] 使用底层 two1.bitcoin.crypto 生成临时 HD 钱包示例...")
    from two1.bitcoin.crypto import HDPrivateKey
    
    # 随机生成一个主私钥 (HD Wallet Root)
    # 注意：two1 库使用 master_key_from_entropy() 生成主密钥，而非 from_random()
    try:
        # master_key_from_entropy 返回 (HDPrivateKey, mnemonic_str)
        master_key, mnemonic = HDPrivateKey.master_key_from_entropy(passphrase='')
        print(" -> [成功] 已成功在内存中生成随机主私钥！")
        print(" -> 助记词 (Mnemonic，请妥善保管): {}".format(mnemonic))
        
        # 派生子密钥 (BIP44 路径: m/44'/0'/0'/0/0)
        # 44': BIP44, 0': Bitcoin, 0': Account 0, 0: External chain, 0: Address index 0
        from two1.bitcoin.crypto import HDKey
        child_private_key = HDKey.from_path(
            master_key,
            "44'/0'/0'/0/0"
        )[-1]  # 取路径最终派生的子私钥
        
        # 获取对应的公钥和比特币地址
        child_public_key = child_private_key.public_key
        bitcoin_address = child_public_key.address()
        
        # HDPrivateKey 用 to_b58check() 序列化，而非 to_wif()
        # to_b58check() 和 address() 返回 bytes，用 .decode() 转为可读字符串
        key_str = child_private_key.to_b58check()
        if isinstance(key_str, bytes):
            key_str = key_str.decode('utf-8')
        addr_str = bitcoin_address
        if isinstance(addr_str, bytes):
            addr_str = addr_str.decode('utf-8')
        print(" -> 派生子私钥 (Base58Check 序列化): {}".format(key_str))
        print(" -> 派生子地址 (Derived Address): {}".format(addr_str))
    except Exception as e:
        print(" -> 运行失败: {}".format(e))

if __name__ == "__main__":
    print("=========================================")
    print("      21 Bitcoin Computer 开发测试脚本    ")
    print("=========================================\n")
    
    if test_imports():
        demo_wallet_usage()
        demo_crypto_fallback()
        
    print("\n=========================================")
    print("测试结束。如果以上步骤均正常，说明您的本地环境已支持 basic offline development。")
