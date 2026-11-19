# Accton/Edgecore platform initialization and health fixes

## Overview

This document tracks sonic-buildimage #30780 and the shared Linux watchdog helper in sonic-platform-common #808. SDK stable-cache exhaustion diagnosed on AS7326 exposed further platform health and monitoring gaps. The implementation includes model-specific fixes for AS5835, AS7326, AS7726 and AS7816; hardware validation covers AS7326/AS7726 and AS7816 environmental monitoring. AS5835 read-only environmental checks are complete; activation of its new PDDF port remains pending.

## Related pull requests

| Repository | Pull request | State |
| --- | --- | --- |
| sonic-platform-common | [#808 — Add a Linux watchdog adapter without query side effects](https://github.com/sonic-net/sonic-platform-common/pull/808) | ![PR state](https://img.shields.io/github/pulls/detail/state/sonic-net/sonic-platform-common/808) |
| sonic-buildimage | [#30780 — Restore SDK initialization and platform health on Edgecore switches](https://github.com/sonic-net/sonic-buildimage/pull/30780) | ![PR state](https://img.shields.io/github/pulls/detail/state/sonic-net/sonic-buildimage/30780) |
| sonic-buildimage (optional) | [#30784 — Retain SDK startup diagnostics and report scache exhaustion](https://github.com/sonic-net/sonic-buildimage/pull/30784) | [![PR state](https://img.shields.io/github/pulls/detail/state/sonic-net/sonic-buildimage/30784)](https://github.com/sonic-net/sonic-buildimage/pull/30784) |

Related reports:

- [sonic-buildimage #30779 — Accton/Edgecore platform failures](https://github.com/sonic-net/sonic-buildimage/issues/30779).
- [sonic-platform-common #807 — Linux watchdog helper](https://github.com/sonic-net/sonic-platform-common/issues/807).

## Optional related SDK diagnostics

[sonic-buildimage #30784 — Retain SDK startup diagnostics and report scache exhaustion](https://github.com/sonic-net/sonic-buildimage/pull/30784)
adds diagnostic capture for Broadcom SDK initialization failures. It retains
the SDK's detailed error output and reports explicit stable-cache exhaustion
in normal SONiC logs, making failures such as those investigated on AS7326
easier to diagnose.

This is a generic Broadcom logging improvement, not a dependency of the Accton
platform fixes. It does not change the stable-cache allocation and can be
reviewed and merged independently of #808 and #30780.

## Scope

| Area | Change | Platforms |
|---|---|---|
| SDK and Cancun | 128 MiB stable cache on AS5835/AS7326/AS7726; packaged Cancun `default` path on AS7326/AS7726. | AS5835, AS7326, AS7726 |
| VXLAN/RIOT | Nine model-specific settings from the matching Edgecore profiles; preserve different resource allocations. | AS5835, AS7326, AS7726 |
| Health/LEDs | Implement missing PDDF health LED methods and align color labels. | AS7326, AS7726, AS7816 |
| Watchdog | Thin adapters around platform-common's shared Linux watchdog helper; query without arming hardware. | AS5835, AS7326, AS7726, AS7816 |
| Fan/thermal recovery | Preserve startup speeds and normal policies; use full-speed fallback for unavailable required readings and recover when available. Retry negative PDDF path lookups. Restore AS7326 integer PWM reporting. | Model-specific monitors; shared PDDF retry; AS7326 rounding |
| Clock ordering | Existing IDT setup runs before PDDF claims muxes. | AS7326, AS7726 |
| PSU health | Hardware voltage/temperature limits where verified, AS5835 model-aware voltage decoding, measured standard airflow labels and narrow unsupported target-speed exclusions; AS7326/AS7726/AS7816 capacity read from hardware. | AS5835, AS7326, AS7726, AS7816 |
| Voltage/current CLI | PSU-backed output sensors through existing sensormond on all four models; AS7326/AS7726 additionally expose verified input telemetry. Unavailable readings are handled explicitly. | AS5835, AS7326, AS7726, AS7816 |
| Environmental APIs | PDDF fan/fan-drawer/PSU/board-thermal APIs over native drivers; repair Linux 6.12 fan/PSU hwmon registration. Preserve native device ownership and cooling policy. | AS5835 |
| CPU inventory | Discover coretemp package/core channels after board inventory; use kernel thresholds. | AS5835, AS7326, AS7726, AS7816 |
| BIOS inventory | Read-only DMI BIOS version through existing PDDF component API. | AS7326, AS7726, AS7816 |

## Dependency and merge order

The watchdog adapters depend on [sonic-platform-common PR #808](https://github.com/sonic-net/sonic-platform-common/pull/808), linked to [issue #807](https://github.com/sonic-net/sonic-platform-common/issues/807). The buildimage submodule pointer records published review commit `1c8e439f9f14ef04dd05fa62d79e635c215d24d6`. Merge #808 first, then select an upstream revision containing the helper before merging buildimage #30780. The helper is independent of the Accton changes.

The latest monitoring changes reuse existing platform-daemons functionality. They add no platform-daemons submodule changes. The experimental sairedis rollback used for hardware validation is not part of buildimage #30780.

## Latest implementation follow-ups

| Commit | Follow-up |
|---|---|
| `01fe703ff` | Expose AS7326/AS7726 PSU voltage/current through existing sensormond; reuse PSU APIs and hardware voltage limits. |
| `a91476558` | Preserve AS7326 integer PWM reporting: full PWM reports 100%, not 101%; retain the original PWM targets and policy. |
| `2e33f40db` | Retry PDDF missing sensor paths instead of caching empty lookups permanently; keep positive caching. |
| `09289bde8` | Add AS7326 CPU package/core inventory after the original board sensors. |
| `08c890784` | Expose AS7326 hardware PSU OT_WARN_LIMIT and remove the obsolete PSU temperature health exclusion. |
| `e58a14a1d` | Add read-only BIOS inventory on AS7326/AS7726 through the existing PDDF component API. |

## Validation

### Software validation

- **149 tests passed** across the Accton platform and PDDF suites (101 Accton, 48 PDDF).
- **Five watchdog-helper tests passed** separately.
- `git diff --check` passes.

```bash
PYTHONPATH=src/sonic-platform-common:src/sonic-py-common:platform/pddf/platform-api-pddf-base \
  python3 -m pytest -q -p no:cacheprovider -o addopts='' \
  platform/broadcom/sonic-platform-modules-accton/tests \
  platform/pddf/platform-api-pddf-base/tests

PYTHONPATH=src/sonic-platform-common:src/sonic-py-common \
  python3 -m pytest --import-mode=importlib -q -p no:cacheprovider -o addopts='' \
  src/sonic-platform-common/tests/linux_watchdog_test.py
```

Regressions cover PSU sensor units, unavailable readings and recovery; hardware voltage/temperature definitions; every AS7326 PWM step and 38/75/100% round trips; recovery from delayed hwmon registration without restarting the controller; CPU discovery and kernel thresholds; read-only BIOS inventory; existing LED/watchdog/thermal behavior; and compiled AS5835 voltage conversion callbacks. Simulated failures do not require fault injection on hardware.

### Hardware validation on AS7326 and AS7726 (2026-11-18–19)

Both models ran `SONiC.accton-fixes2-itjamie.20261118-20-ztp` (master-derived source `892dccbb`, Debian 13.7, Broadcom XGS SAI `15.2.1.0.0.0.50.1`). That experimental image pins sairedis to the SAI-header rollback in [sonic-sairedis #2170](https://github.com/sonic-net/sonic-sairedis/pull/2170). **The sairedis rollback is not part of this PR.** The latest monitoring fixes were applied live to that image and tested after the relevant service restarts; a full image containing the latest follow-ups has not been built.

| Check | AS7326-56X | AS7726-32X |
|---|---|---|
| SDK, interfaces and provisioning | SDK running, 56 ports present, fresh-install ZTP successful | SDK running, 32 ports present, fresh-install ZTP successful |
| Chassis fans | All twelve present/healthy; speed and target 38%; the original 38/75/100% policy is preserved | All twelve present/healthy; speed and target 38%; original policy preserved |
| Temperature recovery | Reproduced the persistent negative-path cache; patched lookups recover, and the running controller returned from full-speed fallback to 38% | Existing thermal monitor remains healthy |
| Voltage/current CLI | Both PSU output readings populated by sensormond, in mV/mA | Same |
| PSU hardware limits | FSF019-611 voltage limits 11.390/12.593 V; OT_WARN_LIMIT exposed as 70000 millidegrees / 70°C on both supplies | Same voltage and temperature limits |
| PSU health | Presence, power-good, airflow and temperature checks enabled; obsolete temperature exclusion removed | Presence, power-good, airflow and temperature checks enabled |
| CPU inventory | Four board sensors retained, followed by CPU package and four cores; kernel thresholds 82/104°C | Five board sensors retained, followed by CPU package and four cores; kernel thresholds 82/104°C |
| Firmware inventory | BIOS `v40.01.01.00` reported by `show platform firmware status` | Same |
| Health and watchdog | Services/hardware OK, status LED green, no failed systemd units; boot watchdog disarm and non-arming status queries work | Same |
| Existing connectivity | Both active 100G uplinks and IPv4/EVPN sessions stayed established | Active 100G uplink and IPv4/EVPN session stayed established |

syncd, SWSS and BGP were not restarted for the live monitoring edits. Unsupported current thresholds remain N/A; BIOS inventory does not imply CPLD version or firmware-update support. End-to-end VXLAN forwarding, warm restart, resource-stress testing and a fresh image/reboot with the latest commits remain outstanding. AS5835 still requires community-image hardware validation. AS7816 environmental validation is documented below; SAI and front-panel port operation were outside that check.

### Earlier 202605 validation

Equivalent platform fixes were exercised on AS7326 and applied live to AS7726 using `SONiC.202605-itjamie.20261113-17-ztp` (upstream `5ef9e45c`). These checks included SDK startup, interfaces, ZTP, health, watchdog disarm, PSU voltage limits and IPv4/EVPN connectivity. These older observations are distinct from the current master-derived image plus live follow-ups above.

### AS5835 validation scope

Working Edgecore ec202111 AS5835 observations identified bad YM-1401A manufacturer voltage-limit decoding. The shared ym2651y fix selects its existing VOUT_MODE-aware callback for YM1401A/YM2401 and preserves LINEAR11 for other supported models. A compiled regression exercises the production callback wiring. CPU discovery and kernel-threshold tests also pass, including sparse core labels. AS5835 full-image validation remains outstanding; AS7816 environmental validation is recorded below.

## Release integration

The implementation PRs target master. No release backport is requested here. A branch-specific backport requires the watchdog dependency and validation against that branch. Latest follow-ups have not been rebuilt into a fresh image; cold-boot integration with those commits, end-to-end VXLAN forwarding, warm restart and resource-stress testing remain outstanding.


### AS5835 PDDF environmental migration (2026-11-19)

Two signed-off commits extend the AS5835-54X support:

| Commit | Change |
| --- | --- |
| [`fb24fc165`](https://github.com/ITJamie/sonic-buildimage/commit/fb24fc165) | Fix native fan/PSU hwmon registration: the chip-info registration API returned EINVAL with no chip-info table on Linux 6.12, removing fan PWM/presence and PSU presence/power-good attributes. Use the group-registration API for the existing client-attribute layout. |
| [`9214803fc`](https://github.com/ITJamie/sonic-buildimage/commit/9214803fc) | Use PDDF fan, fan-drawer, PSU and board-thermal APIs over native-driver sysfs mappings; reuse shared PSU output voltage/current adapters and report hardware capacity. |

The native platform service retains I2C client creation and the original 40/65/80/100% cooling policy. Native LEDs, EEPROM, firmware inventory, watchdog, SFP handling and port events are preserved. These are environmental API mappings, not a generic PDDF device-creation topology. Both rotors per tray are mapped; missing fault data stays unhealthy. Existing names and narrow unsupported PSU health exclusions are preserved. CPU sensors remain appended after the four board sensors. Native YM-1401A output power is converted from mW to W. Input telemetry and PSU fan targets remain explicitly unsupported.

The earlier native output-sensor implementation from `b64a2fcbd` is superseded by shared PDDF adapters, retaining unavailable-reading handling and the existing sensormond integration. No sonic-platform-daemons changes are included.

Validation:

- **149 Accton/PDDF tests pass** (101 Accton, 48 PDDF), including real PDDF path resolution, both PSU interfaces, rotor RPM/faults, unscaled native PWM writes, API units, missing/malformed samples, inventory and recovery.
- Fan, PSU and dependent CPLD modules compile and link against Debian Linux 6.12.117 headers.
- Read-only checks on AS5835 hardware running the existing community image confirm PDDF access to both PSUs' voltage/current/power, hardware voltage limits, 400 W capacity, RPM and temperature, plus all four board temperatures and 80°C thresholds.
- Corrected modules have not been loaded on the exact SONiC kernel. Live fan/presence/health validation and a full image/reboot with the migration remain pending; the older installed image also lacks the shared PSU sensor module included by this branch.


### AS7326/AS7726 input telemetry follow-up (2026-11-19)

Signed-off commit `5b9c212e4` registers input voltage/current/power (PMBus READ_VIN 0x88, READ_IIN 0x89 and READ_PIN 0x97) using each model's PSU bus/address mappings. An opt-in adapter exposes V/A/W through the PSU API; input voltage/current sensors are appended after existing output inventory for sensormond. Input power uses `get_input_power()`; no platform-daemons source changes are included. Missing, invalid, absent or power-faulted samples stay unavailable. Manufacturer ratings are not used as warning thresholds.

Read-only PMBus checks on FSF019-611 PSUs in both models returned input voltage around 226–228 V, current around 0.31–0.38 A and input power around 72–80 W. All four supplies remained power-good. These checks validate hardware telemetry, not deployment of the new reporting code. AS5835 YM-1401A input voltage/current/power registers returned zeros despite active output; AS5835 input telemetry remains unsupported.

All **144 Accton/PDDF tests pass** (96 Accton, 48 PDDF), including six input telemetry tests for register mappings, units, unavailable readings, recovery, sensor limits and AS5835 exclusion. The new reporting still needs deployment validation.


### AS7816 environmental validation and follow-up (2026-11-19)

Signed-off buildimage commit `45a93cbc9` completes AS7816-64X environmental monitoring. It registers YM-2851F output-voltage limits, temperature warning limits and manufacturer maximum output power; reports capacity from hardware rather than the former 1200 W constant; uses real PSU airflow readings and standard labels; enables output voltage/current sensors; appends CPU sensors after the six existing board sensors; and adds read-only BIOS inventory. Only unsupported PSU fan target comparisons are excluded. Input telemetry remains explicitly unsupported because both supplies returned zero for input voltage/current/power despite active output.

| Check | AS7816-64X result |
| --- | --- |
| Test image and method | `SONiC.accton-fixes2-itjamie.20261118-20-ztp`; environmental changes applied live and checked after relevant environmental service restarts. The image's separate sairedis rollback remains outside this PR. |
| PSU output monitoring | Both YM-2851F supplies report voltage/current through standard sensor commands; hardware voltage limits are 11.390–12.593 V. |
| PSU temperature and capacity | Hardware OT_WARN_LIMIT is 107°C on both supplies; temperature checks are enabled. Manufacturer output capacity is 850 W per supply, read dynamically. |
| Fan control and recovery | All eight chassis fans present and healthy at the original 52% policy. The shared missing-path retry fixed the observed long-running controller's false missing-temperature fallback; CPU discovery preserves all six board sensor indices. |
| PSU fans | Real F2B readings produce standard EXHAUST labels; presence/status/airflow remain checked, with only unsupported target-speed comparisons excluded. |
| CPU and BIOS inventory | CPU package and four cores report kernel thresholds 82/104°C; BIOS reports v40.01.01.02. |
| System health | Services and Hardware OK, status LED green, all Monit checks OK and no failed systemd units. Environmental daemons running after restart. |
| Watchdog queries | Supported iTCO_wdt remained inactive before and after status/time-left queries. |

SAI and port configuration were left untouched. syncd/SWSS container identities and start times were unchanged; front-panel port operation and forwarding were intentionally outside this validation. A fresh image containing the latest changes still needs build/reboot validation.

All **144 Accton/PDDF tests pass** (96 Accton, 48 PDDF), including AS7816 PSU register mappings and API units, dynamic capacity, unsupported inputs, airflow labels, CPU/BIOS inventory, preserved fan policy and delayed-hwmon recovery. No platform-daemons source changes are added.


### AS7326/AS7726 hardware PSU capacity follow-up (2026-11-19)

Signed-off commit `25e1c0590` registers MFR_POUT_MAX (PMBus 0xa7) on both PSU interfaces for AS7326-56X and AS7726-32X. Both `get_maximum_supplied_power()` and `get_capacity()` now use the manufacturer reading through PDDF's existing milliwatt-to-watt conversion, replacing the former 1200 W constants. AS7816 already uses the same hardware-derived capacity approach; AS5835 capacity reporting is unchanged.

Live checks on FSF019-611-equipped AS7326 and AS7726 switches returned **650000 mW / 650 W from all four supplies**. After re-registering only the PSU telemetry interfaces and restarting only psud, both capacity APIs returned 650 W, all supplies remained power-good, system health stayed green and chassis fans retained their 38% targets. Capacity is read dynamically rather than replaced with a 650 W constant. SAI and port configuration were untouched.

All **144 Accton/PDDF tests pass** (96 Accton, 48 PDDF). Four new capacity regressions cover each interface's bus/address/register, both API units, changing manufacturer readings, and missing/failed reads without a fabricated fallback rating. The latest live-tested changes still need validation in a freshly built image.
