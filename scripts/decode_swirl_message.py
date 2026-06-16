#!/usr/bin/env python3
"""Decode 21 Swirl protobuf messages.

This is an offline helper. It does not connect to the network or hardware.
"""
import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
TWO1_SRC = ROOT / "two1_source" / "two1-3.10.9"
sys.path.insert(0, str(TWO1_SRC))
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def load_bytes(args):
    if args.file:
        return Path(args.file).read_bytes()

    raw = args.data.strip()
    if args.input == "hex":
        return binascii.unhexlify("".join(raw.split()))
    if args.input == "base64":
        return base64.b64decode(raw)
    if args.input == "text":
        return raw.encode()
    raise ValueError("unsupported input type")


def maybe_strip_header(data, mode):
    if mode == "none":
        return None, data
    if len(data) < 2:
        return None, data

    size = struct.unpack(">H", data[:2])[0]
    if mode == "strip":
        return size, data[2:]
    if mode == "auto" and size == len(data) - 2:
        return size, data[2:]
    return None, data


def bytes_to_hex_in_dict(value):
    if isinstance(value, dict):
        return {k: bytes_to_hex_in_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [bytes_to_hex_in_dict(v) for v in value]
    if isinstance(value, bytes):
        return value.hex()
    return value


class ProtoReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def eof(self):
        return self.pos >= len(self.data)

    def read_varint(self):
        shift = 0
        value = 0
        while True:
            if self.pos >= len(self.data):
                raise ValueError("truncated varint")
            b = self.data[self.pos]
            self.pos += 1
            value |= (b & 0x7f) << shift
            if not b & 0x80:
                return value
            shift += 7
            if shift > 70:
                raise ValueError("varint too long")

    def read_len(self):
        size = self.read_varint()
        if self.pos + size > len(self.data):
            raise ValueError("truncated length-delimited field")
        out = self.data[self.pos:self.pos + size]
        self.pos += size
        return out

    def read_field(self):
        key = self.read_varint()
        return key >> 3, key & 0x07

    def skip(self, wire_type):
        if wire_type == 0:
            self.read_varint()
        elif wire_type == 1:
            self.pos += 8
        elif wire_type == 2:
            self.read_len()
        elif wire_type == 5:
            self.pos += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire_type}")


def parse_message(data, field_map):
    reader = ProtoReader(data)
    out = {}
    while not reader.eof():
        field_no, wire_type = reader.read_field()
        spec = field_map.get(field_no)
        if spec is None:
            reader.skip(wire_type)
            continue

        name, value_type = spec
        if value_type == "varint" or value_type == "bool":
            if wire_type != 0:
                raise ValueError(f"{name} expected varint, got wire type {wire_type}")
            value = reader.read_varint()
            if value_type == "bool":
                value = bool(value)
        elif value_type == "bytes":
            if wire_type != 2:
                raise ValueError(f"{name} expected bytes, got wire type {wire_type}")
            value = reader.read_len().hex()
        elif value_type == "string":
            if wire_type != 2:
                raise ValueError(f"{name} expected string, got wire type {wire_type}")
            value = reader.read_len().decode("utf-8", errors="replace")
        elif isinstance(value_type, dict):
            if wire_type != 2:
                raise ValueError(f"{name} expected nested message, got wire type {wire_type}")
            value = parse_message(reader.read_len(), value_type)
        else:
            raise ValueError(f"unsupported value type {value_type}")

        if name in out:
            if not isinstance(out[name], list):
                out[name] = [out[name]]
            out[name].append(value)
        else:
            out[name] = value
    return out


