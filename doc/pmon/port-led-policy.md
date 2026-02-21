# Port LED Policy #

## Table of Content

### 1. Revision
 | Rev |     Date    |       Author                  | Change Description     |
 |:---:|:-----------:|:-----------------------------:|------------------------|
 | 0.1 | 02/17/2026  |  Justin Oliver, Aaron Payment | Initial version        |

### 2. Scope
This document describes an updated LED policy for front panel port LEDs.

### 3. Definitions/Abbreviations

| Term | Definition |
|:-----|:-----------|
| SFP | Small Form-factor Pluggable |
| QSFP | Quad Small Form-factor Pluggable |
| OSFP | Octal Small Form-factor Pluggable |
| Front Panel Port Cage | A slot where a transceiver can be inserted |
| LEDD | LED Daemon responsible for managing port LED states |

### 4. Overview

SONiC's current LED policy implementation uses the deprecated Platform API V1 and has several issues with ambiguous behavior, particularly around port breakout scenarios where a single physical port is split into multiple logical interfaces. The LED state determination is inconsistent across different SKUs and platform vendors.

This design proposes a new LED policy that:
- Clearly defines LED states (ALL_UP, PARTIAL_UP, DOWN) based on logical interface status
- Uses standard LED colors for each state
- Handles port breakout configurations deterministically
- Uses Platform API V2 for consistent LED control across platforms
- Moves LED policy logic to the LEDD daemon for centralized control
- Provides a new CLI for displaying LED states

### 5. Requirements

#### 5.1. Functional Requirements

1. **LED State Definition**: Define LED states based on logical interface status:
   - ALL_UP: All associated logical interfaces that are admin up are also link up
   - PARTIAL_UP: At least one logical interface is admin up but link down
   - DOWN: No interfaces exist or all interfaces admin down

2. **LED State Definition**: Define LED colors for each state:
   - ALL_UP: LED is GREEN
   - PARTIAL_UP: LED is AMBER/YELLOW
   - DOWN: LED is off

3. **Support all Port Breakouts**: Have deterministic rules for mapping lanes to LEDs for all breakout scenarios

4. **Multiple LEDs per Port**: Support front panel ports with 0-N LEDs

5. **Platform API V2**: Use Platform API V2 for LED control, with fallback to V1 for legacy platforms

#### 5.2. Configuration Requirements

1. LED policy should work without additional configuration
2. LED behavior should be consistent across all platforms implementing the API
3. Platforms must report LED capabilities (available colors)

#### 5.3. Management Requirements

1. Provide CLI to display LED status for each subport

#### 5.4. Non-Requirements

1. This design does not cover system LEDs (fan, PSU, status LEDs)
2. This design does not define behavior for custom platform-specific LED configurations beyond the standard port LEDs

### 6. Architecture Design

This feature enhances the existing PMON (Platform Monitor) architecture without changing the overall SONiC architecture. The changes are isolated to the LED daemon (ledd) and the platform layer.

