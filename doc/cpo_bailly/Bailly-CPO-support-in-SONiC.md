# Bailly CPO support in SONiC

## Table of Contents

- [Bailly CPO support in SONiC](#bailly-cpo-support-in-sonic)
  - [Table of Contents](#table-of-contents)
  - [1. Revision](#1-revision)
  - [2. Scope](#2-scope)
  - [3. Definitions/Abbreviations](#3-definitionsabbreviations)
  - [4. Overview](#4-overview)
  - [5. Requirements](#5-requirements)
  - [6. High-Level Design](#6-high-level-design)
    - [6.1. Problem Statement](#61-problem-statement)
    - [6.2. New Approach](#62-new-approach)
      - [6.2.1. cpo.json](#621-cpojson)
      - [6.2.2. SfpOptoeBase](#622-sfpoptoebase)
      - [6.2.3. ChassisBase](#623-chassisbase)
      - [6.2.4. CmisMemMap](#624-cmismemmap)
      - [6.2.5. CmisApi](#625-cmisapi)
      - [6.2.6. CmisCodes](#626-cmiscodes)
      - [6.2.7.XcvrApiFactory](#627xcvrapifactory)
      - [6.2.8. CmisManagerTask](#628-cmismanagertask)
      - [6.2.9. SfpStateUpdateTask](#629-sfpstateupdatetask)
      - [6.2.10. DomInfoUpdateTask](#6210-dominfoupdatetask)
      - [6.2.11. Show interfaces transceiver CLI](#6211-show-interfaces-transceiver-cli)
      - [6.2.12. optoe driver](#6212-optoe-driver)
    - [6.3. Implementation Flow](#63-implementation-flow)
      - [6.3.1. Chassis Init Flow](#631-chassis-init-flow)
      - [6.3.2. Module Presence Flow](#632-module-presence-flow)
      - [6.3.3.  API Call Flow](#633--api-call-flow)
      - [6.3.4.  CmisManagerTask State Machine](#634--cmismanagertask-state-machine)
    - [6.4. Unit Test cases](#64-unit-test-cases)
    - [6.5. Open/Action items - if any](#65-openaction-items---if-any)

## 1. Revision

| Rev |      Date      | Author | Change Description                       |
| :-: | :------------: | :----: | ---------------------------------------- |
| 1.0 | April 14 2026 | Kroos | Initial version                          |
| 1.1 |  May 25 2026  | Kroos | Revised based on the actual running code |

## 2. Scope

This document is based on the Micas CPO overall design document:[CPO support in SONiC by KroosMicas · Pull Request #2152 · sonic-net/SONiC](https://github.com/sonic-net/SONiC/pull/2152/)， and details how Broadcom Bailly CPO is adapted based on the overall design.

## 3. Definitions/Abbreviations

| Term  | Definition                                 |
| ----- | ------------------------------------------ |
| OE    | Optical Engine                             |
| CPO   | Co-packaged optics                         |
| CMIS  | Common Management Interface Specification  |
| ELSFP | External Laser Small Form Factor Pluggable |
| ELS   | External Laser Sources                     |
| optoe | Optical Transceiver Open EEPROM driver     |
| VDM   | Versatile Diagnostics Monitoring           |
| I2C   | Inter-Integrated Circuit                   |
| SPI   | Serial Peripheral Interface                |
| ASIC  | Application-Specific Integrated Circuit    |

## 4. Overview

This low-level design document describes the support for Broadcom Bailly Co-packaged Optics (CPO) in SONiC.

Broadcom Bailly CPO is implemented in the form of vmodule, which means platform management is consistent with that of regular optical modules, and no special revisions for CPO are required. On the basis of implementing the basic functions of CPO ports through vmodule, this document supplements the method for obtaining additional debugging information of CPO (i.e., the external exposure of Bailly's custom debug register interface).

## 5. Requirements

The overall design document is adopted as-is. This document mainly illustrates how Broadcom Bailly CPO implements the following functions:

1. Mapping between ports and OE/ELS
2. Mapping of Broadcom Bailly CPO CMIS memory map
3. How Broadcom Bailly CPO reuses the xcvrd module management framework

## 6. High-Level Design

### 6.1. Problem Statement

The overall design document is adopted as-is. Adaptation for Broadcom Bailly CPO is required.

### 6.2. New Approach

Main revised components are as follows:

Compared with the overall design, many functions of Broadcom Bailly CPO are modified through MCU linkage, so not all components mentioned in the overall design need to be modified. The specific components that need to be modified are explained as follows:

| Original Module | Revised/New Module | Type     | Description                                                                                                                                                                                                                                                                       |
| :-------------- | ------------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Na              | cpo.json           | New      | OE/ELS-related configuration information<br />Switch Vendors are required to config this file.<br />The mapping relationships between ports and OE/ELS, as well as bank‑based configuration references.<br />Switch Vendors are required to config this file.                  |
| SfpOptoeBase    | CpoOptoeBase       | New      | An abstract port management class used by the xcvrd framework for port management.<br />It mainly provides EEPROM access interfaces for OE and ELS.<br />Switch vendors are required to instantiate this class and use it with revisions to the platform.json configuration file. |
| ChassisBase     | Chassis            | Modified | An original vendor-implemented class used during initialization to determine<br />whether a port uses the CpoOptoeBase type or the original OptoeBase type.<br />Switch vendors are required to instantiate this class.                                                           |
| CmisMemMap      | BaillyMemMap       | New      | Broadcom Bailly CPO adopts the joint mode, and ELS-related information is obtained through BaillyMemMap                                                                                                                                                                           |
| CmisApi         | BaillyApi          | New      | Some APIs are unavailable; additional APIs are added based on BaillyMemMap                                                                                                                                                                                                        |
| CmisCodes       | BaillyCodes        | New      | Add the unique parsing codes specific to Bailly                                                                                                                                                                                                                                   |
| optoe driver    | optoe driver       | Modified | Adds multi-bank memory map support.                                                                                                                                                                                                                                               |

#### 6.2.1. cpo.json

Consistent with the overall design, but Broadcom Bailly CPO does not require configuration of fields such as "els_cmis_path". The field "cpo_eeprom_mode":"joint" is added to support both separate mode and joint mode compatibility.

In addition, the "base_page": "0xb0" field is added to the elss section, which is used to directly access addresses through the combined oe_cmis_path in joint mode. This eliminates the need to repeatedly write Bailly's CmisMemMap even if one OE corresponds to multiple ELSs.

The mapping relationship between ports and oe/els is bound through the "interfaces" section.

```
   "cpo_eeprom_mode":"joint" 
   "oes":{
        "oe0": {  // start with OE 0
            "index": 0,
            "oe_cmis_path": "/sys/bus/i2c/devices/i2c-24/24-0050/",
        },
         ...
        "oe7": {
            "index": 7,
            "oe_cmis_path": "/sys/bus/i2c/devices/i2c-31/31-0050/",
    },
  "elss": {
    "els0": {
      "index": 0,
      "els_presence": {
        "presence_file": "/dev/fpga1",
        "presence_offset": "0x64",
        "presence_len": "4",
        "presence_value": "0",
        "presence_bit": "8"
      }
    },
     ...
    "els15": {
      "index": 15,
      "els_presence": {
        "presence_file": "/dev/fpga1",
        "presence_offset": "0x64",
        "presence_len": "4",
        "presence_value": "0",
        "presence_bit": "31"
      }
    }
  },
  "interfaces": {
    "Ethernet1": {
      "index": "1,1,1,1,1,1,1,1",
      "lanes": "1,2,3,4,5,6,7,8",
      "oe_id": 0,
      "oe_bank_id": 0,
      "els_id": 0
    },
  ...
  }
```

#### 6.2.2. SfpOptoeBase

Inherit the original SfpOptoeBase class and implement the functions related to CPO bailly.

```
class CpoOptoeBase(SfpOptoeBase):
    def __init__(self):
        super().__init__()
        self._port_id = -1
        self._oe_bank_id = -1
        self._oe_id = -1
        self._els_id = -1
        self._els_bank_id = -1

    def get_oe_eeprom_path(self):
        cpo_bus = self.get_oes_config().get("oe_cmis_path", None)
        return cpo_bus + "eeprom" if cpo_bus is not None else None

    def get_oes_config(self):
        key = f"oe{self._oe_id}"
        config = get_cpo_json_data().get("oes", None)
        return config.get(key)

    def get_elss_config(self):
        key = f"els{self._els_id}"
        config = get_cpo_json_data().get("elss", None)
        return config.get(key)

    def read_eeprom(self, offset, num_bytes):
        try:
            with open(self.get_eeprom_path(), mode='rb', buffering=0) as f:
                f.seek(offset)
                ret = bytearray(f.read(num_bytes))
                return ret
        except (OSError, IOError):
            return None

    def write_eeprom(self, offset, num_bytes, write_buffer):
        try:
            with open(self.get_eeprom_path(), mode='r+b', buffering=0) as f:
                f.seek(offset)
                f.write(write_buffer[0:num_bytes])
        except (OSError, IOError):
            return False
        return True

    def get_els_presence(self):
        try:
            els_presence = self.get_elss_config().get("els_presence", None)
            els_presence_file = els_presence.get("presence_file", None)
            presence_offset = int(els_presence.get("presence_offset", None), 16)
            presence_len = int(els_presence.get("presence_len", None))
            presence_bit = int(els_presence.get("presence_bit", None))
            presence_value = int(els_presence.get("presence_value", None))
            with open(els_presence_file, mode='rb', buffering=0) as f:
                f.seek(presence_offset)
                byte_value = f.read(presence_len)
                raw = bytearray(byte_value)
                int_value = int.from_bytes(raw, byteorder='little')
                is_bit_presence = ((int_value >> presence_bit) & 1) == presence_value
                return is_bit_presence
        except (OSError, IOError):
            return False
  
    def get_presence(self):
        return self.get_els_presence()

    def get_els_base_page(self):
        els_index = int(self.get_elss_config().get("index", None))
        els_second = els_index % 2
        base_page = 0
        if els_second:
            base_page = 4
        return base_page

    def get_oe_bank_id(self):
        return self._oe_bank_id
    def get_oe_id(self):
        return self._oe_id
    def get_els_bank_id(self):
        return self._els_bank_id
    def get_els_id(self):
        return self._els_id

    @abc.abstractmethod
    def check_fiber_dirty(self):
        """
        Check whether the fiber is dirty. True:check ok; False: check failed
        """
        raise NotImplementedError

    @abc.abstractmethod
    def check_calibration(self):
        """
        Check whether the calibration such as oe power sufficient. True:check ok; False: check failed
        """
        raise NotImplementedError
  
    @abc.abstractmethod
    def is_els_power_sufficient(self):
        """
        Check whether els power sufficient.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_calibration_checked(self):
        """
        Check whether the calibration such as oe power sufficient detection has been completed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_fiber_checked(self):
        """
        Check whether the fiber detection has been completed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_els_tx_on(self):
        """
        Check the ELS TX status to see if it is emitting light normally.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_els_tx_enabled(self):
        """
        Check whether the ELS TX enable has been set.
        """
        raise NotImplementedError
```

Vendors need to inherit this class and instantiate it. Here is an example: Based on the type of CMIS required by the vendor, rewrite the get_xcvr_api

```
OE_BANK_NUM = 8

class CPO(CpoOptoeBase):
    def __init__(self, index, oe_id, oe_bank_id,  els_id, els_bank_id):
        super().__init__()
        self._port_id = index
        self._oe_id = oe_id
        self._oe_bank_id = oe_bank_id
        self._els_id = els_id
        self._els_bank_id= els_bank_id
        # need after _oe_bank_id init
        self.remove_xcvr_api()
        self.get_xcvr_api()
        self.check_and_set_eeprom_bank_size()

    def get_xcvr_api(self):
        """
        Retrieves the XcvrApi associated with this cpo

        Returns:
            An object derived from XcvrApi that corresponds to the cpo
        """
        els_base_page = self.get_els_base_page()
        loc_bank = int(self._oe_bank_id % OE_BANK_NUM)
        oe_xcvr_eeprom = XcvrEeprom(self.read_eeprom, self.write_eeprom, BaillyMemMap(BaillyCodes, bank=loc_bank, base_page=els_base_page))
        self._xcvr_api = BaillyApi(oe_xcvr_eeprom)
        return self._xcvr_api
  
    def get_oe_eeprom_bank_size_path(self):
        cpo_bus = self.get_oes_config().get("oe_cmis_path", None)
        return cpo_bus + "max_bank_size" if cpo_bus is not None else None

    def get_eeprom_bank_size(self):
        try:
            bank_size_path = self.get_oe_eeprom_bank_size_path()
            with open(bank_size_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            return int(content)
        except Exception as e:
            return None
  
    def set_eeprom_bank_size(self, value):
        try:
            bank_size_path = self.get_oe_eeprom_bank_size_path()
            with open(bank_size_path, 'w', encoding='utf-8') as f:
                f.write(str(value))
            return True
        except Exception as e:
            return False

    def check_and_set_eeprom_bank_size(self):
        current_val = self.get_eeprom_bank_size()
        if current_val is None:
            return False

        api = self.get_xcvr_api()
        api_size = api.get_bank_size() 
        size_advt = api_size 
        if current_val == size_advt:
            return True
        else:
            return self.set_eeprom_bank_size(size_advt)

    def get_eeprom_path(self):
        return self.get_oe_eeprom_path()

```

#### 6.2.3. ChassisBase

According to the cpo.json configuration file, confirm the loaded CPO class or traditional optical module class

```
class Chassis(ChassisBase):
    def __init__(self):
        ChassisBase.__init__(self)
        self._ports_config = get_cpo_json_data().get("interfaces", None) 
        self._oes_config = get_cpo_json_data().get("oes", None)                   # oe_config from cpo.json
        if self.is_cpo_device():
            self._cpo_eeprom_mode = get_cpo_json_data().get("cpo_eeprom_mode", "joint")
            self._elss_config = get_cpo_json_data().get("elss", None)             # ELS from cpo.json
            self._init_port_mappings()

    def _init_port_mappings():
        self._sfp_list = []
        cpo_config = XcvrApiConfig(
            codes_cls=CmisCodes,
            mem_map_cls=BaillyMemMap,
            api_cls=BaillyApi
        )
        interfaces = self.get_all_ports_config()
        for eth_name, eth_info in interfaces.items():
            port_id = eth_info.get("index", 0).split(",")[0]
            oe_id = eth_info.get("oe_id", None)
            if oe_id != None:
                oe_bank_id= eth_info.get("oe_bank_id", None)
                els_id = eth_info.get("els_id", None)
                els_bank_id = eth_info.get("els_bank_id", None)
                self._sfp_list.append(CpoOptoeBase(port_id, oe_id, oe_bank_id, els_id, els_bank_id, cpo_config))
            else:
                self._sfp_list.append(SfpOptoeBase(port_id))
```

#### 6.2.4. CmisMemMap

The design idea is consistent with the overall design. Specific mapping: general registers adopt the CMIS5.2 standard, with added multi-bank processing; all other parts fully inherit the community CmisMap, as shown in BaillyMemMap below.

Broadcom Bailly CPO adds mappings for vendor-specific custom registers, such as pages 0xb0-0xb3, as shown in BaillyMemMap below. This code is located in the switch vendor directory and is not part of the platform code.

Platform common map:

```
PAGES_PER_BANK  = 256
class BaillyMemMap(CmisMemMap):
    def __init__(self, codes, bank=0, base_page=0):
        self._bank = bank
        self._base_page = base_page
        super(BaillyMemMap, self).__init__(codes)

        self.DIAG_BANK_SIZE = NumberRegField(bailly_consts.DIAG_BANK_SIZE_SUPPORT_ADVT_FIELD, self.getaddr(0x1, 142),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0 , 2)))
        # Define Bailly-specific fields in addition to the standard CMIS fields
        self.CPO_INFO = RegGroupField(bailly_consts.CPO_INFO_FIELD,
            CodeRegField(bailly_consts.CPO_IDENTIFIER, self.getaddr(0xb0, 128), self.codes.XCVR_IDENTIFIERS),
            NumberRegField(bailly_consts.CPO_REVISION, self.getaddr(0xb0, 129), format="B", size=1),
            NumberRegField(bailly_consts.LASER_GRID_AND_COUNT, self.getaddr(0xb0, 130), size=1, format="B"),
            CodeRegField(bailly_consts.LASER_WAVELENGTH_GRID, self.getaddr(0xb0, 130),
                self.codes.LASER_WAVELENGTH_GRID,
                RegBitField(bailly_consts.BIT4_FIELD, bitpos=4, ro=True)
            ),
            CodeRegField(bailly_consts.LASER_COUNT, self.getaddr(0xb0, 130),
                self.codes.LASER_COUNT,
                RegBitsField(bailly_consts.BITS0_3_FIELD, bitpos=0, size=4, ro=True)
            ),
        )

    def getaddr(self, page, offset, page_size=128):
        if 0xb0 <= page <= 0xb7:
            page = self._base_page + page
        if 0 <= page <= 0xf or 0xb0 <= page <= 0xb7:
            bank_id = 0
        else:
            bank_id = self._bank
        return (bank_id * PAGES_PER_BANK + page) * page_size + offset

```

#### 6.2.5. CmisApi

Inherit the original CmisApi implementation and add the specific related functions unique to Bailly.

```
class BaillyApi(CmisApi):
    def __init__(self, xcvr_eeprom):
        super(BaillyApi, self).__init__(xcvr_eeprom)
  
    def get_dpinit_pending(self):
        '''
        Bailly not supported, return fake value.
        '''
        dpinit_pending_dict = {}
        for lane in range(self.NUM_CHANNELS):
            key = "DPInitPending{}".format(lane + 1)
            dpinit_pending_dict[key] = True
        return dpinit_pending_dict
  
    def get_active_apsel_hostlane(self):
        '''
        Bailly not supported Deinit, if it is deinit return fake value.
        '''
        has_zero  = False
        current_map = {}
        for lane in range(self.NUM_CHANNELS):
            lane_key = 'ActiveAppSelLane{}'.format(lane + 1)
            app_lane = self.get_application(lane)
            current_map[lane_key] = app_lane
            if app_lane == 0:
                has_zero = True
  
        if has_zero:
            return current_map
        else:
            normal =  super().get_active_apsel_hostlane()
            return normal

    def _format_revision(self, revision):
        if revision is None:
            return None
        return "{}.{}".format((revision >> 4) & 0xf, revision & 0xf)

    def get_transceiver_info(self):
        info = super().get_transceiver_info()
        if info is None:
            return None

        els_info = self.get_els_info()
        cpo_info = els_info.get("cpo_info")
        vendor_info = els_info.get("vendor_info")
        laser_power_mode = els_info.get("laser_power_mode")
        if cpo_info is None and vendor_info is None and laser_power_mode is None:
            return info

        if cpo_info is not None:
            info.update({
                "els_identifier": cpo_info.get(bailly_consts.CPO_IDENTIFIER),
                "els_revision": self._format_revision(cpo_info.get(bailly_consts.CPO_REVISION)),
                "els_laser_grid_and_count": cpo_info.get(bailly_consts.LASER_GRID_AND_COUNT),
                "els_laser_wavelength_grid": cpo_info.get(bailly_consts.LASER_WAVELENGTH_GRID),
                "els_laser_count": cpo_info.get(bailly_consts.LASER_COUNT),
            })

        if vendor_info is not None:
            info.update({
                "els_vendor_name": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_NAME_ASCII_FIELD)
                ),
                "els_vendor_oui": vendor_info.get(bailly_consts.VENDOR_OUI_HEX_FIELD),
                "els_vendor_pn": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_PART_NUMBER_ASCII_FIELD)
                ),
                "els_vendor_rev": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_REVISION_ASCII_FIELD)
                ),
                "els_vendor_sn": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_SERIAL_NUMBER_ASCII_FIELD)
                ),
                "els_date_code": self._strip_str(
                    vendor_info.get(bailly_consts.DATE_CODE_FIELD)
                ),
                "els_max_power": vendor_info.get(bailly_consts.MAX_POWER_CONSUMPTION_FIELD),
            })

        if laser_power_mode is not None:
            info.update({
                "els_laser_power_mode_control": laser_power_mode.get(
                    bailly_consts.LASER_POWER_MODE_CONTROL_BITS_FIELD
                ),
            })

        return info

    def get_els_vendor_info(self):
        return self.xcvr_eeprom.read(bailly_consts.CPO_VENDOR_INFO_FIELD)

    def get_els_info(self):
        return {
            "cpo_info": self.xcvr_eeprom.read(bailly_consts.CPO_INFO_FIELD),
            "vendor_info": self.get_els_vendor_info(),
            "laser_power_mode": self.xcvr_eeprom.read(bailly_consts.LASER_POWER_MODE_CONTROL_FIELD),
        }

```

#### 6.2.6. CmisCodes

Add the unique parsing codes specific to Bailly

```
class BaillyCodes(CmisCodes):
    # Vendor specific implementation to be added here
    XCVR_IDENTIFIERS = {
        **CmisCodes.XCVR_IDENTIFIERS,
        128: 'CPO Bailly',
    }

    XCVR_IDENTIFIER_ABBRV = {
        **CmisCodes.XCVR_IDENTIFIER_ABBRV,
        128: 'QSFP-DD',
    }

    HOST_ELECTRICAL_INTERFACE = {
        **CmisCodes.HOST_ELECTRICAL_INTERFACE,
        253: 'Bailly-Reserverd-1',
        254: 'Bailly-Reserverd-2',
    }

    SM_MEDIA_INTERFACE = {
        **CmisCodes.SM_MEDIA_INTERFACE,
        193: 'Bailly-800G-2xFR4',
        253: 'Bailly-Reserverd-LC-1',
        254: 'Bailly-Reserverd-LC-2',
    }

    LASER_WAVELENGTH_GRID = {
        0: "CWDM4",
        1: "DR4",
    }

    LASER_COUNT = {
        code: code + 1 for code in range(16)
    }

    POWER_MODE = {
        0: "High power mode",
        1: "Low power mode",
    }

    INTERRUPT_STATUS = {
        0: "Interrupt event occurred",
        1: "Interrupt event cleared",
    }

    LASER_DISABLE_CONTROL = {
        0: "Enable",
        1: "Disable",
    }

    LASER_ACTIVE_STATUS = {
        0: "Inactive",
        1: "Active",
    }

    LASER_POWER_MODE_ENABLE = {
        0: "Disable",
        1: "Enable",
    }

    MAX_BANKS_SUPPORTED = {
        **CmisCodes.MAX_BANKS_SUPPORTED,
        3: 8,
    }
```

#### 6.2.7.XcvrApiFactory

Since the SfpOptoeBase class contains  self.remove_xcvr_api() and  self.get_xcvr_api(). When instantiating the CPO, one can directly get_xcvr_api and complete the instantiation of cmis memmap,cmis api and cmis codes, so the XcvrApiFactory class is no longer necessary.

#### 6.2.8. CmisManagerTask

The CMIS state machine of Broadcom Bailly CPO is consistent with that of regular optical modules, and no revision to the management process is required. ELS-related logic is modified through MCU linkage.

#### 6.2.11. Show interfaces transceiver

The design idea is consistent with the overall design. For details of the information that can be obtained through the Broadcom Bailly CPO CLI.

Here is an example:

```
root@sonic:/home/admin# show interfaces transceiver eeprom -d Ethernet505
Ethernet505: SFP EEPROM detected
        Active Firmware: N/A
        Active application selected code assigned to host lane 1: 6
        Active application selected code assigned to host lane 2: 6
        Active application selected code assigned to host lane 3: 6
        Active application selected code assigned to host lane 4: 6
        Active application selected code assigned to host lane 5: 6
        Active application selected code assigned to host lane 6: 6
        Active application selected code assigned to host lane 7: 6
        Active application selected code assigned to host lane 8: 6
        Application Advertisement: 400GAUI-4-L C2M (Annex 120G) - Host Assign (0x11) - 400G-FR4/400GBASE-FR4 (Cl 151) - Media Assign (0x11)
                                   200GAUI-4 C2M (Annex 120E) - Host Assign (0x11) - 200GBASE-FR4 (Cl 122) - Media Assign (0x11)
                                   Bailly-Reserverd-2 - Host Assign (0x11) - Bailly-Reserverd-LC-2 - Media Assign (0x11)
                                   CAUI-4 C2M (Annex 83E) with RS(528,514) FEC - Host Assign (0x11) - 100G CWDM4 MSA Spec - Media Assign (0x11)
                                   Bailly-Reserverd-1 - Host Assign (0x1) - Bailly-Reserverd-LC-1 - Media Assign (0x1)
                                   800GAUI-8 L C2M (Annex 120G) - Host Assign (0x1) - Bailly-800G-2xFR4 - Media Assign (0x1)
        CMIS Rev: 5.2
        Connector: LC
        Encoding: N/A
        Extended Identifier: Power Class 8 (20.0W Max)
        Extended RateSelect Compliance: N/A
        Host Lane Count: 8
        Identifier: CPO Bailly
        Inactive Firmware: N/A
        Length Cable Assembly(m): 0.0
        Media Interface Technology: Others
        Media Lane Count: 8
        Module Hardware Rev: 0.0
        Nominal Bit Rate(100Mbs): N/A
        Specification compliance: sm_media_interface
        Vendor Date Code(YYYY-MM-DD Lot): 2024-09-15
        Vendor Name: BROADCOM
        Vendor OUI: 38-ba-b0
        Vendor PN: BCM789096FBB0KLG
        Vendor Rev: A0
        Vendor SN: SB243500207
        els_date_code: 2024-03-19
        els_identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        els_laser_count: 8
        els_laser_grid_and_count: 7
        els_laser_power_mode_control: 0
        els_laser_wavelength_grid: CWDM4
        els_max_power: 12.0
        els_revision: 0.1
        els_vendor_name: BROADCOM
        els_vendor_oui: ec-01-e2
        els_vendor_pn: ARLM-96F8DMZ
        els_vendor_rev: A0
        els_vendor_sn: FD2412VG004
        is_replaceable: False
        type_abbrv_name: QSFP-DD
        vdm_supported: False
        ChannelMonitorValues:
                RX1Power: 2.279dBm
                RX2Power: 2.03dBm
                RX3Power: 2.627dBm
                RX4Power: 2.653dBm
                RX5Power: 0.658dBm
                RX6Power: 0.297dBm
                RX7Power: 0.775dBm
                RX8Power: 1.222dBm
                TX1Bias: 68.116mA
                TX1Power: 1.791dBm
                TX2Bias: 57.676mA
                TX2Power: 1.836dBm
                TX3Bias: 63.76mA
                TX3Power: 1.86dBm
                TX4Bias: 59.836mA
                TX4Power: 1.918dBm
                TX5Bias: 68.116mA
                TX5Power: 1.934dBm
                TX6Bias: 57.676mA
                TX6Power: 1.92dBm
                TX7Bias: 63.76mA
                TX7Power: 1.827dBm
                TX8Bias: 59.836mA
                TX8Power: 1.955dBm
        ChannelThresholdValues:
                RxPowerHighAlarm  : 6.0dBm
                RxPowerHighWarning: 4.003dBm
                RxPowerLowAlarm   : -11.203dBm
                RxPowerLowWarning : -8.202dBm
                TxBiasHighAlarm   : 137.5mA
                TxBiasHighWarning : 132.5mA
                TxBiasLowAlarm    : 5.0mA
                TxBiasLowWarning  : 7.5mA
                TxPowerHighAlarm  : 6.0dBm
                TxPowerHighWarning: 4.0dBm
                TxPowerLowAlarm   : -7.201dBm
                TxPowerLowWarning : -4.201dBm
        ModuleMonitorValues:
                Temperature: 81.312C
                Vcc: 3.292Volts
        ModuleThresholdValues:
                TempHighAlarm  : 90.0C
                TempHighWarning: 85.0C
                TempLowAlarm   : 15.0C
                TempLowWarning : 20.0C
                VccHighAlarm   : 3.465Volts
                VccHighWarning : 3.399Volts
                VccLowAlarm    : 3.135Volts
                VccLowWarning  : 3.201Volts
```

#### 6.2.12. optoe driver

Consistent with the overall design, the following multi-bank solution is still used:

> https://github.com/sonic-net/sonic-linux-kernel/pull/473

### 6.3. Implementation Flow

#### 6.3.1. Chassis Init Flow

Consistent with the overall design. Bailly CPO initializes BaillyApi and BaillyMemMap in joint mode.

![1776331863073](image/Bailly-CPO-support-in-SONiC/1776331863073.png)

#### 6.3.2. Module Presence Flow

Consistent with the overall design. For details, refer to the overall design document.

#### 6.3.3.  API Call Flow

Consistent with the original community framework, only the class names are changed.

#### 6.3.4.  CmisManagerTask State Machine

No revision is required.

### 6.4. Unit Test cases

1. Function tests for each function of the newly added `CpoOptoeBase` class
2. Function tests for each function of the newly added `BaillyApi` class
3. Function tests corresponding to the newly added `BaillyMemMap` class

### 6.5. Open/Action items - if any

1. This design has provided a basic OE/ELS access framework; OE/ELS firmware upgrade will be reflected in subsequent HLD documents.
