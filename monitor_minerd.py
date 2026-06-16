# -*- coding: utf-8 -*-
"""
21 Bitcoin Computer - minerd 守护进程实时状态监控脚本
本脚本通过监听 /tmp/minerd.sock 套接字，实时接收并解析 minerd 矿工进程发送的原始 JSON 事件。
可用于观测挖矿算力、芯片温度、提交的 Shares 状态以及底层硬件运行事件。
"""

import os
import sys
import socket
import json
from datetime import datetime

# 平台兼容性警告：socket.AF_UNIX 在 Windows 上不可用，本脚本仅能在 Linux/macOS 上运行
if sys.platform == 'win32':
    print("[警告] 本脚本使用 AF_UNIX 套接字，仅支持 Linux/macOS 平台。Windows 上无法运行！")
    sys.exit(1)

MINERD_SOCK = '/tmp/minerd.sock'

def monitor_minerd():
    if not os.path.exists(MINERD_SOCK):
        print("[错误] 未找到套接字文件: {}".format(MINERD_SOCK))
        print("请确保 21 矿工后台进程已启动。运行命令启动：")
        print("  sudo minerd -u <您的用户名> <矿池地址>")
        sys.exit(1)

    print("==================================================")
    print("       21 Bitcoin Computer 状态实时监控器")
    print("       正在连接 {} ...".format(MINERD_SOCK))
    print("==================================================\n")

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(MINERD_SOCK)
        print(" -> [成功] 已成功连接到 minerd 套接字。正在等待事件数据...\n")
    except Exception as e:
        print(" -> [失败] 无法连接到套接字: {}".format(e))
        sys.exit(1)

    buf = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                print("\n[提示] minerd 服务端已断开连接。")
                break
            
            buf += chunk
            while b"\n" in buf:
                pos = buf.find(b"\n")
                data = buf[0:pos].decode('utf-8', errors='ignore')
                buf = buf[pos+1:]
                
                if not data:
                    continue
                
                try:
                    event = json.loads(data)
                    parse_event(event)
                except json.JSONDecodeError:
                    print("[警告] 无法解析 JSON 数据: {}".format(data))
    except KeyboardInterrupt:
        print("\n监控被用户中止。正在退出...")
    finally:
        s.close()

def parse_event(event):
    event_type = event.get("type", "UnknownEvent")
    # timestamp 字段从事件中读取，备用（目前我们用本地时间更为清晰）
    # timestamp = event.get("timestamp", "")
    payload = event.get("payload", {})
    
    # 格式化时间戳
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("[{}] 收到事件: {}".format(time_str, event_type))
    
    if event_type == "StatisticsEvent":
        stats = payload.get("statistics", {})
        uptime = stats.get("uptime", 0)
        hashrate = stats.get("hashrate", {})
        temp = stats.get("temp", "N/A") # 如果 minerd 支持温度传感器读取的话
        
        # 将运行秒数转换为小时/分钟
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = "{:02d}小时{:02d}分钟{:02d}秒".format(int(hours), int(minutes), int(seconds))
        
        print("  |-- 运行时间 (Uptime): {}".format(uptime_str))
        print("  |-- 当前温度 (Temp):   {} °C".format(temp))
        print("  |-- 5分钟平均算力:     {:.2f} GH/s".format(hashrate.get("5min", 0) / 1e9))
        print("  |-- 15分钟平均算力:    {:.2f} GH/s".format(hashrate.get("15min", 0) / 1e9))
        print("  |-- 60分钟平均算力:    {:.2f} GH/s".format(hashrate.get("60min", 0) / 1e9))
        print("  |-----------------------------------------------")
        
    elif event_type == "ShareSubmitEvent":
        share = payload.get("share", {})
        result = payload.get("result", "Unknown")
        print("  |-- 提交结果: {}".format(result))
        print("  |-- Work ID:  {}".format(share.get("work_id", "")))
        print("  |-- Nonce:    {}".format(share.get("nonce", "")))
        print("  |-----------------------------------------------")
        
    else:
        # 其他类型事件直接打印 payload
        print(json.dumps(payload, indent=4, ensure_ascii=False))
        print("  |-----------------------------------------------")

if __name__ == "__main__":
    monitor_minerd()
