#!/usr/bin/env python3
"""Find known work fields inside a captured ASIC byte stream.

The tool is intentionally simple: give it a binary/hex trace and known fields,
and it reports offsets for direct, reversed-byte, and 32-bit word-swapped forms.
"""
import argparse
import binascii
import json
from pathlib import Path


def parse_hex(s):
    cleaned = "".join(str(s).strip().split())
    if not cleaned:
        return b""
    return binascii.unhexlify(cleaned)


def read_trace(path, fmt):
    data = Path(path).read_bytes()
    if fmt == "bin":
        return data
    if fmt == "hex":
        return parse_hex(data.decode())
    raise ValueError("trace format must be bin or hex")


def reverse_words_32(data):
    if len(data) % 4:
        return None
    words = [data[i:i + 4] for i in range(0, len(data), 4)]
    return b"".join(word[::-1] for word in words)


def find_all(haystack, needle):
    offsets = []
    start = 0
    while True:
        pos = haystack.find(needle, start)
        if pos == -1:
            return offsets
        offsets.append(pos)
        start = pos + 1


def variants(field_bytes):
    result = {"direct": field_bytes}
    result["byte_reversed"] = field_bytes[::-1]
    word_swapped = reverse_words_32(field_bytes)
    if word_swapped is not None:
        result["word32_byte_reversed"] = word_swapped
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", help="captured trace file")
    parser.add_argument("--trace-format", choices=["bin", "hex"], default="bin")
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="NAME=HEX",
        help="known field to search; can be repeated",
    )
    parser.add_argument("--fields-json", help="JSON file containing {name: hex}")
    parser.add_argument(
        "--min-field-size",
        type=int,
        default=1,
        help="skip fields shorter than this many bytes",
    )
    args = parser.parse_args()

    trace = read_trace(args.trace, args.trace_format)
    fields = {}
    if args.fields_json:
        fields.update(json.loads(Path(args.fields_json).read_text(encoding="utf-8")))
    for item in args.field:
        if "=" not in item:
            raise SystemExit("--field must use NAME=HEX")
        name, value = item.split("=", 1)
        fields[name] = value

    output = {
        "trace": args.trace,
        "trace_size": len(trace),
        "matches": {},
    }

    for name, value in fields.items():
        field_bytes = parse_hex(value)
        if len(field_bytes) < args.min_field_size:
            output["matches"][name] = {
                "field_size": len(field_bytes),
                "skipped": "empty or shorter than --min-field-size",
            }
            continue
        output["matches"][name] = {
            "field_size": len(field_bytes),
            "variants": {},
        }
        for variant_name, variant_bytes in variants(field_bytes).items():
            offsets = find_all(trace, variant_bytes)
            output["matches"][name]["variants"][variant_name] = {
                "offsets": offsets,
                "count": len(offsets),
            }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
