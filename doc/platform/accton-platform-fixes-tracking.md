# Accton/Edgecore platform initialization and health fixes

## Overview

This document tracks sonic-buildimage #30780 and the shared Linux watchdog helper in sonic-platform-common #808. SDK stable-cache exhaustion diagnosed on AS7326 exposed further platform health and monitoring gaps. The implementation includes model-specific fixes for AS5835, AS7326, AS7726 and AS7816; hardware validation covers AS7326/AS7726 and AS7816 environmental monitoring. AS5835 environmental monitoring and startup follow-ups were validated live.

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
| Environmental APIs | PDDF fan/fan-drawer/PSU/board-thermal APIs over native drivers; repair Linux 6.12 fan/PSU hwmon registration and host initialization order. Preserve native device ownership and cooling policy; scope PSU airflow health exclusions. | AS5835 |
| CPU inventory | Discover coretemp package/core channels after board inventory; use kernel thresholds. | AS5835, AS7326, AS7726, AS7816 |
| BIOS inventory | Read-only DMI BIOS version through existing PDDF component API. | AS7326, AS7726, AS7816 |

## Dependency and merge order

The watchdog adapters depend on [sonic-platform-common PR #808](https://github.com/sonic-net/sonic-platform-common/pull/808), linked to [issue #807](https://github.com/sonic-net/sonic-platform-common/issues/807). The buildimage submodule pointer records published review commit `e6c4beb0c743cb46296a98456e21cd795092f049`. Merge #808 first, then select an upstream revision containing the helper before merging buildimage #30780. The helper is independent of the Accton changes.

The latest monitoring changes reuse existing platform-daemons functionality. They add no platform-daemons submodule changes. The experimental sairedis rollback used for hardware validation is not part of buildimage #30780.

## Latest implementation follow-ups

| Commit | Follow-up |
|---|---|
| `c5a6e3aab` | Expose AS7326/AS7726 PSU voltage/current through existing sensormond; reuse PSU APIs and hardware voltage limits. |
| `a707ff7aa` | Preserve AS7326 integer PWM reporting: full PWM reports 100%, not 101%; retain the original PWM targets and policy. |
| `a4d3313a1` | Retry PDDF missing sensor paths instead of caching empty lookups permanently; keep positive caching. |
| `49ab88bcb` | Add AS7326 CPU package/core inventory after the original board sensors. |
| `85d15b6ec` | Expose AS7326 hardware PSU OT_WARN_LIMIT and remove the obsolete PSU temperature health exclusion. |
| `4ab65164a` | Add read-only BIOS inventory on AS7326/AS7726 through the existing PDDF component API. |

## Validation

### Software validation

- **157 tests passed** across the Accton platform and PDDF suites (109 Accton, 48 PDDF).
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

syncd, SWSS and BGP were not restarted for the live monitoring edits. Unsupported current thresholds remain N/A; BIOS inventory does not imply CPLD version or firmware-update support. End-to-end VXLAN forwarding, warm restart, resource-stress testing and a fresh image/reboot with the latest commits remain outstanding. AS5835 community-image hardware results are documented below. AS7816 environmental validation is documented below; SAI and front-panel port operation were outside that check.

### Earlier 202605 validation

Equivalent platform fixes were exercised on AS7326 and applied live to AS7726 using `SONiC.202605-itjamie.20261113-17-ztp` (upstream `5ef9e45c`). These checks included SDK startup, interfaces, ZTP, health, watchdog disarm, PSU voltage limits and IPv4/EVPN connectivity. These older observations are distinct from the current master-derived image plus live follow-ups above.

### AS5835 validation scope

Working Edgecore ec202111 AS5835 observations identified bad YM-1401A manufacturer voltage-limit decoding. The shared ym2651y fix selects its existing VOUT_MODE-aware callback for YM1401A/YM2401 and preserves LINEAR11 for other supported models. A compiled regression exercises the production callback wiring. CPU discovery and kernel-threshold tests also pass, including sparse core labels. AS5835 and AS7816 environmental validation is recorded below.

## Release integration

The implementation PRs target master. No release backport is requested here. A branch-specific backport requires the watchdog dependency and validation against that branch. Latest follow-ups have not been rebuilt into a fresh image; cold-boot integration with those commits, end-to-end VXLAN forwarding, warm restart and resource-stress testing remain outstanding.


### AS5835 PDDF environmental migration and live validation (2026-11-20)

| Signed-off commit | Change |
| --- | --- |
| [`308c2305e`](https://github.com/ITJamie/sonic-buildimage/commit/308c2305e) | Fix native fan/PSU hwmon registration for the existing client-attribute layout. |
| [`54a93bf6f`](https://github.com/ITJamie/sonic-buildimage/commit/54a93bf6f) | Use PDDF environmental APIs over native-driver sysfs mappings, including both fan rotors and shared PSU output sensors. |
| [`a181355f4`](https://github.com/ITJamie/sonic-buildimage/commit/a181355f4) | Construct PddfApi before reading plugin data so host startup creates the platform link before EEPROM, health and watchdog API initialization. |
| [`890a7ccdd`](https://github.com/ITJamie/sonic-buildimage/commit/890a7ccdd) | Exclude only the two PSU fan direction comparisons under the explicit AS5835 policy assumption that installed PSU airflow matches the chassis. |

The native platform service retains I2C client creation, the original 40/65/80/100% cooling policy, LEDs, EEPROM, firmware inventory, watchdog, SFP handling and port events. These are environmental API mappings; generic PDDF device creation is not enabled. CPU sensors remain appended after the four board sensors. Native YM-1401A power is converted from mW to W, with capacity read from hardware. Input telemetry and PSU fan target speeds remain unsupported. No sonic-platform-daemons changes are included.

The startup issue was reproduced on the host: the AS5835 native initialization path leaves `/usr/share/sonic/platform` absent, and reading `pd-plugin.json` before constructing PddfApi raises FileNotFoundError. EEPROM identity decoding consequently fails, ZTP sends error text in its identity headers, and system-health/watchdog-control fail to start. Constructing PddfApi first follows the initialization order used by the working PDDF models and preserves PMON's existing directory layout.

Airflow policy is explicit: raw chassis readings report intake and raw PSU readings report exhaust. Those values remain visible. Physical alignment is assumed by operator policy; only `PSU-1 FAN-1.direction` and `PSU-2 FAN-1.direction` health comparisons are excluded. PSU fan presence/status, chassis fan direction/speed and PSU voltage checks remain enabled. Existing unsupported PSU target-speed and PSU temperature-threshold exclusions are unchanged.

| Hardware check | AS5835-54X result |
| --- | --- |
| Image | `SONiC.accton-fixes2-itjamie.20261120-12-ztp`, Debian 13.7 / Linux 6.12.94; the two follow-ups were applied live. The experimental sairedis rollback remains outside this PR. |
| SDK and inventory | SAI running; all 54 interfaces present, with two 100G physical links up. |
| Fans and PSUs | All ten chassis rotors and both PSUs present and healthy; normal chassis speed/target 40%. YM-1401A capacity 400 W through the PSU API. |
| Sensors | Board/CPU/PSU temperatures and output voltage/current commands work. Voltage limits are hardware-derived; CPU thresholds are 71/91°C. |
| EEPROM and ZTP identity | Product, serial and base-MAC decoding succeeds. A request using the ZTP identity headers receives HTTP 200 through the management VRF; existing provisioning was not re-executed. |
| Watchdog | wdat_wdt passed a real 30-second arm/immediate-disarm test; watchdog-control completes successfully. |
| System health | Service runs successfully. Services OK / Hardware OK and physical LED green under the documented airflow policy; no failed systemd units. |

**157 Accton/PDDF tests pass** (109 Accton, 48 PDDF), plus **five watchdog-helper tests**. Four startup regressions use the production context loader and PDDF initialization against a temporary filesystem: missing/existing host aliases, PMON directory layout and initialization errors. Four airflow regressions exercise the production SONiC health checker to verify the narrow exclusions, retained PSU presence/status and chassis direction/speed faults, and unchanged raw direction reporting.


### AS7326/AS7726 input telemetry follow-up (2026-11-19)

Signed-off commit `ed7bd5d96` registers input voltage/current/power (PMBus READ_VIN 0x88, READ_IIN 0x89 and READ_PIN 0x97) using each model's PSU bus/address mappings. An opt-in adapter exposes V/A/W through the PSU API; input voltage/current sensors are appended after existing output inventory for sensormond. Input power uses `get_input_power()`; no platform-daemons source changes are included. Missing, invalid, absent or power-faulted samples stay unavailable. Manufacturer ratings are not used as warning thresholds.

Read-only PMBus checks on FSF019-611 PSUs in both models returned input voltage around 226–228 V, current around 0.31–0.38 A and input power around 72–80 W. All four supplies remained power-good. These checks validate hardware telemetry, not deployment of the new reporting code. AS5835 YM-1401A input voltage/current/power registers returned zeros despite active output; AS5835 input telemetry remains unsupported.

All **144 Accton/PDDF tests pass** (96 Accton, 48 PDDF), including six input telemetry tests for register mappings, units, unavailable readings, recovery, sensor limits and AS5835 exclusion. The new reporting still needs deployment validation.


### AS7816 environmental validation and follow-up (2026-11-19)

Signed-off buildimage commit `e7e99426f` completes AS7816-64X environmental monitoring. It registers YM-2851F output-voltage limits, temperature warning limits and manufacturer maximum output power; reports capacity from hardware rather than the former 1200 W constant; uses real PSU airflow readings and standard labels; enables output voltage/current sensors; appends CPU sensors after the six existing board sensors; and adds read-only BIOS inventory. Only unsupported PSU fan target comparisons are excluded. Input telemetry remains explicitly unsupported because both supplies returned zero for input voltage/current/power despite active output.

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

Signed-off commit `fcb77b966` registers MFR_POUT_MAX (PMBus 0xa7) on both PSU interfaces for AS7326-56X and AS7726-32X. Both `get_maximum_supplied_power()` and `get_capacity()` now use the manufacturer reading through PDDF's existing milliwatt-to-watt conversion, replacing the former 1200 W constants. AS7816 already uses the same hardware-derived capacity approach; AS5835 capacity reporting is unchanged.

Live checks on FSF019-611-equipped AS7326 and AS7726 switches returned **650000 mW / 650 W from all four supplies**. After re-registering only the PSU telemetry interfaces and restarting only psud, both capacity APIs returned 650 W, all supplies remained power-good, system health stayed green and chassis fans retained their 38% targets. Capacity is read dynamically rather than replaced with a 650 W constant. SAI and port configuration were untouched.

All **144 Accton/PDDF tests pass** (96 Accton, 48 PDDF). Four new capacity regressions cover each interface's bus/address/register, both API units, changing manufacturer readings, and missing/failed reads without a fabricated fallback rating. The latest live-tested changes still need validation in a freshly built image.
