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
- stop syncd docker
  - warm shutdown
  - save the SAI states in ```/host/warmboot/sai```.
- save the appdb and asic db into the files.
  - save appdb db in ```/host/warmboot/appdb.json``` 
  - save asic db in ```/host/warmboot/asicdb.json```
- stop database
- use kexec to reboot

Plan to re-use fast-reboot script. Improve the fast-reboot to handle warm-reboot scenario, have a symbol link to warm-reboot. 
The script detects the name, and call corresponding reboot. 

# going up path

- start database
  - recover app db and asic from ```/host/warmboot/appdb.json``` and ```/host/warmboot/asicdb.json```
  - implemented in database system service
- start syncd docker
  - implemented inside syncd docker
  - recover SAI state from ```/host/warmboot/sai``` 
  - the host interface will be also recovered.
- start swss docker
  - orchagent will wait till syncd has been started to do init view.
  - will read from APP DB and do comparsion logic.
- start teamd docker
  - at the same time as swss docker. swss will not read teamd app db until it finishes the comparison logic.
- start bgp docker
  - at the same time as swss docker. swss will not read bgp route table until it finishes the comparison logic.
