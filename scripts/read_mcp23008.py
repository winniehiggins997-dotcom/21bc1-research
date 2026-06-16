#!/usr/bin/env python3
"""Read MCP23008 registers without writing anything.

Run on a Raspberry Pi or Linux SBC with I2C enabled. This script is read-only.
"""
import argparse
import json
import subprocess


REGISTERS = {
    0x00: "IODIR",
    0x01: "IPOL",
    0x02: "GPINTEN",
    0x03: "DEFVAL",
    0x04: "INTCON",
    0x05: "IOCON",
    0x06: "GPPU",
    0x07: "INTF",
    0x08: "INTCAP",
    0x09: "GPIO",
    0x0A: "OLAT",
}


def read_with_smbus(bus_num, addr):
    try:
        import smbus2
    except ImportError:
        return None

    values = {}
    with smbus2.SMBus(bus_num) as bus:
        for reg in REGISTERS:
            values[reg] = bus.read_byte_data(addr, reg)
    return values


def read_with_i2cget(bus_num, addr):
    values = {}
    for reg in REGISTERS:
        cmd = ["i2cget", "-y", str(bus_num), hex(addr), hex(reg)]
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        values[reg] = int(proc.stdout.strip(), 16)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--addr", type=lambda x: int(x, 0), default=0x20)
    args = parser.parse_args()

    values = read_with_smbus(args.bus, args.addr)
    backend = "smbus2"
    if values is None:
        values = read_with_i2cget(args.bus, args.addr)
        backend = "i2cget"

    decoded = {}
    for reg, name in REGISTERS.items():
        value = values[reg]
        decoded[name] = {
            "register": f"0x{reg:02x}",
            "value": f"0x{value:02x}",
            "bits": f"{value:08b}",
        }

    print(json.dumps({
        "device": "MCP23008",
        "mode": "read-only",
        "backend": backend,
        "bus": args.bus,
        "addr": f"0x{args.addr:02x}",
        "registers": decoded,
    }, indent=2))


if __name__ == "__main__":
    main()
