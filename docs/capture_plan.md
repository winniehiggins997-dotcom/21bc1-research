# 21BC1 Capture Plan

本文档用于指导 21BC1 / 21 Bitcoin Computer mining HAT 的安全抓包。
目标是确认 HAT 到 ASIC 的真实底层通信协议，而不是直接控制 ASIC。

## 目标

当前已经能离线复现：

```text
Swirl WorkNotification
  -> coinbase
  -> merkle root
  -> 80-byte block header
  -> SHA-256 midstate / second chunk / getwork-like 128-byte data
```

仍需真实抓包确认：

```text
ASIC transport frame
ASIC initialization sequence
nonce/result return frame
reset/enable timing
frequency/PLL/config commands
```

## 安全原则

- 先只监听，不主动发送数据。
- 先接 Raspberry Pi/HAT 主机侧信号，不直接碰 ASIC 裸信号侧。
- 逻辑分析仪阈值先按 3.3V 主机侧设置。
- 不要在散热器拆除状态下长时间上电。
- 不要随意写 MCP23008 寄存器。
- 抓包前拍照记录接线，抓包后记录环境和命令。

## 推荐设备

```text
逻辑分析仪: 8 通道或更多
采样率: 至少 10 MHz；若怀疑高速 SPI，优先 25 MHz 或更高
万用表: 确认 GND、3.3V、5V、风扇/核心电压测试点
原机或 Raspberry Pi: 尽量运行原始 two1/minerd 环境
```

## 第一阶段：只读 I2C 抓包

目的：确认 MCP23008 地址、寄存器读写、reset/enable/LED 相关控制线。

建议通道：

```text
CH0 = I2C SDA
CH1 = I2C SCL
CH2 = suspected reset/enable line, if visible
CH3 = status/interrupt line, if visible
GND = HAT/Pi common ground
```

建议抓包场景：

```text
capture_i2c_idle
capture_i2c_power_on
capture_i2c_minerd_start
capture_i2c_minerd_stop
```

需要记录：

```text
日期时间
供电方式
树莓派型号
系统镜像/软件版本
运行命令
MCP23008 地址
寄存器写入顺序
每次写入前后的板子状态
```

## 第二阶段：候选 SPI 抓包

目的：确认 Raspberry Pi SPI0 是否参与 ASIC work 下发或 nonce 返回。

候选引脚：

```text
SPI0 MOSI = Raspberry Pi physical pin 19 / BCM GPIO10
SPI0 MISO = Raspberry Pi physical pin 21 / BCM GPIO9
SPI0 SCLK = Raspberry Pi physical pin 23 / BCM GPIO11
SPI0 CE0  = Raspberry Pi physical pin 24 / BCM GPIO8
```

建议通道：

```text
CH0 = SCLK
CH1 = MOSI
CH2 = MISO
CH3 = CE0/CS
CH4 = reset/enable candidate
CH5 = interrupt/status candidate
GND = common ground
```

建议抓包场景：

```text
capture_spi_idle
capture_spi_minerd_start
capture_spi_work_dispatch
capture_spi_share_or_nonce_return
capture_spi_minerd_stop
```

导出格式：

```text
preferred: raw binary / hex bytes
also useful: CSV with timestamp, MOSI, MISO, CS, CLK
```

## 第三阶段：候选 UART 抓包

目的：确认 ASIC 是否使用类似串口链路的通信方式。

建议做法：

```text
1. 找疑似 TX/RX 或经过电平转换器的成对数据线。
2. 同时抓两条方向线。
3. 先自动波特率尝试，常见候选从 9600 到数 Mbps。
4. 比较 minerd 启动、work 下发、nonce 返回时是否有突发数据。
```

建议通道：

```text
CH0 = candidate TX/RX A
CH1 = candidate TX/RX B
CH2 = reset/enable candidate
CH3 = status/interrupt candidate
GND = common ground
```

## 第四阶段：字段匹配

抓包后，把同一时刻的 work 信息转成字段文件：

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 --enonce2 00000001 --nonce 0 \
  --fields-out examples/generated_trace_fields_midstate.json \
  --trace-out examples/generated_header_midstate.hex
```

然后匹配抓包数据：

```bash
python scripts/asic_trace_correlator.py capture.hex \
  --trace-format hex \
  --fields-json examples/generated_trace_fields_midstate.json \
  --min-field-size 4
```

优先关注这些字段：

```text
block_header
header_first64
header_tail16
sha256_midstate_bytes_be
sha256_second_chunk64
sha256_first_pass_128
getwork_data_like_128
merkle_root_internal
ntime_le
nbits_le
nonce_le
```

## 判断标准

如果匹配到：

```text
完整 80-byte block_header
```

则 ASIC transport 可能接收原始 header 或近似 header。

如果匹配到：

```text
sha256_midstate_bytes_be
sha256_second_chunk64
```

则 ASIC transport 可能接收 midstate + second chunk。

如果匹配到：

```text
sha256_first_pass_128
getwork_data_like_128
```

则 ASIC transport 可能接收 getwork 风格的 128 字节 first-pass input。

如果只匹配到短字段：

```text
ntime_le
nbits_le
nonce_le
work_id
```

还不能确认协议，需要结合帧头、长度、CRC、时序重复性继续分析。

## 抓包文件命名建议

```text
captures/
  2026-xx-xx/
    README.md
    i2c_idle.csv
    i2c_minerd_start.csv
    spi_minerd_start.csv
    uart_candidate_a.csv
    work_notification.json
    generated_trace_fields.json
    notes.md
```

不要把包含账号、钱包、公网 IP、私密矿池信息的原始抓包直接上传。

## 最小可交付资料

如果要让别人帮忙分析，至少提供：

```text
1. 抓包文件
2. 通道说明
3. 采样率
4. 抓包时运行的命令
5. 同一时间的 WorkNotification 或 generated_trace_fields.json
6. 板子供电和连接照片
7. 是否有风扇/LED/温度/日志变化
```
