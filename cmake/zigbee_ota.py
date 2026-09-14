#!/usr/bin/env python3
"""
zigbee_ota.py - Wrap binary firmware in a ZCL OTA image
Originally by pvvx

Generates a Zigbee OTA update image from a compiled binary by prefixing
a Zigbee Cluster Library (ZCL) OTA file header and chunk header.
"""

from __future__ import annotations

import argparse
import binascii
import os
import struct

OTA_MAGIC = b"\x5d\x02"


def main(args: argparse.Namespace) -> None:
    assert args.input_file != args.output

    with open(args.input_file, "rb") as bin_file:
        firmware = bytearray(bin_file.read())

    if firmware[6:8] != OTA_MAGIC:
        # Ensure FW size is multiple of 16
        padding = 16 - len(firmware) % 16
        if padding < 16:
            firmware += b"\xff" * padding
        # Fix FW length
        firmware[0x18:0x1C] = (len(firmware) + 4).to_bytes(4, byteorder="little")
        # Add magic constant
        firmware[6:8] = OTA_MAGIC
        # Add CRC
        crc = binascii.crc32(firmware) ^ 0xFFFFFFFF
        firmware += crc.to_bytes(4, byteorder="little")

    ota_hdr_s = struct.Struct("<I5HIH32sI")
    header_size = 56
    firmware_len = len(firmware)
    total_image_size = firmware_len + header_size + 6
    manufacturer_code = int.from_bytes(firmware[18:20], byteorder="little")
    image_type = int.from_bytes(firmware[20:22], byteorder="little")
    file_version = args.set_version or int.from_bytes(firmware[2:6], byteorder="little")
    hs = b"ZigbeeTLc to BLE".ljust(32, b"\x00")
    ota_hdr = ota_hdr_s.pack(
        0xBEEF11E,
        0x100,  # header version is 0x0100
        header_size,
        0,
        manufacturer_code,
        image_type,
        file_version,
        args.ota_version,
        hs,
        total_image_size,
    )
    # add chunk header: 0 - firmware type
    ota_hdr += struct.pack("<HI", 0, firmware_len)

    out_filename = args.output
    if not out_filename:
        head, tail = os.path.split(args.input_file)
        if args.path:
            head = args.path
        if args.output_title:
            name = args.output_title
        else:
            name, _ = os.path.splitext(tail)
        out_filename = os.path.join(
            head,
            f"{manufacturer_code:04x}-{image_type:04x}-{file_version:08x}-{name}.zigbee",
        )

    out_dir = os.path.dirname(out_filename)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_filename, "wb") as output:
        output.write(ota_hdr)
        output.write(firmware)
    print(f"{out_filename} was created with ZCL OTA Header.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Zigbee OTA image from binary firmware"
    )
    parser.add_argument("input_file", help="Input binary file")
    parser.add_argument(
        "-ot", "--output-title", help="Replace original file name with this string"
    )
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-p", "--path", help="Path to output directory")
    parser.add_argument(
        "-s", "--ota-version", type=int, help="OTA stack version", default=2
    )
    parser.add_argument(
        "-v",
        "--set-version",
        type=lambda x: int(x, 0),
        help="Override version from BIN",
    )
    _args = parser.parse_args()
    main(_args)
