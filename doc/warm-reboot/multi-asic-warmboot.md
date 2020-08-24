# Approch note for Warmboot in multi-asic platforms.

This design note details the warm boot approach in fixed format SKU's with multiple AISCs handling the data path traffic.

In the multi-asic platforms these are the notable changes that needs to be considered.
  - the following services viz databse, swss, syncd, teamd, bgp, lldp are replicated and one instance per ASIC that is present in the platform.
  - each of these above set of services run in their own linux network namespace.
  - there are port channel interfaces present between the ASIC's. These interfaces are allways up and bundled with backplane interfaces.
  - there are IBGP sessions between the BGP instances running in various ASIC namespace.
  
The Following is the **going down path** for warm boot on a single asic device.  

  - stop bgp docker 
  - stop teamd docker
  - stop swss docker
  - save the whole Redis databse into ```/host/warmboot/dump.rdb```
  - stop syncd docker
  - warm shutdown
  - save the SAI states in ```/host/warmboot/sai-warmboot.bin```
  - kill syncd docker
  - stop database
  - use kexec to reboot, plus one extra kernel argument


On the way up after warm reboot, the sequence could be same as what we do for the 