CLIENT_AUTH = {
    1: ("hardware", "varint"),
    2: ("username", "string"),
    3: ("uuid", "string"),
}
CLIENT_SUBMIT_SHARE = {
    1: ("message_id", "varint"),
    2: ("work_id", "varint"),
    3: ("enonce2", "bytes"),
    4: ("otime", "varint"),
    5: ("nonce", "varint"),
}
SERVER_AUTH_YES = {
    1: ("enonce1", "bytes"),
    2: ("enonce2_size", "varint"),
    3: ("wallet_id", "varint"),
}
SERVER_AUTH_NO = {1: ("error", "string")}
SERVER_AUTH_POOL_DOWN = {
    1: ("reason", "string"),
    2: ("retry_seconds", "varint"),
}
SERVER_AUTH_REPLY = {
    1: ("auth_reply_yes", SERVER_AUTH_YES),
    2: ("auth_reply_no", SERVER_AUTH_NO),
    3: ("auth_reply_pool_down", SERVER_AUTH_POOL_DOWN),
}
SERVER_SUBMIT_SHARE = {
    1: ("message_id", "varint"),
    2: ("submit_status", "varint"),
}
SERVER_WORK = {
    1: ("work_id", "varint"),
    2: ("version", "varint"),
    3: ("prev_block_hash", "bytes"),
    4: ("height", "varint"),
    5: ("nbits", "varint"),
    6: ("ntime", "varint"),
    7: ("coinb1", "bytes"),
    8: ("coinb2", "bytes"),
    9: ("merkle_edge", "bytes"),
    10: ("new_block", "bool"),
    11: ("bits_pool", "varint"),
}
CLIENT_OUTER = {
    100: ("auth_request", CLIENT_AUTH),
    101: ("submit_share_request", CLIENT_SUBMIT_SHARE),
}
SERVER_OUTER = {
    200: ("auth_reply", SERVER_AUTH_REPLY),
    201: ("submit_share_reply", SERVER_SUBMIT_SHARE),
    202: ("work_notification", SERVER_WORK),
}


def decode_with_builtin(payload, kind):
    outer = CLIENT_OUTER if kind == "client" else SERVER_OUTER
    decoded = parse_message(payload, outer)
    msg_type = next(iter(decoded.keys()), None)
    return msg_type, decoded.get(msg_type, decoded), "builtin"


def decode_with_protobuf(payload, kind):
    from google.protobuf.json_format import MessageToDict
    from two1.server import swirl_pb3

    if kind == "server":
        msg = swirl_pb3.SwirlServerMessage()
        oneof = "servermessages"
    elif kind == "client":
        msg = swirl_pb3.SwirlClientMessage()
        oneof = "clientmessages"
    else:
        raise ValueError("kind must be server or client")

    msg.ParseFromString(payload)
    msg_type = msg.WhichOneof(oneof)
    body = getattr(msg, msg_type) if msg_type else msg
    data = MessageToDict(
        body,
        preserving_proto_field_name=True,
        including_default_value_fields=True,
    )
    return msg_type, bytes_to_hex_in_dict(data), "protobuf"


def decode_message(payload, kind, decoder):
    if decoder in ("auto", "protobuf"):
        try:
            return decode_with_protobuf(payload, kind)
        except Exception as exc:
            if decoder == "protobuf":
                raise
            protobuf_error = str(exc)
    msg_type, decoded, backend = decode_with_builtin(payload, kind)
    if decoder == "auto" and "protobuf_error" in locals():
        decoded = {"_protobuf_fallback_reason": protobuf_error, **decoded}
    return msg_type, decoded, backend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", nargs="?", help="message bytes in selected input format")
    parser.add_argument("-f", "--file", help="read message bytes from file")
    parser.add_argument("--input", choices=["hex", "base64", "text"], default="hex")
    parser.add_argument("--kind", choices=["server", "client"], default="server")
    parser.add_argument("--decoder", choices=["auto", "protobuf", "builtin"], default="auto")
    parser.add_argument(
        "--length-header",
        choices=["auto", "strip", "none"],
        default="auto",
        help="Swirl frames normally use a 2-byte big-endian length prefix",
    )
    args = parser.parse_args()

    if not args.file and args.data is None:
        parser.error("provide data or --file")

    data = load_bytes(args)
    declared_size, payload = maybe_strip_header(data, args.length_header)
    msg_type, decoded, backend = decode_message(payload, args.kind, args.decoder)

    print(json.dumps({
        "kind": args.kind,
        "decoder": backend,
        "message_type": msg_type,
        "length_header": declared_size,
        "payload_size": len(payload),
        "decoded": decoded,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
