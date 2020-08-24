# Approch note for Warmboot in multi-asic platforms.
This design note details the warm boot approach in fixed format SKU's with multiple AISCs handling the data path traffic.

In the multi-asic platforms these are the notable changes that needs to be considered.
  - the following services viz databse, swss, syncd, teamd, bgp, lldp are replicated and one instance per ASIC that is present in the platform.
  - each of these above set of services run in their own linux network namespace.
  - there are port channel interfaces present between the ASIC's. These interfaces are allways up and bundled with backplane interfaces.
  - there are IBGP sessions between the BGP instances running in various ASIC namespace.


## Steps done when the device goes down during warm boot

### For single ASIC platform.

  - stop bgp docker 
  - stop teamd docker
  - stop swss docker
  - save the whole Redis database into ```/host/warmboot/dump.rdb```
  - stop syncd docker
  - warm shutdown
  - save the SAI states in ```/host/warmboot/sai-warmboot.bin```
  - kill syncd docker
  - stop database
  - use kexec to reboot, plus one extra kernel argument


### The design changes for multi-ASIC platform.

The approach is to do an action eg: stop bgp, in all the asic_instances at the same time and wait for it to be donw and state to be Ok in all the asic_instances before proceeding to the next state.

**Introduce a warm restart table in the StateDB in the global database docker service running on the linux host.**
```
WARM_RESTART_TABLE
;Stores warm-reboot lifecycle state for that asic_instance


key             = WARM_RESTART_TABLE|asic_instance        ; asic_instance is a unique ID or name to identify
                                                          ; the instance of set of services <database, swss
                                                          ; syncd, teamd, bgp, lldp> running in a namespace

state           = "db_save" / bgp_done" / "swss_done" / "syncd_done" / "teamd_done" / "database_done"
                                                             ; FSM state of the services bound to a particular 
                                                             ; asic_instance.
```
There needs to be a process or a script to watch the state of an "asic_instance" group of services. Two approaches here 

  1. Introduce a new process named "warmBootd" running in the linux host.
    - It monitors the WARM_RESTART_TABLE which we introduced above on the state of an asic_instance, when an action is initiated.
    - It proceeds to the next state only of the state in WARM_RESTART_TABLE for all asic_instances is advanced to the next state.
    - In case of error in any of the asic_instance, try again ? or do a cold reboot ? can we revert back to the original state here ?

  2. Enhance the warm-reboot script to add the state check and wait loop at various points so that the services will be cleaned stopped.

**Save the Redis DB in each ASIC instance**
<TODO>
  
**Save the SAI states in each ASIC instance**
<TODO>



## Steps done when the device comes back up after warm boot

On the way up after warm reboot, the sequence could be same as what we do for a single ASIC platform. The design change would be with the 
  - usage of different redis database saved file per ASIC instance
  - usage of different sai warboot saved files per ASIC instance.
 
