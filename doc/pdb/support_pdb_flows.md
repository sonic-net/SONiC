# Support PDB flows

## 1. Requirments
PDB, power distributed board, will be installed on direct-current platform and replace PSU. SONiC needs to provide several facilities to monitor status of this new kind of hardware. 
This HLD proposes a new SONiC platform object, PDBobject,as the platform abstraction and corresponding small updates to the chassis base object. In addition to that, a new platform daemon, PDB daemon, which similar to PSU daemon will be provided, as well as new CLI command.

## 2. New sonic-platform-common PDBobject APIs

### 2.1 APIs inherited from Device Base object
```
    def get_name(self):
        """
        Retrieves the name of the PDB object (e.g., PDB1, PDB2).

        Returns:
            A string representing the PDB object name.
        """


    def get_presence(self):
        """
        Retrieves the presence status of the PDB.

        Returns:
            A boolean, True if PDB is present, False if not readable.
        """


    def get_status(self):
        """
        Retrieves the operational status of the PDB.

        Returns:
            A boolean, True if PDB is operational, False if not readable.
        """


    def get_model(self):
        """
        Retrieves the model number of the PDB.

        Returns:
            A string representing the model number, or 'N/A' if not available.
        """


    def get_serial(self):
        """
        Retrieves the serial number of the PDB.

        Returns:
            A string representing the serial number, or 'N/A' if not available.
        """


    def get_revision(self):
        """
        Retrieves the hardware revision of the PDB.

        Returns:
            A string representing the hardware revision, or 'N/A' if not available.
        """


    def is_replaceable(self):
        """
        Indicates whether the PDB is replaceable.

        Returns:
            A boolean, False since PDB is generally not replaceable.
        """

```

### 2.2  APIs new for PDB object
```
    def get_input_current(self):
        """
        Retrieves the input current reading.

        Returns:
            A float representing the input current in Amperes, or 'N/A' if not available.
        """


    def get_input_power(self):
        """
        Retrieves the input power reading.

        Returns:
            A float representing the input power in Watts, or 'N/A' if not available.
        """


    def get_input_voltage(self):
        """
        Retrieves the input voltage reading.

        Returns:
            A float representing the input voltage in Volts, or 'N/A' if not available.
        """


    def get_output_current(self):
        """
        Retrieves the output current reading.

        Returns:
            A float representing the output current in Amperes, or 'N/A' if not available.
        """


    def get_output_power(self):
        """
        Retrieves the output power reading.

        Returns:
            A float representing the output power in Watts, or 'N/A' if not available.
        """


    def get_output_voltage(self):
        """
        Retrieves the output voltage reading.

        Returns:
            A float representing the output voltage in Volts, or 'N/A' if not available.
        """


    def get_maximum_supplied_power(self):
        """
        Retrieves the maximum supplied power capacity.

        Returns:
            A float representing the maximum supplied power in Watts, or 'N/A' if not available.
        """


    def get_temperature(self):
        """
        Retrieves the current temperature reading.

        Returns:
            A float representing the temperature in Celsius, or 'N/A' if not available.
        """


    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this PDB

        Returns:
            An integer, the number of thermals available on this PDB
        """


    def get_all_thermals(self):
        """
        Retrieves all thermals available on this PDB

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this PDB
        """


    def get_thermal(self, index):
        """
        Retrieves thermal unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the thermal to
            retrieve

        Returns:
            An object dervied from ThermalBase representing the specified thermal
        """

```

## 3. New functions of ChassisBase object
```
    def get_num_pdbs(self):
        """
        Retrieves the number of installed PDBs.

        Returns:
            An integer representing the number of installed PDBs. Returns 0
            for PSU-based platforms.
        """


    def get_all_pdbs(self):
        """
        Retrieves a list of all PDB objects.

        Returns:
            A list of PDB objects. Returns an empty list [] for PSU-based
            platforms.
        """


    def get_pdb(self, index):
        """
        Retrieves the PDB object at the specified index.

        Args:
            index: An integer, the index of the PDB object to retrieve.

        Returns:
            The PDB object at the specified index, or None if the index is
            out of range.
        """


```

