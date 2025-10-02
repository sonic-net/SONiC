# **Single ASIC VOQ Fixed System SONiC**

# **High Level Design Document**

Rev 1.3

[azure-team@nexthop.ai](mailto:azure-team@nexthop.ai)

# **Table of Contents**

\[Single ASIC VOQ Fixed System SONiC\]

\[High Level Design Document\]

[Rev 1.0]

[Table of Contents]

[Revision]

[About this Manual]

[Scope]

[1 Requirements Overview]

[1.1 Functional Requirements]

[1.2 Configuration requirements]

[1.3 Agent requirements]

[1.3.1 Orchagent]

[1.3.2 Bgpconfd]

[1.3.3 Sonic-utilities]

[1.3.4 Sonic-host-services Caclmgrd]

[2 Modules Design]

[2.1 Switch Type “VOQ” For Both Chassis and Single-ASIC cases]

[2.1.1 Orchagent Changes]

[2.1.2 Bgpconfd Changes]

[2.1.3 Sonic-utilities, Sonic-host-services/Caclmgrd Changes]

[2.1.4 CLI Changes]

[2.1.5 Config Generation Changes]

# 

# **Revision**

| Rev | Date | Author | Change Description |
| :---- | :---- | :---- | :---- |
| 1.0 | 06/10/2025 | Eswaran Baskaran[Lakshmi Yarramaneni](mailto:lakshmi@nexthop.ai) | Initial public version |
| 1.1 | 06/23/2025 | Lakshmi Yarramaneni | Details on single-ASIC VOQ flag |
| 1.2 | 7/1/2025 | Lakshmi Yarramaneni | Updated to use chassis config file |
| 1.3 | 8/13/2025 | Lakshmi Yarramaneni | Added details about neighbors and mirror orch. |

# **About this Manual** {#about-this-manual}

This document describes the design details for supporting SONiC on a single-ASIC VOQ Fixed System (referred to as single-ASIC VOQ in this doc).

# **Scope**

This specification focuses on how to support VOQ switch functionality on single-ASIC VOQ and understand the impact on various Sonic modules in single-ASIC vs. chassis.

# **1 Requirements Overview**

## **1.1 Functional Requirements**

The single-ASIC VOQ implementation shall support VOQ mode without relying on the presence of Chassis DB.

## **1.2 Configuration requirements**

iBGP configuration that was generated for chassis-based VOQ systems is not needed in single-ASIC VOQ. QoS configuration that was generated for system ports continues to be needed for single-ASIC VOQ.

## 1.3 Port Management

Compared to a chassis system that required all system ports to be configured across all linecards Sonic instances, the single-asic-voq system only needs a system port to be configured for each local port.

We do not need to create the inband port in single-asic-voq systems. We will continue to need fabric ports so that fabric port statistics can be exposed.

## **1.4 Agent requirements**

### **1.4.1 Orchagent**

- Support VOQ and single-ASIC VOQ modes  
    
  - Interface with Chassis DB in Chassis VOQ system but not in a single-ASIC VOQ  
  - Enable and manage fabric ports for single ASIC VOQ case also

  ### **1.4.2 Bgpconfd**

- Spawn off ChassisDbMgr only on Chassis VOQ system but not on single-ASIC VOQ  

  ### **1.4.3 Sonic-utilities**

- Support line card extensions only on Chassis VOQ system but not on single-ASIC VOQ  
    
- Differentiate between internal and external BGP neighbors on Chassis VOQ only  
    
- Fabric port status should only be retrieved from Chassis DB on Chassis VOQ systems but not on single-ASIC VOQ system  
    
- Multi ASIC checks must evaluate to false on single ASIC VOQ

  ### **1.4.4 Sonic-host-services Caclmgrd**

- Support midplane traffic only on Chassis VOQ system

# **2 Modules Design**

### **2.1 Switch Type “VOQ” For Both Chassis and Single-ASIC cases**

This method reuses the *voq* switch type for non chassis systems as well. This means the agents, utilities and CLI config tools will need to differentiate between chassis system vs non chassis in voq mode. Chassis configuration file *chassisdb.conf* can indicate if the voq system is a chassis system or not.

In the platform configuration file *platform.env*, there is a *disaggregated\_chassis* flag which indicates the presence of a database-chassis container. We do not intend to use this flag as we will not be using chassis db at all.

API *is\_voq\_chassis* will check for the presence of the *chassisdb.conf* file.

### **2.1.1 Orchagent Changes**

- Orchagent will handle VOQ functionality the same way i.e. creation of system ports. But connect to Chassis DB only if chassis DB is supported in the sonic system.  
    
- Given the inband ports are not created, we need to make sure orchagent is updated to not look for these ports in single-asic-voq mode.

### **2.1.2 Bgpconfd Changes**

- No changes needed with proposed update to ***is\_voq\_chassis()***

### **2.1.3 Sonic-utilities, Sonic-host-services/Caclmgrd Changes**

- Update ***sonic-py-common/device\_info.is\_voq\_chassis()*** to check for chassisdb.confi file.

### **2.1.4 CLI Changes**

- Display “*show chassis*” command output only if ***is\_chassis/is\_voq\_chassis()*** true.

### **2.1.5 Config Generation Changes**

We do not generate config for chassis if the system is not a chassis system. eg. internal iBGP peering config is not needed in single-ASIC VOQ.
