#!/usr/bin/env python3
"""
tl_check_fw.py - Verify and patch Telink firmware header for OTA
Originally by pvvx
Reference: https://github.com/pvvx/ATC_MiThermometer/issues/186#issuecomment-1030410603

Ensures firmware binary size is 16-byte aligned, updates firmware length,
adds magic constant and appends CRC32 checksum.
"""

from __future__ import annotations

import binascii
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <firmware.bin>", file=sys.stderr)
        sys.exit(1)

    bin_path = sys.argv[1]
    with open(bin_path, "rb") as f:
        firmware = bytearray(f.read())

    if firmware[6:8] != b"\x5d\x02":
        # Ensure FW size is multiple of 16
        padding = 16 - len(firmware) % 16
        if padding < 16:
            firmware += b"\xff" * padding
        # Fix FW length
        firmware[0x18:0x1C] = (len(firmware) + 4).to_bytes(4, byteorder="little")
        # Add magic constant
        firmware[6:8] = b"\x5d\x02"
        # Add CRC
        crc = binascii.crc32(firmware) ^ 0xFFFFFFFF
        firmware += crc.to_bytes(4, byteorder="little")
        # Write the new firmware back to the file
        with open(bin_path, "wb") as f:
            f.write(firmware)
        print("Firmware for OTA has been adjusted.")
    else:
        print("Firmware for OTA has already been adjusted!")


if __name__ == "__main__":
    main()
