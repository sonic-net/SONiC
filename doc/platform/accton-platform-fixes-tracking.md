# Accton/Edgecore platform initialization and health fixes

## Overview

This document tracks the related changes in `sonic-buildimage` and
`sonic-platform-common` to address Accton/Edgecore platform initialization and
hardware-health failures.

On AS7326-56X with newer Broadcom SAI/SDK versions, insufficient stable-cache
allocation prevents SDK initialization, leaving front-panel interfaces
unavailable. Once initialization succeeds, additional platform integration
issues affect health reporting, status LEDs, watchdog access, thermal control
and PSU monitoring.

The implementation also addresses corresponding code and configuration in
AS5835-54X, AS7726-32X and AS7816-64X where applicable. Hardware validation has
been performed on AS7326-56X; the changes do not imply that every model has
the same failure or requires every fix.

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
| --- | --- | --- |
| SDK initialization | Increase stable cache to 128 MiB; select the packaged Cancun `default` symlink on AS7326/AS7726. | AS5835, AS7326, AS7726 |
| VXLAN configuration | Restore nine settings from Edgecore's matching BCM profiles, preserving model-specific overlay resource allocations. | AS5835, AS7326, AS7726 |
| Health and LEDs | Implement the PDDF chassis health LED APIs and align color labels with health configuration. | AS7326, AS7726, AS7816 |
| Watchdog | Provide thin platform adapters using the shared `LinuxWatchdog` helper; add the native AS5835 getter and the missing PDDF `syslog` import. | AS5835, AS7326, AS7726, AS7816 |
| Thermal control | Request full fan speed when required sensor data is unavailable, retry through the existing polling loop and resume the normal policy when readings recover. | AS5835, AS7326, AS7726, AS7816 |
| Clock initialization | Order existing IDT setup before PDDF claims the I2C muxes. | AS7326, AS7726 |
| PSU monitoring | Expose AS7326/AS7726 PMBus voltage limits, correct AS5835 manufacturer voltage-limit decoding, and exclude unsupported per-PSU-fan target-speed comparisons; recognize the observed `F2B*` airflow label on AS7326 only. | AS5835, AS7326, AS7726 |
| CPU monitoring | Append dynamically discovered coretemp package/core sensors after the existing board inventory; read kernel thresholds and report unavailable inputs. | AS5835, AS7726 |

