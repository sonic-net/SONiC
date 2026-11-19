# SONiC Steady State Watchdog HLD #

## Table of Content

1. [Scope](#Scope)
2. [Overview](#Overview)
3. [Requirements](#Requirements)
4. [Architecture Design](#Architecture%20Design)
5. [High Level Design](#High%20level%20Design)
6. [Configuration and management](#Configuration%20and%20management)
7. [Warmboot and Fastboot Design Impact](Warmboot%20and%20Fastboot%20Design%20Impact)
8. [Testing Requirements/Design](#Testing%20Requirements/Design)



### Revision

### Scope

This document provides a mechanism to enable the Linux watchdog service in steady state in SONiC.


### Definitions/Abbreviations

This section covers the abbreviation if any, used in this high-level design document and its definitions.

### Overview

Currently in SONiC, hardware watchdog is not enabled and used in steady state. SONiC watchdog-control service comes up and disables the watchdog in the system. The reasons for doing this might have been historical or related to debugability issues on specific platforms. Regardless, the watchdog is disabled in steady state by default.

This document specifies how SONiC can enable the Linux watchdog daemon so that a selected hardware watchdog is periodically stroked during normal device operation. This provides a standard SONiC mechanism to enable watchdog protection in steady state while keeping the feature disabled by default and controlled by SONiC configuration.

On watchdog expiry, the normal hardware action is to reboot the system. The exact behavior on watchdog expiry is however platform defined. A platform may simply reset the router, or it may collect kernel dump and other debug information before completing the reboot, depending on the platform hardware capability and software support. 

### Requirements

Enable the Linux watchdog service when requested through SONiC configuration.

The following requirements are covered by this design:

- Watchdog is disabled by default.
- Watchdog can be enabled and disabled using SONiC CLI.
- Watchdog identity, timeout, and pretimeout can be configured using SONiC CLI.
- Updating identity, timeout, or pretimeout restarts the watchdog service if watchdog is enabled.
- Timeout and pretimeout follow Linux watchdog semantics and are validated against the selected device's capabilities and supported timeout range.
- Existing reboot code paths that use `watchdogutil` continue to operate as before.

### Architecture Design

Since SONiC is used on multiple vendor devices, the current design might be sufficient or desirable for some vendors e.g. if the vendor does not have a hardware watchdog protection on the board or there is no way to identify a watchdog triggered reboot in the system etc. In order to not cause a churn, the solution should aim at supporting the watchdog if desired by configuration.

#### Linux Watchdog service

Linux does support a watchdog daemon which can be configured for stroking the watchdog periodically. This provides a standard mechanism to support this requirement without inventing something completely new. The service would need to be brought in and enabled through SONiC configuration.

The watchdog service is provided by the Debian `watchdog` package. SONiC installs this package into the host image and owns the selected runtime configuration required to stroke the chosen hardware watchdog periodically.

It is important that the watchdog stroking frequency and watchdog timer design is chosen carefully in order to not cause false alarms in the system.

Since the linux watchdog daemon comes from the community, we would get the benefit of community supported code, configuration mechanisms and any improvements which might be made in future.

### High Level Design

#### SONiC configuration based enablement

The watchdog feature is controlled through SONiC configuration.

The `watchdog` Debian package is installed into the SONiC host image. During image build, SONiC merges its default watchdog daemon settings into `/etc/watchdog.conf` and disables the package-provided `watchdog.service` so the service does not start by default.

The SONiC `watchdog-control.service` runs `/usr/local/bin/watchdog-control.sh` as a oneshot service. The script reads the `WATCHDOG|config` entry from CONFIG_DB and either starts the Linux watchdog service or keeps it disabled.

The CLI commands are:

	config watchdog enable
	config watchdog disable
	config watchdog identity <name>
	config watchdog timeout <timeout> [--pretimeout <pretimeout>]
	config watchdog pretimeout <pretimeout>

SONiC provides separate configuration for watchdog timeout and pretimeout, following Linux watchdog semantics. All values are specified in seconds.

The operator can configure either value individually or update both together using `config watchdog timeout <timeout> --pretimeout <pretimeout>`.

The CLI updates CONFIG_DB and immediately invokes `watchdog-control.sh` so the runtime state follows the configuration change. If the watchdog is already enabled, changing `identity`, `timeout`, or `pretimeout` causes the Linux watchdog service to be reconfigured and restarted. Configuring timeout or pretimeout does not enable watchdog protection by itself.

Before updating CONFIG_DB, the CLI validates the proposed configuration against the selected device's capabilities and supported timeout range. Invalid settings are rejected without changing CONFIG_DB or stopping the running watchdog service.

The default state is disabled. SONiC enables the Linux watchdog service only after `config watchdog enable`.

#### Watchdog Selection

There can be multiple watchdog drivers present in the system. This can be observed on platforms which expose more than one watchdog device.

	sonic@sonic:~$ ls /sys/class/watchdog/
	watchdog0  watchdog1
	sonic@sonic:~$ cat /sys/class/watchdog/*/identity
	board
	wdat_wdt

However only a specific watchdog may be appropriate for use as the system watchdog. Some watchdog devices may reset only part of the system or may be intended for a different hardware component.

The Linux watchdog daemon uses `/etc/watchdog.conf` to select the watchdog device. However, `/dev/watchdog*` numbers are based on device discovery order, so directly selecting `/dev/watchdog1` or another numbered device is not always stable across systems.

To avoid platform-specific symlinks, SONiC stores an optional watchdog identity in CONFIG_DB. The identity is matched against the `identity` file exposed by Linux watchdog devices under `/sys/class/watchdog`.

If the operator configures:

	config watchdog identity board

then `watchdog-control.sh` scans `/sys/class/watchdog/watchdog*/identity`, finds the device whose identity is `board`, and writes the corresponding `/dev/watchdogN` device into `/etc/watchdog.conf`.

If no identity is configured, SONiC uses `/dev/watchdog0` as the default watchdog device.

##### Watchdog Configuration

SONiC provides a default watchdog daemon configuration that is merged into the package-provided `/etc/watchdog.conf` during image build. This follows the same general model used for other host configuration where SONiC updates selected keys in the default Linux configuration instead of replacing the full package file.

The SONiC defaults are:

| Setting | Default |
| --- | --- |
| `watchdog-device` | `/dev/watchdog0` |
| `watchdog-timeout` | SONiC default timeout |
| `interval` | `10` seconds |
| `realtime` | `yes` |

At runtime, `watchdog-control.sh` updates the following keys in `/etc/watchdog.conf` based on CONFIG_DB:

- `watchdog-device`: Device selected by identity matching, or `/dev/watchdog0` when no identity is configured.
- `watchdog-timeout`: Configured total timeout, or the SONiC default timeout when no timeout is configured.

SONiC programs pretimeout through the Linux watchdog interface. Pretimeout is not an additional setting in `/etc/watchdog.conf`.

Some important static configs are listed below.

	# Specifies how often (in seconds) the watchdog daemon "kicks" (resets) the watchdog timer
	interval = 10

	# Real time priority mode to ensure watchdog is kicked reliably
	realtime = yes

The linux watchdog daemon can monitor the cpu load, critical processes, file activity, disk space, thermal runaway, RTC drift etc. However this document is only providing SONiC config support for the hardware watchdog.

#### Timeout semantics

SONiC uses the Linux watchdog definitions:

- **Timeout** is the total interval from the last watchdog keepalive until final watchdog expiry.
- **Pretimeout** is the interval between the early watchdog event and final expiry. The early event therefore occurs `timeout - pretimeout` seconds after the last keepalive.
- A pretimeout of zero disables the early event while retaining the final timeout.

Timeout must be positive. Pretimeout must be nonnegative and strictly less than timeout.

The action at the early event is platform defined. A platform may use this event to trigger a crash dump or other debug collection. Pretimeout provides the recovery interval available before final watchdog expiry.

If recovery successfully reboots the system during this interval, final watchdog expiry may never occur. Otherwise, final expiry causes the platform-defined watchdog action, normally a hardware reset.

Platforms without pretimeout support use only the final timeout.

If timeout is not configured, SONiC uses its default timeout.

If pretimeout is not configured, SONiC uses its default pretimeout on a device that supports it. On a device without pretimeout support, the effective default is zero. An explicitly configured nonzero pretimeout is rejected on an unsupported device.

Updating either setting individually preserves the other configured value, or uses its applicable default when absent. SONiC does not automatically resize pretimeout when timeout changes. If the resulting pair is invalid, the update is rejected.

The combined command updates both values together:

	config watchdog timeout <timeout> --pretimeout <pretimeout>

#### Interaction with watchdogutil

SONiC reboot and shutdown code paths may use `watchdogutil` to arm the hardware watchdog. Platform implementations should preserve these operations whether steady state watchdog protection is enabled or disabled.

The platform implementation should determine whether the Linux watchdog daemon is active and managing the same watchdog device, accounting for different device paths that refer to the same underlying device.

When the daemon manages the same device, the platform implementation should:

- Treat an arm request as a successful no-op and return the currently programmed watchdog timeout.
- Treat a disarm request as a successful no-op, leaving the watchdog and its daemon running.
- Allow status queries without acquiring device ownership, interrupting keepalives, or modifying watchdog configuration.

Operators should use `config watchdog disable` to disable steady state watchdog protection. A successful `watchdogutil disarm` request should not override an active Linux watchdog daemon managing the same device.

When the daemon is inactive or manages a different device, the platform implementation should retain its existing arm and disarm behavior.

#### Serviceability & Debugability

Watchdog triggered reboots will recover the system in case of a fault, however there is a side effect that there might be no clear indication on the reason for the failure.

The behavior on watchdog expiry is platform defined. The normal action on watchdog expiry is a reboot of the system. A platform may optionally collect kernel dump, logs, or other debug information before rebooting the router if the platform hardware and software support such a mechanism. Platforms should also support providing a reboot reason for watchdog triggered reboots.


#### Platform Requirements

In order to safely use the Linux watchdog feature on a platform, the following should be considered. This can be used as a reference for enabling this feature by default on a platform as well.

- Verify the correct Linux watchdog identity under `/sys/class/watchdog/watchdog*/identity`.
- Configure the watchdog identity with `config watchdog identity <name>` if the default `/dev/watchdog0` is not the desired device.
- Configure timeout and pretimeout if the SONiC defaults are not appropriate. Use `config watchdog timeout <timeout> --pretimeout <pretimeout>` to update both values together.
- Verify that the selected watchdog device supports nonzero pretimeout before configuring it. Choose a pretimeout that provides sufficient time for any supported crash dump or debug collection.
- Ensure the platform watchdog driver follows Linux timeout and pretimeout semantics and reports the remaining time until final watchdog expiry.
- Ensure existing platform reboot or shutdown code paths using `watchdogutil` continue to work when SONiC watchdog is enabled.
- Enable kernel dump or other debug collection on watchdog expiry if supported by the platform.
- Ensure reboot cause is correctly updated on watchdog triggered reboot.

#### Summary of Changes

Following repos have code changes

	sonic-buildimage
	   - Install watchdog Debian package in the host image
	   - Merge SONiC watchdog defaults into /etc/watchdog.conf
	   - Disable package-provided watchdog.service by default
	   - Update watchdog-control.service ordering and oneshot behavior
	   - Update watchdog-control.sh to read CONFIG_DB and control watchdog.service
	   - Program timeout and pretimeout independently, with capability and configuration validation
	sonic-utilities
	   - Add config watchdog CLI
	   - Support individual and combined timeout and pretimeout updates
	   - Add CLI tests for enable, disable, identity, timeout, pretimeout, and invalid configuration rejection
	platform
	   - Preserve existing watchdogutil arm behavior for reboot and shutdown paths


### Configuration and management

Configuration for enabling the watchdog is covered by SONiC CLI and CONFIG_DB. The Linux watchdog daemon still consumes `/etc/watchdog.conf`, and SONiC owns the runtime values for the selected device, timeout, and pretimeout.


#### CLI/YANG model Enhancements

The initial CLI support is under the SONiC `config watchdog` command:

	config watchdog enable
	config watchdog disable
	config watchdog identity <name>
	config watchdog timeout <timeout> [--pretimeout <pretimeout>]
	config watchdog pretimeout <pretimeout>

The existing `watchdogutil` command is still useful in checking watchdog state and performing manual arm/disarm triggers.

#### Config DB Enhancements

Watchdog configuration is stored in CONFIG_DB under the `WATCHDOG` table:

The following example shows an enabled configuration on a device that supports pretimeout. Timeout and pretimeout values are specified in seconds and must satisfy the constraints in [Timeout semantics](#timeout-semantics).

	"WATCHDOG": {
	    "config": {
	        "enabled": "true",
	        "identity": "board",
	        "timeout": "600",
	        "pretimeout": "300"
	    }
	}

Fields:

- `enabled`: `true` enables the Linux watchdog service. `false` or missing disables it.
- `identity`: Optional identity string matched against `/sys/class/watchdog/watchdog*/identity`.
- `timeout`: Optional positive integer total timeout in seconds. A missing value uses the SONiC default timeout.
- `pretimeout`: Optional nonnegative integer interval between the early event and final expiry, in seconds. A missing value uses the SONiC default pretimeout on supported devices and zero on unsupported devices. Zero disables the early event. Nonzero values require device support, and pretimeout must be less than timeout.

The CLI validates the proposed configuration before writing this table and runs `watchdog-control.sh` immediately after the update. When enabled, the control script programs the device timeout and pretimeout, writes `watchdog-device` and `watchdog-timeout` into `/etc/watchdog.conf`, updates `/etc/default/watchdog` to run the watchdog daemon with that config file, and restarts `watchdog.service`.


### Warmboot and Fastboot Design Impact

Linux watchdog runs at host level, so there is no impact to warm boot expected.

In case of fast reboot, a new kernel instance is started (Kexec), skipping the CPU reset and Bios init, so that the system comes up quickly. There are other aspects of the fast reboot, however from the watchdog design perspective, the key requirement is that the watchdog should not interrupt the fast boot process. The system watchdog timer should be set to a time that is big enough for the new kexec kernel to boot and restart the watchdog daemon.

This could be done by a platform reboot plugin so that there is no impact to fast reboot. It is advised for a platform to make sure the watchdog timer is extended in the fast reboot plugin before the system restarts so that the system stays up.

### Restrictions/Limitations

The watchdog expiry behavior is platform defined. SONiC configures and starts the Linux watchdog service, but the final hardware action and any pre-reboot debug collection depend on platform support.

### Testing Requirements/Design

SONiC management test cases are already existing which verify watchdog functionality. Small modifications may be needed there and certain new test cases will be added related to the configuration methology added in this document.

	- Test watchdog reset when keepalives cease without disarming the watchdog.
	- Test reboot reason as watchdog for watchdog triggered reboot
	- Test kernel core file collection or other debug collection as part of watchdog reset if the platform supports it.
	- Test config watchdog enable starts watchdog.service.
	- Test config watchdog disable stops and disables watchdog.service.
	- Test config watchdog identity correctly selects the watchdog device by matching /sys/class/watchdog/watchdog*/identity.
	- Test timeout and pretimeout defaults, configuration updates, and expiry behavior follow the documented semantics on supported and unsupported devices.
	- Test invalid or unsupported timeout and pretimeout settings are rejected without changing CONFIG_DB, device timer settings, or the running watchdog service.
	- Test watchdogutil arm/disarm/status works as expected when SONiC watchdog is enabled.


### Open/Action items - if any

