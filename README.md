# ATC_MiThermometer — Wireless Display Edition

A specialized fork of [pvvx's ATC_MiThermometer](https://github.com/pvvx/ATC_MiThermometer) custom firmware for Telink-based BLE thermometers (such as the Xiaomi Mijia LYWSD03MMC), optimized for use as a dedicated wireless remote display via ESPHome's [`pvvx_mithermometer`](https://esphome.io/components/display/pvvx_mithermometer.html) display platform.

---

## Purpose & Key Modifications

In standard upstream firmware, external data sent via BLE command `0x22` (`CMD_ID_EXTDATA`) is treated as a secondary view in a periodic carousel, cycling back and forth between external data and local sensor readings every ~2.5 seconds. In addition, LCD refreshes were queued for the next periodic timer tick rather than applied immediately.

This fork turns the thermometer into an efficient, responsive wireless screen:

1. **Exclusive External Display Mode (`src/lcd.c`)**:
   - While external data remains valid (within `vtime_sec`), the display strictly shows the external data rather than alternating with local temperature and humidity measurements.
   - If external updates cease and the validity timer expires (e.g., ESP32 goes offline), the display cleanly falls back to local sensor readings as a failsafe.

2. **Zero-Latency Screen Updates (`src/cmd_parser.c`)**:
   - Invokes `SET_LCD_UPDATE()` immediately when `CMD_ID_EXTDATA` is received over BLE.
   - Screen content redraws instantly upon transmission rather than waiting up to 2.5–5 seconds for the internal cadence timer.

3. **Modern CMake Build System**:
   - Replaced legacy Telink IoT Studio Eclipse configuration with a modern CMake toolchain (`tc32-elf-gcc`).
   - Clean VS Code build/clean tasks and submodule-based SDK dependency management.

---

## ESPHome Integration

Use the official ESPHome `pvvx_mithermometer` display component with an active `ble_client`:

```yaml
esp32_ble_tracker:

ble_client:
  - mac_address: A4:C1:38:XX:XX:XX
    id: ble_display

display:
  - platform: pvvx_mithermometer
    ble_client_id: ble_display
    update_interval: 60s
    validity_period: 300s
    lambda: |-
      it.print_bignum(id(power_usage).state);
      it.print_unit(pvvx_mithermometer::UNIT_NONE);
      it.print_smallnum(id(outside_temp).state);
      it.print_percent(false);
      it.print_happy(true);
```

### Best Practices for Wireless Display Use

- **Battery Optimization (CR2032)**:
  Each BLE connection draws ~8–12 mA during radio exchange. Keep `update_interval` at **60–120s** (or trigger updates conditionally on significant sensor changes) to maintain multi-month battery life.
- **Validity Margin**:
  Set `validity_period` to $2\times$–$3\times$ your `update_interval` so temporary RF interference does not cause premature fallback to local sensor data.
- **Device Config Settings**:
  In the web flasher configuration ([TelinkMiFlasher](https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html)), make sure **"Show battery"** and **"Show clock"** are disabled so they do not periodically override the external display fields. You can also increase the internal measurement interval to conserve battery power.

---

## Building

### Prerequisites

- [Telink TC32 Toolchain](https://github.com/pvvx/tc32) (`tc32-elf-gcc`)
- CMake $\ge$ 3.16 and Ninja / Make
- Python 3

### Command Line

```bash
git submodule update --init --recursive
cmake -B build -G "Ninja" -DCMAKE_TOOLCHAIN_FILE=cmake/tc32-toolchain.cmake
cmake --build build
```

Pre-configured build tasks are also available in `.vscode/tasks.json` for VS Code users.

---

## Acknowledgments & Upstream

- Original firmware and reverse engineering by [pvvx](https://github.com/pvvx/ATC_MiThermometer).
- Custom firmware foundations by [atc1441](https://github.com/atc1441/ATC_MiThermometer).
- ESPHome display platform implementation by [ESPHome contributors](https://esphome.io/components/display/pvvx_mithermometer.html).
