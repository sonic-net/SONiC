# SONiC Kernel Update Proposal

## Table of Contents
  - [Revision history](#revision-history)
  - [Overview](#overview)
  - [Update Plan](#update-plan)
    - [Patches](#patches)
    - [Process](#process)
    - [Testing](#testing)
  - [Maintainers/Point-of-Contact](#maintainers)

## Revision history

| Rev        | Date       | Authors                           | Change Description         |
|------------|------------|-----------------------------------|----------------------------|
| 0.1        | 01/26/2026 | Saikrishna Arcot                  | Initial version            |
| 0.2        | 06/30/2026 | Saikrishna Arcot                  | Expand process and testing |

## Overview

This document is being created to describe a cadence for regular, predictable
kernel updates for the master branch as well as a few recent release branches.
This is so that we can regularly bring in bug fixes and security fixes. Only
minor kernel upgrades (where the z in x.y.z is changed) will be done.

## Update Plan

For each branch in scope (described later), kernel updates will be done twice a
year. The new target kernel version will be decided around the end of December and
end of June, and the update to that kernel version will be completed by the end of
April and the end of October. This includes all necessary platform-specific
updates for that kernel version (kernel patches, SDKs, etc.). The
platforms/ASICs considered here are those that are checked by the PR checker.
In the years that we are doing a base image upgrade to a newer version of
Debian, the June-October upgrade will be skipped on all branches, so as to be
able to focus on the new kernel that will be coming in in that new Debian
version.

Branches that are in scope include the master branch and the two most recent
release branches. For example, for the upgrade that would happen in
January-March 2026, the branches included will consist of the master branch,
202511, and 202505. If there is a request to do so, and there is willingness to
do so, additional branches could be considered.

### Patches

At the time of writing, there are [115
patches](https://github.com/sonic-net/sonic-linux-kernel/tree/master/patches-sonic)
in the master branch of sonic-linux-kernel that we apply. Many of these patches
come from platform vendors and are related to making hardware work. Many of
these are backports from newer versions of Linux, but some are not present in
mainline Linux. This means that when doing an update to a newer version of
Linux (minor or major update), some of these patches will need to be updated to
resolve patch conflicts. Depending on patch/conflict complexity, this might
require support from the platform vendor.

### Process

A branch will be created for the sonic-linux-kernel and sonic-buildimage repos
in a personal fork, where all changes related to the new kernel version will go
in. There, patches that apply with either no conflicts or with minor conflicts
will get applied (and corrected, if needed, for clean application). Patches
that have been backported will be commented out and removed. Patches that have
major conflicts will be commented out, and will likely require help from the
vendor to update it appropriately. Externally-built kernel modules in
sonic-buildimage will also be updated as necessary for compilation purposes.
Out-of-tree patches that get applied into the sonic-linux-kernel build from
sonic-buildimage will not be tested here; it is the responsibility of the
provider of the patches to update them as necessary.

Once an image is built for all platforms checked by the PR checker, testing
will begin as described in the next section.

### Testing

Tests for the new kernel version will include, at minimum:

1. Booting up on one (or multiple, if available) platforms of each ASIC type.
   All ASIC types covered by the PR checkers must be covered here.
2. Verifying that BGP is up
3. Verifying the transceiver types are detected and transceiver EEPROM is
   readable
4. Verifying that the bootup time and runtime CPU usage (or alternatively, the
   load average) is not significantly different compared to before the upgrade
   on some given hardware
5. Run tests/platform_tests on the device to cover some platform-specific code
   paths
6. Check the syslog for any errors from the kernel

Additional tests (such as stress tests) can be incorporated into this test plan
if there is a specific suggestion to do so.

## Maintainers/Point-of-Contact

The actual kernel upgrade work will be driven by a rotating group of
people/companies. Exact list TDB.
