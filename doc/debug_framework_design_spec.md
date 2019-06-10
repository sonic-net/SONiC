# Debug Framework in SONiC
# Design Specification
#### Rev 0.2

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1. Requirements ](#1-requirements)
  * [2. Functional Description](#2-functional-description)
  * [3. Design](#3-design)	  
  * [4. Flow Diagrams](#4-flow-diagrams)
  * [5. Serviceability and Debug](#5-serviceability-and-debug)
  * [6. Warm Boot Support](#6-warm-boot-support)
  * [7. Scalability](#7-scalability)
  * [8. Unit Test](#8-unit-test)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)  
[Table 2: Configuration options and defaults](#table-2-defaults)

# Revision
| Rev | Date       | Author                      | Change Description         |
|-----|------------|-----------------------------|----------------------------|
| 0.1 | 05/19/2019 | Anil Sadineni, Laveen T     | Initial version            |
| 0.2 | 05/31/2019 | Anil Sadineni, Laveen T     | Address comments from Ben  |

# About this Manual
This document provides general information about the debug framework and additional debug features implementation in SONiC.

# Scope
Current implementation of SONiC offers logging utility and utilities to display the contents of Redis. In an effort to enhance debug ability, A new debug framework is added with below functionality:  
 * Provide a framework that allows components to register and dump running snapshots of component internals using dump routines.  
 * Handle assert conditions to collect more info.  
 * Implement dump routines in OrchAgent using debug framework. 
 
Additionally, below debug features are done to enhance debug ability.  
 * Enhance existing show tech-support utility.  
 * Add additional scripts to enforce policies on debug related files.  
 
This document describes the above scope. 

# Definition/Abbreviation

# Table 1: Abbreviations

| **Term**          | **Meaning**                                                                                           |
|-------------------|-------------------------------------------------------------------------------------------------------|
|   Singleton       |  The singleton pattern is a design pattern that restricts the instantiation of a class to one object. |              |

# 1 Requirements
## 1.1 Functional Requirements
1. A framework to allow component registration and subsequently trigger dump routines. Triggers are from administrative CLI commands or from assert for this release.  
2. Assert routines for production environment to delay the reload for gathering information or notify admin and delegate the decision of reload to admin.    
3. Enhance tech-support to collect comprehensive info.  
4. Add a helper script to facilitate an upload of the debug info in a non-intrusive way.  
5. Rate limit and redirect logs for better debug ability without affecting stability of running processes.  

## 1.2 Configuration and Management Requirements
1. Need a config file to configure default options on the framework actions.  
2. New CLI for triggering dump routines of Daemons.  
3. New CLI to display drop/error interface counters.   
4. New CLI to trigger upload of debug information.  
5. Existing CLI is extended to filter the display counters on a specific interface.  

## 1.3 Scalability Requirements
None

## 1.4 Warm Boot Requirements
None

# 2 Functionality
## 2.1 Functional Description

**1. Dump Routines**
- Framework facilitates to collect developer-level component internal data state under certain system conditions. 
- The triggers to dump information might come from administrative commands, from assert or in response to some critical notifications.  
- Framework provides interface for components to register and an interface for utilities to trigger the components to invoke dump routines.  

**2. Assert utility**
- This utility adds some data collection of certain system information when an assert condition is hit.

**3. Tech-support enhancements**
- Current tech-support collects exhaustive information. The tech-support is enhanced to additionally collect STATE_DB dump, dump of ASIC specifics, filter and redirect critical logs to persistent log file for quick reference.

**4. Helper Scripts**
New utility scripts are provided to:  
- Print "headline" information for a quick summary of the system state.
- Facilitate upload of the collected information.
- Enforce policy on the number of debug-related files.

# 3 Design
## 3.1 Overview
### 3.1.1 Framework for dump routines

**Block Diagram**
![Debug Framework Block Diagram](images/debug_framework_block_diagram.png)


Debug framework provides an API for components to register with the framework. It also provides interface for administrator, assert utilities, error handling functions to invoke framework actions. Framework uses Redis Publish/Subscribe implementation for communicating the trigger message from entity invoking the trigger to the registered components. Framework actions are configurable. These actions are applicable uniformly to all registered components. Please refer [Table-2](#table-2) for configurable actions and default actions.  

Debug Framework itself will not have an executing context. Framework actions are performed in the registered component's thread context. Trigger APIs are executed in the context of invoking utility or invoking process. Debug Framework will be implemented as a Singleton meaning there is going to be only one instance of framework in the system. 
Please refer [Flow Diagram](#4-flow-diagrams) for execution sequence.

**Framework Responsibilities**

Each registered component provides the routines to dump the component-specific state via callback functions. It is then the responsibility of the framework to 
- Monitor for specific system triggers or listen on framework trigger APIs invocation
- Process the trigger and call appropriate dump routines 
- Manage the output location
- Follow up with post actions like redirect summary to console/ compress the files and upload the file.
- Report summary or upload complete info is done either to a pre-defined location or a configured location.

**Component Responsibilities**

Components implement dump routines following below guidelines
- Implement a function of type DumpInfoFunc.  
  `typedef std::function< void (std::string componentName, KeyOpFieldsValuesTuple args) > DumpInfoFunc;`
- Within the function, dump the information into a string buffer and use a macro `SWSS_DEBUG_PRINT`.  Macro will further process the information based on intended framework action.
- Handle KeyOpFieldsValuesTuple as argument. Arguments like dumpType and pass thru arguments that instruct the level of info dump ( short summary/specific info/filtered output/full info) should be handled by components. These arguments are opaque to framework. Additional optional arguments like output location and post-actions are for the framework consumption.  
- Interpreting arguments is at discretion of components.  Components may choose to dump same info for all trigger types ignoring input arguments.
- Dump routines registered with framework should be thread safe. Necessary synchronization needs to be ensured.

**Component registration options**

Framework only manages component registration and invocation of callback functions. Framework itself does not have an executing context. To execute the callback function, components have an option to instruct framework either to create an additional thread that runs in the registrant context or not create a thread but merely publish an event to Redis and expect component to handle the event.  
Components have an option to register with debug framework using any one of the below APIs:  
Option #1. `SWSSDebug::linkWithFramework()`  
Option #2. `SWSSDebug::linkWithFrameworkNoThread()`  

Option #1 is preferred. However if a component already handles RedisDB events and doesn't want an additional thread (to avoid thread synchronization issues) might opt for option #2  

Option #1 ( Framework creates a Thread )
---------
Components register dump routine with debug framework using the API:  
`SWSSDebug::linkWithFramework(std::string componentName, std::function <DumpInfoFunc> componentDumpFuncPtr);`  

Framework does the following:  
- Update framework internal data structure to save the registration information of components.  
- Create a `swss::Selectable` object.  
- Create a subscriber to a table/channel in DebugDumpReq database in RedisDB with a unique channel name for receiving triggers.  
- Create a thread and wait on events/triggers.  
- Invoke component specific dump routine in this thread context on receipt of a trigger.  
- Handle the configured framework action within SWSS_DEBUG_PRINT. For example: Redirect the output to syslog or component specific log file.  
- Update Redis DB to indicate callback action completion. 
- Post-processing of information based on the configured framework action. For example: bundle the information and upload the information to a server.

Option #2 ( Framework does not create a Thread )
---------
Components register dump routine with debug framework using the API:  
`SWSSDebug::linkWithFrameworkNoThread(std::string componentName);`  
Framework will limit the job to the following:  
- Update framework internal data structure to save the registration information of components.  
- Handle the configured framework action within SWSS_DEBUG_PRINT. For example: Redirect the output to syslog or component specific log file.
- Post-processing of information based on the configured framework action. For example: bundle the information and upload the information to a server.

The below activity is delegated to the component
- Optional creation of a swss::Selectable object. 
- Create a subscriber instance to DebugDumpReq database in RedisDB for receiving triggers.
- Optionally create a thread to wake on triggers.
- Invoke component specific dump routine on receipt of a trigger.
- Update Redis DB to indicate callback action completion.


**Implementation brief**  
Framework will be implemented in C++ as a class in SWSS namespace.  

```
    class SWSSDebug  
    {  
       public:
         static SWSSDebug  &getInstance();       // To have only one instance aka singleton  
   
         typedef std::function< void (std::string componentName, KeyOpFieldsValuesTuple args) > DumpInfoFunc;  
	
  	 // Component registration option 1  API  
         static void linkWithFramework(componentName, DumpInfoFunc);  

         // Component registration option 2  API
         static void linkWithFrameworkNoThread(componentName);   

         // Interface to invoke triggers
         static void invokeTrigger(std::string componentName, std::string args);  
	   
	 // API to configure the framework action. Function will be overloaded with arguments
	 static void setFrameworkAction();
	   
       private: 
         SWSSDebug();
         std::map<std::string, DumpInfoFunc> m_registeredComps;
	 std::map<std::string, std::string>  m.configParams;
       
	     // Thread in while(1) for handling triggers and invoking callbacks
         [[ noreturn ]] void runnableThread();  
     };
```

#### 3.1.1.1 Integration of OrchAgent with framework
##### 3.1.1.1.1 Triggers to OrchAgent 
OrchAgent already has a thread that handles events from RedisDB and hence will register with framework (option #2) using below API:   

```
   void OrchAgentDump(std::string componentName, std::vectorFieldsValuesTuple args)
   {
     if routeOrch  
     {  
        SWSS_DEBUG_PRINT();  
     }  
     else if NeighOrch  
     {  
        SWSS_DEBUG_PRINT();  
     }  
   }  

   SWSSDebug::linkWithFrameworkNoThread(std::string componentName, OrchAgentDump);  
```

The component subscribes to DebugDumpReq database in RedisDB. OrchAgent then gets a `swss::Selectable` object and updates the existing selectable map. When a trigger is received, OrchAgent executes OrchAgentDump() in the context of its own thread.

##### 3.1.1.1.2 Triggers to OrchAgent 
show commands will act as triggers for OrchAgent.  
Syntax:  `show debug <component> <keyword> <option-1> .... <option-n>`

##### 3.1.1.1.3 Sample CLI
*RouteOrch:*

| Syntax                                                  | Description                                                                                 |
|---------------------------------------------------------|---------------------------------------------------------------------------------------------|  
|show debug routeOrch routes [all] [ip_prefix]            | Dump all Routes or routes specific to a prefix                                              |
|show debug routeOrch nhgrp [addr-1] [addr-2] [addr-3]    | NexthopGroup/ECMP info from RouteOrch::m_syncdNextHopGroups                                 |
|show debug routeOrch counters                            | Dump internal counters associated with the component                                        |
|show debug routeOrch dumpall                             | Translates to list of APIs to dump, which can be used for specific component based triggers |
 
*NeighborOrch:*
 
| Syntax                    | Description        |
|---------------------------|--------------------|  
|show debug NeighOrch nhops | Dump Nexthops info |
|show debug NeighOrch neighs| Dump Neighbor info |

##### 3.1.1.1.4 Sample Databases

```
;RouteOrch - Channel/Table Name
;
key       = RouteOrch | Routes ; Dump routes map in RouteOrch
vrf       = vrf_name           ; vrf name for which to dump the routes info
prefix    = v4/v6 address      ; search for specific ip prefix
idx       = seq_id/timestamp   ; to uniquely identify this msg/request
 
key       = RouteOrch | nhgrp  ; Dump Nexthop Group table in RouteOrch
prefix    = v4/v6 address      ; list of nexthop ipaddress
idx       = seq_id/timestamp   ; identifier

;NeighborOrch -  Channel/Table Name
;
Key       = NeighborOrch | nhops ; Dump syncdnexthops map in NeighborOrch

```

#### 3.1.1.3 Configuring Framework
Debug framework will initialize with below default parameters and shall be considered if options are not specified as arguments in the triggers.  
The defaults are read from the debugFm.ini file.  

# Table 2: Configuration Options and Defaults

| **Parameter**                 | **options**                         |  **Default**                  |
|-------------------------------|-------------------------------------|-------------------------------|
| DumpLocation                  |  "syslog" / "filename"              | /var/log/<comp_name>_dump.log |
| TargetComponent               |  "all" / "componentname"            | all                           |
| Post-action                   |  "upload" / "compress-rotate-keep"  | compress-rotate-keep          |
| Server-location               |  ipaddress                          | 127.0.0.1                     |
| Upload-method                 |  "scp" / "tftp"                     | tftp                          |
| Upload-directory              |  "dir_path" / "default_dir"         | default_dir                   | 


### 3.1.2 Assert Framework

#### 3.1.2.1 Overview
Asserts are added in the program execution sequence to confirm that the data/state at a certain point is valid/true. During developement, if the programming sequence fails in an assert condition then the program execution is stopped by crash/exception. In Production code, asserts are normally removed. This framework enhances/extendes the assert to provide more debug details when an assert fails.  

Classify assert failure conditions based on following types, assert() will have type and the module as additional arguments  
- DUMP: Invokes the debug framework registered callback API corresponding to the module
- BTRACE: Prints bracktrace and continue
- SYSLOG: Update syslog with the assert failure
- ABORT: Stop/throw exception


#### 3.1.2.2 PsuedoCode:

```
    class dbgAssert: public SWSSDebug
    {
        public:
        enum Type {
            SYSLOG,   // recoverable: log to trace error conditions
            DUMP,     // Functional impact: No depencies with other module, System may continue to operate
            BTRACE,   // Unexpected flow: Print backtrace and continue
            ABORT,    // System Fault: System reached a state where it cannot recover / should not continue
            UNKNOWN
        };

        inline assert(exp)
        {
            syslog("Assert:expression", __FUNCTION__, __FILE__);
        }

        void assert(Type type, string module, boolean expr);
    }

    void dbgAssert::assert(Type type, string module, boolean expr)
    {
        if(!expr)
            if(type == BTRACE)
                backtrace();
            if(type == DUMP)
                SWSSDebug::dump(module>);
            else if(type == ABORT)
                SWSSDebug::dump(module>);
                abort();
    }

    gDbgAssert = new dbgAssert();

    #ifdef assert
    #undef assert
    #define assert(exp) gDbgAssert::assert(exp)
    #endif
```

## 3.2 DB Changes

### 3.2.1 APP DB

**Dump table**

For triggering dump routines  

```
; Defines schema for DEBUG Event attributes
key               = DAEMON:daemon_name              ; daemon_session_name is unique identifier;  
; field           = value  
DUMP_TYPE         = "short" / "full"                ; summary dump or full dump  
DUMP_TARGET       = "default" / "syslog"            ; syslog or specified file  
PASSTHRU_ARGS     = arglist                         ; zero or more strings separated by ","

```
**Dump done table**
```
; Defines schema for DEBUG response attributes
key                = DAEMON:daemon_name             ; daemon_session_name is unique identifier;
; field            = value  
RESPONSE_TYPE      = < enum DumpResponse::result >  ; pending/failure/successful  
```

## 3.3 CLI

### 3.3.1 Show Commands

|Syntax                         | Description                                                                   |
|-------------------------------|-------------------------------------------------------------------------------|
|show debug all                 | This command will invoke dump routines for all components with default action |
|show debug < component >       | This command will invoke dump routine for specific component                  |
|show debug actions < options > | This command will display the configured framework actions                    |  

### 3.3.2 Debug/Error Interface counters
show interfaces pktdrop is added to display debug/error counters for all interfaces.

# 4 Flow Diagrams

![Framework and component interaction](images/debug_framework_flow_diagram.png)

# 5 Serviceability and Debug
None

# 6 Warm Boot Support

No change.



# 7 Scalability
No Change


# 8 Unit Test
### 8.1.1 Debug Framework
1.  Verify that Framework provides a shared library  (a) for components to link and register with the framework and (b) for the utilities to issue triggers.
2.  Verify that on a running system, without any triggers framework does not add any CPU overhead. 
3.  Verify that dump routines are invoked when a trigger is issued with all arguments from the trigger utilities/ show debug commands.
4.  Verify that number of subscribers is incremented using redis-cli after successful registration of component.
5.  Verify that SWSS_DEBUG_DUMP macro writes to dump location specified in the .ini file when the target location for dump is not specified or specified as "default". 
6.  Verify that SWSS_DEBUG_DUMP macro writes to SYSLOG when DUMP_TARGET in trigger is mentioned as syslog. 
7.  Verify that if the utility function triggers dump for all, framework loops through the registrations and updates the table for each component.
8.  Verify that framework executes the configured post action. 
9.  Verify the behaviour of framework when some component doesnt send a DONE message.
10. Verify that framework handles multiple consecutive triggers and handles triggers independently. 

# 9 Internal Design Information
Internal BRCM information to be removed before sharing with the community

Go back to [Beginning of the document](#Debug-Framework-in-SONiC).

