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