```
┌────────────────────────────────────────────────────────────────┐
│                         User Space                             │
│  ┌──────────────┐                                              │
│  │  CLI (show   │                                              │
│  │  interface   │                                              │
│  │  led status) │                                              │
│  └──────┬───────┘                                              │
│         │                                                      │
│         │ READ                                                 │
│         ▼                                                      │
│  ┌─────────────────────────┐ ┌────────────────────────────────┐│
│  │ STATE_DB                │ │ APPL_DB: PORT_TABLE            ││
│  │   PORT_LED_STATUS table │ │ CONFIG_DB: PORT (admin, lanes) ││
│  └──────────────┬──────────┘ └──────────────┬─────────────────┘│
│                 ▲ WRITE                     │ READ             │
│                 │                           ▼                  │
│  ┌──────────────────────────────────────────┐                  │
│  │         LEDD Daemon (PMON)               │                  │
│  │                                          │                  │
│  │  ┌────────────────────────────────────┐  │                  │
│  │  │  LED Policy Logic                  │  │                  │
│  │  │  - Track interface states          │  │                  │
│  │  │  - Calculate LED states            │  │                  │
│  │  │  - Map interfaces to LEDs          │  │                  │
│  │  │  - Write status to STATE_DB        │  │                  │
│  │  └────────────────────────────────────┘  │                  │
│  │                 │                        │                  │
│  │                 ▼                        │                  │
│  │  ┌────────────────────────────────────┐  │                  │
│  │  │  Platform API V2 Interface         │  │                  │
│  │  │  - get_num_leds()                  │  │                  │
│  │  │  - get_all_leds()                  │  │                  │
│  │  │  - get_led(index)                  │  │                  │
│  │  └────────────────────────────────────┘  │                  │
│  └──────────────────┬───────────────────────┘                  │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────┐                  │
│  │      Platform Layer                      │                  │
│  │                                          │                  │
│  │  ┌────────────────────────────────────┐  │                  │
│  │  │  SFP Object (SfpBase)              │  │                  │
│  │  │  - get_num_leds()                  │  │                  │
│  │  │  - get_all_leds()                  │  │                  │
│  │  │  - get_led(index)                  │  │                  │
│  │  └──────────────┬─────────────────────┘  │                  │
│  │                 │                        │                  │
│  │                 ▼                        │                  │
│  │  ┌────────────────────────────────────┐  │                  │
│  │  │  LED Object (new class)            │  │                  │
│  │  │  - get_name()                      │  │                  │
│  │  │  - get_color_capabilities()        │  │                  │
│  │  │  - set_color(color)                │  │                  │
│  │  └────────────────────────────────────┘  │                  │
│  └──────────────────┬───────────────────────┘                  │
└─────────────────────┼──────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────────┐
│              Kernel Space                                      │
│  ┌────────────────────────────────────────┐                    │
│  │  /sys/class/leds/* (optional)          │                    │
│  │  Platform-specific LED drivers         │                    │
│  └──────────────┬─────────────────────────┘                    │
└─────────────────┼──────────────────────────────────────────────┘
                  │
                  ▼
           Hardware LEDs
```

**Key Components:**

1. **LEDD Daemon**: Enhanced to implement LED policy logic and use Platform API V2
2. **Platform Layer**: Extended SfpBase class with LED-related methods
3. **LED Class**: New class to represent individual port LEDs
4. **Legacy Support**: Fallback to Platform API V1 for platforms not yet migrated

The architecture maintains backward compatibility by detecting Platform API V2 support and falling back to the legacy implementation when needed.

### 7. High-Level Design

#### 7.1. Feature Type
This is a built-in SONiC feature, not an Application Extension. It enhances the existing PMON container.

#### 7.2. Modules and Repositories

**Modified Repositories:**
1. **sonic-platform-common**: Add new LED class and extend SfpBase
2. **sonic-platform-daemons**: Modify ledd daemon to implement new LED policy
3. **sonic-utilities**: Add new CLI command `show interface led status`

**Modified Modules:**
- `sonic-platform-common/sonic_platform_base/sfp_base.py`: Add LED-related methods
- `sonic-platform-common/sonic_led/led_control_base.py`: New LED class
- `sonic-platform-daemons/sonic-ledd/scripts/ledd`: Enhanced LED policy logic
- `sonic-utilities/show/interfaces.py`: New port LED status command

#### 7.3. LED Policy Details

##### 7.3.1. LED-to-Interface Mapping

A front panel port will have 0 to N LEDs associated with it. The LED policy will evenly split the logical interfaces of a front panel port across the available LEDs. If the number of LEDs exceeds the number of logical interfaces, the extra LEDs will remain off.

For example, an OSFP port with 2 LEDs:

| Breakout Config | LED 0 | LED 1 |
|:----------------|:-------------------------|:------|
| 1x (8 lanes) | Ethernet0 | None |
| 2x (4 lanes each) | Ethernet0 | Ethernet4 |
| 4x (2 lanes each) | Ethernet0, Ethernet2 | Ethernet4, Ethernet6 |
| 8x (1 lane each) | Ethernet0-3 | Ethernet4-7 |

A QSFP port with 4 LEDs:

