# File Inventory

This document explains the current one-folder-per-purpose repository layout.

## Top Level

| Path | Purpose | Public release note |
| --- | --- | --- |
| `README.md` | Project entry point, current status, folder layout, quick commands. | Safe to publish. |
| `LICENSE` | Repository license. | Safe to publish. |
| `.gitignore` | Keeps local research inputs and private captures out of Git. | Safe to publish. |

## `docs/`

| Path | Purpose | Public release note |
| --- | --- | --- |
| `docs/protocol_notes.md` | Clean protocol notes: Swirl, Bitshare, Bitcoin header, midstate, ASIC transport hypotheses. | Safe to publish. |
| `docs/capture_plan.md` | Safe capture plan for I2C/SPI/UART and ASIC work-field matching. | Safe to publish. |
| `docs/decoder_design.md` | Staged design for trace decoder and future ASIC protocol decoder. | Safe to publish. |
| `docs/development_log.md` | Full running development log and research history. | Safe to publish after checking for personal data. |
| `docs/FILE_INVENTORY.md` | This repository map. | Safe to publish. |

## `scripts/`

| Path | Purpose | Safety |
| --- | --- | --- |
| `scripts/decode_swirl_message.py` | Offline decoder for captured Swirl protobuf frames. | Read-only/offline. |
| `scripts/bitshare_padding_calc.py` | Reproduces Bitshare coinbase padding calculations. | Offline. |
| `scripts/compact_block_builder.py` | Builds coinbase, merkle root, 80-byte header, trace fields, and midstate fields from a Swirl-like JSON file. | Offline. |
| `scripts/sha256_midstate.py` | Pure-Python SHA-256 compression helper for Bitcoin block-header midstate analysis. | Offline. |
| `scripts/asic_trace_correlator.py` | Searches captured byte traces for known work/header/midstate fields. | Offline. |
| `scripts/read_mcp23008.py` | Read-only MCP23008 register dump for Raspberry Pi/Linux SBCs. | Hardware read-only. |
| `scripts/README.md` | Script usage guide. | Safe to publish. |

These scripts intentionally avoid writing ASIC control lines. The only hardware
script currently included is a read-only MCP23008 register dump.

## `examples/`

| Path | Purpose | Public release note |
| --- | --- | --- |
| `examples/work_notification_minimal.json` | Minimal Swirl-like work example. | Safe to publish. |
| `examples/capture_fields_template.json` | Field template for bus-trace matching. | Safe to publish. |
| `examples/generated_header.hex` | Generated 80-byte block-header sample. | Safe to publish. |
| `examples/generated_trace_fields.json` | Generated trace-field sample. | Safe to publish. |
| `examples/generated_header_midstate.hex` | Generated midstate-focused 80-byte header sample. | Safe to publish. |
| `examples/generated_trace_fields_midstate.json` | Generated trace fields including SHA-256 midstate and second chunk. | Safe to publish. |

The generated files are synthetic test vectors, not real mining secrets.

## `demos/`

| Path | Purpose | Public release note |
| --- | --- | --- |
| `demos/example_wallet.py` | Wallet/API compatibility demo for the old `two1` Python package. | Safe if no private keys or mnemonic output are committed. |
| `demos/payment_api_demo.py` | Payment API demo code. | Safe after checking for credentials/endpoints. |
| `demos/monitor_minerd.py` | Reads/monitors the old minerd Unix socket event stream. | Safe to publish. |

## `assets/images/`

| Path | Purpose | Public release note |
| --- | --- | --- |
| `assets/images/` | Board photos, manual images, chip/interface references. | Safe if the images are yours or you have permission to publish them. |

The old Chinese-named image folder has been merged into `assets/images/` for
easier cross-platform tooling.

## `reference/`

| Path | Purpose | Public release note |
| --- | --- | --- |
| `reference/two1-package-metadata/` | Local copy of old `two1` package metadata files. | Ignored by default; review license before publishing. |

For clean-room open-source work, keep notes, independent tools, and short
references in this repository. Avoid redistributing third-party source trees
unless the license and attribution are fully handled.

## Ignored Local Research Inputs

These paths are useful locally but should not be uploaded by default:

```text
two1_source/
two1_download/
reference/two1-package-metadata/
captures/private/
*.sal
*.logicdata
```

## Current Protocol Boundary

Known and implemented:

```text
Swirl WorkNotification
  -> coinb1 + enonce1 + enonce2 + coinb2
  -> Bitshare padding
  -> coinbase txid
  -> merkle root
  -> 80-byte block header
  -> SHA-256 midstate + second chunk
```

Unknown and still needs capture:

```text
ASIC transport frame
ASIC initialization commands
nonce/result return frame
```

## Suggested Public Upload Set

Include:

```text
README.md
LICENSE
docs/
scripts/
examples/
demos/
assets/images/
```

Exclude unless license/privacy has been checked:

```text
two1_source/
two1_download/
reference/two1-package-metadata/
private captures
credentials
wallet mnemonics
copied third-party source
```
