#!/usr/bin/env python3
"""
tl_mem_info.py - TLSR825x Memory Layout & Usage Reporter
Originally by pvvx

Inspects an ELF binary using tc32-elf-nm to display memory section breakdown
and verifies Retention SRAM limits.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

__progname__ = "TLSR825x MemInfo"
__version__ = "26.06.24"

SRAM_BASE_ADDR = 0x840000


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
        prog="tl_mem_info",
        description=f"{__progname__} version {__version__}",
    )
    parser.add_argument(
        "--size",
        "-s",
        type=lambda x: int(x, 0),
        default=32768,
        help="Chip Retention SRAM Size in bytes (default: 32768)",
    )
    parser.add_argument(
        "-t",
        "--tools",
        default="tc32-elf-nm",
        help="Path and name of tc32-elf-nm (default: tc32-elf-nm)",
    )
    parser.add_argument("elffname", help="Path to ELF file")
    args = parser.parse_args()

    print(f"{__progname__} version {__version__}")

    sec_name = [
        "ramcode",
        "text",
        "rodata",
        "rtdata",
        "nc",
        "ictag",
        "icdata",
        "data",
        "bss",
        "irq_stk",
        "stack",
        "flash",
    ]
    sec_des = [
        "Resident Code SRAM",
        "Code Flash",
        "Read Only Data Flash",
        "Retention SRAM",
        "Wasteful Area SRAM",
        "Cache Table SRAM",
        "Cache Data SRAM",
        "Init Data SRAM",
        "BSS Data SRAM",
        "IRQ Stack SRAM",
        "CPU Stack SRAM",
        "Bin Size Flash",
    ]
    sec_start = [
        "__start",
        "_start_text_",
        "_start_rodata_",
        "_retention_data_start_",
        "_retention_data_end_",
        "_ictag_start_",
        "_ictag_end_",
        "_start_data_",
        "_start_bss_",
        "_start_bss_",
        "_end_bss_",
        "__start",
    ]
    sec_end = [
        "_rstored_",
        "_end_text_",
        "_end_rodata_",
        "_retention_data_end_",
        "_ictag_start_",
        "_ictag_end_",
        "_ictag_end_",
        "_end_data_",
        "_end_bss_",
        "IRQ_STK_SIZE",
        "__RAM_SIZE_MAX",
        "_bin_size_",
    ]
    sec_start_add = [0] * 12
    sec_end_add = [0, 0, 0, 0, 0, 0, 0x800, 0, 0, 0, SRAM_BASE_ADDR, 0]

    symbols = parse_symbols(args.elffname, args.tools)

    chip_sram_size = symbols.get("__RAM_SIZE_MAX", 0)
    chip_retram_size = symbols.get("__RAM_RETENTION_SIZE", 0) or args.size

    start_bss = symbols.get("_start_bss_", 0)
    if start_bss:
        sec_end_add[9] = start_bss

    load_sram = symbols.get("_icload_size_div_16_", 0) << 4
    ictag = symbols.get("_ictag_addr_div_256_", 0) << 8

    print("===================================================================")
    header = (
        f"{'Section':>8}|{'Description':>21}|{'Start (hex)':>12}|"
        f"{'End (hex)':>12}|{'Used space':>10}"
    )
    print(header)
    print("-------------------------------------------------------------------")

    sec_size: list[int] = []
    for i in range(len(sec_name)):
        ss = symbols.get(sec_start[i], 0) + sec_start_add[i]
        se = symbols.get(sec_end[i], 0) + sec_end_add[i]
        sz = int(se - ss)
        sec_size.append(sz)
        print(f"{sec_name[i]:>8}|{sec_des[i]:>21}|{ss:>12X}|{se:>12X}|{sz:>10d}")
    print("-------------------------------------------------------------------")

    ram_used = symbols.get("_end_bss_", 0) - SRAM_BASE_ADDR
    retram_used = symbols.get("_start_data_", 0) - SRAM_BASE_ADDR
    print(f"Start Load SRAM : {load_sram} (ICtag: 0x{ictag:X})")
    print(f"Total Used RRAM : {retram_used} from {chip_retram_size}")
    print(f"Total Used SRAM : {ram_used} from {chip_sram_size}")
    free_sram = sec_size[4] + sec_size[10]
    print(f"Total Free SRAM : {sec_size[4]} + stack[{sec_size[10]}] = {free_sram}")

    if sec_size[10] < 256:
        print("Warning! Stack is low!", file=sys.stderr)

    if chip_retram_size < retram_used:
        overflow = retram_used - chip_retram_size
        print(f"\nError: Retention SRAM Overflow ({overflow} bytes)!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
