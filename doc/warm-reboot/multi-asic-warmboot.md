# Approch note for Warmboot in multi-asic platforms.

This design note details the warm boot approach in fixed format SKU's with multiple AISCs handling the data path traffic.
In the multi-asic platforms these are the notable changes that needs to be considered.

![Multi ASIC namespaces](img/architecture_diagram.jpg)


- the following services viz databse, swss, syncd, teamd, bgp, lldp are replicated and one instance per ASIC that is present in the platform.
- each of these above set of services run in their own linux network namespace.
- there are port channel interfaces present between the ASIC's. These interfaces are allways up and bundled with backplane interfaces.
- there are IBGP sessions between the BGP instances running in various ASIC namespace.

## Steps done when the device goes down during warm boot

### For single ASIC platform.

  These are the steps when the system goes down on warm reboot 

```
  --- Pausing orchagent 
  
   --- Stopping radv
   
    --- Stopping bgp 
    
     --- Syncd pre-shutdown 
      
       --- Backing up database
       
        --- Stopping teamd 
        
         --- Stopping syncd 
         
          --- Stopping all remaining containers 
          
           --- use kexec to reboot with the added kernel parameters

```


### The design changes for multi-ASIC platform.

The following are the main thoughts into the warm boot design approach for multi-asic.

#### 1. Introduce a warm restart table in the StateDB

This Warm restart table will store the lifecycle state per asic instance.

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


#### 2. Approach to control the warm restart lifecycle with multiple instances

There needs to be a new process or a enhancement to the existing script to watch the state of services per "asic_instance".

**Approach 1.** Introduce a new process named "warmBootd" running in the linux host.
- It forks multiple threads per ASIC and each one does the warm boot sequence, updates the WARM_RESTART_TABLE with the states in the lifecycle.
- The job of the parent process is to check each ASIC process does finish the activities in a state 
- If all of the ASIC threads reach a state, move to the next state.
    
**Approach 2.** Enhance the warm-reboot script to spawn multiple python threads to work on asic's in parallel 
- Similar to above the parent task will check each thread for the progress and move to the next state on completion.

#### 3 Warm-boot sequence and Failure scenario

   In case of Multi-asic we do the warm boot of each ASIC in parallel. The idea is to do the "more failure prone activities" at begining of the warm reboot lifecycle after pre-check and be able to revert ( if possible ) the system to a good state in case of failure in any one of the ASIC threads.
   
   The most critical activities where a failure could result in the warm-reboot fail are **Pausing orchagent** and **Syncd pre-shutdown**.The Syncd pre-shutdown is where the SAI_SWITCH_ATTR_PRE_SHUTDOWN attribute is send to let SAI/SDK do save the state, shutdown most functions. The CPU port will remain active so that packets could be send out from control plane.

   The following sequence is proposed in each of the thread handling warm reboot lifecycle per asic.
   
   ```
   
  --- Pausing orchagent  < check failure, if failure in any ASIC, can we unpause and recover ? > 
    --- Syncd pre-shutdown   < check failure, if failure in any exit, ask user to do cold reboot ? > 
    
     -------- From here on no looking back -------- 
    
      --- Stopping radv
      
       --- Stopping bgp 
   
       --- Backing up database
       
        --- Stopping teamd 
        
         --- Stopping syncd 
         
          --- Stopping all remaining containers 
   
```
   
#### 4. Save the Redis DB in each ASIC instance

TODO
  



#### 5. Save the SAI states in each ASIC instance

TODO





## Steps done when the device comes back up after warm boot

On the way up after warm reboot, the sequence could be same as what we do for a single ASIC platform. The design change would be related to 
  - restore from different redis database saved file per ASIC instance
  - restore from different sai warboot saved files per ASIC instance.
  


## Updates for fast-reboot

TODO

 
