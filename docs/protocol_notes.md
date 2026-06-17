# 21BC1 Protocol Notes

This document separates confirmed protocol layers from hypotheses. It is meant
to guide clean-room capture and decoding work for the 21BC1 mining HAT.

## Status

Confirmed:

- Bitcoin proof-of-work uses an 80-byte block header.
- Header hashes in the header are stored in internal byte order.
- Non-hash integer fields in the header are little-endian.
- The local `two1` source contains Swirl protobuf work/share messages.
- The local `two1` source contains Bitshare-specific coinbase padding logic.
- The local `two1` source computes a SHA-256 midstate over the first 64 bytes
  of the block header.

Unknown:

- The private HAT-to-ASIC transport frame format.
- Whether the physical transport is SPI, UART, parallel, or a mixed control bus.
- The ASIC reset/enable/frequency initialization sequence.
- Whether the ASIC receives raw header chunks, midstates, coinbase midstates, or
  a 21-specific packed work format.

## Layer Model

```text
Pool / server work
  -> Swirl WorkNotification
  -> coinb1 + enonce1 + enonce2 + coinb2
  -> Bitshare coinbase padding
  -> coinbase txid
  -> merkle root
  -> 80-byte block header
  -> SHA-256 first-64-byte midstate + second chunk
  -> ASIC transport frame
  -> nonce result
  -> Swirl submit_share_request
```

## Bitcoin Header Work

An 80-byte Bitcoin block header is:

```text
4  bytes version
32 bytes previous block header hash, internal byte order
32 bytes merkle root hash, internal byte order
4  bytes ntime
4  bytes nBits
4  bytes nonce
```

The first SHA-256 pass over an 80-byte header consumes two chunks:

```text
chunk 0: header[0:64]
chunk 1: header[64:80] + SHA256 padding for an 80-byte message
```

This makes the following fields especially important for ASIC work protocols:

```text
header_first64
header_tail16
sha256_midstate(header_first64)
sha256_second_chunk64
nonce
target / pool target
```

## 21 Swirl Wire Format

Swirl's outer framing, as implemented by local `two1/server/message_factory.py`,
is:

```text
2-byte big-endian protobuf payload length
protobuf payload
```

The protobuf top-level message uses `oneof` envelopes. Field numbers observed in
the generated local `two1/server/swirl_pb3.py` are:

```text
client auth_request          = 100
client submit_share_request  = 101

server auth_reply            = 200
server submit_share_reply    = 201
server work_notification     = 202
```

Auth request fields:

```text
1 hardware  enum: bitshare=0, generic=1
2 username  string
3 uuid      string
```

Successful auth reply fields:

```text
1 enonce1       bytes
2 enonce2_size  uint32
3 wallet_id     uint32
```

## 21 Swirl Work Fields

From local `two1/server/swirl_pb3.py` and `two1/commands/mine.py`, the work
notification field map is:

```text
1  work_id          uint32
2  version          uint32
3  prev_block_hash  bytes
4  height           uint32
5  nbits            uint32
6  ntime            uint32
7  coinb1           bytes
8  coinb2           bytes
9  merkle_edge      repeated bytes
10 new_block        bool
11 bits_pool        uint32
```

The CPU mining path reconstructs:

```text
coinbase = coinb1 + enonce1 + enonce2 + coinb2
coinbase_hash = double_sha256(coinbase)
merkle_root = fold_double_sha256(coinbase_hash, merkle_edge)
block_header = version + prev_block_hash + merkle_root + ntime + nbits + nonce
```

Share submission fields:

```text
1 message_id  uint32
2 work_id     uint32
3 enonce2     bytes
4 otime       uint32
5 nonce       uint32
```

Share submit reply includes the original `message_id` and a status enum:

```text
good      = 0
bad       = 1
stale     = 2
duplicate = 3
```

Important boundary: this Swirl layer is the pool/server protocol. It tells us
what work means and how a share is reported, but it does not directly reveal
the private electrical frame sent to the HAT ASIC.

## Bitshare Padding

Local `two1/bitcoin/coinbase.py` contains Bitshare-specific padding. Its purpose
is to make a client-serialized coinbase segment align to a 512-bit boundary.

The practical meaning for protocol reverse engineering:

- The ASIC may not receive full `coinb1/coinb2`.
- The host may precompute coinbase-related SHA-256 state.
- Captures should search for both coinbase-derived hashes and block-header
  derived fields.

## Public Mining Protocol Analogs

These public protocols are not the 21BC1 private ASIC transport, but they are
useful references for what mining work usually looks like before it reaches
hardware.

### getwork

Bitcoin Wiki's `getwork` page describes an older JSON-RPC mining protocol. Its
work `data` field is a preprocessed SHA-256 input in little-endian 32-bit word
order. To recover the normal 80-byte Bitcoin header from that format, each
32-bit word must be byte-swapped and the SHA-256 padding removed.

Important points for 21BC1 capture work:

```text
getwork data ~= 80-byte header + SHA-256 padding, with 32-bit word byte swaps
nonce offset = bytes 76..79 of the 80-byte header
common optimization = precompute SHA-256 midstate for the first 512-bit chunk
optional noncerange = start/end nonce range
```

This reinforces the need to search captures for:

```text
block_header
sha256_first_pass_128
getwork_data_like_128
sha256_midstate_bytes_be
sha256_second_chunk64
nonce_le
nonce ranges
```

`scripts/sha256_midstate.py` and `scripts/compact_block_builder.py` now export
`sha256_first_pass_128` and `getwork_data_like_128` for this reason.

### Stratum V1

