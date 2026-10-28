# Aspeed BMC Boot Watchdog Disarm — High Level Design

## Table of Contents

- [Scope](#scope)
- [Definitions and Abbreviations](#definitions-and-abbreviations)
- [Background](#background)
- [Problem Statement](#problem-statement)
- [Requirements](#requirements)
- [Proposed Solution](#proposed-solution)

## Scope

This document covers the design of a new systemd service for Aspeed AST2720-based BMC platforms running SONiC. The service disarms the AST2720 WDTA (Watchdog Timer) boot watchdog early in the Linux boot sequence when ABR (Alternate Bootblock Recovery) is enabled.

## Definitions and Abbreviations

| Term | Definition |
| :---- | :---- |
| ABR | Alternate Bootblock Recovery — An OTP-configurable hardware feature that allows the BMC's boot controller to attempt boot from an alternate boot source should boot fail from the primary boot source |
| WDTA | Watchdog Timer A — the hardware boot watchdog on the AST2720 that triggers ABR |
| BMC | Baseboard Management Controller |

## Background

### ABR Architecture in AST2720

The Aspeed AST2720 BMC chip supports a dual boot source with hardware redundancy via the ABR mechanism:

```
Power On
   │
   ▼
AST2720
   │  is ABR enabled?
   │  if yes: starts WDTA countdown
   ▼
Boot Primary Boot Source
   │  loads OS kernel
   ▼
Linux / SONiC boots
   │
   ├── WDTA disarmed before timeout →  stays on Primary Boot Source
   └── WDTA expires                 →  chip resets → boot Alternate Boot Source
```

## Problem Statement

When ABR is enabled, WDTA starts counting at power-on and will try to trigger a reset and boot from the vendor-configured alternate boot source if the WDTA expires.
Therefore, a mechanism is required to disarm WDTA in the usual boot process before it expires.

## Requirements

1. On Aspeed AST2720-based BMC platforms where ABR is enabled, WDTA must be disarmed before its timeout expires during a normal SONiC boot.
   **NOTE:** The configuring of the WDTA timeout value is left to the vendor's u-boot implementation.
2. The Disarming Mechanism must be visible in system logs especially in case of failure.
3. The Disarming Mechanism must not block or delay the rest of the boot sequence in case of failure.
4. On hardware where ABR is not enabled, the service must exit cleanly without side effects.

## Proposed Solution

A new `oneshot` systemd service — `aspeed-disable-boot-watchdog` — is introduced to the `aspeed-platform-services` package. It runs early in the Linux boot sequence, before `local-fs.target`, and disarms WDTA by clearing the enable bit in the WDTA control register via a direct memory-mapped register write.

The service is ordered `Before=local-fs.target` so it executes well ahead of any SONiC services that could delay the disarming process. It uses `Wantedby=` dependency semantics so a failure is logged but does not block the rest of the boot sequence.

The boot sequence with the service in place:

```
AST2720 → Boot(Primary Src) → kernel → systemd early boot
                                          │
                                          ▼
                          aspeed-disable-boot-watchdog  ← Before=local-fs.target
                              (disarms WDTA via register write)
                                          │
                                          ▼
                              local-fs.target
                                          │
                                          ▼
                              ... rest of SONiC boots ...
                              (WDTA already disarmed — No Reset to Alt. Boot Src)
```

On hardware where WDTA is not running (ABR not enabled), the register write is a safe no-op and the service exits cleanly.
