# Platform Monitor Requirement for Chassis Subsystem #

### Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      SONiC Chassis Workgroup      | Initial version                   |

## 1. Mandatory/Needed Requirements:
1. On LC the reboot command should power-cycle the entire LC . Expectation is Peer node should detect link down asap when reboot is given on LC
2. On RP the reboot command should reboot the entire system (RP and LC). . Expectation is Peer node should detect link down when reboot is given on RP.
3. Ungraceful Reboot of Supervisor should bring all LC's. LC's should not run headless.
4. Config shut/unshut of LC will be supported as per the Chassis-d design.
5. Generate syslog for all the critical events and share the threshold (for appropriate/needed components)  in documents and recommended for given threshold range.  Expectation is we will bind syslog to our Alert Orchestration system and perform recommnded action based on the documents.
6. PCI-e issue of not able to detect FC ASIC’s and LC ASIC’s and syslog for same.https://github.com/sonic-net/SONiC/blob/master/doc/pcie-mon/pcie-monitoring-services-hld.md.
7. HW-Watchdog adhering to current SONiC behavior. Start before reboot and explicitly disabled post reboot by SONiC.
8. chassisd daemon support on both LC and RP with all fields of table "CHASSIS_MODULE_TABLE|xxxx” correctly populated.
9. chassisd daemon support populating fields in table "CHASSIS_ASIC_TABLE|xxx", this is used to start swss/syncd in SUP when FABRIC ASIC is ready.
10. Implementation of psud power algorithm on supervisor as specified in chassis design document.
11. PSU LED Status  in the show command of supervisor.
12. TEMPERATURE_INFO table update into Chassis State DB from both Supervisor and LC. Local TEMPERATURE_INFO is also available in LC STATE_DB.
13. Implementation of Fan speed algorithm on supervior as specified in chassis design document.
14. FAN LED Status in the show command of supervisor.
15. Support of both reboot-cause reason and history for Supervisor and LC's.
16. show commands for mid-plane switch as per Chassis Design Document.
17. Process for RMA the card (Fabric/LC). This is just a discussion to document correct process for doing so.
18. LC/FC Fabric Link down Handling.
19. Support "show system-health detail/monitor-list/summary" commands in supervisor/LC's.
20. Platform specific check on the supervisor to check if the LCs are  reachable and syslog it.
21. Enhance "Show chassis module status" command should display linecard hostname instead of generic names like LINECARD1.
	 
## 2. Future Requirements/Enhancements:
1. Generic console for LC using . Possible using this: https://github.com/Azure/SONiC/blob/master/doc/console/SONiC-Console-Switch-High-Level-Design.md
2. Auto Handling by Platfrom SW to reboot/shutdown the HW Component when detecting the critical Fault’s.
3. Module/Chassis/Board LED’s .  Need general infra enhancement of led daemon and show commands.
4. Temperature Measuring Category Enhancements. More Granular and Increase Polling Interval for same. Also show command optimize not dump all sesors and filter based on location.
5. Move Voltage and Current sensors support from existing sensorsd/libsensors model to PMON/ thermalCtld model This provide ability/mechanism in SONiC NOS to poll for board’s Voltage and Current sensors (from platform) for power alogorithm.
6. Support for Midplane Switch Counters (Debugging) /Modifying QOS Properties if needed (Performance)  (Applicable for HW based Midplane switch).
