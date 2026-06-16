#!/usr/bin/env python3
"""Calculate 21 Bitshare coinbase padding from a client-serialized length."""
import argparse
import json


def bitshare_padding(client_serialize_len):
    cb1_len_bits = client_serialize_len * 8
    num_bits_padding = (512 - (cb1_len_bits % 512)) % 512
    if num_bits_padding % 8:
        raise ValueError("padding is not byte-aligned")

    num_bytes_padding = num_bits_padding // 8
    if num_bytes_padding == 0:
        padding = b""
    elif num_bytes_padding == 1:
        padding = b"\x00"
    else:
        padding = bytes([num_bytes_padding - 1]) + bytes(num_bytes_padding - 1)
    return cb1_len_bits, num_bits_padding, padding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-serialize-len",
        type=int,
        required=True,
        help="length in bytes after removing the Bitshare output and locktime",
    )
    args = parser.parse_args()

    cb1_len_bits, padding_bits, padding = bitshare_padding(args.client_serialize_len)
    print(json.dumps({
        "client_serialize_len": args.client_serialize_len,
        "client_serialize_bits": cb1_len_bits,
        "padding_len": len(padding),
        "padding_bits": padding_bits,
        "padding_hex": padding.hex(),
        "aligned_len": args.client_serialize_len + len(padding),
        "aligned_bits": (args.client_serialize_len + len(padding)) * 8,
        "aligned_to_512_bits": ((args.client_serialize_len + len(padding)) * 8) % 512 == 0,
    }, indent=2))


if __name__ == "__main__":
    main()