## 4. New platform daemon for pdb
New PDB daemon pdbd shall be created, it can be configured to skip on psu based platform.
It must be enabled on pdb based platform.
```
pmon_daemon_control.json

“skip_pdbd”: true/false
```

![pdb daemon flow](https://github.com/yuazhe/SONiC/blob/26bd990514cc13b5ebe00a6e1fa23082786c66be/images/pdb/pdb_daemon_flow.png)


The purpose of PDB daemon is to collect platform pdb data, supervisord takes charge of this daemon. This daemon will loop every 3 seconds and get the data from platform API and then write it the Redis DB.
The pdb_num will store in "chassis_info" table. It will just be invoked one time when system boots up or reloads. The key is chassis_name, the field is "pdb_num" and the value is from get_pdb_num() of chassis object.
The pdb_status and pdb_presence will store in "pdb_info" table. It will be updated every 3 seconds. The key is pdb_name, the field is "presence" and "status", the value is from get_pdb_presence() and get_pdb_num(). This table will store all the important information of the pdb object.

## 5. Thermalctld change to support PDB
for supporting the pdb device, a new logic will be added to the *update* fucntion of  *class TemperatureUpdater*
```
for pdb in get_all_pdbs():
            if psu.get_presence():
                for thermal in enumerate(pdb.get_all_thermals()):
                    self._refresh_temperature_status(thermal)

```
since in legacy psu based platform the get_all_pdbs() will return none so there is no performace overhead.


## 6. database scheme
Keys of PDB_INFO|PDB X, it will be updated by pdb daemon
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
temperature                      = FLOAT                                ; current temperature (C)
led_status                       = STRING                               ; LED status (e.g., green/amber/off)
timestamp                        = FLOAT                                ; data updated timestamp
```

Keys of TEMPERATURE_INFO||PDB X Temp, it will be updated by thermalctld daemon
```
; Defines information for a thermal sensor object
key                              = TEMPERATURE_INFO|object_name         ; name of the thermal object 
; field                          = value
temperature                      = FLOAT                                ; current temperature (C)
maximum_temperature              = FLOAT                                ; maximum recorded temperature (C)
critical_threshold               = FLOAT                                ; temperature critical high threshold (C)
timestamp                        = STRING                               ; timestamp for the temperature reading
```

## 7. CLI Command 

![CLI data flow](https://github.com/yuazhe/SONiC/blob/9e9b4c2cd6feba0706112f3865feef5498a6c759/images/pdb/CLI_data_flow.png) 

### 7.1 show platform pdbstatus
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

show plat temp

### 7.2 show platform psustatus output 
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

### 7.3 show platform temperture
in pdb based platform, the pdb temperture will be displayed and replace psu 
```
                Sensor    Temperature    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
----------------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
...
            PDB-1 Temp       XX.XX        XX.XX      XX.XX           XX.XX          XX.XX      False  XXXXXXXXXXXXXXXXX
            PDB-2 Temp       XX.XX        XX.XX      XX.XX           XX.XX          XX.XX      False  XXXXXXXXXXXXXXXXX
...
            PDB-X Temp       XX.XX        XX.XX      XX.XX           XX.XX          XX.XX      False  XXXXXXXXXXXXXXXXX
...
```

## 8. system-health update
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

## 9. new element in platform.json
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

## 10. Testing

### 10.1 Unit testing 

The object unit tests will validate the API's default fields for a fixed PDB, such as name, model, serial, and revision, ensuring non-replaceable status and graceful returns on read errors or missing nodes. The daemon unit tests will mock power failure and good signals to confirm that metrics correctly transition to None and then recover. Additionally, the CLI unit tests will cover both normal and error output scenarios to ensure robust handling and accurate reporting.

### 10.2 mgmt testing

Since there are several new extensions had been added to SONiC for support PDB, mgmt testing need to be extended to cover them and should be ready correspondingly with the code change PRs.
