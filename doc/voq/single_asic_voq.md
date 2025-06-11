# **Single ASIC VOQ SONiC**

# **High Level Design Document**

### **Rev 1.0**

# **Table of Contents**

[Single ASIC VOQ SONiC](#single-asic-voq-sonic)

[High Level Design Document](#high-level-design-document)

[Rev 1.0](#rev-1.0)

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

[2.1.1 Orchagent, Bgpconfd Changes](#2.1.1-orchagent,-bgpconfd-changes)

[2.1.2 Sonic-utilities, Sonic-host-services/Caclmgrd Changes](#2.1.2-sonic-utilities,-sonic-host-services/caclmgrd-changes)

[2.1.3 CLI Changes](#2.1.3-cli-changes)

[2.1.4 Config Generation Changes](#2.1.4-config-generation-changes)

[2.2 Separate Switch Type for Single ASIC VOQ (“single-asic-voq”)](#2.2-separate-switch-type-for-single-asic-voq-\(“single-asic-voq”\))

[2.2.1 Orchagent, Bgpconfd Changes](#2.2.1-orchagent,-bgpconfd-changes)

[2.2.2 Sonic-utilities, Sonic-host-services/Caclmgrd Changes](#2.2.2-sonic-utilities,-sonic-host-services/caclmgrd-changes)

[2.2.3 CLI Changes](#2.2.3-cli-changes)

[2.2.4 Config Generation Changes](#2.2.4-config-generation-changes)

###### **Revision**

| Rev | Date | Author | Change Description |
| ----- | ----- | ----- | ----- |
| 1.0 | 06/10/2025 | Eswaran Baskaran[Lakshmi Yarramaneni](mailto:lakshmi@nexthop.ai) | Initial public version |

# **About this Manual**

This document describes the design details for supporting SONiC on a single-ASIC VOQ System. 

# **Scope**

This specification focussed on how to support VOQ switch functionality on single-ASIC VOQ systems. And understand the impact on various Sonic modules in single-ASIC vs. chassis based.

# **1 Requirements Overview**

## **1.1 Functional Requirements**

The single-ASIC VOQ implementation shall support VOQ mode without relying on the presence of Chassis DB.

## **1.2 Configuration requirements**

iBGP configuration that was generated for chassis-based VOQ systems is not needed in single-ASIC VOQ systems. QoS configuration that was generated for system ports continues to be needed for single-ASIC VOQ systems. 

## **1.3 Agent requirements**

### **1.3.1 Orchagent**

- Support VOQ and single-ASIC VOQ systems  
  - Interface with Chassis DB in Chassis VOQ system but not in a single-ASIC VOQ system  
  - Enable and manage fabric ports for single ASIC VOQ

  ### **1.3.2 Bgpconfd**

- Spawn off ChassisDbMgr only on Chassis VOQ system but not on single-ASIC VOQ system  
- Handle TSA only on chassis VOQ and not on single-ASIC VOQ

  ### **1.3.3 Sonic-utilities**

- Support line card extensions only on Chassis VOQ system but not on single-ASIC VOQ  
- Differentiate between internal and external BGP neighbors on Chassis VOQ only  
- Fabric port status should only be retrieved from Chassis DB on Chassis VOQ systems but not on single-ASIC VOQ system  
- Multi ASIC checks must evaluate to false on single ASIC VOQ

  ### **1.3.4 Sonic-host-services Caclmgrd**

- Should support midplane traffic only on Chassis VOQ system

# **2 Modules Design**

There are 2 approaches to support VOQ mode in single ASIC systems. They are described in sections 2.1 and 2.2 below.

### **2.1 Switch Type “VOQ” For Both Chassis and Single-ASIC cases**

This method reuses the VOQ switch type for non chassis systems as well. This means the agents, utilities and CLI config tools will need to differentiate between chassis system vs non chassis by checking for the presence of the chassis db config file. (/usr/share/sonic/device/$platform/chassisdb.conf)

### **2.1.1 Orchagent, Bgpconfd Changes**

- Copy chassisdb.conf to Orchagent, Bgpconfd containers  
- Orchagent will handle VOQ functionality the same way. But connect to Chassis DB only if chassis config is present  
- Bgpconfd will create ChassisDB manager only if chassis config is present

### **2.1.2 Sonic-utilities, Sonic-host-services/Caclmgrd Changes**

- Update ***sonic-py-common/device\_info.is\_chassis()*** to check for chassis config file

### **2.1.3 CLI Changes**

- Display “*show chassis*” command output only if ***is\_chassis/is\_voq\_chassis()*** true.

### **2.1.4 Config Generation Changes**

- All the FRR, BGP, buffers, QOS j2 templates need to generate config for VOQ. And generate config for chassis (only if chassis config is present).  
  Need a way to check for chassis config from a j2 template 

### **2.2 Separate Switch Type for Single ASIC VOQ (“single-asic-voq”)**

Create a new switch type to represent a single ASIC VOQ system (single-asic-voq). This approach will retain the current assumption that the VOQ system is always a chassis.

### **2.2.1 Orchagent, Bgpconfd Changes**

- Orchagent will handle VOQ and SingleVOQ the same way.   
- Orchagent will connect to Chassis DB for VOQ switch type  
- Bgpconfd will create ChassisDbMgr only on VOQ switch type

### **2.2.2 Sonic-utilities, Sonic-host-services/Caclmgrd Changes**

- No change

### **2.2.3 CLI Changes**

- Display “*show chassis*” command output only if ***is\_chassis/is\_voq\_chassis()*** true.

### **2.2.4 Config Generation Changes**

- No change needed to BGP j2 templates  
- All QOS j2 templates need to generate config for single-ASIC VOQ switch type also  
- Port and Qos yang models will need to include a single-asic-voq switch type also.

