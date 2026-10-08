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
- Watchdog parameters such as identity, timeout etc can be configured using SONiC CLI.
- Updating identity or timeout restarts the watchdog service if watchdog is enabled.
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
	config watchdog timeout <timeout>

The CLI updates CONFIG_DB and immediately invokes `watchdog-control.sh` so the runtime state follows the configuration change. If the watchdog is already enabled, changing `identity` or `timeout` causes the Linux watchdog service to be reconfigured and restarted.

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

	watchdog-device = /dev/watchdog0
	watchdog-timeout = 30
	interval = 10
	realtime = yes

At runtime, `watchdog-control.sh` updates the following keys in `/etc/watchdog.conf` based on CONFIG_DB:

	# Device selected by identity matching or defaulted to /dev/watchdog0
	watchdog-device = /dev/watchdog0

	# Watchdog timeout configured by CLI or defaulted to 30 seconds
	watchdog-timeout = 30

Some important static configs are listed below.

	# Specifies how often (in seconds) the watchdog daemon "kicks" (resets) the watchdog timer
	interval = 10

	# Real time priority mode to ensure watchdog is kicked reliably
	realtime = yes

The linux watchdog daemon can monitor the cpu load, critical processes, file activity, disk space, thermal runaway, RTC drift etc. However this document is only providing SONiC config support for the hardware watchdog.

#### Interaction with watchdogutil

SONiC platform reboot and shutdown code paths may already use `watchdogutil` to arm the watchdog before rebooting the system. This behavior should remain unchanged whether steady state watchdog is configured or not.

If the Linux watchdog service is not enabled, `watchdogutil arm` should continue to arm the watchdog as expected. If the Linux watchdog service is already enabled and managing the same watchdog device, `watchdogutil arm` should be treated as a no-op and return success. This avoids competing ownership of the watchdog device while preserving existing reboot code paths.

#### Serviceability & Debugability

Watchdog triggered reboots will recover the system in case of a fault, however there is a side effect that there might be no clear indication on the reason for the failure.

The behavior on watchdog expiry is platform defined. The normal action on watchdog expiry is a reboot of the system. A platform may optionally collect kernel dump, logs, or other debug information before rebooting the router if the platform hardware and software support such a mechanism. Platforms should also support providing a reboot reason for watchdog triggered reboots.


#### Platform Requirements

In order to safely use the Linux watchdog feature on a platform, the following should be considered. This can be used as a reference for enabling this feature by default on a platform as well.

- Verify the correct Linux watchdog identity under `/sys/class/watchdog/watchdog*/identity`.
- Configure the watchdog identity with `config watchdog identity <name>` if the default `/dev/watchdog0` is not the desired device.
- Configure the watchdog timeout with `config watchdog timeout <timeout>` if the default `30` second timeout is not appropriate.
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
	sonic-utilities
	   - Add config watchdog CLI
	   - Add CLI tests for enable, disable, identity, and timeout
	platform
	   - Preserve existing watchdogutil arm behavior for reboot and shutdown paths


### Configuration and management

Configuration for enabling the watchdog is covered by SONiC CLI and CONFIG_DB. The Linux watchdog daemon still consumes `/etc/watchdog.conf`, but SONiC owns the runtime values for the selected device and timeout.


#### CLI/YANG model Enhancements

The initial CLI support is under the SONiC `config watchdog` command:

	config watchdog enable
	config watchdog disable
	config watchdog identity <name>
	config watchdog timeout <timeout>

The existing `watchdogutil` command is still useful in checking watchdog state and performing manual arm/disarm triggers.

#### Config DB Enhancements

Watchdog configuration is stored in CONFIG_DB under the `WATCHDOG` table:

	"WATCHDOG": {
	    "config": {
	        "enabled": "true",
	        "identity": "board",
	        "timeout": "30"
	    }
	}

Fields:

- `enabled`: `true` enables the Linux watchdog service. `false` or missing disables it.
- `identity`: Optional identity string matched against `/sys/class/watchdog/watchdog*/identity`.
- `timeout`: Optional positive integer timeout in seconds. Missing value defaults to `30`.

The CLI writes this table and runs `watchdog-control.sh` immediately. The control script writes `watchdog-device` and `watchdog-timeout` into `/etc/watchdog.conf`, updates `/etc/default/watchdog` to run the watchdog daemon with that config file, and restarts `watchdog.service` when enabled.


### Warmboot and Fastboot Design Impact

Linux watchdog runs at host level, so there is no impact to warm boot expected.

In case of fast reboot, a new kernel instance is started (Kexec), skipping the CPU reset and Bios init, so that the system comes up quickly. There are other aspects of the fast reboot, however from the watchdog design perspective, the key requirement is that the watchdog should not interrupt the fast boot process. The system watchdog timer should be set to a time that is big enough for the new kexec kernel to boot and restart the watchdog daemon.

This could be done by a platform reboot plugin so that there is no impact to fast reboot. It is advised for a platform to make sure the watchdog timer is extended in the fast reboot plugin before the system restarts so that the system stays up.

### Restrictions/Limitations

The watchdog expiry behavior is platform defined. SONiC configures and starts the Linux watchdog service, but the final hardware action and any pre-reboot debug collection depend on platform support.

### Testing Requirements/Design

SONiC management test cases are already existing which verify watchdog functionality. Small modifications may be needed there and certain new test cases will be added related to the configuration methology added in this document.

	- Test watchdog reset if watchdog daemon is stopped.
	- Test reboot reason as watchdog for watchdog triggered reboot
	- Test kernel core file collection or other debug collection as part of watchdog reset if the platform supports it.
	- Test config watchdog enable starts watchdog.service.
	- Test config watchdog disable stops and disables watchdog.service.
	- Test config watchdog identity correctly selects the watchdog device by matching /sys/class/watchdog/watchdog*/identity.
	- Test config watchdog timeout updates watchdog-timeout in /etc/watchdog.conf and restarts watchdog.service when enabled.
	- Test watchdogutil arm/disarm/status works as expected when SONiC watchdog is enabled.


### Open/Action items - if any

