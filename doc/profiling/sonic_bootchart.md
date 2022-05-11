<!-- omit in toc -->
# SONiC Boot Chart #

<!-- omit in toc -->
## Table of Content

- Revision
- Scope
- Definitions/Abbreviations
- Overview
- Requirements
- Architecture Design
- High-Level Design
- SAI API
- Configuration and management
	- Manifest (if the feature is an Application Extension)
	- CLI/YANG model Enhancements
	- Config DB Enhancements
- Warmboot and Fastboot Design Impact
- Restrictions/Limitations
- Testing Requirements/Design
	- Unit Test cases
	- System Test cases
- Open/Action items - if any

### Revision

### Scope

SONiC OS is highly modular and composible system, where every new feature is often implemented as a new script, utility, daemon or docker container. A lot of these components start at SONiC boot togather with respect to their dependencies requirements. Majority of start scripts use short-living small utilities written in python, bash or other scripting languages, invoke Jinja2 template generation. This leads to potential boot time performance degradation that we need a tool to detect and analyze.

### Definitions/Abbreviations

N/A

### Overview

This document describes an integration of one of systemd tools called *systemd-bootchart*. This tool is a sampling based system profiler that is used to analyze boot up performance but not limited to and can be used to collect samples after the system is booted. The output produced by systemd-bootchart is an SVG image that looks like this:

<p align=center>
<img src="img/bootchart.svg" alt="Figure 1. Bootchart example">
</p>

### Requirements

- Integrate systemd-bootchart with SONiC OS
- SONiC CLI tool to interact with systemd-bootchart
- Support commands to enable/disable systemd-bootchart
- Configure the amount of samples to collect and frequency
- Displaying systemd-bootchart configuration and generated SVG plots

### Architecture Design

N/A

### High-Level Design

SONiC build system includes a new build-time flag to INCLUDE_BOOTCHART. When this flag is set a *systemd-bootchart* debian package is installed in SONiC host from upstream debian repositories (Installed size 128 KB).
SONiC provides a default configuration for bootchart located at /etc/systemd/bootchart.conf:

```ini
[Bootchart]
Samples=4500
Frequency=25
```

This configuration means that samples are collected for 3 minutes of uptime with a frequency of 25 samples per second.

SONiC utilities is extendeded with a new script under *scripts/* to include a new utility *sonic-bootchart*.

### SAI API

N/A

### Configuration and management

*sonic-bootchart* is a stand alone utility, like *sonic-kdump-config*, *sonic-installer*, etc.

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

Once bootchart is enabled a systemd-bootchart.service is enabled in systemd which starts a daemon early at boot that collects samples.
This setting is permanent, meaning, after it is enabled, bootchart will always run at boot until disabled, *config save*, *config reload* do not affect this setting.


Update configuration:

```
admin@sonic:~$ sudo sonic-bootchart config --samples 500 --frequency 10
admin@sonic:~$ sudo sonic-bootchart show
Status      Operational Status    Samples    Frequency    Time (sec)  Output
--------  --------------------  ---------  -----------  ------------  ------------------------------------
enabled              in-active        500           10            50  /run/log/bootchart-20220504-1325.svg
```

*systemd-bootchart* saves the plots to a temporary directory /run/log that is flushed after reboot.


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

### Open/Action items - if any

N/A
