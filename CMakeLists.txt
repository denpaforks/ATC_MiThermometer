cmake_minimum_required(VERSION 3.16)

# ─── Toolchain configuration ───────────────────────────────────────────────────
# When configured via Telink VSCode extension (which passes -DTOOLCHAIN_NAME and
# -DTOOLCHAIN_PATH directly instead of -DCMAKE_TOOLCHAIN_FILE), include the toolchain
# before project() so CMake configures tc32-elf-gcc properly.
if(NOT CMAKE_TOOLCHAIN_FILE)
    include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/tc32-toolchain.cmake")
endif()

# ─── Project ───────────────────────────────────────────────────────────────────
if(NOT DEFINED PROJECT_NAME)
    set(PROJECT_NAME ATC_Thermometer)
endif()

# Only C and ASM: tc32-elf-gcc 4.5.1 does not support C++.
project(${PROJECT_NAME} LANGUAGES C ASM)

# Generate compile_commands.json for IntelliSense (picked up by clangd / C++ extension)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ─── Paths ─────────────────────────────────────────────────────────────────────
set(SDK_PATH          "${CMAKE_SOURCE_DIR}/SDK")
set(SDK_COMPONENTS    "${SDK_PATH}/components")
set(SDK_LIB_PATH      "${SDK_COMPONENTS}/proj_lib")
set(PROJECT_SRC       "${CMAKE_SOURCE_DIR}/src")
set(LINKER_SCRIPT     "${PROJECT_SRC}/boot.link")

# ─── Python interpreter ────────────────────────────────────────────────────────
# Prefer python3 on Linux/macOS; fall back to python (Windows default).
find_program(PYTHON_EXE NAMES python3 python REQUIRED
    DOC "Python interpreter used for post-processing scripts")

# ─── Compiler flags (mirrors GCC_FLAGS in makefile) ───────────────────────────
set(C_COMPILE_FLAGS
    -ffunction-sections
    -fdata-sections
    -Wall
    -O2
    -fpack-struct
    -fshort-enums
    -finline-small-functions
    -std=gnu99
    -funsigned-char
    -fshort-wchar
    -fms-extensions
    -DCHIP_TYPE=CHIP_TYPE_8258
)

# Assembly flag (BOOT_FLAG in makefile)
set(ASM_BOOT_FLAG -DMCU_STARTUP_825X)

# ─── Source files ──────────────────────────────────────────────────────────────

