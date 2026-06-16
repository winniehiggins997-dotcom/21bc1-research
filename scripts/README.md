# 21BC1 Research Scripts

These helpers are intentionally conservative.

- `decode_swirl_message.py`: offline decoder for 21 Swirl protobuf frames.
- `bitshare_padding_calc.py`: reproduces the Bitshare coinbase padding rule from `two1/bitcoin/coinbase.py`.
- `asic_trace_correlator.py`: scans a captured byte stream for known work fields.
- `compact_block_builder.py`: builds coinbase, merkle root, block header, and trace fields from a Swirl-like work JSON.
- `read_mcp23008.py`: read-only MCP23008 register dump for Raspberry Pi/Linux SBCs.

None of these scripts writes to ASIC control lines. `read_mcp23008.py` only reads registers.

Example loop:

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 --enonce2 00000001 --nonce 0 \
  --fields-out examples/generated_trace_fields.json \
  --trace-out examples/generated_header.hex

python scripts/asic_trace_correlator.py examples/generated_header.hex \
  --trace-format hex --fields-json examples/generated_trace_fields.json \
  --min-field-size 4
```
