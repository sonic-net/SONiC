<!-- omit in toc -->
# SONiC Boot Chart #

<!-- omit in toc -->
## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
	- [Manifest (if the feature is an Application Extension)](#manifest-if-the-feature-is-an-application-extension)
	- [CLI/YANG model Enhancements](#cliyang-model-enhancements)
	- [Config DB Enhancements](#config-db-enhancements)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
	- [Unit Test cases](#unit-test-cases)
	- [System Test cases](#system-test-cases)
- [Open/Action items](#openaction-items)

### Revision

### Scope

SONiC OS is highly modular and composible system, where every new feature is
often implemented as a new script, utility, daemon or docker container. A lot of
these components start at SONiC boot togather with respect to their dependencies
requirements. Majority of start scripts use short-living small utilities written
in python, bash or other scripting languages, invoke Jinja2 template generation.
This leads to potential boot time performance degradation that we need a tool to
detect and analyze.

### Definitions/Abbreviations

N/A

### Overview

This document describes an integration of one of systemd tools called
*systemd-bootchart*. This tool is a sampling based system profiler that is used
to analyze boot up performance but not limited to and can be used to collect
samples after the system is booted. The output produced by systemd-bootchart is
an SVG image that looks like this:

<p align=center>
<img src="img/bootchart.svg" alt="Figure 1. Bootchart example">
</p>

### Requirements

- Integrate systemd-bootchart with SONiC OS
- systemd-bootchart is by default installed in the system
- systemd-bootchart is by default disabled and user need to enable it via CLI
- SONiC CLI tool to interact with systemd-bootchart
- Support commands to enable/disable systemd-bootchart
- Configure the amount of samples to collect and frequency
- Displaying systemd-bootchart configuration and generated SVG plots

### Architecture Design

N/A

### High-Level Design

SONiC build system includes a new build-time flag to INCLUDE_BOOTCHART (y/n).
When this flag is set a *systemd-bootchart* debian package is installed in SONiC
host from upstream debian repositories (Installed size 128 KB).

Example INCLUDE_BOOTCHART flag usage:

Include bootchart:
```
make INCLUDE_BOOTCHART=y target/sonic-mellanox.bin
```

Do not include bootchart:
```
make INCLUDE_BOOTCHART=n target/sonic-mellanox.bin
```

SONiC provides a default configuration for bootchart located at
/etc/systemd/bootchart.conf:

```ini
[Bootchart]
Samples=4500
Frequency=25
```

This configuration means that samples are collected for 3 minutes of uptime with
a frequency of 25 samples per second.

SONiC utilities is extendeded with a new script under *scripts/* to include a
new utility *sonic-bootchart*.

Also a flag added to the build incdicating default status:

```
ENABLE_BOOTCHART=y
```

### SAI API

N/A

### Configuration and management

*sonic-bootchart* is a standalone utility, like *sonic-kdump-config*,
**sonic-installer*, etc.

Command line interface:

```
admin@sonic:~$ sudo sonic-bootchart
Usage: sonic-bootchart [OPTIONS] COMMAND [ARGS]...

  Main CLI group

Options:
  --help  Show this message and exit.

Commands:
  config   Configure bootchart NOTE: This command requires elevated (root)...
  disable  Disable bootchart NOTE: This command requires elevated (root)...
  enable   Enable bootchart NOTE: This command requires elevated (root)...
  show     Display bootchart configuration
```

Enable/Disable bootchart:

```
admin@sonic:~$ sudo sonic-bootchart enable
Running command: systemctl enable systemd-bootchart
admin@sonic:~$ sudo sonic-bootchart disable
Running command: systemctl disable systemd-bootchart
```

In case image is built without bootchart included (INCLUDE_BOOTCHART=n)
sonic-bootchart will print an error:

```
admin@sonic:~$ sudo sonic-bootchart enable
systemd-bootchart is not installed
```

Once bootchart is enabled a systemd-bootchart.service is enabled in systemd
which starts a daemon early at boot that collects samples. This setting is
permanent, meaning, after it is enabled, bootchart will always run at boot until
disabled, *config save*, *config reload* do not affect this setting.


Update configuration example:

```
admin@sonic:~$ sudo sonic-bootchart config --time-span 50 --frequency 10
```

This command will update /etc/systemd/bootchart.conf. The next time bootchart
will run (at system start after reboot) it will take the new values.
*systemd-bootchart* saves the plots to a temporary directory /run/log that is
*flushed after reboot.

Displaying configuration, operational status and output SVG plots:

```
admin@sonic:~$ sudo sonic-bootchart show
Status      Operational Status   Frequency    Time Span (sec)  Output
--------  --------------------  -----------  ----------------  ------------------------------------
enabled              in-active          10                 50  /run/log/bootchart-20220504-1325.svg
```

Fields description:

| Field              | Comment                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Status             | Output of "systemctl is-enabled systemd-bootchart". Shows whether this service is configured to start at boot (enabled/disabled)      |
| Operational Status | Output of "systemctl is-action systemd-bootchart". Shows whether this service is currently collecting samples (active/in-active)      |
| Frequency          | How frequent to collect samples per second                                                                                            |
| Time Span          | The time how long after boot samples will be collected. Based on it the samples count is calculated as Frequency x Time Span          |
| Output             | If systemd-bootchart finished collecting samples (in-active) this column will display resulting plots, otherwise this column is empty |


Usage example:

- First make sure you have SONiC image built with INCLUDE_BOOTCHART=y
- Enable bootchart: "sudo sonic-bootchart enable"
- Perform any kind of reboot: "sudo reboot" or "sudo warm-reboot" or "sudo
fast-reboot"
 - Wait till system reboots and the plot is generated by quering
"sudo sonic-bootchart show"

#### Manifest (if the feature is an Application Extension)

N/A

#### CLI/YANG model Enhancements

N/A

#### Config DB Enhancements

N/A

### Warmboot and Fastboot Design Impact
N/A

### Restrictions/Limitations

### Testing Requirements/Design
N/A

#### Unit Test cases

Cover CLI with UT for:
  - enabling bootchart
  - disabling bootchart
  - config/show commands

#### System Test cases

N/A

### Open/Action items

- SONiC installer bootchart config migration. Being able to run this tool for reboot with SONiC-2-SONiC upgrade
- Requested a possibility to run the tool in runtime after boot