Vendor configuration references come from [Edgecore's platform sources](https://github.com/edge-core/sonic-buildimage/tree/d39662e996c0e8748c9b96ad88dc5f5f524e8048/device/accton).
Clock ordering also follows the approach proposed in
[sonic-buildimage #30498](https://github.com/sonic-net/sonic-buildimage/pull/30498).
The implementation PR contains the individual changes and additional related
reports.

## Dependency and merge order

`sonic-platform-common` PR #808 introduces
`sonic_platform_base.linux_watchdog.LinuxWatchdog`. It implements the existing
watchdog interface for the Linux `iTCO_wdt` and `wdat_wdt` driver identities.
Construction and status queries use sysfs without opening the watchdog
character device or changing the armed state. Explicit arm/disarm operations
use the character device and kernel ioctls.

The Accton watchdog adapters in `sonic-buildimage` PR #30780 import this helper.
They therefore require a `sonic-platform-common` revision containing #808.
The shared helper does not depend on the Accton platform changes, so the
dependency is one-way.

Merge sequence:

1. Review and merge `sonic-platform-common` PR #808.
2. Update the `src/sonic-platform-common` submodule pointer in buildimage
   PR #30780 to an upstream revision containing the merged helper, then rerun
   the relevant regression checks.
3. Merge buildimage PR #30780 after its platform review and checks complete.

The buildimage PR currently pins the published review commit
`1c8e439f9f14ef04dd05fa62d79e635c215d24d6`. This is a review dependency, not the
final upstream integration revision. Before merge, recursive submodule fetches
must be able to obtain the selected commit from the configured upstream remote.

## Validation

### Software

The master-based buildimage checkout and companion platform-common change pass
39 regression tests and 41 subtests. Coverage includes the Linux watchdog
helper and platform adapters, health LED delegation, thermal failure/recovery,
PSU voltage, airflow and narrowly scoped health exclusions, and AS5835/AS7726 CPU
discovery, kernel thresholds, read failures/recovery and chassis integration.

The watchdog helper's standalone suite passes five tests with fake sysfs and
mocked device/ioctl operations. The combined totals above include these tests.

### AS7326-56X hardware

Equivalent platform patches were exercised in
`SONiC.202605-itjamie.20261113-17-ztp`, built from upstream `5ef9e45c`, with
Broadcom XGS SAI `15.2.1.0.0.0.50.1` and SDK `6.5.35-SP1`.

- SDK initialization succeeds and all 56 front-panel ports are available.
- Fresh-install ZTP completes and saved configuration survives reboot.
- System health reports green, with services and hardware OK.
- Boot-time watchdog disarm succeeds.
- Two L2 VNIs are created and advertised, and IPv4/EVPN BGP sessions establish
  to the connected spine.
- Both FSF019-611 PSUs expose voltage limits of 11.390/12.593 V through sysfs,
  the platform API and STATE_DB.
- No container or systemd automatic restarts were observed during approximately
  34 minutes of post-boot observation.

### AS7726 vendor comparison

Read-only comparison used working Edgecore ec202111 (SDK 6.5.21) and Broadcom
Enterprise 4.5.1 installations. Both report FSF019 PSU voltage limits of
11.390/12.593 V; the enterprise PDDF definitions specify voltage-limit
registers `0xa4`/`0xa5` on PSU1 bus/address `0x32/0x5b` and PSU2 `0x31/0x58`.
The community change adds these mappings without hardcoding voltage limits.

The enterprise API leaves PSU fan target speed unsupported, while Edgecore
returns the measured speed as its target. Neither provides an independent
expected-speed reference. Only the two PSU-fan target-speed comparisons are
excluded; other PSU/fan monitoring remains enabled.

Edgecore exposes CPU package/core sensors through the coretemp platform
path. The new community reader discovers those labelled channels, reads
kernel thresholds and tolerates hwmon/channel renumbering. Invalid or missing
readings are unavailable, rather than 0 degrees. CPU sensors are discovered
at chassis construction; an absent optional coretemp device does not block
the existing five PDDF board sensors.

These observations inform the implementation and its software tests; they
do not establish hardware validation of the new AS7726 community changes.

### AS5835 vendor comparison and software regressions

Working Edgecore ec202111 AS5835-54X observations identified YM-1401A PSU
manufacturer voltage limits of -768/1472 V, already incorrect in native
sysfs. The shared `ym2651y` driver registered these thresholds with its
LINEAR11 callback instead of its existing model-aware voltage callback.
The fix selects VOUT_MODE decoding for YM1401A/YM2401 and retains LINEAR11
for other supported supplies; it does not hardcode voltage limits.
A compiled regression executes the production functions and registered
callbacks for both formats and fails with the original callback wiring.

The native PSU fan target method no longer returns measured speed as its
own target. Only `PSU-1 FAN-1.speed` and `PSU-2 FAN-1.speed` comparisons are
excluded. Chassis PWM targets, presence/fault checks and airflow mappings
remain unchanged.

CPU package/core sensors are appended after the four existing board sensors.
Tests cover sparse kernel labels (cores 2/6/8/12), kernel-provided 71/91 degree
thresholds, renumbering, invalid/missing inputs and native chassis integration.
Fan startup speeds and control policy remain unchanged. These additions are
software-tested; AS5835 community-image hardware validation is outstanding.

### Remaining validation

A full master image build and hardware checks on AS5835, AS7726 and AS7816
remain outstanding. End-to-end VXLAN forwarding, warm restart and
maximum-resource workloads are not established by the current tests.

The 128 MiB stable-cache allocation is a working value, not a measured minimum.
The PSU-fan exclusions remove only target-speed comparisons where a usable
target is unavailable; presence/status, measured speed, airflow and voltage
checks remain enabled.

## Release integration

The implementation PRs target master. No release-branch backport is requested
at this stage; any later backport needs the helper dependency and validation
for the selected branch.
