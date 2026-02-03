# Support PDB flows

## 1. Requirments
PDB, power distributed board, will be installed on direct-current platform and replace PSU. SONiC needs to provide several facilities to support this new kind of hardware. In general, only monitoring functionality is required.
This HLD proposes a new SONiC platform object, PDBobject,as the platform abstraction and corresponding small updates to the chassis base object. In addition to that, a new platform daemon, PDB daemon, which similar to PSU daemon will be provided, as well as new CLI command.

## 2. New sonic-platform-common PDBobject APIs
```
APIs inherited from Device Base object
“” Return a string to indicate the pdb object name, normally PDB1, PDB2, … PDB3.
“” No parameter required.
def get_name()

“” Return a boolean to indicate whether PDB is presence, N/A if not readable.
“” No parameter required.
def get_presence()

“” Return a boolean to indicate the operational status, false if not readable.
“” No parameter required.
def get_status()

“” Return a string to indicate the model number, N/A if not availible
“” No parameter required.
def get_model() 

“” Return a string to indicate the model number, N/A if not availible
“” No parameter required.
def get_serial() 

“” Return a string to indicate the model number, N/A if not availible
“” No parameter required.
def get_revision()

“” Return false since PDB is not replaceable
“” No parameter required.
def is_replaceable()




APIs new for PDB object
“” Return a float to indicate the input current, N/A if not availible
“” No parameter required.
def get_input_current()

“” Return a float to indicate the input power, N/A if not availible
“” No parameter required.
def get_input_power()

“” Return a float to indicate the input voltage, N/A if not availible
“” No parameter required.
def get_input_voltage()

“” Return a float to indicate the output current N/A if not availible
“” No parameter required.
def get_output_current()

“” Return a float to indicate the output power, N/A if not availible
“” No parameter required.
def get_output_power()

“” Return a float to indicate the output voltage, N/A if not availible
“” No parameter required.
def get_output_voltage()

“” Return a float to indicate the max supplied power, N/A if not availible
“” No parameter required.
def get_maximum_supplied_power()

“” Return a float number of current temperature
“” No parameter required.
def get_temperature()
```

## 3. New functions of ChassisBase object
```
“” Return an integer as the num of installed PDBs, 0 in PSU based platform
“” No parameter required.
def get_num_pdbs()

“” Return a list of PDB objects, []in PSU based platform
“” No parameter required.
def get_all_pdbs()

“” Return the pdb object at the index, none if out of range.
“” Require an integer parameter as the index of the pdb object
def get_pdb(index)
```

## 4. New platform daemon for pdb
New PDB daemon pdbd shall be created, it can be configured to skip on psu based platform.
It must be enabled on pdb based platform.
```
pmon_daemon_control.json

“skip_pdbd”: true/false
```

![pdb daemon flow](https://github.com/yuazhe/SONiC/blob/9e9b4c2cd6feba0706112f3865feef5498a6c759/images/pdb/pdb_daemon_flow.png)


The purpose of PDB daemon is to collect platform pdb data, supervisord takes charge of this daemon. This daemon will loop every 3 seconds and get the data from platform API and then write it the Redis DB.
The pdb_num will store in "chassis_info" table. It will just be invoked one time when system boots up or reloads. The key is chassis_name, the field is "pdb_num" and the value is from get_pdb_num() of chassis object.
The pdb_status and pdb_presence will store in "pdb_info" table. It will be updated every 3 seconds. The key is pdb_name, the field is "presence" and "status", the value is from get_pdb_presence() and get_pdb_num(). This table will store all the important information of the pdb object.

## 5. database scheme
Keys of PDB_INFO|PDB X, it should be updated by PDB daemon
```
; Defines information for a power supply object
key                              = PSU_INFO|object_name                 ; name of the power supply object
; field                          = value
is_replaceable                   = BOOLEAN                              ; field-replaceable (FRU)
presence                         = BOOLEAN                              ; device presence
status                           = BOOLEAN                              ; device operational status
input_power                      = FLOAT                                ; output power (W)
input_current                    = FLOAT                                ; input current (A)
input_voltage                    = FLOAT                                ; input voltage (V)
output_voltage                   = FLOAT                                ; output voltage (V)
output_current                   = FLOAT                                ; output current (A)
output_power                     = FLOAT                                ; output power (W)
max_output_power                 = FLOAT                                ; maximum rated output power (W)
led_status                       = STRING                               ; LED status (e.g., green/amber/off)
timestamp                        = FLOAT                                ; data updated timestamp
```

Keys of TEMPERATURE_INFO||PDB X Temp, it should be updated by PDB daemon
```
; Defines information for a thermal sensor object
key                              = TEMPERATURE_INFO|object_name         ; name of the thermal object 
; field                          = value
temperature                      = FLOAT                                ; current temperature (C)
maximum_temperature              = FLOAT                                ; maximum recorded temperature (C)
critical_threshold               = FLOAT                                ; temperature critical high threshold (C)
timestamp                        = STRING                               ; timestamp for the temperature reading
```

## 6. CLI Command 

![CLI data flow](https://github.com/yuazhe/SONiC/blob/9e9b4c2cd6feba0706112f3865feef5498a6c759/images/pdb/CLI_data_flow.png) 

### 6.1 show platform pdbstatus
The status field represents the status of the PDB, which can be the following:
1.	OK represents no alarm
2.	Not OK can be caused by power is not good, which means the PDB is present but no power (Eg. the power is down or power cable is unplugged)
3.	WARNING can be caused by power exceeding the PDB's max power threshold
The led field represents the single power led, it’s maintained by CPLD in the front panel. There is no specific led for each pdb, so they all will share this led status.

```
PDB    Model        Serial       HW Rev  Voltage (V)   Current (A)   Power (W)   Status   LED
-----  ------------ ------------ ------- ------------  ------------  ----------  -------  -----
PDB 1  XXXX         SNXXXX       RXX     XX.XX         XX.XX         XX.XX       OK       green
PDB 2  XXXX         SNXXXX       RXX     XX.XX         XX.XX         XX.XX       NotOK    red
…      …            …            …       …             …             …           …        …
PDB X  XXXX         SNXXXX       RXX     XX.XX         XX.XX         XX.XX       OK       green
```

### 6.2 show platform psustatus output 
when number of psu is 0, the old output is:
```
Error: Failed to get the number of PSUs
Error: Failed to get PSU status
Error: failed to get PSU status from state DB
```
However, this error is false in PDB based system, so the new output would be simply:
```
PSU doesn’t exist in PDB platform
```

Wherase in PSU platform, the error message will be:
```
ERROR: PSU not detected
```

## 7. system-health update
System Health output will include the PDB status, there would be a new hardware checker function 
def _check_pdb_status(self, config) 
this fucntion will monitoring the PDB_INFO table to determine the PDB status.
sudo show system-health detail
```
Name                     Status    Type
-----------------------  --------  ----------
…
…
PDB 1                    OK        PDB
PDB 2                    NotOK     PDB
…
PDB X                    OK        PDB
```

## 8. new element in platform.json
```
"pdbs": [
            {
                "name": "PDB 1",
            },
            {
                "name": "PDB 2",
            }
     ……
            {
                "name": "PDB X",
            },
 
        ],
```

## 9. Testing
1. UT of API - Validates default fields for a fixed PDB such as name, model/serial/revision and non-replaceable by default. On read errors or missing nodes, return None gracefully.
2. UT of daemon - Mock power failure/good signal and all metrics return to None first and then back.
3. UT of CLI – UT to cover the nomal/error output