# Project application sources (from src/project.mk)
set(PROJECT_C_SOURCES
    ${PROJECT_SRC}/utils.c
    ${PROJECT_SRC}/app.c
    ${PROJECT_SRC}/lcd.c
    ${PROJECT_SRC}/lcd_lywsd03mmc.c
    ${PROJECT_SRC}/lcd_cgdk2.c
    ${PROJECT_SRC}/lcd_mjwsd05mmc.c
    ${PROJECT_SRC}/lcd_mjwsd05mmc_en.c
    ${PROJECT_SRC}/lcd_mjwsd06mmc.c
    ${PROJECT_SRC}/lcd_mho_c122.c
    ${PROJECT_SRC}/lcd_zth03.c
    ${PROJECT_SRC}/lcd_lktmzl02.c
    ${PROJECT_SRC}/lcd_zy_zth02pro.c
    ${PROJECT_SRC}/lcd_zth05z.c
    ${PROJECT_SRC}/lcd_ts0201_wing.c
    ${PROJECT_SRC}/epd_cgg1.c
    ${PROJECT_SRC}/epd_cgg1n.c
    ${PROJECT_SRC}/epd_mho_c401.c
    ${PROJECT_SRC}/epd_mho_c401n.c
    ${PROJECT_SRC}/epd_lywsd02mmc.c
    ${PROJECT_SRC}/sensors.c
    ${PROJECT_SRC}/sensor_lx.c
    ${PROJECT_SRC}/ens160.c
    ${PROJECT_SRC}/scd41.c
    ${PROJECT_SRC}/ina226.c
    ${PROJECT_SRC}/ina3221.c
    ${PROJECT_SRC}/my18b20.c
    ${PROJECT_SRC}/hx71x.c
    ${PROJECT_SRC}/rtc_pcf85163.c
    ${PROJECT_SRC}/bme280.c
    ${PROJECT_SRC}/sdm_out.c
    ${PROJECT_SRC}/trigger.c
    ${PROJECT_SRC}/rds_count.c
    ${PROJECT_SRC}/app_att.c
    ${PROJECT_SRC}/battery.c
    ${PROJECT_SRC}/rh.c
    ${PROJECT_SRC}/rh2.c
    ${PROJECT_SRC}/ble.c
    ${PROJECT_SRC}/i2c.c
    ${PROJECT_SRC}/cmd_parser.c
    ${PROJECT_SRC}/ext_ota.c
    ${PROJECT_SRC}/flash_eep.c
    ${PROJECT_SRC}/logger.c
    ${PROJECT_SRC}/blt_common.c
    ${PROJECT_SRC}/ccm.c
    ${PROJECT_SRC}/custom_beacon.c
    ${PROJECT_SRC}/mi_beacon.c
    ${PROJECT_SRC}/bthome_beacon.c
    ${PROJECT_SRC}/scanning.c
    ${PROJECT_SRC}/xbr818.c
    ${PROJECT_SRC}/main.c
)

# SDK chip-driver sources (from src/drivers_8258.mk)
set(DRIVER_SOURCES
    ${SDK_COMPONENTS}/drivers/8258/adc.c
    ${SDK_COMPONENTS}/drivers/8258/aes.c
    ${SDK_COMPONENTS}/drivers/8258/analog.c
    ${SDK_COMPONENTS}/drivers/8258/audio.c
    ${SDK_COMPONENTS}/drivers/8258/bsp.c
    ${SDK_COMPONENTS}/drivers/8258/clock.c
    ${SDK_COMPONENTS}/drivers/8258/emi.c
    ${SDK_COMPONENTS}/drivers/8258/flash.c
    ${SDK_COMPONENTS}/drivers/8258/gpio_8258.c
    ${SDK_COMPONENTS}/drivers/8258/i2c.c
    ${SDK_COMPONENTS}/drivers/8258/lpc.c
    ${SDK_COMPONENTS}/drivers/8258/qdec.c
    ${SDK_COMPONENTS}/drivers/8258/rf_pa.c
    ${SDK_COMPONENTS}/drivers/8258/s7816.c
    ${SDK_COMPONENTS}/drivers/8258/spi.c
    ${SDK_COMPONENTS}/drivers/8258/timer.c
    ${SDK_COMPONENTS}/drivers/8258/uart.c
    ${SDK_COMPONENTS}/drivers/8258/watchdog.c
)

# SDK application/print sources (from src/uprintf.mk)
set(PRINT_SOURCES
    ${SDK_COMPONENTS}/application/print/putchar.c
    ${SDK_COMPONENTS}/application/print/u_printf.c
)

# Startup assembly: compiled with BOOT_FLAG + GCC_FLAGS (from src/boot.mk)
set(STARTUP_ASM_SOURCES
    ${PROJECT_SRC}/cstartup_825x.S
)

# Division/modulo assembly: compiled with BOOT_FLAG only (from src/div_mod.mk)
# Note: in the original makefile the div_mod pattern rule is overridden by boot.mk's
# later-defined identical pattern, so div_mod.S also ends up with GCC_FLAGS in practice.
# We compile it separately here with explicit flags to match the original intent.
set(DIVMOD_ASM_SOURCES
    ${PROJECT_SRC}/div_mod.S
)

