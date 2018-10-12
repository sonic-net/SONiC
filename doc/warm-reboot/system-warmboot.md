# System-wide Warmboot

# going down path

- stop bgp docker 
  - enable bgp graceful restart
  - same as fast-reboot
- stop teamd docker
  - just kill
  - same as fast-reboot
- stop swss docker
  - disable mac learning and aging
  - freeze orchagent
  - set redis flag WARM_RESTART_TABLE:system
  - kill swss dockers
- save the appdb and asic db into the files.
  - save applDB db in ```/host/warmboot/appl_db.json``` 
  - save configDB db in ```/host/warmboot/config_db.json``` 
  - save stateDB db (only FDB and WARM_RESTART_TABLE) in ```/host/warmboot/state_db.json``` 
  - save asicDB in ```/host/warmboot/asic_db.json```
- stop syncd docker
  - warm shutdown
  - save the SAI states in ```/host/warmboot/sai-warmboot.bin```
  - kill syncd docker
- stop database
- use kexec to reboot, plus one extra kernel argument

Plan to re-use fast-reboot script. Improve the fast-reboot to handle warm-reboot scenario, have a symbol link to warm-reboot. 
The script detects the name, and call corresponding reboot.

## Details of kernel arguments
In fast-reboot or warm-reboot, we will use kernel argument to indicate the whole system reboot type for the next boot up. The argument format is ```SONIC_BOOT_TYPE=[fast-reboot|warm|cold]```. Benefits:
1. not possible to set both fast and warm
2. less conflict with vanilla linux kernel arguments
3. all existing checker for ```*fast-reboot*``` still work

Later if we improve the consistency ```SONIC_BOOT_TYPE=[fast|warm|cold]```, this way the production image upgrading process will be smooth (no disruptive change)

## SAI expectations for warm shutdown
- Application (e.g. SONiC) sets switch attribute SAI_SWITCH_ATTR_RESTART_WARM to true before calling remove_switch().
  - Note that this attribute doesn't have to be set at switch_create() time. This is a dynamic decision, setting before calling remove_switch is sufficient.
- Application sets profile attribute SAI_KEY_WARM_BOOT_WRITE_FILE to a valid path/filename where the SAI data will be saved during upcoming warm shutdown.
  - Depending on the SAI implementation, this value might have been read by SAI at switch_create() time only. It is recommended to set this value before calling crete_switch().

# going up path

- Use kernel argument ```warmboot``` to determine in warm starting mode
- start database
  - recover redis from ```/host/warmboot/*.json```
  - implemented in database system service
- start syncd docker
  - implemented inside syncd docker
  - recover SAI state from ```/host/warmboot/sai-warmboot.bin``` 
  - the host interface will be also recovered.
- start swss docker
  - orchagent will wait till syncd has been started to do init view.
  - will read from APP DB and do comparsion logic.
- start teamd docker
  - at the same time as swss docker. swss will not read teamd app db until it finishes the comparison logic.
- start bgp docker
  - at the same time as swss docker. swss will not read bgp route table until it finishes the comparison logic.

## SAI expectations for warm recovery
- Application sets profile value SAI_KEY_BOOT_TYPE to 1 to indicate WARM BOOT. (0: cold boot, 2: fast boot)
- Application sets profile value SAI_KEY_WARM_BOOT_READ_FILE to the SAI data file from previous warm shutdown.
- Note: Switch attribute SAI_SWITCH_ATTR_WARM_RECOVER is not required by SAI.
- Application calls create_switch with 1 attribute: SAI_SWITCH_ATTR_INIT_SWITCH set to true. SAI shall recover other attributes programmed before.
- Application re-register all callbacks/notificaions. These function points are not retained by SAI across warm boot.
