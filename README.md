# 21bc1-research

21 Bitcoin Computer / 21BC1 mining HAT research notes and clean-room helper
tools.

This repository is focused on understanding the board, documenting what is
known, and preparing safe protocol reverse-engineering tools. It does not yet
contain a complete ASIC driver.

## Current Status

Confirmed and reproducible:

- Swirl pool/server work and share message structure.
- Bitshare coinbase padding rule.
- Bitcoin coinbase, merkle root, 80-byte block header construction.
- SHA-256 first-64-byte midstate and second chunk generation.
- Offline field matching against byte traces.
- Read-only MCP23008 register dump helper for Raspberry Pi/Linux SBCs.

Still unknown:

- Private HAT-to-ASIC transport frame format.
- Whether the ASIC data path is SPI, UART, parallel, or mixed.
- ASIC reset/enable/frequency initialization sequence.
- Exact nonce/result return frame.

## Recommended Reading Order

1. [docs/protocol_notes.md](docs/protocol_notes.md): protocol layer model,
   Swirl fields, midstate hypothesis, capture strategy.
2. [docs/FILE_INVENTORY.md](docs/FILE_INVENTORY.md): file-by-file inventory
   and open-source notes.
3. [scripts/README.md](scripts/README.md): helper script usage.
4. [docs/development_log.md](docs/development_log.md): full running
   development log.

## Folder Layout

| Folder | Content |
| --- | --- |
| `docs/` | Protocol notes, file inventory, development log. |
| `scripts/` | Offline protocol, midstate, trace, and safe hardware-read helpers. |
| `examples/` | Synthetic work examples and generated test vectors. |
| `demos/` | Old `two1` wallet/payment/minerd demo scripts. |
| `assets/images/` | Board photos and manual images. |
| `reference/` | Local-only third-party reference metadata; ignored by default. |

## Quick Protocol Test

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 --enonce2 00000001 --nonce 0 \
  --fields-out examples/generated_trace_fields_midstate.json \
  --trace-out examples/generated_header_midstate.hex

python scripts/sha256_midstate.py --header-file examples/generated_header_midstate.hex

python scripts/asic_trace_correlator.py examples/generated_header_midstate.hex \
  --trace-format hex \
  --fields-json examples/generated_trace_fields_midstate.json \
  --min-field-size 4
```

Expected result: raw block-header fields match inside the 80-byte header;
derived fields such as SHA-256 midstate do not appear inside the raw header.
If those derived fields appear in a real ASIC bus capture, that supports the
midstate-work-frame hypothesis.

## Open-Source Boundary

This project should keep explanations, independent tools, measurements, images,
and links. Do not copy third-party miner implementations or proprietary vendor
source into the public repository unless the license allows it and attribution
is clear.

`two1_source/`, `two1_download/`, and `reference/two1-package-metadata/` are
local research inputs and are ignored by Git by default.

---

## 中文说明

这是一个围绕 **21 Bitcoin Computer / 21BC1 挖矿 HAT 模块** 的研究仓库。
目标是整理硬件资料、协议资料、可复现实验脚本，以及后续开发驱动所需的
clean-room 逆向分析工具。

目前这个仓库**还不是完整 ASIC 驱动**。它更像是开发前的资料库和工具箱：
先把能确认的内容整理清楚，再通过逻辑分析仪抓包确认真正的 HAT 到 ASIC
底层通信协议。

## 当前已经能确认和复现的内容

- Swirl 矿池/服务器 work 与 share 消息结构。
- Bitshare coinbase padding 规则。
- Bitcoin coinbase、merkle root、80 字节 block header 构造。
- SHA-256 first-64-byte midstate 与 second chunk 生成。
- 使用离线工具在抓包字节流中匹配 header / midstate / nonce 等字段。
- Raspberry Pi / Linux SBC 上只读 MCP23008 寄存器的辅助脚本。

## 当前仍未知的内容

- HAT 到 ASIC 的私有 transport frame 格式。
- ASIC 主数据通道到底是 SPI、UART、并口，还是混合控制总线。
- ASIC reset / enable / frequency 初始化序列。
- nonce / result 返回帧格式。

## 推荐阅读顺序

1. [docs/protocol_notes.md](docs/protocol_notes.md)：协议分层、Swirl 字段、
   midstate 假设、抓包策略。
2. [docs/FILE_INVENTORY.md](docs/FILE_INVENTORY.md)：所有文件和目录用途。
3. [scripts/README.md](scripts/README.md)：脚本使用方法。
4. [docs/development_log.md](docs/development_log.md)：完整开发记录。

## 目录说明

| 目录 | 内容 |
| --- | --- |
| `docs/` | 协议说明、文件清单、开发日志。 |
| `scripts/` | 离线协议工具、midstate 工具、trace 匹配工具、安全只读硬件工具。 |
| `examples/` | 合成 work 示例和生成的测试向量。 |
| `demos/` | 旧 `two1` 钱包、支付、minerd 监听示例。 |
| `assets/images/` | 硬件照片和说明书图片。 |
| `reference/` | 本地参考资料，默认不上传。 |

## 快速协议测试

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 --enonce2 00000001 --nonce 0 \
  --fields-out examples/generated_trace_fields_midstate.json \
  --trace-out examples/generated_header_midstate.hex

python scripts/sha256_midstate.py --header-file examples/generated_header_midstate.hex

python scripts/asic_trace_correlator.py examples/generated_header_midstate.hex \
  --trace-format hex \
  --fields-json examples/generated_trace_fields_midstate.json \
  --min-field-size 4
```

预期结果：原始 80 字节 block header 里的字段可以被匹配到；SHA-256
midstate 这类派生字段不会直接出现在原始 header 中。后续如果在真实 ASIC
总线抓包里看到这些 midstate 字段，就能支持“ASIC 接收 midstate + second
chunk”的候选模型。

## 开源边界

本仓库建议保留：解释文档、独立工具、测量结果、自己拍摄的图片、公开资料链接。

不建议直接上传：第三方矿机项目源码、厂商私有源码、钱包助记词、账号凭据、
私密抓包、未确认授权的资料。

`two1_source/`、`two1_download/`、`reference/two1-package-metadata/` 都是本地
研究输入，默认已经被 `.gitignore` 忽略。