# ─── Object library – div_mod.S (minimal flags, shared across targets) ─────────
add_library(divmod_objects OBJECT ${DIVMOD_ASM_SOURCES})
target_compile_options(divmod_objects PRIVATE ${ASM_BOOT_FLAG})

# ─── Function to register a device firmware target ────────────────────────────
function(add_atc_target TARGET_NAME)
    set(ELF_FILE "${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}.elf")
    set(BIN_FILE "${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}.bin")

    set(TARGET_DEFS "")
    foreach(DEF IN LISTS ARGN)
        list(APPEND TARGET_DEFS "-D${DEF}")
    endforeach()

    add_library(objs_${TARGET_NAME} OBJECT
        ${PROJECT_C_SOURCES}
        ${DRIVER_SOURCES}
        ${PRINT_SOURCES}
        ${STARTUP_ASM_SOURCES}
    )

    target_compile_options(objs_${TARGET_NAME} PRIVATE
        $<$<COMPILE_LANGUAGE:C>:${C_COMPILE_FLAGS};${TARGET_DEFS}>
        $<$<COMPILE_LANGUAGE:ASM>:${ASM_BOOT_FLAG};${C_COMPILE_FLAGS};${TARGET_DEFS}>
    )

    target_include_directories(objs_${TARGET_NAME} PRIVATE
        ${SDK_COMPONENTS}
        ${PROJECT_SRC}
    )

    add_custom_command(
        OUTPUT "${ELF_FILE}" "${BIN_FILE}"
        COMMAND "${PYTHON_EXE}"
                "${CMAKE_SOURCE_DIR}/cmake/link_firmware.py"
                "${TC32_LD}"
                "${TC32_NM}"
                "${TC32_OBJCOPY}"
                "${ELF_FILE}"
                "${BIN_FILE}"
                "${LINKER_SCRIPT}"
                "${SDK_LIB_PATH}"
                "${CMAKE_SOURCE_DIR}"
                "${PYTHON_EXE}"
                $<TARGET_OBJECTS:objs_${TARGET_NAME}>
                $<TARGET_OBJECTS:divmod_objects>
        DEPENDS $<TARGET_OBJECTS:objs_${TARGET_NAME}>
                $<TARGET_OBJECTS:divmod_objects>
                "${LINKER_SCRIPT}"
                "${CMAKE_SOURCE_DIR}/cmake/link_firmware.py"
        COMMAND_EXPAND_LISTS
        VERBATIM
        COMMENT "Linking ${TARGET_NAME} (two-pass) and generating binary..."
    )

    add_custom_target(${TARGET_NAME} ALL
        DEPENDS "${ELF_FILE}" "${BIN_FILE}"
    )
endfunction()

# ─── Device Targets (matching MakeAll.cmd) ────────────────────────────────────
set(DEFAULT_DEVICE_TARGET "ATC" CACHE STRING "Default device target built with ALL (default: ATC)")

