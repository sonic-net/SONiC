# Dump Utility for Easy Debugging #
#### Rev 0.1

# Table of Contents
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [Definitions/Abbreviation](#definitionsabbreviations)
  * [Overview](#overview)
  * [1. Requirements](#1-requirements)
      * [1.1 Intended Usage](#11-intended-usage)
      * [1.2 Customization Options](#12-customization-options)
      * [1.3 Extensibility](#13-extensibility)
      * [1.4 Directory Structure](#14-directory-structure)
  * [2. Design](#2-design)
      * [2.0 The Executor Class](#20-the-executor-class)
      * [2.1 Adding new Modules](#21-adding-new-modules)
      * [2.2 Module Internals](#22-module-internals)
      * [2.3 Helper Methods Available](#23-helper-methods-available)
      * [2.4 Redis Match Infra](#24-Redis-Match-Infra)
      * [2.5 RMRequest Examples](#25-rmrequest-examples)
  * [3. Unit Tests](#3-unit-tests)
  * [4. TechSupport](#4-techsupport)
   
### Revision  

| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 0.1 | 05/01/2021  | Vivek Reddy Karri        | Initial version       |

## About this Manual
This document describes the details of a dump cli utility which collects and dumps the redis state for a given feature/module. 

## Definitions/Abbreviations 
###### Table 1: Abbreviations
| Abbreviation | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| APP DB       | Application Database                                         |
| ASIC DB      | ASIC Database                                                |
| CONF DB      | Configuration Database                                       |
| RMEngine     | RedisMatchEngine                                             |
| RMRequest    | RedisMatchRequest                                            |

                     
In this document, the term '**redis state**' refers to the intermediate state of a given feature present across all the Redis DB's 

## Overview 
In SONiC, there usually exists a one-to-many, many-to-many logical mappings between the CONF DB <-> APPL DB <-> ASIC DB.
(This applies to other DB's as well, but focussing on these 3 as an example). 

###### Table 2: COPP trap id logical mappings
| CONF DB      |  APP DB             |      ASIC DB                          |
| ------------ | ------------------- |  -----------------------------------  |
| Trap Group   | Trap Group          |  SAI_OBJECT_TYPE_HOSTIF_TRAP          |
| Trap Id      |                     |  SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP    |
|              |                     |  SAI_OBJECT_TYPE_QUEUE                |
|              |                     |  SAI_OBJECT_TYPE_POLICER              |

The task of debugging quickly becomes tedious because currently, there is no utility which does print a unified view of the redis-state.
This is the problem which is addressed by this dump utility.

This utility provides the base infrastructure and guidelines to make is easy for the developers to extend and support the utility for different modules.

## **1 Requirements**

### 1.1 Intended Usage

Note: Currently, `state` is the only subcommand under `dump`.

```
dump state <feature/module> <arg>

Example usage for Port feature which accepts an argument port_name
dump state port <port_name>
dump state port Ethernet4
dump state port Ethernet4,Ethernet8,Ethernet12
dump state port all
```

#### 1.1 Intended Usage
1) The `dump state` subcommand will take a feature/module or any logical top-level name as the first argument. 
2) A Second Argument should also be defined for a feature. 
3) This argument could either be a table-key or a unique-field-value present in either Conf DB or Appl DB.
   * Eg: For PORT, the second argument will be an interface name i.e 'Ethernet128' which is a table-key. On the other hand, the secondary argument for COPP will be a trap_id such as  'arp_req', which is a field-value present in one of the tables of CONF DB.
4) The decision of what to pass as a secondary argument lies with the discretion of the one who is writing the module.
6) The Command should also take a list of comma seperated inputs for the secondary argument
7) The Command should also accept an "all" value and which means it should print the unified view for every entry related to that feature.

```
root@sonic# dump state --help
Usage: dump state [OPTIONS] MODULE ARG

  Dump the redis state of the module specified

Options:
  -s, --show     Display all the Modules and the name of their correponding secondary argument 
  -d, --db TEXT  Only dump from these Databases
  -t, --table    Print in tabular format  [default: False]
  -r, --rid      Dont Extract VidToRid Mappings for ASIC DB Dumps  [default: False]
  -k, --key-map  Only Return Key mappings, Dont return Field-Value Dumps [default: False]
  -v, --verbose  Prints any intermediate output to stdout useful for dev & troubleshooting  [default: False]
  --help         Show this message and exit.
  
root@sonic# dump state --show
Module            Args
--------------    ------
copp              trap_id
port              port_name
random_feature    key
```

### 1.2 Customization Options

1) The unified view printed can be filtered per db using -d option
2) VidToRid Mappings are generated by default, to disable them use -r option
3) Output is displayed in JSON format by default. Use -t to print in tabular format.
4) All the available modules should be displayed using a -s option
5) If Field-Value Tuples are not required, use -k option to specify that


### 1.3 Extensibility

Utility should be open to extension i.e. any new modules can be added easily without the need to change the common logic. 
The common logic should be closed to modification unless there is a very specific use case which demands so.

### 1.4 Directory Structure

```
sonic-utilities/
       ├──── dump
             ├── __init__.py
             ├── .......
             ├── <Add any common logic here>
             ├── plugins/
                 ├── __init__.py
                 ├── executor.py
                 ├── copp.py
                 ├── port.py 
                 ├── sflow.py
                 ├── ........ 
                 ├── <Add new modules here>
```

## **2 Design**

### 2.0 The Executor Class

This is the base class which all the module classes should inherit from.

```
class Executor(ABC):

    ARG_NAME = "arg" # Override this to change the name of the argument

    @abstractmethod
    def execute(self, arg):
        pass
    
    @abstractmethod
    def get_all_args(self):
        pass
```

### 2.1 Adding new Modules

To add a new module, these guidelines have to be followed.

* Create a class which inherits from the Executor class. This should implement the execute() method.
* The class name (converted to lower case) will be reflected in the click command and the name of the file, should also be the same.
* Name of the argument is set to "arg". If this has to be changed,  override ARG_NAME class variable.
* This name specified in the "ARG_NAME" is reflected when the command `dump state --show` is run.
* The Module Class should implement `execute(arg)` and `get_all_args()` method

###### Requirements on the Module Class for execute(arg) method
* The execute method will receive a dictionary. The value passed from the user can be fetched by using ARG_NAME i.e.  `args[ARG_NAME]`
* The execute method should return a dictionary of the format JSON Template 1.
* Implementation of the execute method is upto the module implementer, all that is expected from the class here is to return the dictionary with the proper information populated. 

###### JSON Template 1: Return dict by Executor
```
{
  "<DB_NAME>": {
        "keys": [],                # Relevant keys i.e. "Table<sep>key" info in the corresponding DB which are of interest
        "tables_not_found" : []    # Populate this list with those table names, which were suppose to have to info the module was looking for and yet it did not find one.
                                     Again, the decision of which tables to look for and which of those are definitely supposed to have the information, is left to the discretion of the module implementer
   }
}

Example Return Object:

This is an example return object from the module class for the trap_id "bgp" for the module "copp". i.e. dump state copp bgp

{
    "CONFIG_DB": {
        "keys": ["COPP_TRAP|bgp", "COPP_GROUP|queue4_group1"],
        "tables_not_found" : []
    },
    "APPL_DB": {
        "keys": ["COPP_TABLE:queue4_group1"],
        "tables_not_found" : []
    },
    "ASIC_DB": {
        "keys": [],
        "tables_not_found": ["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP"]
    }
}

Note: When properly configured by the orchagent, the ASIC_DB is supposed to have a TRAP obj and a corresponding TRAP_GROUP object. 
Assuming there is an issue in copporch, the corresponding entries for "bgp" trap_id will not be written to the ASIC_DB.
Subsequently, "tables_not_found" will reflect the names of these tables. 
Note: This Utility doesn't determine the root cause on why did it happen, it merely reflects the current redis-state.
```

###### Requirements on the Module Class for handling 'all' keyword
* When the "all" argument is given by the user, get_all_args() method will be invoked and it's the responsibility of the module class to implement this.
* get_all_args() should return a tuple of list and the list contains all the arguments for which the redis-state has to be returned. 
   * Eg: For Copp, get_all_args() should return a list of trap_ids i.e. (['arp_req', 'bgpv6', 'sample_packet',..........])
* An example implementation is given in the section 2.3
* Using this information, The execute method will then be invoked for every value provided in the list.

Note: VidToRid Mapping, field-value data, db filtering, printing/formatting of output to stdout, inclusion in the techsupport output are all handled in the common logic and the module need not bother about these details.

### 2.2 Module Internals

###### Module Example 1: PORT
```
class Port(Executor):

    ARGS = "port_name"
    
    def get_all_args(self):
        all_port_names = []
        .......  # Find and fill this list of all_port_names,
        return (all_ports) #Eg: (['Ethernet0', 'Ethernet4', 'Ethernet8', 'Ethernet12', ....])
    
    def execute(self, args):
        self.template = display_template(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB"])
        port = args[ARG_NAME] 
        get_config_info(port) # Populate the return template with the info taken from Config DB
        get_appl_info(port) # Populate the return template with the info taken from Appl DB
        get_asic_info(port) # Populate the return template with the info taken from Asic DB
        ......... # Add the details for any other db's of interest
        return self.template
```

### 2.3 Helper Methods Available

###### List of available helper methods useful when drafting new Executor Modules

```
1) display_template(dbs=['CONFIG_DB', 'APPL_DB', 'ASIC_DB']): Returns a dictionary of format JSON Template 1
2) RedisMatchEngine / RedisMatchRequest: Part of Redis Match Infra to get the required data from redis db. More info in the next section.
3) verbose_print(str_): prints to the stdout based on verbosity provided by the user.  
```

### 2.4 Redis Match Infra

Most of the heavy lifting in filling the return dictionary is in getting data out of redis and parse it based on user requirements. 
To Abstract this functionality out, a RMEngine class is created. A RMRequest object has to be passed to the fetch() method of the RMEngine class 

###### JSON Template 2: RMRequest Object:

```
{
  "Table": "<STR>",             # Mandatory, A Valid Table Name
  "key_regex": "<STR>",         # Mandatory, Defaults to "*" 
  "field": "<STR>",             # Mandatory, Defaults to None
  "value": "<STR>",             # Mandatory, Value to match, Defaults to None
  "return_fields": [
    "<STR>"                     # An optional List of fields for which the corresponding values are returned
  ],
  "db": "<STR>",                # Mandatory, A Valid DB name
  "just_keys": "true|false"     # Mandatory, if true, Only Returns the keys matched. Does not return field-value pairs. Defaults to True
}
```

###### RMEngine Usage Details

* Case 1: field and value in the RMRequest are None. Result: RMEngine returns all the keys which are regex matched by "Table|key_regex".
* Case 2: field and value in the RMRequest are not None and a set of keys are matched by the "Table|key_regex". Result: The RMEngine looks into each of these keys and returns those keys who has their field-value pairs equated to what is provided. 
* Case 3: For a valid combination of db, Table, key_regex, field and value, if all the field-value pairs are required, set just_keys to true.
* Case 4: For a valid combination of db, Table, key_regex, field and value, if only a few specific fields are required, set just_keys to false and use return_fields option.

###### JSON Template 3: Return Dictionary by the RMEngine:

```
{
  "status": <INT>,              # 0 for sucess       
  "error": "<STR>",             # Error String, if any
  "keys": [],                   # Match found for the request
  "return_values": {}           # Return Values for the corresponding return_fields passed
}
```

### 2.5 RMRequest Examples:

```
1) Fetch the entry for ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002cf (Only Keys)

req = RedisMatchRequest()
req.table = "ASIC_STATE:SAI_OBJECT_TYPE_QUEUE"
req.key_regex = "oid:0x150000000002cf"
req.db = "ASIC_DB"
req.just_keys = True
req.return_fields = []

Return Dict:
{
  "status": 0,                 
  "error": "",             
  "keys": ["ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x1500000000052f"],                  
  "return_values": {}       
}

2) Fetch the entry for ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002cf (Keys + Field-Value Pairs)

req = RedisMatchRequest()
req.table = "ASIC_STATE:SAI_OBJECT_TYPE_QUEUE"
req.key_regex = "oid:0x150000000002cf"
req.db = "ASIC_DB"
req.just_keys = False
req.return_fields = []

Return Dict:
{
  "status": 0,                 
  "error": "",             
  "keys": [{"ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x1500000000052f": {
                    "NULL": "NULL",
                    "SAI_QUEUE_ATTR_TYPE": "SAI_QUEUE_TYPE_UNICAST",
                    "SAI_QUEUE_ATTR_INDEX": "4"}],                  
  "return_values": {}       
}


3) Fetch the entry for ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP table which has trap type SAI_HOSTIF_TRAP_TYPE_BGPV6

req = RedisMatchRequest()
req.table = "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP"
req.key_regex = "*"
req.field = "SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE"
req.value = "SAI_HOSTIF_TRAP_TYPE_BGPV6"
req.db = "ASIC_DB"
req.return_fields = ["SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP"]

Return Dict:
{
  "status": 0,                 
  "error": "",             
  "keys": ["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x22000000000592"],                  
  "return_values": {"ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x22000000000592" : {"SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP" : "oid:0x11000000000591"}}       
}
```

## 3 **Unit Tests**:

| S.No | Test case synopsis                                                                                                                      |
|------|-----------------------------------------------------------------------------------------------------------------------------------------|
|  1   | Verify RMEngine funtionality in cases of invalid Request Objects                                                                        |
|  2   | Verify RMEngine Match functionality is as expected                                                                                      |
|  3   | Verify VidToRid Mappings are extracted as expected                                                                                      |
|  4   | Verify dump cli options are working as expected                                                                                         |
|  5  | Add unit tests for every module added                                                                                                   |


## 4 **TechSupport**
Output for every <feature/module> which extends from Executor class will be added to the techsupport dump. 
Every Json file will have the corresponding output: `dump state <corresponding_feature> all -k`. 
Only the related keys information will be present in the unified_dump_folder as entire DB dumps are already present in the dump/folder.

```
$BASE
   ├──── dump/
         ├── unified_view_dump/
             ├── copp
             ├── port
             ├── sflow
             ├── <random_feature>
             ├── .......
             ├── <One file for every feature should be present here>        
   ├──── etc/
   ├──── log/  
   ├──── ......
   ├──── ......
```








