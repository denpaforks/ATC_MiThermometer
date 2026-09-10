# ─── Telink TC32 Cross-Compilation Toolchain ──────────────────────────────────
# For use with the Telink TLSR8258 chip and tc32-elf-gcc.
#
# The toolchain binary directory is resolved in this order:
#   1. CMake variable  TC32_TOOLCHAIN_PATH  (pass via -DTC32_TOOLCHAIN_PATH=...)
#   2. Environment variable  TC32_TOOLCHAIN_PATH
#   3. Default install location used by the Telink VSCode Extension
#      (~/.Telink_Tools/tc32_130_Windows/tc32/bin)
# ──────────────────────────────────────────────────────────────────────────────

set(CMAKE_SYSTEM_NAME      Generic)
set(CMAKE_SYSTEM_PROCESSOR tc32)

# ─── Critical: tell CMake not to try to run the cross-compiled output ──────────
# Must be set BEFORE the first project()/enable_language() call, which is why
# it lives here in the toolchain file.
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# ─── Resolve toolchain directory ──────────────────────────────────────────────
if(NOT TC32_TOOLCHAIN_PATH)
    if(DEFINED TOOLCHAIN_PATH)
        if(EXISTS "${TOOLCHAIN_PATH}/bin")
            set(TC32_TOOLCHAIN_PATH "${TOOLCHAIN_PATH}/bin")
        else()
            set(TC32_TOOLCHAIN_PATH "${TOOLCHAIN_PATH}")
        endif()
    elseif(DEFINED ENV{TC32_TOOLCHAIN_PATH})
        set(TC32_TOOLCHAIN_PATH "$ENV{TC32_TOOLCHAIN_PATH}")
    else()
        # Default: Telink VSCode Extension install location (Windows)
        set(TC32_TOOLCHAIN_PATH
            "$ENV{USERPROFILE}/.Telink_Tools/tc32_130_Windows/tc32/bin")
    endif()
endif()

# Normalise path separators (handles both / and \)
file(TO_CMAKE_PATH "${TC32_TOOLCHAIN_PATH}" TC32_TOOLCHAIN_PATH)

set(_TC32 "${TC32_TOOLCHAIN_PATH}/tc32-elf-")

# ─── Compiler / tool executables ──────────────────────────────────────────────
set(CMAKE_C_COMPILER   "${_TC32}gcc.exe" CACHE FILEPATH "TC32 C compiler")
set(CMAKE_ASM_COMPILER "${_TC32}gcc.exe" CACHE FILEPATH "TC32 assembler (via GCC driver)")
set(CMAKE_LINKER       "${_TC32}ld.exe"  CACHE FILEPATH "TC32 linker")
set(CMAKE_AR           "${_TC32}ar.exe"  CACHE FILEPATH "TC32 archiver")

# Force the compiler ID so CMake doesn't spend time probing an unknown target
set(CMAKE_C_COMPILER_ID      "GNU"   CACHE STRING "Forced compiler ID"      FORCE)
set(CMAKE_C_COMPILER_VERSION "4.5.1" CACHE STRING "Forced compiler version" FORCE)

# GCC 4.5.1 predates CMake 4.0's compiler standard database.
# Without these, CMake 4.0 errors: "CMAKE_C_STANDARD_COMPUTED_DEFAULT should be set"
set(CMAKE_C_STANDARD_COMPUTED_DEFAULT   "90" CACHE STRING "" FORCE)
set(CMAKE_C_EXTENSIONS_COMPUTED_DEFAULT  "ON" CACHE STRING "" FORCE)

# Export for use in CMakeLists.txt custom commands
set(TC32_OBJCOPY "${_TC32}objcopy.exe" CACHE FILEPATH "TC32 objcopy")
set(TC32_OBJDUMP "${_TC32}objdump.exe" CACHE FILEPATH "TC32 objdump")
set(TC32_NM      "${_TC32}nm.exe"      CACHE FILEPATH "TC32 nm")
set(TC32_LD      "${_TC32}ld.exe"      CACHE FILEPATH "TC32 ld (for custom link step)")

# ─── Search paths ─────────────────────────────────────────────────────────────
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
