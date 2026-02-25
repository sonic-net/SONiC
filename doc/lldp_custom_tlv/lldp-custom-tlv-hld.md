# SONiC LLDP Custom TLV

## Table of Content

1. [Revision](#revision)
2. [Scope](#scope)
3. [Definitions/Abbreviations](#definitionsabbreviations)
4. [Overview](#overview)
5. [Requirements](#requirements)
6. [Architecture Design](#architecture-design)
7. [High-Level Design](#high-level-design)
8. [SAI API](#sai-api)
9. [Configuration and management](#configuration-and-management)
10. [Testing Requirements](#testing-requirements)


## Revision

| Rev |    Date    |       Author        | Change Description |
|:---:|:----------:|:-------------------:|--------------------|
| 0.1 | 11/06/2025 | Shivashankar C R    | Initial version    |
|     |            | Praveen HM          |                    |
|     |            | Ashutosh Agarwal    |                    |
|     |            | Venkata Rajesh Etla |                    |

## Scope

This document provides a high-level design for LLDP Custom TLV feature in SONiC. The feature allows either users to configure custom TLVs that they want to be advertised or another feature in SONiC which needs to use custom TLVs for communicating with the neighbouring devices.

## Definitions/Abbreviations

| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| LLDP                     | Link Layer Discovery Protocol       |
| TLV                      | Type-Length-Value                   |
| OUI                      | Organizationally Unique Identifier  |
| LLDPD                    | LLDP daemon                         |
| ConfigDB                 | Configuration Database              |
| StateDB                  | State Database                      |

## Overview

Link Layer Discovery Protocol (LLDP) is a vendor-neutral Layer 2 protocol that allows network devices to advertise information about themselves to other devices on the network. While LLDP defines standard TLVs for common information exchange, there are scenarios where custom TLVs are needed to transmit vendor-specific or application-specific information.

Adding support for a new LLDP TLV normally would require making code changes to the lldpd daemon to provide configuration commands and interpret TLV contents while processing packets. To avoid making code changes, lldpd provides support for configuring custom TLVs where the data can be given as input by the user. This information is then used by lldpd daemon to include the custom TLV in the LLDP PDUs transmitted. 

The LLDP Custom TLV feature in SONiC provides the capability to:
- Configure custom TLV elements with user-specified content
- Associate custom TLVs with specific network interfaces/ports
- Manage custom TLV configurations through standard SONiC interfaces
- Support other feature daemons requesting LLDP for custom TLV exchange with peers
- Persistent configuration that survives docker restart and system reboot


## Requirements

### Functional Requirements

* **R0** : **Custom TLV Definition**: Users must be able to define custom TLV with elements:
   - Custom TLV name 
   - Organizationally Unique Identifier (OUI) value
   - Subtype value
   - OUI information as comma-separated hex bytes

* **R1** : **Global Association**: Users must be able to:
   - Associate one or more custom TLVs at global level which will be applied to all interfaces
   - Remove individual TLV associations while preserving others at global level

* **R2** : **Interface Association**: Users must be able to:
   - Associate one or more custom TLVs with specific interfaces
   - Support single interface or range of interfaces
   - Remove individual TLV associations while preserving others

* **R3** : **Operational Commands**: Provide CLI commands to:
   - Display all custom TLV definitions with detailed information
   - Show specific custom TLV configuration by name
   - Display TLVs associated globally
   - Display TLVs associated per interface

* **R4** : **Feature Daemon Integration Requirements**

    For SONiC features that need to communicate with peer devices using LLDP custom TLVs, the following requirements must be supported:

    a. **Dynamic TLV Transmission Request**: Feature daemons must be able to:
      - Request transmission of custom TLVs on specific interfaces through StateDB
      - Specify OUI, subtype, and OUI info data dynamically
      - Update TLV content in real-time based on operational state changes
      - Remove TLV transmission requests when no longer needed

    b. **TLV Reception and Notification**: Feature daemons must be able to:
      - Receive notifications when custom TLVs are received from peer devices
      - Access received TLV content through StateDB subscription
      - Parse and process TLV information for protocol-specific logic
      - Handle TLV content changes from peer devices

    c. **Coexistence of multiple TLVs**: The system must ensure:
      - Multiple feature daemons can use custom TLVs simultaneously
      - TLVs from different features don't interfere with each other
      - User-configured TLVs and feature daemon TLVs coexist properly

**Note** : **Warm Boot Requirements**
    Currently in SONiC there is no special handling being made for LLDP with respect to warm reboot, as there is no impact to data traffic. Hence there are no sepcific requirements for custom TLV feature for warm reboot.

### Example Use Cases

#### 1. Switch-to-NIC Handshake for Device-Specific Capability Enablement
Implements a handshake mechanism between the switch and NIC using custom TLVs to dynamically negotiate and activate device-specific capabilities, thereby optimizing hardware interoperability and performance.

#### 2. BGP Auto-Peering Using LLDP
Automatically form BGP sessions between directly connected devices that support auto-peering.

Reference link:
https://datatracker.ietf.org/doc/html/draft-acee-idr-lldp-peer-discovery-19

#### 3. Port-to-Device Mapping (Console Port Metadata)
**Description**:
Terminal servers can use custom TLVs to advertise real-time mappings between physical console ports and connected network devices.

**Initial TLV**:
Declares static port-to-device relationships (e.g., Port 1 → Router1, Port 2 → Switch3).
   
**Dynamic Updates**:
TLVs are updated automatically when devices are swapped or reconnected (e.g., Switch3 replaced by Switch7).

Eliminates the need for manual tracking of device-to-port assignments. Enables orchestration systems and NOC operators to instantly identify which network device is attached to each console port.

#### 4. Out-of-Band (OOB) Management Role Advertisement
**Description**:
Custom TLVs can advertise the management role of the terminal server within the OOB network topology.

**Initial TLV**:
Declares whether the terminal server is acting as a primary OOB path or a backup.

**Dynamic Updates**:
Automatically reflects changes in failover status (e.g., backup becomes active).

Facilitates intelligent decision-making in orchestration platforms by signaling which terminal servers are actively responsible for OOB access.

#### 5. Security and Access Policy Enforcement
**Description**:
Terminal servers can broadcast security policy-related metadata via TLVs.

**Initial TLV**:
Device whitelists for authorized console connections (e.g., based on serial number, MAC address).

**Dynamic Updates**:
Triggered when unauthorized or unknown devices are connected.

Acts as a preventative control against unauthorized physical access. Helps detect rogue or spoofed devices connected to console ports.


## Architecture Design

The LLDP Custom TLV architecture supports both user-configured TLVs and dynamic feature daemon interactions. The design includes multiple data flows and database interactions to handle different use cases.

### Architecture Flow Diagram

The following diagram illustrates the complete architecture including user configuration paths, feature daemon integration, and bidirectional TLV communication:

<div align="left"> <img src=images/lldp_architecture.png width=1100 /> </div>


### Key Architecture Components

1. The LLDP Manager (lldpmgrd) is responsible for handling all the user configurations from CONFIG DB and custom TLV updates by other features from STATE DB. lldpmgrd interacts with lldpd via lldpcli for updating the configurations to lldpd.
2. LLDPD handles all the custom TLV configurations made via lldpcli and takes care of including the custom TLVs in the transmitted packets
3. LLDP Sync Daemon (lldp_syncd) retrieves the operational data from lldpd and updates into APP DB and STATE DB. The custom TLV information received in LLDP packets are updated into STATE DB, allowing other features to get the custom TLV information by subscribing to the STATE DB tables.


## High-Level Design

### Database Schema

### Config DB Schema

#### LLDP_CUSTOM_TLV Table

This table stores the definitions of custom TLVs.

```json
{
  "LLDP_CUSTOM_TLV": {
    "TLV_NAME": {
      "oui": "STRING (3 bytes of comma-separated value in hex format)",
      "subtype": "STRING (1 byte value in hex format)",
      "oui_info": "STRING (comma-separated byte values in hex format)"
    }
  }
}
```

**Example:**
```json
{
  "LLDP_CUSTOM_TLV": {
    "vendor1-tlv": {
      "oui": "00,20,2c",
      "subtype": "1",
      "oui_info": "12,46,5c,04,9a,4d,01,01,28,b1,87,1c"
    },
    "vendor2-tlv": {
      "oui": "00,12,34",
      "subtype": "2",
      "oui_info": "48,65,6c,6c,6f,20,57,6f,72,6c,64"
    }
  }
}
```

#### LLDP GLOBAL Table

This table stores the LLDP global level configuration including the custom TLVs that are applied at global level.

```json
{
  "LLDP": {
      "GLOBAL": {
        "custom_tlv_name": "STRING (comma-separated list)"
    }
  }
}
```

**Example:**
```json
{
  "LLDP": {
      "GLOBAL": {
        "custom_tlv_name": "vendor1-tlv,vendor2-tlv"
    }
  }
}
```

#### LLDP_PORT Table

Extended to include custom TLV associations.

```json
{
  "LLDP_PORT": {
    "INTERFACE_NAME": {
      "admin_status": "STRING",
      "custom_tlv_name": "STRING (comma-separated list)"
    }
  }
}
```

**Example:**
```json
{
  "LLDP_PORT": {
    "Ethernet0": {
      "admin_status": "enabled",
      "custom_tlv_name": "vendor1-tlv,vendor2-tlv"
    },
    "Ethernet4": {
      "admin_status": "enabled", 
      "custom_tlv_name": "vendor1-tlv"
    },
    "Ethernet8": {
      "admin_status": "enabled",
      "custom_tlv_name": "vendor2-tlv"
    }
  }
}
```
**Note** : Global and port-level configurations are mutually exclusive but can coexist; interface-level configurations do not override global settings.


### State DB Schema

#### LLDP_RX_CUSTOM_TLV Table

This table is used by LLDP to notify other feature daemons that are interested in receiving custom TLVs from peer devices.

```json
{
  "LLDP_RX_CUSTOM_TLV": {
    "INTERFACE_NAME": {
      "oui-value|subtype": {
        "oui_info": "STRING (comma-separated byte values in hex format)"
      }
    }
  }
}
```

**Example:**
```json
{
  "LLDP_RX_CUSTOM_TLV": {
    "Ethernet0": {
      "00,20,2c|1": {
        "oui_info": "12,46,5c,04,9a,4d,01,01,28,b1,87,1c"
      },
      "00,12,34|2": {
        "oui_info": "48,65,6c,6c,6f,20,57,6f,72,6c,64"
      }
    }
  }
}
```

#### LLDP_TX_CUSTOM_TLV Table

This table is used by feature daemons to notify LLDP about custom TLVs that need to be transmitted.

```json
{
  "LLDP_TX_CUSTOM_TLV": {
    "INTERFACE_NAME": {
      "oui-value|subtype": {
        "oui_info": "STRING (comma-separated byte values in hex format)"
      }
    }
  }
}
```

**Example:**
```json
{
  "LLDP_TX_CUSTOM_TLV": {
    "Ethernet0": {
      "00,1a,2b|10": {
        "oui_info": "52,61,63,6b,3a,31,30,2c,52,6f,77,3a,41"
      }
    }
  }
}
```

### Component Design

#### LLDP Manager

The LLDP Manager (lldpmgrd) is responsible for:

1. **Configuration Management**:
   - Subscribe to LLDP_CUSTOM_TLV table notifications in ConfigDB
   - Subscribe to LLDP_GLOBAL table notifications in ConfigDB
   - Subscribe to LLDP_PORT table notifications in ConfigDB
   - Subscribe to LLDP_TX_CUSTOM_TLV table notifications in StateDB (for feature daemon requests)
   - Load existing custom TLV configurations and port associations on startup
   - Maintain local cache of custom TLV definitions and port mappings

2. **Event Processing**:
   - **Custom TLV Events**: Process SET/DEL operations on LLDP_CUSTOM_TLV table
     - On SET: Update local cache and apply to all associated ports
     - On DEL: Remove from cache
   - **Global Association Events**: Process SET/DEL operations on LLDP_GLOBAL table
     - Parse comma-separated custom_tlv_name field
     - Apply TLVs at global level
   - **Port Association Events**: Process SET/DEL operations on LLDP_PORT table
     - Parse comma-separated custom_tlv_name field
     - Apply TLVs to the interface/port
   - **Feature Daemon Events**: Process SET/DEL operations on LLDP_TX_CUSTOM_TLV table
     - On SET: Apply feature-requested TLVs on the specified interfaces
     - On DEL: Remove feature-requested TLVs from interface

3. **LLDPCLI Integration**:
   - Execute lldpcli commands to configure custom TLVs on interfaces
   - Commands used:
     ```bash
     lldpcli configure lldp custom-tlv add/replace oui <oui> subtype <subtype> oui-info <info>
     lldpcli unconfigure lldp custom-tlv oui <oui> subtype <subtype>
     lldpcli configure ports <port> lldp custom-tlv add/replace oui <oui> subtype <subtype> oui-info <info>
     lldpcli unconfigure ports <port> lldp custom-tlv oui <oui> subtype <subtype>
     ```


#### LLDPD Integration

LLDPD integrates with the LLDP Manager through lldpcli interface:
   - LLDP Manager communicates with lldpd through lldpcli commands
   - Immediate application of custom TLV changes globally or to the respective interfaces
   - Include configured custom TLVs in transmitted LLDP packets


#### LLDP Sync Daemon (lldp_syncd)
   - Retreive the operational data from lldpd using the lldpcli commands
   - Extract custom TLVs from the operational data and update State DB (LLDP_RX_CUSTOM_TLV table) for feature daemon consumption
   - Existing operational data sync happens every 10 seconds, while the LLDP custom TLV information will be synced every 1 second to ensure the feature daemon gets the updates quickly
   

### Configuration Flow

#### LLDP global level user configuration flow
<div align="left"> <img src=images/lldp_global_config.png width=600 /> </div>

This is the basic use case where users configure custom TLVs globally. 

**Flow:**
1. User configures custom TLV via CLI
2. User associates custom TLV at LLDP global level
3. Configuration stored in ConfigDB (LLDP_CUSTOM_TLV and LLDP_GLOBAL tables)
4. LLDP Manager receives configuration events
5. LLDP Manager applies configuration to lldpd via lldpcli commands
6. lldpd transmits custom TLVs in LLDP packets


#### LLDP port level user configuration flow
<div align="left"> <img src=images/lldp_config.png width=600 /> </div>

This is the basic use case where users configure custom TLVs to be transmitted from specific interfaces. 

**Flow:**
1. User configures custom TLV via CLI
2. User associates custom TLV with interfaces
3. Configuration stored in ConfigDB (LLDP_CUSTOM_TLV and LLDP_PORT tables)
4. LLDP Manager receives configuration events
5. LLDP Manager applies configuration to lldpd via lldpcli commands
6. lldpd transmits custom TLVs in LLDP packets


#### Feature Daemon Request Flow

This use case supports scenarios where feature daemons need to exchange information with peer devices via LLDP TLVs. The TLV contents might change based on negotiations with peer devices or operational state changes.

**Transmit Flow (Feature → LLDP):**

<div align="left"> <img src=images/lldp_feature_daemon.png width=600 /> </div>

1. Feature daemon determines need for custom TLV transmission
2. Feature daemon updates StateDB (LLDP_TX_CUSTOM_TLV table)
3. LLDP Manager monitors StateDB for custom TLV requests
4. LLDP Manager configures lldpd with requested TLVs
5. lldpd transmits feature-requested TLVs in LLDP packets

**Alternative:** Feature daemon can directly listen for LLDP packets and process TLVs of interest.

**Receive Flow (LLDP → Feature):**

<div align="left"> <img src=images/lldp_rx_tlv.png width=600 /> </div>

1. Peer device sends LLDP packet with custom TLVs
2. lldpd receives and processes LLDP packet
3. LLDP sync daemon (lldp_syncd) updates StateDB (LLDP_RX_CUSTOM_TLV table)
4. Feature daemon monitors StateDB for received custom TLVs
5. Feature daemon processes received TLV information



### CLI Commands 

#### Configuration Commands

```bash
# Define custom TLV 
config lldp custom-tlv add <tlv-name> oui <oui-value> subtype <sub-type-value> oui-info <oui-info-value>

# Remove custom TLV 
config lldp custom-tlv remove <tlv-name>

# Associate custom TLV at global level
config lldp custom-tlv apply-global <tlv-name> 

# Remove custom TLV from global level
config lldp custom-tlv remove-global <tlv-name> 

# Associate custom TLV with interface
config interface lldp custom-tlv add <interface> <tlv-name>

# Remove custom TLV association from interface  
config interface lldp custom-tlv remove <interface> <tlv-name>

```

#### Show Commands

```bash
# Show all custom TLV definitions
show lldp custom-tlv

# Show specific custom TLV definition
show lldp custom-tlv <tlv-name>

# Show custom TLV associated at global level
show lldp custom-tlv --global-status

# Show custom TLV associations per interface
show interfaces lldp custom-tlv
```

#### Configuration Examples

##### Example 1: Basic Custom TLV Configuration

```bash
# Create a Vendor1 custom TLV 
admin@sonic:~$ config lldp custom-tlv add vendor1-tlv oui 00,20,2C subtype 1 oui-info 12,46,5C,04,9A,4D,01,01,28,B1,87,1C


# Create a vendor2 custom TLV 
admin@sonic:~$ config lldp custom-tlv add vendor2-tlv oui 00,12,34 subtype 2 oui-info 48,65,6c,6c,6f,20,57,6f,72,6c,64

# Associate custom TLVs globally
admin@sonic:~$ config interface lldp custom-tlv apply-global vendor3-tlv

# Associate custom TLVs with interfaces
admin@sonic:~$ config interface lldp custom-tlv add Ethernet0 vendor1-tlv
admin@sonic:~$ config interface lldp custom-tlv add Ethernet0 vendor2-tlv
admin@sonic:~$ config interface lldp custom-tlv add Ethernet4 vendor2-tlv
admin@sonic:~$ config interface lldp custom-tlv add Ethernet8 vendor1-tlv
```

##### Example 2: Interface Range Configuration

```bash
# Associate custom TLV with multiple interfaces
admin@sonic:~$ config interface lldp custom-tlv add Ethernet12-24 vendor2-tlv
```

##### Example 3: Removing Configurations

```bash
# Remove custom TLV association globally
admin@sonic:~$ config interface lldp custom-tlv remove-global vendor3-tlv

# Remove custom TLV association from specific interface
admin@sonic:~$ config interface lldp custom-tlv remove Ethernet0 vendor1-tlv

# Remove custom TLV definition 
admin@sonic:~$ config lldp custom-tlv remove vendor1-tlv

```

#### Show Command Examples

##### Example 1: Show All Custom TLVs

```bash
admin@sonic:~$ show lldp custom-tlv

LLDP Custom TLV: vendor1-tlv
==========================
  OUI               : 00,20,2c
  Subtype           : 1
  OUI Info          : 12,46,5c,04,9a,4d,01,01,28,b1,87,1c


LLDP Custom TLV: vendor2-tlv
===========================
  OUI               : 00,12,34
  Subtype           : 2
  OUI Info          : 48,65,6c,6c,6f,20,57,6f,72,6c,64

```

##### Example 2: Show Specific Custom TLV 

```bash
admin@sonic:~$ show lldp custom-tlv vendor1-tlv

LLDP Custom TLV: vendor1-tlv
==========================
  OUI               : 00,20,2c
  Subtype           : 1
  OUI Info          : 12,46,5c,04,9a,4d,01,01,28,b1,87,1c

```

##### Example 3: Show global level Custom TLV Associations

```bash
admin@sonic:~$ show lldp custom-tlv --global-status
Global custom TLVs : vendor3-tlv, vendor4-tlv  

```

##### Example 4: Show Interface Custom TLV Associations

```bash
admin@sonic:~$ show interfaces lldp custom-tlv
Port       Name                      
---------  ----------------------    
Ethernet0  vendor1-tlv, vendor2-tlv  
Ethernet4  vendor2-tlv               
Ethernet8  vendor1-tlv               
```


## SAI API

No changes in SAI API is required for this feature.


## Configuration and Management

### YANG Model

```yang
module sonic-lldp {
    namespace "http://github.com/Azure/sonic-lldp";
    prefix lldp;

    import sonic-common {
        prefix cmn;
    }

    container sonic-lldp {
        container LLDP {
            container GLOBAL {                
                leaf custom_tlv_name {
                    type string;
                    description "Comma-separated list of custom TLV names applied globally to all interfaces";
                }
            }
        }

        container LLDP_CUSTOM_TLV {
            description
                "Custom TLVs for LLDP";

            list LLDP_CUSTOM_TLV_LIST {
                key "name";

                leaf name {
                    type string {
                        length "1..32";
                        pattern "[a-zA-Z0-9_-]+";
                    }
                    description
                        "Custom TLV name. Can contain letters, numbers, hyphens, and underscores.";
                }

                leaf oui {
                    type string {
                        pattern "([0-9a-fA-F]{2},){2}[0-9a-fA-F]{2}";
                    }
                    mandatory true;
                    description
                        "Organizationally Unique Identifier (OUI) as 3 comma-separated hex bytes.
                        Example: 00,12,34";
                }

                leaf subtype {
                    type string {
                        pattern "(0x[0-9a-fA-F]{1,2})|([0-9a-fA-F]{1,2})";
                    }
                    mandatory true;
                    description
                        "Subtype value in hexadecimal format (0x00-0xFF).
                        Example: 0x01, 01";
                }

                leaf oui_info {
                    type string {
                        pattern "([0-9a-fA-F]{2},)*[0-9a-fA-F]{2}";
                    }
                    mandatory true;
                    description
                        "OUI info as comma-separated hex bytes (max 507 bytes).
                        Example: 12,34,ab,cd";
                }
            }
        }
        
        container LLDP_PORT {
            description "LLDP interface configuration";
            
            list LLDP_PORT_LIST {
                key "name";
                
                leaf name {
                    type string;
                    description "Interface name";
                }
                
                leaf admin_status {
                    type enumeration {
                        enum "enabled";
                        enum "disabled";
                    }
                    default "enabled";
                    description "LLDP admin status on the interface";
                }
                
                leaf custom_tlv_name {
                    type string;
                    description "Comma-separated list of custom TLV names associated with this interface";
                }
            }
        }
    }
}
```

## Testing Requirements

### Unit Tests

### Configuration Commands

#### Custom TLV Definition Management
1. Verify adding new custom TLV with all parameters
2. Verify modifying the parameters of existing custom TLV 
3. Verify removing of custom TLV
4. Verify removing of custom TLV is not allowed when it's associated with interfaces.
5. Verify removing of a non-existent custom TLV fails.
6. Verify configuring of custom TLV with oui-info with max length of 507 bytes.
7. Verify the input values for OUI, subtype, OUI info are rejected if the values are not in expected format.

#### Global Custom TLV Management
1. Verify applying custom TLV globally results in all interface sending LLDP packets with global custom TLV included
2. Verify applying multiple custom TLVs globally
3. Verify removing specific custom TLV from global configuration while preserving others
4. Verify removing all custom TLVs from global configuration
5. Verify applying non-existent custom TLV globally fails
6. Verify global custom TLVs are applied to newly added interfaces, when say port is breakout.
7. Verify global custom TLVs coexist with interface-specific custom TLVs, verify both TLVs are present in the LLDP packets

#### Interface Custom TLV Association
1. Verify adding custom TLV to single interface
2. Verify adding multiple custom TLVs to same interface  
3. Verify adding custom TLV to interface range (e.g., Ethernet0-12)
4. Verify removing custom TLV from an interface
5. Verify removing specific TLV when multiple TLVs are configured on the interface
6. Verify removing nonexistent TLVs from an interface fails
7. Verify removing custom TLV from invalid interface fails
8. Verify adding already associated TLVs will work fine
9. Verify adding same custom TLV again to an interface


### Show Commands
1. Verify "show lldp custom-tlv" displays all the custom TLVs configured on the system
2. Verify "show lldp custom-tlv" shows a message when there are no custom TLVs configured on the system
3. Verify "show lldp custom-tlv <tlv-name>" displays only the tlv that is specified
4. Verify "show lldp custom-tlv <tlv-name>" notifies custom TLV not found when non-existent tlv is given as input
5. Verify "show interfaces lldp custom-tlv" displays all the interfaces and the custom TLVs that are configured on those interfaces. 
6. Verify "show interfaces lldp custom-tlv" displays the list of TLVs for an interface when multiple custom TLVs are configured on that interface.


#### Integration Scenarios
1. Verify when custom TLVs are configured on an interface, the LLDP packets have the TLVs included by capturing the packet.
2. Verify when custom TLVs are removed from on interface, the LLDP packets stop including the TLVs by capturing the packet.
3. Verify when a feature daemon requests for including the TLV, the LLDP packets have the TLVs included by capturing the packet.
4. Verify when a feature daemon removes custom TLVs from an interface, the LLDP packets stop including the TLVs by capturing the packet.
5. Verify with both user configured custom TLVs and feature daemon custom TLVs on same interface, the LLDP packets include both TLVs. Verify adding and removing of these TLVs and check the LLDP packets include or exclude the TLVs.
6. Verify the feature daemon is able to get the received custom TLV by subscribing to the stateDB table, when custom TLVs are received from the neighbouring device.
7. Verify when port goes down and comes up, LLDP packets with custom TLVs configured are transmitted.  

#### Restart and Reboot Scenarios
1. Verify the custom TLVs associated with interface are applied after LLDP docker restart. Verify LLDP packets include the custom TLVs.
2. Verify after save and reboot of system, custom TLVs associated with interface are applied on bootup. Verify LLDP packets include the custom TLVs.