Stratum V1's `mining.notify` work model carries:

```text
job id
previous block hash
generation transaction part 1
generation transaction part 2
merkle branches
block version
nBits
nTime
clean jobs flag
```

Client share submission carries:

```text
worker name
job id
ExtraNonce2
nTime
nOnce
```

This is structurally close to 21 Swirl's work/share fields:

```text
Stratum: coinb1 + extranonce1 + extranonce2 + coinb2 + merkle branches
Swirl:   coinb1 + enonce1     + enonce2     + coinb2 + merkle_edge
```

The important conclusion is not that 21BC1 uses Stratum; it does not at the
local `two1` layer. The important conclusion is that Swirl exposes enough data
to reconstruct the same Bitcoin mining work objects that modern Stratum miners
also reconstruct before feeding ASICs.

## Candidate ASIC Work Frame Fields

Local `two1/bitcoin/block.py` computes a midstate from:

```text
bytes(block_header)[0:64]
```

That is a strong clue that the low-level miner path needs the SHA-256 midstate
for the first block-header chunk. It is still not proof of the exact ASIC frame:
the transport could carry the midstate directly, a word-swapped midstate, raw
header chunks, or a compact 21-specific work structure.

Likely fields to search for in captures:

```text
work_id / job id
version_le
prev_block_hash_internal
merkle_root_internal
ntime_le
nbits_le
nonce start / nonce range / nonce mask
target or difficulty bits
header_first64
header_tail16
sha256_midstate words
sha256_second_chunk64 words
sha256_first_pass_128
getwork_data_like_128
```

Less certain, but worth checking:

```text
coinbase_hash_internal
coinbase midstate
enonce2
frequency / PLL register writes
reset / enable command frames
CRC / checksum / sequence number
```

What a useful capture match would look like:

```text
case A: raw header protocol
  header_first64 and header_tail16 appear directly or word-swapped.

case B: midstate protocol
  sha256_midstate words and sha256_second_chunk64 appear directly or
  word-swapped, while the full 80-byte header does not appear.

case C: getwork-like internal protocol
  a 128-byte padded SHA-256 first-pass input appears, likely with 32-bit
  word byte swaps.

case D: higher-level compact protocol
  coinbase/merkle/header-derived fields appear mixed with command bytes,
  lengths, job id, sequence numbers, or checksums.
```

## Capture Strategy

1. Capture I2C during idle, startup, and `minerd` start.
2. Identify MCP23008 register writes and any reset/enable timing.
3. Capture the bus between Raspberry Pi side and the level translator.
4. Record the exact Swirl work fields at the same time as the bus capture.
5. Generate `trace_fields` using `scripts/compact_block_builder.py`.
6. Generate SHA-256 midstate data using `scripts/sha256_midstate.py`.
7. Use `scripts/asic_trace_correlator.py` to search trace data.
8. Only after passive matching, attempt safe replay on sacrificial hardware.

## Tools

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 --enonce2 00000001 --nonce 0 \
  --fields-out examples/generated_trace_fields.json \
  --trace-out examples/generated_header.hex

python scripts/sha256_midstate.py --header-file examples/generated_header.hex

python scripts/asic_trace_correlator.py examples/generated_header.hex \
  --trace-format hex \
  --fields-json examples/generated_trace_fields.json \
  --min-field-size 4
```

`compact_block_builder.py` also exports `sha256_midstate_bytes_be` and
`sha256_second_chunk64` in its `trace_fields` output. It also exports
`sha256_first_pass_128` and `getwork_data_like_128` to help test older
getwork-style internal byte layouts.

For the midstate-focused generated example files:

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 --enonce2 00000001 --nonce 0 \
  --fields-out examples/generated_trace_fields_midstate.json \
  --trace-out examples/generated_header_midstate.hex

python scripts/asic_trace_correlator.py examples/generated_header_midstate.hex \
  --trace-format hex \
  --fields-json examples/generated_trace_fields_midstate.json \
  --min-field-size 4
```

Expected interpretation for that synthetic test: fields that are literally
inside the 80-byte header should match, while `sha256_midstate_bytes_be` and
`sha256_second_chunk64` should not match the raw header. In real ASIC bus
captures, seeing those midstate fields would support the midstate protocol
hypothesis.

## Clean-Room Notes

- Do not copy third-party miner implementations into this repository unless
  their license is compatible and attribution is explicit.
- Prefer short explanations plus source links.
- Treat local `two1_source/` as research input, not as code to redistribute
  wholesale.
- Keep captured bus traces, derived field maps, and independent decoders
  separate from vendor source.

## References

Bitcoin block header and nBits reference:

Link: https://developer.bitcoin.org/reference/block_chain.html

Bitcoin transaction reference:

Link: https://developer.bitcoin.org/reference/transactions.html

Bitcoin Core `getblocktemplate` reference:

Link: https://developer.bitcoin.org/reference/rpc/getblocktemplate.html

cgminer ASIC device support notes:

Link: https://github.com/ckolivas/cgminer

cgminer ASIC README:

Link: https://raw.githubusercontent.com/ckolivas/cgminer/master/ASIC-README

ESP-Miner project:

Link: https://github.com/bitaxeorg/ESP-Miner

Bitaxe project:

Link: https://github.com/bitaxeorg/bitaxe

Bitcoin Wiki `getwork` reference:

Link: https://en.bitcoin.it/wiki/Getwork

Bitcoin Wiki Stratum mining protocol reference:

Link: https://en.bitcoin.it/wiki/Stratum_mining_protocol

PyPI `two1` package metadata:

Link: https://pypi.org/project/two1/3.10.9/
