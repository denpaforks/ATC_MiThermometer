#!/usr/bin/env python3
"""
tl_ret_mem_addr.py - TLSR825x Retention Memory Address Calculator
Originally by pvvx

Extracts the retention data end address or ictag start address from
an ELF binary to compute the optimal -Ttext address for the linker.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def parse_symbols(elf_path: str, nm_tool: str) -> dict[str, int]:
    """Extract symbol addresses from an ELF binary using tc32-elf-nm."""
    try:
        proc = subprocess.run(
            [nm_tool, elf_path],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print(
            f"Error: Tool '{nm_tool}' not found. Check toolchain PATH.", file=sys.stderr
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running '{nm_tool}':\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

    symbols: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        fields = line.strip().split()
        if len(fields) >= 3 and fields[1] not in ("w", "W"):
            try:
                symbols[fields[2]] = int(fields[0], 16)
            except ValueError:
                continue
    return symbols


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tl_ret_mem_addr",
        description="Calculate optimal TLSR825x linker -Ttext address from ELF symbols",
    )
    parser.add_argument(
        "-e",
        "--elffile",
        default="out.elf",
        help="Path to ELF file (default: out.elf)",
    )
    parser.add_argument(
        "-t",
        "--tools",
        default="tc32-elf-nm",
        help="Path and name of tc32-elf-nm (default: tc32-elf-nm)",
    )
    args = parser.parse_args()

    symbols = parse_symbols(args.elffile, args.tools)

    ret_end = symbols.get("_retention_data_end_", 0)
    if ret_end == 0:
        ret_end = symbols.get("_ictag_start_", 0)

    if ret_end > 0:
        ttext_addr = (ret_end + 255) & 0x0001FF00
        print(f"0x{ttext_addr:x}")
    else:
        print("0x8000")


if __name__ == "__main__":
    main()
