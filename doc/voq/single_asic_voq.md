# **Single ASIC VOQ Fixed System SONiC** {#single-asic-voq-fixed-system-sonic}

# **High Level Design Document** {#high-level-design-document}

Rev 1.2

azure-team@nexthop.ai

# **Table of Contents** {#table-of-contents}

[Single ASIC VOQ Fixed System SONiC](#single-asic-voq-fixed-system-sonic)

[High Level Design Document](#high-level-design-document)

[Rev 1.0](#heading=h.snl1xsdxyqtx)

[Table of Contents](#table-of-contents)

[Revision](#revision)

[About this Manual](#about-this-manual)

[Scope](#scope)

[1 Requirements Overview](#1-requirements-overview)

[1.1 Functional Requirements](#1.1-functional-requirements)

[1.2 Configuration requirements](#1.2-configuration-requirements)

[1.3 Agent requirements](#1.3-agent-requirements)

[1.3.1 Orchagent](#1.3.1-orchagent)

[1.3.2 Bgpconfd](#1.3.2-bgpconfd)

[1.3.3 Sonic-utilities](#1.3.3-sonic-utilities)

[1.3.4 Sonic-host-services Caclmgrd](#1.3.4-sonic-host-services-caclmgrd)

[2 Modules Design](#2-modules-design)

[2.1 Switch Type “VOQ” For Both Chassis and Single-ASIC cases](#2.1-switch-type-“voq”-for-both-chassis-and-single-asic-cases)

[2.1.1 Orchagent Changes](#2.1.1-orchagent-changes)

[2.1.2 Bgpconfd Changes](#2.1.2-bgpconfd-changes)

[2.1.3 Sonic-utilities, Sonic-host-services/Caclmgrd Changes](#2.1.3-sonic-utilities,-sonic-host-services/caclmgrd-changes)

[2.1.4 CLI Changes](#2.1.4-cli-changes)

[2.1.5 Config Generation Changes](#2.1.5-config-generation-changes)

# 

# **Revision** {#revision}

| Rev | Date | Author | Change Description |
| ----- | ----- | ----- | ----- |
| 1.0 | 06/10/2025 | Eswaran Baskaran[Lakshmi Yarramaneni](mailto:lakshmi@nexthop.ai) | Initial public version |
| 1.1 | 06/23/2025 | Lakshmi Yarramaneni | Details on single-ASIC VOQ flag |
| 1.2 | 7/1/2025 | Lakshmi Yarramaneni | Updated to use chassis config file |

# **About this Manual** {#about-this-manual}

This document describes the design details for supporting SONiC on a single-ASIC VOQ Fixed System (referred to as single-ASIC VOQ in this doc). 

# **Scope** {#scope}

This specification focuses on how to support VOQ switch functionality on single-ASIC VOQ and understand the impact on various Sonic modules in single-ASIC vs. chassis.

# **1 Requirements Overview** {#1-requirements-overview}

## **1.1 Functional Requirements** {#1.1-functional-requirements}

The single-ASIC VOQ implementation shall support VOQ mode without relying on the presence of Chassis DB.

## **1.2 Configuration requirements** {#1.2-configuration-requirements}

iBGP configuration that was generated for chassis-based VOQ systems is not needed in single-ASIC VOQ. QoS configuration that was generated for system ports continues to be needed for single-ASIC VOQ. 

## **1.3 Agent requirements** {#1.3-agent-requirements}

### **1.3.1 Orchagent** {#1.3.1-orchagent}

- Support VOQ and single-ASIC VOQ modes  
  - Interface with Chassis DB in Chassis VOQ system but not in a single-ASIC VOQ  
  - Enable and manage fabric ports for single ASIC VOQ case also

  ### **1.3.2 Bgpconfd** {#1.3.2-bgpconfd}

- Spawn off ChassisDbMgr only on Chassis VOQ system but not on single-ASIC VOQ  
- Handle TSA (Traffic Shift Away) only on chassis VOQ and not on single-ASIC VOQ

  ### **1.3.3 Sonic-utilities** {#1.3.3-sonic-utilities}

- Support line card extensions only on Chassis VOQ system but not on single-ASIC VOQ  
- Differentiate between internal and external BGP neighbors on Chassis VOQ only  
- Fabric port status should only be retrieved from Chassis DB on Chassis VOQ systems but not on single-ASIC VOQ system  
- Multi ASIC checks must evaluate to false on single ASIC VOQ

  ### **1.3.4 Sonic-host-services Caclmgrd** {#1.3.4-sonic-host-services-caclmgrd}

- Support midplane traffic only on Chassis VOQ system

# **2 Modules Design** {#2-modules-design}

### **2.1 Switch Type “VOQ” For Both Chassis and Single-ASIC cases** {#2.1-switch-type-“voq”-for-both-chassis-and-single-asic-cases}

This method reuses the *voq* switch type for non chassis systems as well. This means the agents, utilities and CLI config tools will need to differentiate between chassis system vs non chassis in voq mode. Chassis configuration file *chassisdb.conf* can indicate if the voq system is a chassis system or not.

In the platform configuration file *platform.env*, there is a *disaggregated\_chassis* flag which indicates the presence of a database-chassis container. We do not intend to use this flag as we will not be using chassis db at all.

API *is\_voq\_chassis* will check for the presence of the *chassisdb.conf* file.

### **2.1.1 Orchagent Changes** {#2.1.1-orchagent-changes}

- Orchagent will handle VOQ functionality the same way i.e. creation of system ports. But connect to Chassis DB only if chassis DB is supported in the sonic system.

### **2.1.2 Bgpconfd Changes** {#2.1.2-bgpconfd-changes}

- No changes needed with proposed update to ***is\_voq\_chassis()***

### **2.1.3 Sonic-utilities, Sonic-host-services/Caclmgrd Changes** {#2.1.3-sonic-utilities,-sonic-host-services/caclmgrd-changes}

- Update ***sonic-py-common/device\_info.is\_voq\_chassis()*** to check for chassisdb.confi file.

### **2.1.4 CLI Changes** {#2.1.4-cli-changes}

- Display “*show chassis*” command output only if ***is\_chassis/is\_voq\_chassis()*** true.

### **2.1.5 Config Generation Changes** {#2.1.5-config-generation-changes}

- Do not generate config for chassis if the system is not a chassis system. eg. internal iBGP peering config is not needed in single-ASIC VOQ.

