# Align transceiver CLIs formatting for common and platform-specific technology extensions

## 1. Revision

| Rev | Date | Author | Change Description |
|:---:|:----:|:------:|:-------------------|
| 0.1 | 05/2026 | | Initial version |

## 2. Scope

This HLD defines the minimal changes required to align the 'sfputil' and 'show interface transceiver' CLIs
to include new common and platform-specific data in the output (CPO as reference use case).

It includes 2 main parts:
1. Ensure we print the common new CPO fields - using new key formatting map for these fields.
2. Create new ability to have key formatting map for the platform-specific fields.

Relevant CLIs:
- `sfputil show eeprom -d`
- `show interfaces transceiver eeprom -d`
- `show interfaces transceiver status`

## 3. Overview

The goal is simple: **New technology fields must be formatted consistently across CLIs**,
while keeping platform-specific formatting logic in platform code.

## 4. Requirements

- Ensure we print the common new CPO fields - using new key formatting map for these fields (as done today for other types).
- Create new ability to have key formatting map for the platform-specific fields (of any technology).
- `sonic-utilities` should not hardcode platform-specific labels/units.
Platform implementations should provide their own maps via the APIs (5.3).

## 5. High-Level Design

### 5.1. How it works today

```python
# The real code is more complex but the following is a simpler version just to present the idea

DATA_MAP = {
    'model': 'Vendor PN',
    'vendor_oui': 'Vendor OUI',
    'vendor_date': 'Vendor Date Code(YYYY-MM-DD Lot)',
    'manufacturer': 'Vendor Name',
    'vendor_rev': 'Vendor Rev',
    # ...
}

# CMIS_DATA_MAP = { ... }
# QSFP_DD_DATA_MAP = { ... }
# DOM_DATA_MAP = { ... }

# ...

sfp = platform_chassis.get_sfp(physical_port)
# Since sfp is platform object, it will return also platform-specific fields.
info = sfp.get_transceiver_info() # Or get_all('TRANSCEIVER_INFO|<port>')

for key in info:
  print(f'{DATA_MAP[key]} : {info[key]}')
```

### 5.2. Add common CPO format maps in utilities (sfputil and sfpshow)

Add/extend CPO-specific display maps in shared utility code for common fields (not platform-specific fields), including:

- CPO transceiver info labels
- CPO DOM labels/units
- CPO status labels

These maps are merged into the existing flows only when the transceiver type is CPO.

### 5.3. Add explicit platform-specific formatting APIs on `SfpBase`

Expose platform hooks as three explicit APIs:

- `get_platform_specific_transceiver_info_format_map() -> dict`
- `get_platform_specific_transceiver_status_format_map() -> dict`
- `get_platform_specific_dom_format_map() -> tuple(dict, dict)`

Default implementation returns empty maps, so platforms with no platform-specific extension continue to work without behavior change.

### 5.4. Keep platform-specific map ownership in platform code

`sonic-utilities` should not hardcode platform-specific labels/units.
Platform implementations should provide their own maps via the APIs above.

### 5.5. Integration Example (Reference)

```python
# src/sonic-platform-common/sonic_platform_base/sfp_base.py:SfpBase

def get_platform_specific_transceiver_info_format_map(self):
        """
        Retrieves the platform-specific transceiver info format map.
        """
        return {}

def get_platform_specific_transceiver_status_format_map(self):
        """
        Retrieves the platform-specific transceiver status format map.
        """
        return {}

def get_platform_specific_dom_format_map(self):
        """
        Retrieves platform-specific DOM format and unit maps.

        Returns:
            tuple(dict, dict): (dom_value_map, dom_unit_map)
        """
        return {}, {}
```

```python
# platform/mellanox/mlnx-platform-api/sonic_platform/sfp.py:CpoPort

CPO_DOM_CHANNEL_FORMAT_MAP = {
        # ...
}

CPO_STATUS_MAP = {
        # ...
}

# ...

def get_platform_specific_transceiver_status_format_map(self):
        """
        Retrieves the platform-specific transceiver status format map.
        """
        return self.CPO_STATUS_MAP
```

```python
# src/sonic-utilities/sfputil/main.py

CMIS_DOM_CHANNEL_MONITOR_MAP = {
    'rx1power': 'RX1Power',
    'rx2power': 'RX2Power',
    # ...
}

''' NEW '''
CPO_DOM_CHANNEL_MONITOR_MAP = {
    'els_tx1bias': 'ELS Lane1Bias',
    'els_tx1voltage': 'ELS Lane1Voltage',
    'els_tx1power': 'ELS Lane1Power',
    # ...
}

# Flow for displaying the DOM information:

# Since sfp is platform object, it will return also platform-specific fields.
info = sfp.get_transceiver_dom_real_value()

format_map = CMIS_DOM_CHANNEL_MONITOR_MAP
''' NEW '''
if sfp_type == 'CPO':
    # Adding new common CPO formatting
    format_map.update(CPO_DOM_CHANNEL_MONITOR_MAP)

print('ChannelMonitorValues:')
for key in info:
    print(f'{format_map[key]} : {info[key]}')

print('ModuleMonitorValues:')
# ...

''' NEW '''
# platform-specific DOM formatting
print('PlatformSpecificDomValues:')
platform_specific_dom_format_map = sfp.get_platform_specific_dom_format_map()
for key in info:
    if key in platform_specific_dom_format_map:
        print(f'{platform_specific_dom_format_map[key]} : {info[key]}')
```