| Breakout Config | LED 0 | LED 2 |  LED 3 | LED 4 |
|:----------------|:-------------------------|:------|:------|:------|
| 1x (4 lanes) | Ethernet0 | None | None | None |
| 2x (2 lanes each) | Ethernet0 | Ethernet2 | None | None |
| 4x (1 lanes each) | Ethernet0 | Ethernet1 | Ethernet2 | Ethernet3 |

**LED Orientation:**
- Index 0 LED represents the leftmost LED (horizontal orientation) or topmost LED (vertical orientation)
- Platform implementation must return LEDs in this order

##### 7.3.2. LED State Mapping

LED states will be set based on the state of the logical interfaces mapped to the LED. Interfaces that are admin down will not contribute to state calculations unless all interfaces are admin down.

| LED State | Interface State |
|:----------|:----------------|
| ALL_UP | All associated logical interfaces that are admin up are also link up |
| PARTIAL_UP | At least one logical interface is admin up but link down |
| DOWN | No associated logical interfaces or all interfaces admin down |

| LED State | LED Color |
|:----------|:----------------|
| ALL_UP | Green |
| PARTIAL_UP | Yellow/Amber |
| DOWN | Off |

##### 7.3.3. Algorithm

```python
# Pseudocode for LED state calculation

for each front_panel_port:
    num_leds = sfp.get_num_leds()

    if num_leds == 0:
        continue  # No controllable LEDs

    # Get all logical interfaces for this port
    logical_ports = get_logical_ports_for_physical_port(front_panel_port)
    num_lanes = get_num_lanes(front_panel_port)

    lanes_per_led = num_lanes / num_leds

    # Map logical ports to LEDs
    for led_idx in range(num_leds):
        led = sfp.get_led(led_idx)

        # Get logical ports for this LED's lanes
        start_lane = led_idx * lanes_per_led
        end_lane = start_lane + lanes_per_led
        associated_ports = get_ports_for_lanes(logical_ports, start_lane, end_lane)

        # Filter out admin down ports
        active_ports = [p for p in associated_ports if not is_admin_down(p)]

        if len(active_ports) == 0:
            led.set_color(LedColor.OFF)
        elif all(is_link_up(p) for p in active_ports):
            led.set_color(LedColor.GREEN)
        elif any(is_link_down(p) for p in active_ports):
            led.set_color(LedColor.AMBER)
        else:
            led.set_color(LedColor.OFF)
```

#### 7.4. Platform API V2 Extensions

##### 7.4.1. SfpBase Extensions

Add to `sonic_platform_base/sfp_base.py`:

```python
class SfpBase:
    def get_num_leds(self):
        """
        Retrieves the number of LEDs associated with this SFP
        """

    def get_all_leds(self):
        """
        Retrieves all LED objects associated with this SFP
        """

    def get_led(self, index):
        """
        Retrieves the LED object at the specified index
        """
```

##### 7.4.2. New LED Class

Add to  `sonic_led/led_control_base.py`:

```python
class LedColor(Enum):
    """Enumeration of LED colors"""
    OFF = 0
    GREEN = 1
    AMBER = 2
    YELLOW = 2  # Alias for AMBER
    RED = 3
    BLUE = 4

class LedBase:
    """
    Base class for platform-specific LED implementations
    """

    def get_name(self):
        """
        Retrieves the name of the LED
        """

    def get_color_capabilities(self):
        """
        Retrieves the color capabilities of this LED
        """

    def set_color(self, color):
        """
        Sets the LED to the specified color
        """

    def get_color(self):
        """
        Retrieves the current color of the LED
        """
```

#### 7.5. LEDD Daemon Changes

The LEDD daemon will be modified to:

1. **Detect Platform API V2 support:**
   - Call `get_num_leds()` on SFP objects
   - If NotImplementedError is raised, fall back to legacy Platform API V1
   - If 0 is returned, platform has implemented API but has no controllable LEDs

2. **Implement LED policy logic:**
   - Track interface state changes from PORT_TABLE in APPL_DB
   - Calculate LED states based on the policy defined above
   - Map logical interfaces to physical LEDs based on policy defined above
   - Call `set_color()` on LED objects when state changes

