#!/usr/bin/env python3
"""Build Bitcoin mining fields from a Swirl-like work JSON file.

This helper is offline and does not talk to hardware. It is meant to generate
known byte patterns for `asic_trace_correlator.py`.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def clean_hex(value):
    if value is None:
        return ""
    return "".join(str(value).strip().split()).lower()


def hex_to_bytes(value, name):
    value = clean_hex(value)
    if len(value) % 2:
        raise ValueError(f"{name} hex length must be even")
    return bytes.fromhex(value)


def u32_le(value):
    return struct.pack("<I", int(value) & 0xffffffff)


def dhash(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def rpc_hash(internal_hash):
    return internal_hash[::-1].hex()


def bits_to_target(bits):
    bits = int(bits)
    shift = bits >> 24
    coefficient = bits & 0x00ffffff
    if shift <= 3:
        return coefficient >> (8 * (3 - shift))
    return coefficient * (1 << (8 * (shift - 3)))


def build_from_work(work, enonce1, enonce2, nonce):
    coinb1 = hex_to_bytes(work["coinb1"], "coinb1")
    coinb2 = hex_to_bytes(work["coinb2"], "coinb2")
    prev_block_hash = hex_to_bytes(work["prev_block_hash"], "prev_block_hash")
    if len(prev_block_hash) != 32:
        raise ValueError("prev_block_hash must be 32 bytes in internal byte order")

    merkle_edge = [hex_to_bytes(item, "merkle_edge") for item in work.get("merkle_edge", [])]
    for item in merkle_edge:
        if len(item) != 32:
            raise ValueError("each merkle_edge item must be 32 bytes")

    coinbase = coinb1 + enonce1 + enonce2 + coinb2
    coinbase_hash = dhash(coinbase)

    merkle_root = coinbase_hash
    for edge in merkle_edge:
        merkle_root = dhash(merkle_root + edge)

    version = int(work["version"])
    ntime = int(work["ntime"])
    nbits = int(work["nbits"])
    header = (
        u32_le(version)
        + prev_block_hash
        + merkle_root
        + u32_le(ntime)
        + u32_le(nbits)
        + u32_le(nonce)
    )
    if len(header) != 80:
        raise AssertionError("block header must be 80 bytes")

    block_hash_internal = dhash(header)
    target = bits_to_target(nbits)
    pool_target = bits_to_target(work.get("bits_pool", nbits))
    hash_int_little = int.from_bytes(block_hash_internal, "little")

    trace_fields = {
        "version_le": u32_le(version).hex(),
        "prev_block_hash_internal": prev_block_hash.hex(),
        "prev_block_hash_rpc": rpc_hash(prev_block_hash),
        "coinbase_hash_internal": coinbase_hash.hex(),
        "coinbase_hash_rpc": rpc_hash(coinbase_hash),
        "merkle_root_internal": merkle_root.hex(),
        "merkle_root_rpc": rpc_hash(merkle_root),
        "ntime_le": u32_le(ntime).hex(),
        "nbits_le": u32_le(nbits).hex(),
        "nonce_le": u32_le(nonce).hex(),
        "block_header": header.hex(),
        "header_first64": header[:64].hex(),
        "header_tail16": header[64:].hex(),
        "block_hash_internal": block_hash_internal.hex(),
        "block_hash_rpc": rpc_hash(block_hash_internal),
    }

    return {
        "work_id": work.get("work_id"),
        "height": work.get("height"),
        "version": version,
        "ntime": ntime,
        "nbits": nbits,
        "bits_pool": int(work.get("bits_pool", nbits)),
        "nonce": int(nonce),
        "enonce1": enonce1.hex(),
        "enonce2": enonce2.hex(),
        "coinbase_size": len(coinbase),
        "coinbase": coinbase.hex(),
        "target_hex": f"{target:064x}",
        "pool_target_hex": f"{pool_target:064x}",
        "hash_int_little_hex": f"{hash_int_little:064x}",
        "meets_block_target": hash_int_little < target,
        "meets_pool_target": hash_int_little < pool_target,
        "trace_fields": trace_fields,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_json", help="JSON file with WorkNotification-like fields")
    parser.add_argument("--enonce1", required=True, help="extra nonce 1 as hex")
    parser.add_argument("--enonce2", required=True, help="extra nonce 2 as hex")
    parser.add_argument("--nonce", type=lambda x: int(x, 0), default=0)
    parser.add_argument("--fields-out", help="write trace_fields JSON for asic_trace_correlator")
    parser.add_argument("--trace-out", help="write the generated 80-byte block header as hex")
    args = parser.parse_args()

    work = json.loads(Path(args.work_json).read_text(encoding="utf-8"))
    result = build_from_work(
        work,
        hex_to_bytes(args.enonce1, "enonce1"),
        hex_to_bytes(args.enonce2, "enonce2"),
        args.nonce,
    )

    if args.fields_out:
        Path(args.fields_out).write_text(
            json.dumps(result["trace_fields"], indent=2) + "\n",
            encoding="utf-8",
        )
    if args.trace_out:
        Path(args.trace_out).write_text(result["trace_fields"]["block_header"] + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
