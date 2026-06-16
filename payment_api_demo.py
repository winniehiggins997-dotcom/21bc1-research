# -*- coding: utf-8 -*-
"""
21 Bitcoin Computer - Flask + bitserv 本地微支付 API 示例
该脚本展示了如何使用 two1 库在本地/局域网搭建一个“付Satoshis币才能调用”的 API 接口。
这是当年 21 系统的核心开发模式。
"""

import sys

def test_requirements():
    print("[1/3] 正在检测运行环境...")
    try:
        import flask
        print(" -> [成功] Flask 库已安装")
    except ImportError:
        print(" -> [提示] 未安装 Flask 库，请运行: pip install flask")
        return False
        
    try:
        from two1.wallet import Wallet
        from two1.bitserv.flask import Payment
        print(" -> [成功] two1 核心微支付模块成功导入")
        return True
    except ImportError as e:
        print(" -> [失败] 无法导入 two1 模块，错误: {}".format(e))
        print("    说明：本脚本需要在安装了 two1 库的设备上运行。")
        return False

def create_payment_app():
    from flask import Flask, jsonify, request
    from two1.wallet import Wallet
    from two1.bitserv.flask import Payment

    app = Flask(__name__)
    
    # 1. 初始化本地钱包
    # 本地开发测试时，这会读取设备本地存储的密钥对
    # 如果没有钱包配置文件，给出友好提示而不是直接崩溃
    try:
        wallet = Wallet()
    except Exception as e:
        print("\n[提示] 本地钱包初始化失败（可能尚未创建钱包）。")
        print("    错误详情: {}".format(e))
        print("    请在树莓派上运行 '21 mine' 或 'two1 mine' 先初始化钱包。")
        print("    在 PC 上测试时可忽略此错误，仅 example_wallet.py 中的离线功能可用。")
        return None

    # 2. 初始化微支付服务对象
    # 这将自动利用 402 Payment Required 机制配置路由保护
    payment = Payment(app, wallet)

    print("\n[2/3] 正在配置微支付路由...")

    # 3. 免费接口示例
    @app.route("/api/free")
    def free_endpoint():
        return jsonify({
            "status": "success",
            "message": "这是一个免费接口，无需支付任何 Satoshis。"
        })

    # 4. 付费接口示例 (使用 payment.required 装饰器)
    # price 设为 1000 satoshis (1000 聪)，大约等于 0.00001 BTC
    # 客户端在访问该接口时，如果请求头中没有携带合法的比特币支付凭证，
    # 服务端将自动返回 HTTP 402 Payment Required 响应，并附带支付发票/通道信息。
    @app.route("/api/premium")
    @payment.required(price=1000)
    def premium_endpoint():
        return jsonify({
            "status": "success",
            "message": "支付成功！这是被保护的收费数据：21BC1 ASIC 芯片内部核心代码的寄存器地址为...",
            "data": {
                "hashrate": "50 GH/s",
                "efficiency": "0.16 J/GH",
                "manufacturer": "Intel"
            }
        })

    # 5. 动态定价接口示例
    # 根据请求参数动态确定所需支付的 Satoshis
    # 注意：回调函数的第一个参数是 Flask request 对象。
    # 将参数命名改为 req 以避免与外层 flask import 的 request 变量名冲突。
    def get_dynamic_price(req, *args, **kwargs):
        # 比如：根据请求的 word 长度收费，每个字符收取 100 聪
        word = req.args.get("word", "")
        return len(word) * 100

    @app.route("/api/length-calculator")
    @payment.required(get_dynamic_price)
    def dynamic_endpoint():
        word = request.args.get("word", "")
        return jsonify({
            "status": "success",
            "word_length": len(word),
            "cost_paid": len(word) * 100
        })

    print(" -> [成功] 路由 /api/free 和 /api/premium 配置完毕。")
    return app

if __name__ == "__main__":
    print("=========================================")
    print("      21 Bitserv 本地 API 搭建示例        ")
    print("=========================================\n")
    
    if test_requirements():
        app = create_payment_app()
        if app is None:
            print("\n[中止] 因钱包初始化失败，无法启动 Flask 服务。")
            print("       请先在 21 Bitcoin Computer 上初始化钱包后再运行本脚本。")
        else:
            print("\n[3/3] 正在本地启动 Flask Web 服务...")
            print(" -> 服务将在 http://127.0.0.1:5000 运行")
            print(" -> 您可以通过局域网其他设备访问树莓派上的这个服务来进行微支付测试！")
            print(" -> 按 Ctrl+C 退出运行")
            
            # 启动 Flask 本地开发服务器
            # debug=True 可以在代码修改时自动重载
            try:
                app.run(host="0.0.0.0", port=5000, debug=False)
            except Exception as e:
                print(" -> 服务启动失败: {}".format(e))