3. **Handle port breakout changes:**
   - React to CONFIG_DB PORT table changes
   - Recalculate LED-to-interface mappings when breakout configuration changes
   - Recalculate LED state when mapping changes

4. **State caching:**
   - Cache current LED states to avoid unnecessary hardware writes
   - Only call `set_color()` when the calculated state differs from cached state

5. **Update STATE_DB:**
   - Write LED status to `PORT_LED_STATUS` table after each LED color change
   - Enable CLI to display current LED status without querying hardware

#### 7.6. Database Changes

**New STATE_DB Table:**

A new table is added to STATE_DB to store current LED status for CLI display:

**Table Name:** `PORT_LED_STATUS`

**Key:** `<logical_port_name>|<led_index>`
- Example: `Ethernet0|0`, `Ethernet4|1`

**Fields:**
| Field | Type | Description |
|:------|:-----|:------------|
| `port_index` | integer | Index of the port |
| `port_name` | string | Platform-specific port name (e.g., "osfp1") |
| `led_name` | string | Platform-specific LED name (e.g., "led1", "port1_led2") |
| `led_color` | string | Current LED color (green, amber, off, red, blue) |

**Example Entries:**
OSFP port with 2x breakout and 2 LEDs:
```
PORT_LED_STATUS|Ethernet0|0
  sfp_index: 1
  sfp_name: osfp1
  led_name: led1
  led_color: green
PORT_LED_STATUS|Ethernet4|1
  sfp_index: 1
  sfp_name: osfp1
  led_name: led2
  led_color: amber
```

QSFP port with 4x breakout and 1 LEDs:
```
PORT_LED_STATUS|Ethernet0|0
  sfp_index: 1
  sfp_name: qsfp1
  led_name: led1
  led_color: green
PORT_LED_STATUS|Ethernet1|0
  sfp_index: 1
  sfp_name: qsfp1
  led_name: led1
  led_color: green
PORT_LED_STATUS|Ethernet2|0
  sfp_index: 1
  sfp_name: qsfp1
  led_name: led1
  led_color: green
PORT_LED_STATUS|Ethernet3|0
  sfp_index: 1
  sfp_name: osfp1
  led_name: led1
  led_color: green
```

**Existing Database Usage:**

- **APPL_DB PORT_TABLE**: Read interface oper status
- **CONFIG_DB PORT**: Read interface configuration (admin status, lanes, breakout mode)

#### 7.7. Linux Dependencies

Platform implementations MAY use `/sys/class/leds/*` interface to control LEDs through kernel drivers, but this is optional and platform-specific. The contract is the Platform API V2, not the sysfs interface.

#### 7.8. Warm Reboot and Fastboot

- LED state is not preserved across reboots (this is consistent with current behavior)
- LEDs will be recalculated based on interface states after daemon restart
- No impact on warm reboot or fastboot timing

#### 7.9. Performance and Scalability

- LED updates are event-driven (triggered by port state changes)
- Hardware writes are minimized through state caching
- Negligible CPU and memory impact

#### 7.10. Platform Dependencies

**Platform vendors must implement:**
1. Following methods in SfpBase derived classes:
- `get_num_leds()`
- `get_all_leds()`
- `get_led(index)`
2. Following methods in LedBase derived classes:
- `get_name()`
- `get_color_capabilities()`
- `set_color()`
- `get_color()`

**Migration path:**
- Existing platforms continue to work with legacy Platform API V1
- Platforms can migrate to V2 at their own pace
- Both APIs can coexist during transition period

### 8. SAI API

**No SAI API changes required.**

### 9. Configuration and management

#### 9.1. Manifest (if the feature is an Application Extension)

Not applicable - this is a built-in SONiC feature.

#### 9.2. CLI/YANG model Enhancements

##### 9.2.1. New Show Command

A new show command will be added to display LED status:

**Command:**
```
show interface led status [<interface_name>]
```

**Description:**
Displays the current LED status for interfaces. If an interface name is provided, shows only that interface. Otherwise, shows all interfaces with controllable LEDs.

