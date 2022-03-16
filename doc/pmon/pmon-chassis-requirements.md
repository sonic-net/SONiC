Section 1 Requirements that are needed by default:-
        1. On LC the reboot command should power-cycle the entire LC . Expectation is Peer node should detect link down when reboot is given on LC
		2. On RP the reboot command should reboot the entire system (RP and LC). . Expectation is Peer node should detect link down when reboot is given on RP
		3. Config shut/unshut of LC will be supported as per the Chassis-d design.
		4. Generate syslog for all the critical events and share the threshold (for appropriate/needed components)  in documents and recommended for given threshold range.  Expectation is we will bind syslog to our Alert Orchestration system and perform recommnded action based on the documents.
		5. PCI-e issue of not able to detect FC ASIC’s and LC ASIC’s and syslog for same.
		Integrate with pcied process in PMON[sonic-platform-daemons/pcied at master · Azure/sonic-platform-daemons (github.com)]. Note: Current PCI daemon polling for pci devices is 60sec which is large poll interval. Does it need optimization ?
		6. Boot-up failure Handling. Need to see the SONiC behaviour from system perspective/docker status/syslog getting generated with required/correct information
		7. HW-Watchdog adhering to current SONiC behavior. Start before reboot and explicitly disabled post reboot by SONiC (This means SONiC is booted up and Services are fine)
		8. chassisd daemon support on both LC and RP with all fields of table "CHASSIS_MODULE_TABLE|xxxx” correctly populated
		9. chassisd daemon support populating fields in table "CHASSIS_ASIC_TABLE|xxx", this is used to start swss/syncd in SUP when FABRIC ASIC is ready.
        10. Slot Nummber in "CHASSIS_MODULE_TABLE|xxxx” need not be unique ? Slot Number is based on physcial layout (Ex: LC can be back facing and can have 0..n and  FC can be Front facing and be 0.n). chassisd can support this model ?
		10. psud power algorithm on supervisor as specified in chassis design document
		11. PSU LED Status  in the show command of supervisor
		12. TEMPERATURE_INFO table update into Chassis State DB from both Supervisor and LC. Local TEMPERATURE_INFO is also available in LC STATE_DB.
		13. Fan speed algorithm on supervior as specified in chassis design document
		14. FAN LED Status in the show command of supervisor
		15. reboot-cause reason and history is working fine for both RP and LC
		16. show commands for mid-plane switch as per Chassis Design Document. Add namespace parameter support for "show chassis midplane-status" command.  
	 
2. Section2: General Chassis Enhancements that are needed:-
		1. LC/FC Fabric Link down Handling
		2. Module/Chassis/Board LED’s .  Need general infra enhancement of led daemon and show commands
		3. LC/FC  operation status detection quicker using (get_change_event() notification handling to detect async card up/down events) rather than using current Polling Interval of 10 sec
		4. Generic console for LC using . Possible using this: https://github.com/Azure/SONiC/blob/master/doc/console/SONiC-Console-Switch-High-Level-Design.md ?
		5. Process for RMA the card (Fabric/LC). This is just a discussion to document correct process for doing so.
		6. Monit check on the supervisor to check if the LCs are  reachable. This is to alert if the linecard is down. Do we need Monit here or use above 10 sec polling ?
		7. Handling of parallel reboot of linecard and supervisor. This should not result in the chassis/linecard to go down or unreachable. (Mention by Arvind) . If we follow Section 1 Point 2 this should           be handled ? 
		8. Mechanism to recover an down/unreachable linecard without power-cycle or reboot of the whole chassis.
		9. Enhance "Show chassis module status" command for linecard should display hostname iso of generic names like LINECARD1
		10. Support "show system-health detail/monitor-list/summary" commands in RP/LC
	 
3. Section3 : Enhancements based on Significat Design Changes 
		1. Auto Handling by Platfrom SW to reboot/shutdown the HW Component when detecting the critical Fault’s.
		2. Temperature Measuring Category Enhancements. More Granular and Increase Polling Interval for same. Also show command optimize not dump all sesors and filter based on location
		3. Move Voltage and Current sensors support from existing sensorsd/libsensors model to PMON/ thermalCtld model This provide Ability/mechanism in SONiC NOS to poll for board’s Voltage and Current sensors (from platform) for power alogorithm.
        4. Midplane Switch Counters (Debugging) /Modifying QOS Properties if needed (Performance) 
