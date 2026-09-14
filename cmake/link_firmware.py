#!/usr/bin/env python3
"""
link_firmware.py - Two-pass linker + post-processing script for TLSR8258

Called by CMake at build time. All paths come from CMake generator expressions
so they are always absolute and properly resolved.

Usage (internal – called by CMakeLists.txt):
    python link_firmware.py <tc32_ld> <tc32_nm> <tc32_objcopy>
                            <elf_file> <bin_file>
                            <linker_script> <sdk_lib_path>
                            <project_root> <python_exe>
                            [object_file ...]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def run(cmd: list[str], description: str = "") -> None:
    """Run a command; abort on non-zero exit."""
    if description:
        print(f">>> {description}")
    print("    " + " ".join(str(a) for a in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            f"\n[ERROR] Command failed with exit code {result.returncode}",
            file=sys.stderr,
        )
        sys.exit(result.returncode)


def main() -> None:
    if len(sys.argv) < 10:
        print(
            "Usage: link_firmware.py <ld> <nm> <objcopy> <elf> <bin> "
            "<linker_script> <sdk_lib_path> <project_root> <python_exe> [objects...]",
            file=sys.stderr,
        )
        sys.exit(1)

    tc32_ld = sys.argv[1]
    tc32_nm = sys.argv[2]
    tc32_objcopy = sys.argv[3]
    elf_file = sys.argv[4]
    bin_file = sys.argv[5]
    linker_script = sys.argv[6]
    sdk_lib_path = sys.argv[7]
    project_root = sys.argv[8]
    python_exe = sys.argv[9]
    object_files = sys.argv[10:]

    # ── Shared link arguments ────────────────────────────────────────────────
    common_link = (
        [
            tc32_ld,
            "--gc-sections",
            "-L",
            sdk_lib_path,
            "-T",
            linker_script,
            "-o",
            elf_file,
        ]
        + object_files
        + ["-llt_8258"]
    )

    # ── Pass 1: standard link ────────────────────────────────────────────────
    run(common_link, "Pass 1: initial link")

    # ── Compute optimal -Ttext address ───────────────────────────────────────
    ttext_script = os.path.join(project_root, "cmake", "tl_ret_mem_addr.py")
    result = subprocess.run(
        [python_exe, ttext_script, "-e", elf_file, "-t", tc32_nm],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"[ERROR] {os.path.basename(ttext_script)} failed:\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    ttext_addr = result.stdout.strip()
    print(f">>> -Ttext address: {ttext_addr}")

    # ── Pass 2: re-link with optimised text address ──────────────────────────
    optimised_link = (
        [
            tc32_ld,
            "--gc-sections",
            "-Ttext",
            ttext_addr,
            "-L",
            sdk_lib_path,
            "-T",
            linker_script,
            "-o",
            elf_file,
        ]
        + object_files
        + ["-llt_8258"]
    )
    run(optimised_link, "Pass 2: re-link with -Ttext optimisation")

    # ── Memory usage report & Retention SRAM check ───────────────────────────
    meminfo_script = os.path.join(project_root, "cmake", "tl_mem_info.py")
    if os.path.exists(meminfo_script):
        run(
            [python_exe, meminfo_script, "-s", "32768", "-t", tc32_nm, elf_file],
            "Analyzing memory layout & Retention SRAM",
        )
    else:
        print(f"[SKIP] tl_mem_info.py not found at {meminfo_script}")

    # ── Generate binary image ────────────────────────────────────────────────
    run([tc32_objcopy, "-v", "-O", "binary", elf_file, bin_file], "Generating .bin")

    # ── Generate listing (.lst) for Telink IDE ───────────────────────────────
    tc32_objdump = tc32_objcopy.replace("objcopy", "objdump")
    lst_file = os.path.splitext(elf_file)[0] + ".lst"
    if os.path.exists(tc32_objdump):
        print(">>> Generating .lst")
        try:
            with open(lst_file, "w") as f:
                subprocess.run(
                    [tc32_objdump, "-x", "-D", "-l", "-S", elf_file], stdout=f
                )
        except Exception as e:
            print(f"[WARN] Failed to generate .lst: {e}")

    # ── Firmware integrity check ─────────────────────────────────────────────
    check_script = os.path.join(project_root, "cmake", "tl_check_fw.py")
    if os.path.exists(check_script):
        run([python_exe, check_script, bin_file], "Checking firmware")
    else:
        print(f"[SKIP] tl_check_fw.py not found at {check_script}")

    # ── Copy finalized binary to bin/ directory ───────────────────────────────
    bin_dir = os.path.join(project_root, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    target_bin = os.path.join(bin_dir, os.path.basename(bin_file))
    shutil.copy2(bin_file, target_bin)

    # ── Zigbee OTA image generation ──────────────────────────────────────────
    ota_script = os.path.join(project_root, "cmake", "zigbee_ota.py")
    ota_out = os.path.join(project_root, "zigbee_ota")
    if os.path.exists(ota_script):
        os.makedirs(ota_out, exist_ok=True)
        run(
            [python_exe, ota_script, bin_file, "-p", ota_out],
            "Generating Zigbee OTA image",
        )
    else:
        print(f"[SKIP] zigbee_ota.py not found at {ota_script}")

    print("\n=== Build complete ===")
    print(f"    ELF : {elf_file}")
    print(f"    BIN : {bin_file}")
    print(f"    OUTPUT BIN : {target_bin}")
    if os.path.exists(lst_file):
        print(f"    LST : {lst_file}")


if __name__ == "__main__":
    main()
