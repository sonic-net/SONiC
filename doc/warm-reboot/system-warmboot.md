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
- stop syncd docker
  - warm shutdown
  - save the SAI states in ```/host/warm-reboot/sai```.
- kill swss and syncd dockers
- save the appdb and asic db into the files.
  - save applDB db in ```/host/warm-reboot/appl_db.json``` 
  - save configDB db in ```/host/warm-reboot/config_db.json``` 
  - save stateDB db (only FDB and WARM_RESTART_TABLE) in ```/host/warm-reboot/state_db.json``` 
  - save asicDB in ```/host/warm-reboot/asic_db.json```
- stop database
- use kexec to reboot, plus one extra kernel argument ```warm-reboot```

Plan to re-use fast-reboot script. Improve the fast-reboot to handle warm-reboot scenario, have a symbol link to warm-reboot. 
The script detects the name, and call corresponding reboot. 

# going up path

- Use kernel argument ```warm-reboot``` to determine in warm starting mode
- start database
  - recover redis from ```/host/warm-reboot/*.json```
  - implemented in database system service
- start syncd docker
  - implemented inside syncd docker
  - recover SAI state from ```/host/warm-reboot/sai``` 
  - the host interface will be also recovered.
- start swss docker
  - orchagent will wait till syncd has been started to do init view.
  - will read from APP DB and do comparsion logic.
- start teamd docker
  - at the same time as swss docker. swss will not read teamd app db until it finishes the comparison logic.
- start bgp docker
  - at the same time as swss docker. swss will not read bgp route table until it finishes the comparison logic.
