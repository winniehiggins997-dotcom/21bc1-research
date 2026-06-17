#!/usr/bin/env python3
"""Compute SHA-256 midstate data used by Bitcoin mining ASIC protocols.

For an 80-byte Bitcoin block header, SHA-256 processes two 64-byte chunks.
ASIC protocols often transmit the state after the first 64 bytes plus the
second chunk containing header_tail16, padding, and the message length.
"""
import argparse
import hashlib
import json
import struct


IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]

K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xffffffff


def compress(chunk, state=None):
    if len(chunk) != 64:
        raise ValueError("SHA-256 chunk must be exactly 64 bytes")
    if state is None:
        state = IV

    w = list(struct.unpack(">16I", chunk))
    for i in range(16, 64):
        s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xffffffff)

    a, b, c, d, e, f, g, h = state
    for i in range(64):
        s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
        ch = (e & f) ^ ((~e) & g)
        temp1 = (h + s1 + ch + K[i] + w[i]) & 0xffffffff
        s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (s0 + maj) & 0xffffffff
        h, g, f = g, f, e
        e = (d + temp1) & 0xffffffff
        d, c, b = c, b, a
        a = (temp1 + temp2) & 0xffffffff

    return [
        (state[0] + a) & 0xffffffff,
        (state[1] + b) & 0xffffffff,
        (state[2] + c) & 0xffffffff,
        (state[3] + d) & 0xffffffff,
        (state[4] + e) & 0xffffffff,
        (state[5] + f) & 0xffffffff,
        (state[6] + g) & 0xffffffff,
        (state[7] + h) & 0xffffffff,
    ]


def clean_hex(value):
    return "".join(str(value).strip().split()).lower()


def second_chunk_for_80_byte_header(header_tail16):
    if len(header_tail16) != 16:
        raise ValueError("header_tail16 must be exactly 16 bytes")
    return header_tail16 + b"\x80" + bytes(39) + struct.pack(">Q", 80 * 8)


def state_to_bytes(state):
    return b"".join(struct.pack(">I", word) for word in state)


def words_le_hex(state):
    return [struct.pack("<I", word).hex() for word in state]


def word32_byteswapped(data):
    if len(data) % 4:
        raise ValueError("data length must be a multiple of 4")
    return b"".join(data[i:i + 4][::-1] for i in range(0, len(data), 4))


def analyse_header(header):
    if len(header) != 80:
        raise ValueError("Bitcoin block header must be exactly 80 bytes")

    first64 = header[:64]
    tail16 = header[64:]
    midstate = compress(first64)
    second_chunk = second_chunk_for_80_byte_header(tail16)
    first_pass_128 = first64 + second_chunk
    first_sha_state = compress(second_chunk, midstate)
    first_sha_digest = state_to_bytes(first_sha_state)
    hashlib_first = hashlib.sha256(header).digest()
    block_hash = hashlib.sha256(first_sha_digest).digest()

    return {
        "header_size": len(header),
        "header_hex": header.hex(),
        "header_first64": first64.hex(),
        "header_tail16": tail16.hex(),
        "sha256_midstate_words_be": [f"{word:08x}" for word in midstate],
        "sha256_midstate_words_le": words_le_hex(midstate),
        "sha256_midstate_bytes_be": state_to_bytes(midstate).hex(),
        "sha256_second_chunk64": second_chunk.hex(),
        "sha256_second_chunk_words_be": [
            f"{word:08x}" for word in struct.unpack(">16I", second_chunk)
        ],
        "sha256_first_pass_128": first_pass_128.hex(),
        "getwork_data_like_128": word32_byteswapped(first_pass_128).hex(),
        "first_sha256_digest": first_sha_digest.hex(),
        "first_sha256_digest_matches_hashlib": first_sha_digest == hashlib_first,
        "block_hash_internal": block_hash.hex(),
        "block_hash_rpc": block_hash[::-1].hex(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--header-hex", help="80-byte block header as hex")
    parser.add_argument("--header-file", help="file containing 80-byte block header hex or binary")
    parser.add_argument("--binary", action="store_true", help="treat --header-file as binary")
    args = parser.parse_args()

    if args.header_file:
        raw = open(args.header_file, "rb").read()
        header = raw if args.binary else bytes.fromhex(clean_hex(raw.decode()))
    elif args.header_hex:
        header = bytes.fromhex(clean_hex(args.header_hex))
    else:
        parser.error("provide --header-hex or --header-file")

    print(json.dumps(analyse_header(header), indent=2))


if __name__ == "__main__":
    main()