# Specific device targets
set(DEVICE_TARGETS
    "ATC:DEVICE_TYPE=DEVICE_LYWSD03MMC"
    "BTH:DEVICE_TYPE=DEVICE_MJWSD05MMC"
    "BTE:DEVICE_TYPE=DEVICE_MJWSD05MMC_EN"
    "MJ6:DEVICE_TYPE=DEVICE_MJWSD06MMC"
    "CGDK2:DEVICE_TYPE=DEVICE_CGDK2"
    "CGG1:DEVICE_TYPE=DEVICE_CGG1 DEVICE_CGG1_ver=0"
    "CGG1M:DEVICE_TYPE=DEVICE_CGG1 DEVICE_CGG1_ver=2022"
    "MHO_C401:DEVICE_TYPE=DEVICE_MHO_C401"
    "MHO_C401N:DEVICE_TYPE=DEVICE_MHO_C401N"
    "MHO_C122:DEVICE_TYPE=DEVICE_MHO_C122"
    "TNK01:DEVICE_TYPE=DEVICE_TNK01"
    "TS0201:DEVICE_TYPE=DEVICE_TS0201"
    "TS0201S1:DEVICE_TYPE=DEVICE_TS0201 USE_SENSOR_MY18B20=1"
    "TS0201S2:DEVICE_TYPE=DEVICE_TS0201 USE_SENSOR_MY18B20=2"
    "TS0201E280:DEVICE_TYPE=DEVICE_TS0201 USE_SENSOR_BME280=1"
    "TS0201B280:DEVICE_TYPE=DEVICE_TS0201 USE_SENSOR_BMP280=1"
    "TH03Z:DEVICE_TYPE=DEVICE_TH03Z"
    "ZTH01:DEVICE_TYPE=DEVICE_ZTH01"
    "ZTH01S1:DEVICE_TYPE=DEVICE_ZTH01 USE_SENSOR_MY18B20=1"
    "ZTH01S2:DEVICE_TYPE=DEVICE_ZTH01 USE_SENSOR_MY18B20=2"
    "ZTH02:DEVICE_TYPE=DEVICE_ZTH02"
    "PLM1:DEVICE_TYPE=DEVICE_PLM1"
    "TB03F:DEVICE_TYPE=DEVICE_TB03F"
    "TH03:DEVICE_TYPE=DEVICE_ZTH03"
    "LKTMZL02:DEVICE_TYPE=DEVICE_LKTMZL02"
    "ZTH05:DEVICE_TYPE=DEVICE_ZTH05Z"
    "ZYZTH02:DEVICE_TYPE=DEVICE_ZYZTH02"
    "ZYZTH02S1:DEVICE_TYPE=DEVICE_ZYZTH02 USE_SENSOR_MY18B20=1"
    "ZYZTH02S2:DEVICE_TYPE=DEVICE_ZYZTH02 USE_SENSOR_MY18B20=2"
    "ZYZTH02P:DEVICE_TYPE=DEVICE_ZYZTH01"
    "ZG227Z:DEVICE_TYPE=DEVICE_ZG_227Z"
    "ZG303Z:DEVICE_TYPE=DEVICE_ZG303Z"
    "ZBTH01:DEVICE_TYPE=DEVICE_ZBEACON_TH01"
    "ZB_MC:DEVICE_TYPE=DEVICE_ZB_MC"
    "ZB2TH01:DEVICE_TYPE=DEVICE_ZBEACON2TH01"
    "LYWSD02MMC:DEVICE_TYPE=DEVICE_LYWSD02MMC"
    "ZG204ZV:DEVICE_TYPE=DEVICE_ZG204ZV"
    "TS0201W:DEVICE_TYPE=DEVICE_TS0201_WING"
)

set(ALL_DEV_TARGETS "")
foreach(DEV_SPEC IN LISTS DEVICE_TARGETS)
    string(REGEX MATCH "^([^:]+):(.*)$" _MATCH "${DEV_SPEC}")
    set(DEV_NAME "${CMAKE_MATCH_1}")
    set(DEV_DEFS_STR "${CMAKE_MATCH_2}")
    separate_arguments(DEV_DEFS_LIST NATIVE_COMMAND "${DEV_DEFS_STR}")
    add_atc_target(${DEV_NAME} ${DEV_DEFS_LIST})
    list(APPEND ALL_DEV_TARGETS ${DEV_NAME})
endforeach()

# Meta-target to build all devices at once (equivalent to MakeAll.cmd)
add_custom_target(all_devices
    DEPENDS ${ALL_DEV_TARGETS}
    COMMENT "Building all 38 device targets..."
)

# ─── Informational messages ────────────────────────────────────────────────────
message(STATUS "Toolchain     : ${TC32_LD}")
message(STATUS "SDK path      : ${SDK_PATH}")
message(STATUS "Default target: ${DEFAULT_DEVICE_TARGET}")
message(STATUS "Device count  : 38 targets + all_devices")

