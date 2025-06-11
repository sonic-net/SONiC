# Reboot support BlockingMode in SONiC

## Table of Content

- [Overview](#overview)
- [Background](#background)
- [Function Design](#function-design)
- [Test Plan](#test-plan)

## Revision

| Revision | Date       | Author     | Change Description |
| -------- | ---------- | ---------- | ------------------ |
| 1.0      | June 12 2025 | Litao Yu | Initial proposal   |

## Overview

We are trying to introduce blocking mode for reboot script, which currently is in non-blocking mode. This will make automation system easier to identify whether the reboot operation is success.

## Background

Currently the reboot script uses linux command `/sbin/reboot`. And this command will not block the script. As the result, SONIC CLI might give different results depends on the linux reboot speed. If the reboot speed is slow, then the SONIC reboot command will exit and give another user prompt. This will confuse the automation system that whether the reboot command succeeds.
So we want to introduce blocking mode to unify the behavior of SONIC reboot command. And to make sure no break changes happen, we will keep the default behavior.

## Function Design

2 types of input is supported to give automation system more flexibility.

### Option 1: Paramter

The reboot command line will be as follow:
```
reboot [--blocking-mode]
```

### Option 2: Config File
The reboot command will check the config file in `/etc/sonic/reboot_cfg`. If the file contains the follow config, SONIC reboot will default use blocking mode.
```
blocking-mode=blocking
```

### Option 3: Environment Variables
The reboot command will check the environment var `SONIC_REBOOT_BLOCKING_MODE`. If the var's value is `blocking`, SONIC reboot will default use blocking mode.

### Functional Test

Functional test plan will be published in [sonic-net/sonic-mgmt](https://github.com/sonic-net/sonic-mgmt).
