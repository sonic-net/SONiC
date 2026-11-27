# Xcvrd Performance Enhancements

## Table of Content

- [Xcvrd Performance Enhancements](#xcvrd-performance-enhancements)
  - [Table of Content](#table-of-content)
    - [1. Revision](#1-revision)
    - [2. Scope](#2-scope)
    - [3. Definitions/Abbreviations](#3-definitionsabbreviations)
    - [4. Overview](#4-overview)
    - [5. Requirements](#5-requirements)
    - [6. Architecture Design](#6-architecture-design)
    - [7. High-Level Design](#7-high-level-design)
      - [7.1 sonic-platform-common changes](#71-sonic-platform-common-changes)
        - [7.1.1 SfpBase.get\_io\_group\_name](#711-sfpbaseget_io_group_name)
        - [7.1.2 SfpBase.set\_bus\_speed](#712-sfpbaseset_bus_speed)
      - [7.2 sonic-platform-daemons changes](#72-sonic-platform-daemons-changes)
        - [7.2.1 sonic-xcvrd thread infrastructure](#721-sonic-xcvrd-thread-infrastructure)
        - [7.2.2 sonic-xcvrd thread creation](#722-sonic-xcvrd-thread-creation)
        - [7.2.3 sonic-xcvrd DomInfoUpdate thread changes](#723-sonic-xcvrd-dominfoupdate-thread-changes)
        - [7.2.4 sonic-xcvrd hidden sleeps](#724-sonic-xcvrd-hidden-sleeps)
        - [7.2.5 sonic-xcvrd unnecessary sleeps](#725-sonic-xcvrd-unnecessary-sleeps)
        - [7.2.6 sonic-xcvrd configure MCI bus speed](#726-sonic-xcvrd-configure-mci-bus-speed)
      - [7.3 sonic-linux-kernel](#73-sonic-linux-kernel)
        - [7.3.1 optoe module improvements via optoe-auto](#731-optoe-module-improvements-via-optoe-auto)
        - [7.3.2 optoe-auto module identification](#732-optoe-auto-module-identification)
        - [7.3.3 optoe-auto module removal/insertion](#733-optoe-auto-module-removalinsertion)
    - [8. SAI API](#8-sai-api)
    - [9. Configuration and management](#9-configuration-and-management)
    - [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
    - [11. Memory Consumption](#11-memory-consumption)
    - [12. Restrictions/Limitations](#12-restrictionslimitations)
    - [13. Testing Requirements/Design](#13-testing-requirementsdesign)
    - [14. Open/Action items - if any](#14-openaction-items---if-any)

### 1. Revision

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 2026-01-20 | Samuel Angebault | Initial Draft      |

### 2. Scope

This document describes the following enhancements to SONiC
- Reducing transceiver telemetry polling interval
- Refactor of xcvrd DOM threading model
- Leverage potential hardware capabilities
- Proposing further enhancements in the transceiver management area

### 3. Definitions/Abbreviations

| Term | Definition |
| ---- | ---------- |
| D State | uninterruptible sleep, waiting for IO |
| DOM | Digital Optical Monitoring |
| CMIS | Common Management Interface Specification |
| MCI | Management Communication Interface |
| MIS | Management Interface Specification |
| XCVR | Transceiver |

### 4. Overview

At the time of proposal the xcvrd process that runs in the pmon container
already has a few threads. Each thread handles a different responsibility but
they all operate on all transceivers.

Transceivers are mostly managed using the I2C protocol.
It is a rather slow protocol which runs at 100kHz by default by SMBus
specification.
Though CMIS introduces a 400kHz minimum supported speed and up to 1MHz for some
modules, IO operations on transceivers remain slow in the context of modern
computing.
Another constraint is that I2C devices have to be addressed individually.

Currently the xcvrd process spends a lot of time in D state which means that it
is waiting for the IO to complete before continuing its operations.
Improving xcvrd performance relies a lot on reducing the IO footprint within
each polling interval.

This can be achieved by working on these aspects:
- reducing overhead between queries to xcvrs to maximize D state
- spreading the load on multiple threads when possible

Hardware vendors can take different approaches when it comes to connecting
xcvrs to the main CPU.
They all have pros and cons but when it comes to performance the fastest it can
get is by having one i2c controller per module.
In that world all modules can be queried in parallel.
Spreading a few xcvrs per i2c controller is a far more common approach for
various technical reasons.
In that model it becomes interesting to create one thread per controller.

Because vendors ultimately know their hardware the best, this configuration
option will be available at the platform API level.

The existing threads in xcvrd are as follow:
 - SfpStateUpdate to handle insertion / removal events
 - SffManager to handle SFPs and QSFP adhering to SFF-8472 and SFF-8636
   respectively
 - CmisManager to handle newer optics adhering to the CMIS
 - DomInfoUpdate to poll DOM information from modules
 - DomThermalInfoUpdate to poll temperature information from modules

Additionally this HLD will focus on a few additional inefficiencies that the
xcvrd has.

### 5. Requirements

 - DOM polling should be distributable across multiple threads, one per IO group
 - IO groups are defined by the platform via a new SfpBase API, default is a
   single group covering all ports
 - xcvrd should configure the MCI bus speed based on module capability after insertion
 - Hidden select sleeps in the DOM polling loop should be eliminated
 - A new optoe-auto kernel entry point must reduce per-operation IO by maintaining
   module state.

### 6. Architecture Design

This feature will only affect the internal architecture of the `sonic-xcvrd`
daemon. Beside a faster update frequency of transceiver telemetry data in
STATE_DB there should not be any other visible changes to other processes.

### 7. High-Level Design

This feature will introduce changes in the following packages:
 - sonic-platform-common to add additional platform APIs
 - sonic-platform-daemons to refactor the xcvrd code

Most of the work will happen in the xcvrd daemon and will be mostly localized
in the area of DOM polling initially.
Refactoring other threads will require additional thoughts but should be
compatible with the design proposed here.

#### 7.1 sonic-platform-common changes

##### 7.1.1 SfpBase.get_io_group_name

The feature introduces a new API to the SfpBase class so that each module can
specify in which groups it belongs. By default only one group will be created
which means the behavior would be unchanged.

```python
class SfpBase:
   ...
   def get_io_group_name(self):
      '''Returns the group name from which the sfp belongs
      This is used to optimize IO operations by grouping sfps and running
      groups in parallel.

      Returns an arbitrary string. Ideally under 10 chars to be fully
      displayed in the thread name.
      '''
      return 'all'
   ...
```

##### 7.1.2 SfpBase.set_bus_speed

As part of the performance improvement effort another platform API is
introduced which aims at configuring the management interface bus speed to the
module.

```python
class SfpBase:
   ...
   def set_bus_speed(self, speed):
      '''Sets the management interface bus speed
      The standard speeds for I2C modules are 100000, 400000, 1000000
      This method should be called after checking which speed is supported by the module.

      Returns a boolean on whether the operation was successful or not
      '''
      raise NotImplementedError
   ...
```

The name of the method is intentionally free of `i2c` or `smbus` references since
it's possible that future xcvr models will use a different management interface.

The `xcvrd` process is expected to call this new platform API method once it has
identified that the module supports the given speed.
This decision will be made after reading the `MciMaxSpeed` register at
00h:02 bits [3:2].
Upon removal `xcvrd` should reset the bus speed to the original speed to
ensure that it can handle future xcvrs inserted.

Even if some modules can support up to 1MHz not all platforms are expected to
have the necessary SI to communicate reliably at those speeds.
It is therefore expected that the `set_bus_speed` implementation of the vendor
should fall back to the fastest safe speed below the desired one.

An alternative would be to provide another platform API method such as
`SfpBase.get_supported_bus_speeds(self)` which reports supported speed per module
and leaves the speed decision to `xcvrd`.

However it is simpler for the platform api to decide whether to honor the
desired bus speed setting rather than having `xcvrd` find the appropriate bus
speed and then have to implement a check in the platform API layer anyways.

Instead the `set_bus_speed` can return `True` when it could set the desired
bus speed properly and `False` when it couldn't.
Thus prompting the `xcvrd` to try a lower speed until the platform API returns True.

#### 7.2 sonic-platform-daemons changes

The bulk of the changes will happen inside `sonic-xcvrd` of the
`sonic-platform-daemons` package.

##### 7.2.1 sonic-xcvrd thread infrastructure

For debuggability purposes threads will be given names.
They are currently unnamed and it is therefore difficult to understand which
one does what.
The `prctl` syscall via `PR_SET_NAME` allows setting a 15 char name.

By hooking into the base threading class we can use either the class name or
the thread name given in the xcvrd code.

The expected threads will be:
 - `SfpStateUpdate`
 - `SffManager`
 - `CmisManager`
 - `DomThermalInfoUpdate`
 - `Dom/{group}` <- new threading model for dom (`Dom/all` by default)

The DomThermalInfoUpdate thread which is an opt-in thread based on a setting in
`pmon_daemon_control.json` will not be touched. It has a dedicated polling
interval which fits the platform cooling algorithm. Until there are guarantees
in the newer Dom threads that the temperature information can be polled as
often as needed we should not remove this thread.

##### 7.2.2 sonic-xcvrd thread creation

A new `xcvrd` option will be introduced to make this feature an opt-in.
This knob can be set on a per platform basis via the `pmon_daemon_control.json`
configuration file.
Proposed `--dom-use-io-threads` as a `boolean`.

Even if it requires a new platform API to be implemented, we want to ensure
that we can revert to a single thread as a mitigation that can be enabled in
production.

When starting, the xcvrd process will iterate over all the `SfpBase` objects of
the platform library and construct a mapping keyed by the output of the new
`SfpBase.get_io_group_name` platform API.

One thread per mapping entry will be created which will manage the
provided `SfpBase` objects.

Note that xcvrd is unaware of the underlying physical topology of the switch
and therefore accepts any arbitrary mapping of xcvr to io group.

##### 7.2.3 sonic-xcvrd DomInfoUpdate thread changes

Initially this thread will continue to perform the same tasks as before.
It will however only work on a smaller subset of sfp objects.

The intended goal is to put the threading infrastructure in place without
changing the core logic extensively.
It should already yield some pretty significant performance improvements.

Once put in place it will be easier to benchmark and iterate on further
improvements.

##### 7.2.4 sonic-xcvrd hidden sleeps

Currently the DOM polling logic of the xcvrd daemon has poor performance due to
hidden sleeps and unnecessary polling interval.

Some calls in the DOM polling loop are checking for events:
 - `port_event_helper.handle_port_config_change` at the loop level
 - `port_change_observer.handle_port_update_event` at the module level

Under the hood, these calls are using `select` with a fixed timeout of 1s.
The expectation is that the call returns early if an event happens and timeout
if nothing happened.
The good path therefore expects that no events happen, which therefore
translates to a penalty of 1s per module and an additional 1s per loop.
On a 64 port system, we're talking about 65s of sleep.

The `select` syscall can take a parameter of `0` to not block which should be
the desired behavior.

The polling loop currently relies on this sleeps to avoid busy looping but it
is simply addressed by adding a sleep at the loop level for the amount of time
remaining before the next expected interval.

##### 7.2.5 sonic-xcvrd unnecessary sleeps

Additionally the DOM polling thread will not query the DOM for an additional 60
seconds after a polling loop is done.

This carries 2 problems:
 - The interval between 2 polling loops is currently computed as the desired
   interval + the time spent in the loop to poll the DOM information leading to
   inconsistent polling interval and much longer than expected
 - End users might want a tighter polling loop at the expense of CPU by
   removing that sleep altogether

Combined with the previous optimization it becomes possible to configure constant
polling with no sleep time.

The poll interval will initially be configurable per platform via the
`pmon_daemon_control.json` configuration file.
However because end users might want faster telemetry, this might require a
CONFIG_DB attribute but is out of scope for this HLD.

##### 7.2.6 sonic-xcvrd configure MCI bus speed

Setting the MCI bus speed is the responsibility of `xcvrd`.

Once the module is detected as present, we should set the bus speed to the
minimum speed, currently 100kHz. This is done in case the bus was left at a
higher speed which is incompatible with the module inserted.

Then `xcvrd` reads the capability register `MciMaxSpeed` and from there deduces
the supported speed for the module.
Followed by calling the `SfpBase.set_bus_speed` with the right parameter.
If the call returns False, `xcvrd` is expected to retry with a lower speed.

If the `MciMaxSpeed` read from the eeprom translates to a speed of `0`, then
`xcvrd` should ignore that speed setting and raise a warning about unsupported
bus speed. This log would mean that a new revision of the CMIS specification
introduced a new official speed that has not yet been added to `xcvrd`.

This `MciMaxSpeed` xcvr Eeprom field will be defined by following the existing
architecture which includes the following additions

Under `sonic_platform_base/sonic_xcvr/fields/consts.py`
```python
MCI_MAX_SPEED = "MCI Max Speed"
```

Under `sonic_platform_base/sonic_xcvr/api/public/cmis.py`
```python
def get_mci_max_speed(self):
    return self.xcvr_eeprom.read(consts.MCI_MAX_SPEED)
```

Under `sonic_platform_base/sonic_xcvr/codes/public/cmis.py`
```python
MCI_MAX_SPEED = {
    0: 400000,
    1: 1000000,
    2: 0, # reserved by spec
    3: 0, # reserved by spec
}
```

Under `sonic_platform_base/sonic_xcvr/mem_maps/public/cmis.py`
```python
self.MGMT_CHARACTERISTICS = RegGroupField(consts.MGMT_CHAR_FIELD,
    NumberRegField(consts.MGMT_CHAR_MISC_FIELD, self.getaddr(0x0, 2),
        RegBitsField(consts.MCI_MAX_SPEED, bitpos=2, size=2),
        RegBitField(consts.FLAT_MEM_FIELD, 7),
    )
)
```

#### 7.3 sonic-linux-kernel

##### 7.3.1 optoe module improvements via optoe-auto

Implementing a new `optoe-auto` entry point to the `optoe` module.

Multiple inefficiencies have been found in the `optoe` module as it stands.
It is possible to divide the IO time by 4 for single byte operations by making
the driver smarter.

On top of the performance issues, the `optoe` module is unable to properly
handle QSA where a SFP is inserted into a QSFP slot which is addressed by that
change.

Because changing the `optoe` module can cause friction, the goal is to
introduce a new entry point that vendors can opt-in, while keeping the older
`optoe1`, `optoe2` and `optoe3` entry points identical.

As of today an eeprom operation from the user land works as follow:
 - userland read 1 byte from the sysfs eeprom
   - optoe module reads the xcvr capabilities (pageable or not, SFF-8636/cmis)
   - optoe module writes the page based on eeprom offset
   - optoe module reads the byte requested by userland
   - optoe module writes the page back to 0

Things can be made much more efficient if the optoe module was aware of the MIS
the xcvr uses by reading the address 0x00 which implements SFF-8024.
From there, there is no longer a need to read xcvr capabilities more than once
or on re-insertion, which removes one read operation.
Additionally by caching the last page used by the xcvr and not going back to
page 0 it is possible to avoid 2 additional writes.

In the best case we go from 4 IO operations down to 1.
 - perform the requested IO by the user if the page doesn't need to change

In the worst case from 4 IO operations down to 2.
 - change the page to match the offset the user operation needs
 - perform the requested read/write operation

##### 7.3.2 optoe-auto module identification

When loaded using `optoe-auto` at the address `0x50` on a given kernel i2c bus,
the module will enter the same probe method used by other `optoe` entrypoints.
However it will set a new attribute `optoe->autodetect` to `true`.

This `autodetect` attribute is then used across the optoe codebase to
differentiate between the old code path and the new `optoe-auto` ones.

In the `autodetect` mode, the xcvr enters an autodetect phase which will read
the SFF-8024 identification information available at address `0x00`.

This information is used to map the module to a MIS enum value which will
differentiate between SFF-8472, SFF-8636 and CMIS.

Once the differentiation is done, the `dev_class` is set appropriately and the
i2c addresses reserved. While CMIS and SFF-8636 use solely address 0x50, the
SFF-8472 uses both 0x50 and 0x51 (sometimes 0x56 in the case of SFP to BASE-T).
The address reservation is mandatory to avoid userland accessing the device
while a kernel driver already is.

Furthermore, the identification process then reads some xcvr capability such as
whether it is pageable, and where the page select register is.

The xcvr is then set to page 0 and the `optoe->current_page` also set to 0.

##### 7.3.3 optoe-auto module removal/insertion

Within the optoe driver it is not straightforward to know when a module has
been replaced. If done quickly enough the driver will not see any difference.

The driver uses multiple mechanisms to handle insertion/removal events.
 - A TIMEOUT error to the xcvr is assumed to be a xcvr removal event
 - A periodic check of the identification register if it hasn't happened in the
   last 1s (configurable). It ensures that the MIS hasn't changed.
   The IO is negligible compared to the savings made from this enhancement.
 - A new `rescan` sysfs entry that can be manually triggered to force a
   rescan. This could also be used by `xcvrd` to force the rescan when it
   detects an OIR since it knows when this happens

### 8. SAI API

N/A

### 9. Configuration and management

The only configuration necessary falls on the platform vendors.
While everything will work as before without additional configuration, vendors
can implement the new platform apis to extract more performance out of the
xcvrs connected to their devices.

Hardware vendors should implement the new Platform APIs and update the content
of their `pmon_daemon_control.json` to leverage the new features.

There is no expected change from the end users unless we implement a new
configuration knob allowing them to override the default `xcvrd` polling interval.

### 10. Warmboot and Fastboot Design Impact

There is no negative impact anticipated with warm-boot/fast-boot operations.
The xcvrs are expected to remain configured during that time and not
re-initialized on the coming up path.

This refactor is currently not touching the management part of the xcvr.
However some enhancements such as the I2C bus speed setting and optoe driver will
make xcvrd faster to start because it indirectly makes all the calls faster.

### 11. Memory Consumption

Memory consumption will increase almost linearly with the number of threads started by
xcvrd. Each thread introduces some overhead for its context and stack.
Additionally, though some collections will be spread evenly across all threads, some
won't.

### 12. Restrictions/Limitations

Performance improvement numbers will vary based on hardware capabilities.
Having one I2C controller per module has obviously more potential than all the
modules under the same I2C controller.

### 13. Testing Requirements/Design

The testing will be updated alongside the code changes.

### 14. Open/Action items - if any

Other shortcomings of `xcvrd` and `sonic_xcvr` in terms of performance have been
identified and will receive follow up improvements.