**Example Output:**
```
admin@sonic:~$ show interface led status

Interface Name  Port Index  Port Name  Alias   LED Index  LED Name  LED Color
--------------  ----------  ---------  ------  ---------  --------  ---------
Ethernet0       1           osfp1      etp1a   0          led1      Green
Ethernet4       1           osfp1      etp1b   1          led2      Green
Ethernet8       2           osfp2      etp2a   0          led1      Amber
Ethernet12      2           osfp2      etp2b   1          led2      Off
Ethernet16      3           osfp3      etp3a   0          led1      Green
Ethernet20      3           osfp3      etp3b   1          led2      Amber
.. .
Ethernet224     57          qsfp57     etp57a  0          led1      Off
```

**Example with Interface Filter:**
```
admin@sonic:~$ show interface led status Ethernet0

Interface Name  Port Index  Port Name  Alias   LED Index  LED Name  LED Color
--------------  ----------  ---------  ------  ---------  --------  ---------
Ethernet0       1           osfp1      etp1a   0          led1      Green
```

**Output Fields:**
- **Interface Name**: SONiC logical interface name
- **Port Index**: Platform-specific port index
- **Port Name**: Platform-specific port name
- **Alias**: Port alias from CONFIG_DB (e.g., "etp1a", "etp1b")
- **LED Index**: LED index within the port (0-based, where 0 is leftmost/topmost)
- **LED Name**: Platform-specific LED name
- **LED Color**: Current LED color (Green, Amber, Off, etc.)

**Implementation Details:**
```python
# Connect to STATE_DB and CONFIG_DB
state_db = daemon_base.db_connect("STATE_DB")
config_db = daemon_base.db_connect("CONFIG_DB")
port_led_table = swsscommon.Table(state_db, "PORT_LED_STATUS")
port_table = swsscommon.Table(config_db, "PORT")

# Get all entries or filter by interface
for key in port_led_table.getKeys():
    # key format: "Ethernet0|0" (interface|led_index)
    interface_name, led_index = key.split('|')

    # Get LED status from STATE_DB
    status, fvp = port_led_table.get(key)
    if status:
        fvs = dict(fvp)

        # Get alias from CONFIG_DB PORT table
        _, port_fvp = port_table.get(interface_name)
        port_fvs = dict(port_fvp)
        alias = port_fvs.get('alias', interface_name)

        # Display: interface_name, port_index, port_name, alias, led_index, led_name, led_color
```

##### 9.2.2. YANG Model

No YANG model changes required.

##### 9.2.3. Backward Compatibility

The new show command is additive and does not impact existing CLI functionality. The command will gracefully handle platforms that have not implemented Platform API V2 by displaying appropriate messages.

#### 9.3. Config DB Enhancements

No Config DB changes required.

### 10. Warmboot and Fastboot Design Impact

As mentioned in 7.8, no requirements or dependencies with respect to warmboot or fastboot:
- LED state is not preserved across reboots (this is consistent with current behavior)
- LEDs will be recalculated based on interface states after daemon restart

### Warmboot and Fastboot Performance Impact

No expected impact on warmboot or fastboot performance.

### 11. Memory Consumption

The feature introduces minimal memory overhead. Memory usage is proportional to port count, which is a fixed hardware characteristic, and all allocations are one-time at initialization.

**LEDD Daemon memory usage:**
   - LED state cache: ~50 bytes per LED (LED index, current color, interface mapping)
   - Interface-to-LED mapping: ~100 bytes per front panel port
   - For a 128-port system with 2 LEDs per port: ~40 KB total
   - Additional Python objects for LED class instances: ~20 KB

This feature is part of the LEDD daemon; it cannot be disabled via compilation separately.

### 12. Restrictions/Limitations

1. **Platform Support**: Platforms must implement Platform API V2 LED methods to use the new policy. Legacy platforms will continue using Platform API V1.

2. **LED Capabilities**: The policy assumes port LEDs can display at least GREEN and AMBER/YELLOW colors.

3. **System LEDs**: This design only covers port LEDs. System status LEDs (fan, PSU, system status) are out of scope.

4. **LED Naming**: LED names are platform-specific and used primarily for debugging. There is no standardized naming scheme across platforms.

