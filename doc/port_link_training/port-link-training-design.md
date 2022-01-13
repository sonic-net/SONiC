# SONiC Port Link Training Design #

## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Abbreviations](#abbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
- [SAI API Requirement](#sai-api-requirement)
- [Configuration and management ](#configuration-and-management)
  - [CLI Enhancements](#cli-enhancements)
    - [Config link training mode](#config-link-training-mode)
    - [Show link training status](#show-link-training-status)
  - [Config DB Enhancements](#config-db-enhancements)
  - [Application DB Enhancements](#application-db-enhancements)
  - [YANG Model Enhancements](#yang-model-enhancements)
  - [DB Migration Considerations](#db-migration-considerations)
  - [SWSS Enhancements](#swss-enhancements)
  - [PMON xcvrd Considerations](#pmon-xcvrd-considerations)
- [Warmboot Design Impact](#warmboot-design-impact)
- [Limitations](#limitations)
- [Testing Requirements](#testing-requirements)
  - [Unit Test cases](#unit-test-cases)
  - [System Test cases](#system-test-cases)
- [Action items](#action-items)

### Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             | Dante (Kuo-Jung) Su| Initial version                   |

### Scope
This document is the design document for port link training feature on SONiC. This includes the requirements, DB schema change, DB migrator change, yang model change and swss change.

### Abbreviations

 | Term    |     Meaning                             |
 |:-------:|:----------------------------------------|
 | ASIC    | Application-Specific Integrated Circuit |
 | BER     | Bit Error Rate                          |
 | FIR     | Finite Impulse Response                 |
 | SFP     | Small Form-factor Pluggable transceiver |

### Overview

Link training is a process by which the transmitter and receiver on a high-speed serial link communicate with each other in order to tune their equalization settings. In theory, link training enables automatic tuning of the FIR filter for each channel in an ASIC to achieve the desired bit error rate (BER)

In current SONiC implementation, user can leverage the platform-specific [media_settings.json](https://github.com/Azure/SONiC/blob/master/doc/media-settings/Media-based-Port-settings.md) to statically update the TX FIR per attached transceiver to improve BER. However, the ODM vendors rarely provide the pre-calibrated pre-emphasis for the CR/KR transceivers, which could result in the link reliability issues.

The IEEE 802.3 standard defines a set of link training protocols for various mediums, and the feature in this document is to focus on IEEE clause 72 and 93 to dynamically improve the link quality over the SFP coppers/backplanes.

This feature could be activated with or without port auto negotiation.

### Requirements

The main goal of this document is to discuss the design of following requirement:

- Allow user to configure link training
- Allow user to get the operational link training status

### Architecture Design

This feature does not change the existing SONiC architecture, while it has to change the configuration flow for port link training which will be covered in orchagent.

### High-Level Design

- SAI API requirements is covered in section [SAI API Requirement](#sai-api-requirement).
- A few new CLI commands will be added to sonic-utilities sub module. These CLI commands support user to configure link training mode as well as show port link training status. See detail description in section [CLI Enhancements](#cli-enhancements).
- A few new fields will be added to existing table in APPL_DB and CONFIG_DB to support link training attributes. See detail description in section [Config DB Enhancements](#config-db-enhancements) and [Application DB Enhancements](#application-db-enhancements).
- YANG Model needs update according to the DB schema change. See detail description in section [YANG Model Enhancements](#yang-model-enhancements)
- PMON xcvrd needs to update transceiver capability to APPL_DB to provide a hint to swss#orchagent for the advanced port link training controls. See detail description in section [PMON xcvrd Considerations](#pmon-xcvrd-considerations)
- Port configuration setting flow will be changed in orchagent of sonic-swss. See detail description in section [SWSS Enhancements](#swss-enhancements).

### SAI API Requirement

Currently, SAI already defines all the necessary port attributes to support port link training.

```cpp
    /**
     * @brief Enable/Disable Port Link Training
     *
     * @type bool
     * @flags CREATE_AND_SET
     * @default false
     */
    SAI_PORT_ATTR_LINK_TRAINING_ENABLE,

    /**
     * @brief Link training failure status and error codes
     *
     * @type sai_port_link_training_failure_status_t
     * @flags READ_ONLY
     */
    SAI_PORT_ATTR_LINK_TRAINING_FAILURE_STATUS,

    /**
     * @brief Status whether the receiver trained or not trained to receive data
     *
     * @type sai_port_link_training_rx_status_t
     * @flags READ_ONLY
     */
    SAI_PORT_ATTR_LINK_TRAINING_RX_STATUS,
```

Vendor-specific SAI implementation is not in the scope of this document, but there are some common requirements for SAI:

1. SAI implementation must return error code if any of the above attributes is not supported, swss and syncd must not crash.
2. SAI implementation must keep port link training disabled by default for backward compatible. As long as swss and SAI keep backward compatible, user need not change anything after this feature is implemented and available in SONiC.

### Configuration and management 

#### CLI Enhancements

A few new CLI commands are designed to support port link training.

##### Config link training mode

```
Format:
  config interface link-training <interface_name> <mode>

Arguments:
  interface_name: name of the interface to be configured. e.g: Ethernet0
  mode: link training mode, can be either "auto", "on" or "off"

Example:
  config interface link-training Ethernet0 auto
  config interface link-training Ethernet0 off

Return:
  error message if interface_name or mode is invalid otherwise empty
```

##### Show link training status

A new CLI command will be added to display the port link training status. All data of this command are fetched from **APPL_DB**.

```
Format:
  show interfaces link-training status <interface_name>

Arguments:
  interface_name: optional. Name of the interface to be shown. e.g: Ethernet0. If interface_name is not given, this command shows link training status for all interfaces.

Example:
  show interfaces link-training status
  show interfaces link-training status Ethernet0

Return:
  error message if interface_name is invalid otherwise:

admin@sonic:~$ show interfaces link-training status
  Interface    LT Oper    LT Admin    LT Failure    LT RxStatus    Oper    Admin
-----------  ---------  ----------  ------------  -------------  ------  -------
  Ethernet0         on          on          none        trained      up       up
  Ethernet8        off         off             -              -    down       up
 Ethernet16         on        auto          none        trained      up       up
 Ethernet24        off           -             -              -    down       up
 Ethernet32        off           -             -              -    down       up
```


#### Config DB Enhancements  

A new field **link_training** will be added to **PORT** table:

	; Defines information for port configuration
	key                     = PORT|port_name     ; configuration of the port
	; field                 = value
	...
	link_training           = STRING             ; link training configuration

Valid value of the new fields are described below:

- link_training:  
String value, the administratively specified port link training configuration.
When "link_training" is not specified, the port link training should be disabled  

 | Mode |     Description                                                 |
 |:----:|:---------------------------------------------------------------:|
 | auto | Enable link-training if applicable to the transceiver attached  |
 | on   | Enable link-training regardless of the transceiver type         |
 | off  | Disable link-training                                           |

For deployment considerations, users are encouraged to use only **auto** and **off** for the **link_training**, while the **on** mode is for test purpose, it should only be activated when the transceiver is not correctly identified by the pmon#xcvrd, and forcing link-training enabled is intended.

#### Application DB Enhancements

The following fields will be introduced into **PORT_TABLE** table:

	; Defines information for port configuration
	key                     = PORT_TABLE:port_name ; configuration of the port
	; field                 = value
	...
	link_training           = STRING               ; operational link training config
	link_training_status    = STRING               ; operational link training status
	link_training_failure   = STRING               ; operational link training failure status
	link_training_rxstatus  = STRING               ; operational link training rx status
	xcvr_capabilities       = STRING               ; transceiver capabilities

- link_training:  
String value, the admin port link training config.
- link_training_status:  
String value, the operational port link training status. "on" indicates port link training is enabled, otherwise disabled.
- link_training_failure:  
String value, the operational port link training failure status. "none" indicates no error is detected, otherwise any of the link training failure status defined in SAI. For example: "none", "lock", "snr" and "timeout".
- link_training_rxstatus:  
String value, the operational port link training rx status. any of the link training rx status defined in SAI. For example: "trained", "not-trained".
- xcvr_capabilities:
String value, the transceiver capabilities provided by pmon#xcvrd, it's a set of capabilities separated by comma, where "LT" stands for "link training". See detail description in section [PMON xcvrd Considerations](#pmon-xcvrd-considerations)

To minimize system overhead, instead of periodically fetching the operational link training status, the corresponding fields in the APPL_DB will only be updated in the following events

- Per-Port link status changes  
In this case, only the **link_training_status** will be updated.

- Explicitly link training status refresh requests via the notification model.  
In this case, the **link_training_failure** and **link_training_rxstatus** of the selected port will be refreshed. See detail description in section [Link Training Status Refresh](#link-training-status-refresh)

Here is the table to map the fields and SAI attributes:  

| **Parameter**          | **sai_port_attr_t**
|:-----------------------|:-------------------------------------------|
| link_training          | SAI_PORT_ATTR_LINK_TRAINING_ENABLE         |
| link_training_failure  | SAI_PORT_ATTR_LINK_TRAINING_FAILURE_STATUS |
| link_training_rxstatus | SAI_PORT_ATTR_LINK_TRAINING_RX_STATUS      |

Please note the operational port link training status in the APPL_DB could be different from the administratively configured link training configuration in the CONFIG_DB due to the hardware limitations or vendor-specific SAI software implementations. For example, port link training is only applicable to the ports with speed >= 10G, and it's not applicable for chip-to-module transceivers.

#### YANG Model Enhancements

The port yang model needs to update according to DB schema change. The yang model changes of new fields are described below:

```
leaf link_training {
  type string {
    pattern "auto|on|off";
  }
}
```

These new yang leaf will be added to sonic-port.yang.

#### DB Migration Considerations

By having port link training disabled if "link_training" is not specified in the CONFIG_DB, this feature is fully backward compatible.

#### SWSS Enhancements

##### Port Configuration Flow

The current SONiC port configuration flow in PortsOrch can be described in following pseudo code:

```
port = getPort(alias)
if autoneg changed:
    setPortAutoNeg(port, autoneg)
```

The new SONiC port configuration flow can be described in following pseudo code:

```
port = getPort(alias)
if autoneg changed:
    setPortAutoNeg(port, autoneg)

if link_training changed and xcvr_capabilities has LT:
    setPortLinkTraining(port, link_training)
```

##### Link Training Status Refresh

To refresh the operational link training status in APPL_DB, a new notification handler will be introduced to PortsOrch, the pseudo code is as follow:

```
portCtrlConsumer = NotificationConsumer("PORT_CTRL")
if portCtrlConsumer received 'op=port_status_refresh', 'data=EthernetXY' and 'type=link_training':
    refreshPortLinkTrainingStatus(EthernetXY)
```

An example code snippet of initiating status refresh is as follow:

```
appl_db = daemon_base.db_connect("APPL_DB")
port_np = swsscommon.NotificationProducer(appl_db, "PORT_CTRL")

fvp = swsscommon.FieldValuePairs([
    ('type', 'link_training')
])
port_np.send('port_state_refresh', port, fvp)
```

#### PMON xcvrd Considerations

Given that port link training shall not be enabled on certain transceivers. For example, a chip-to-module transceiver. It's better to have pmon#xcvrd provide a hint to the swss#orchagent for the advanced link training controls. Hence, **xcvr_capabilities** is introduced into APPL_DB.  

When **link_training=auto**, swss#orchagent should request syncd to enable port link training only if **LT** is specified in **xcvr_capabilities**.

### Warmboot Design Impact

SAI and lower layer must not flap port during warmboot no matter what link training parameter is given.

### Limitations

N/A

### Testing Requirements

#### Unit Test cases

For **sonic-platform-daemons**, we will leverage the existing [test_xcvrd.py](https://github.com/Azure/sonic-platform-daemons/blob/master/sonic-xcvrd/tests/test_xcvrd.py) for this. A few new test cases will be added:

1. Test attribute xcvr_capabilities on both SFP insertion and removal scenario. Verify xcvr_capabilities is added/dropped from APPL_DB and has correct value.
2. Test attribute xcvr_capabilities for a QSFP/QSFP-DD DAC transceiver. Verify xcvr_capabilities is in APPL_DB and with "LT".
3. Test attribute xcvr_capabilities for a QSFP/QSFP-DD DR transceiver. Verify xcvr_capabilities is in APPL_DB and without "LT".

For **sonic-swss**, we will leverage the existing [test_port.py](https://github.com/Azure/sonic-swss/blob/master/tests/test_port.py) for this. A few new test cases will be added:

1. Test attribute **link_training** on both direct and warm-reboot scenario. Verify SAI_PORT_ATTR_LINK_TRAINING_ENABLE, SAI_PORT_ATTR_LINK_TRAINING_FAILURE_STATUS and SAI_PORT_ATTR_LINK_TRAINING_RX_STATUS are in ASIC_DB and has correct value.

For **sonic-utilities**, we will leverage the existing [unit test framework](https://github.com/Azure/sonic-utilities/tree/master/tests) for this. A few new test cases will be added:

1. Test command `config interface link-training <interface_name> <mode>`. Verify the command return error if given invalid interface_name or mode.

#### System Test cases

Will leverage sonic-mgmt to test this feature.

### Action items

TBD