5. **Orientation Assumption**: The LED index 0 orientation (leftmost/topmost) assumes standard front-to-back or top-to-bottom LED arrangements. Platforms with non-standard layouts should document their LED ordering.

6. **Breakout Limitations**: The LED-to-interface mapping assumes even lane distribution. Asymmetric breakout configurations (if supported by hardware) may require custom platform logic.

### 13. Testing Requirements/Design

#### 13.1. Unit Test cases

**LEDD Daemon Tests:**

1. **Test LED Policy Logic**
   - Test LED state calculation for single interface per LED
   - Test LED state calculation for multiple interfaces per LED
   - Test admin down interface exclusion from LED state
   - Test all interface combinations (all up, partial up, all down)

2. **Test Platform API V2 Detection**
   - Test fallback to Platform API V1 when V2 not implemented
   - Test handling of `get_num_leds()` returning 0
   - Test handling of `get_num_leds()` raising NotImplementedError

3. **Test Breakout Configuration Mapping**
   - Test LED-to-interface mapping for 1x breakout
   - Test LED-to-interface mapping for 2x breakout
   - Test LED-to-interface mapping for 4x breakout
   - Test LED-to-interface mapping for 8x breakout
   - Test dynamic reconfiguration when breakout mode changes

4. **Test State Caching**
   - Verify `set_color()` is only called when state changes
   - Verify cached state is properly maintained across port state changes

**Platform API Tests:**

5. **Test LED Class Implementation**
   - Test `get_name()` returns valid string
   - Test `get_color_capabilities()` returns valid LedColor list
   - Test `set_color()` with valid colors succeeds
   - Test `set_color()` with unsupported color fails gracefully
   - Test `get_color()` returns current color

6. **Test SfpBase LED Extensions**
   - Test `get_num_leds()` returns correct count
   - Test `get_all_leds()` returns ordered LED list
   - Test `get_led(index)` returns correct LED object
   - Test `get_led(invalid_index)` handles errors appropriately

**CLI Tests:**

7. **Test Show Command**
   - Test `show interface led status` displays all interfaces
   - Test `show interface led status <interface>` filters correctly
   - Test output format and column alignment
   - Test behavior on platforms without Platform API V2 support

#### 13.2. System Test cases

**Basic Functionality:**

1. **Test Single Interface LED Behavior**
   - Bring interface up, verify LED turns green
   - Bring interface down (link down), verify LED turns amber
   - Set interface admin down, verify LED turns off
   - Remove transceiver, verify LED turns off

2. **Test Breakout Configuration LEDs**
   - Configure port in 1x mode, verify LED behavior
   - Change to 2x mode, verify both LEDs controlled independently
   - Change to 4x mode, verify LED grouping
   - Verify LED states update correctly after breakout change

3. **Test Multiple Interfaces Per LED**
   - Configure 2x breakout with 2 LEDs
   - Bring up first interface, verify first LED green
   - Bring up second interface, verify second LED green
   - Bring down first interface, verify first LED amber
   - Configure 4x breakout with 2 LEDs
   - Verify LED shows green when both associated interfaces up
   - Verify LED shows amber when at least one associated interface down

**Stress Testing:**

4. **Test Scale**
   - Test system with maximum number of ports (e.g., 128+ ports)
   - Toggle all ports simultaneously
   - Verify memory usage remains stable

5. **Test Daemon Restart**
   - Start ledd with various port states
   - Verify all LEDs initialize to correct states
   - Restart ledd daemon, verify LEDs recalculate correctly

**Regression Testing:**

6. **Verify Existing Functionality**
   - Verify existing platforms using Platform API V1 continue to work
   - Verify LED behavior on legacy platforms unchanged
   - Verify no regressions in other PMON functionality

#### 13.3. Warmboot/Fastboot Testing

1. **Test Warmboot**
   - Perform warmboot
   - Verify LEDs restore to same states after warmboot

2. **Test Fastboot**
   - Perform fastboot
   - Verify LEDs initialize correctly after fastboot

### 14. Open/Action items - if any

**Documentation Updates**
   - Update Platform API V2 documentation with LED class specification
   - Update LEDD daemon documentation
   - Create platform developer guide for implementing LED support
   - Update https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md with new CLI

