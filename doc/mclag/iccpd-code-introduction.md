# Brief introduction of ICCP code

## 1 app_csm.c

**Application State Machine instance initialization and events handler.**

In function app_csm_transit(), when ICCP state machine becomes OPERATIONAL, application state machine will be OPERATIONAL immediately. All application state machines will become OPERATIONAL.

## 2 iccp_cli.c

**Functions to set ICCP parameters.**

Five parameters can be set, they are domain-id, local-ip, peer-ip, peer-link, mclag-interface.
System-id is a global configuration, it is the value of 'mac' in 'localhost'.

## 3 iccp_cmd.c

**Read configurations from file '/etc/iccpd/iccpd.conf'.**

When starting ICCP docker, it will read some configurations from CFG_DB and record them in a file by command ‘sonic-cfggen -d -t /usr/share/sonic/templates/iccpd.j2 > /etc/iccpd/iccpd.conf’. Please see relative files in ＇dockers/docker-iccp/＇.

## 4 iccp_cmd_show.c

**Functions to display ICCP information.**

Mclagctld supports  new defined CLIs so that  ICCPd related information can be displayed. If user inputs command like 'mclagdctl -i <MC-LAG-id> dump arp', mclagdctl process will make a connection to iccpd process and send the command to iccpd. Iccpd receives the command and sends back a reply for displaying.

## 5 iccp_consistency_check.c

**Functions to take ICCP consistency check.**

From the connection message, Peer IP and local IP will be checked  if they do not match the configuration, the peer connection can’t be established. Please see the codes in function scheduler_server_accept().
Enable MC-LAG portchannel interface check: Interface mode must be the same, both must be configured as L2 or L3 interface  at the same time. If it is configured as L3 interface, then the IP address assigned must be the same in both peers. If they join a vlan, then the vlan must be the same in both peers.

## 6 iccp_csm.c

**ICCP Connection State Machine initialization and events handler.**

The ICCP Connection state machine is defined to have six states in RFC 7275 section 4.2.1.

## 7 iccp_ifm.c

**ICCP interface management, such as get interfaces and read ARP information from Linux kernel through netlink.**

ICCP only keeps the ARP information that are learned from MCLAG enable interfaces or from VLAN interfaceswhere MCLAG enable ports are joined.

## 8 iccp_main.c

**Function main() is the entrance of ICCP module.**

- During warm-reboot, a USR1 signal is sent to ICCP. Then ICCP sends a message to the peer to notify that this device will be warm-rebooted. Please see function iccpd_signal_init() and iccpd_signal_handler().
- Function scheduler_init() makes system initialization.
- Function scheduler_start() starts the main loop of ICCP.
- Function system_finalize() makes system cleanup. This function is called when an exception is caught or when  a USR1 signal is received indicating a warm-reboot.

## 9 iccp_netlink.c

**ICCP interacts with Linux kernel through netlink.**

- Get member ports of PortChannel (iccp_get_port_member_list(),iccp_genric_event_handler()).
- Change MAC address of the port or interface in Linux kernel (update_if_ipmac_on_standby(),recover_if_ipmac_on_standby()).
- Port create and destroy (iccp_event_handler_obj_input_newlink(),iccp_event_handler_obj_input_dellink()).
- Get IP address of interface from Linux kernel (iccp_local_if_addr_update()).
- Get ARP entries from Linux kernel (do_one_neigh_request(),iccp_route_event_handler(),iccp_receive_arp_packet_handler()).

## 10 logger.c

**Write ICCP debug information to syslog.**

## 11 mlacp_fsm.c

**MCLAG finite state machine handler.**

The main function is mlacp_fsm_transit(). This function will take action only after peer connection is established.
There are four states in MCLAG finite state machine:

- MLACP_STATE_INIT: Peer connection is not established.
- MLACP_STATE_STAGE1: Peer connection is established, first sync up ARP and MAC info with peer, then if this switch is standby, sends a sync request to active. If active received this request, it will sync up all info with standby.
- MLACP_STATE_STAGE2: If this switch is active, sends a sync request to standby. If standby received this request, it will sync up all info with active.
- MLACP_STATE_EXCHANGE: This is the steady state. Function mlacp_exchange_handler() handle some events in this switch.

## 12 mlacp_link_handler.c

**MCLAG link events handler, such as link add, delete, up, down etc.**

- MCLAG link add: It must be isolated from peer-link (mlacp_mlag_link_add_handler()).
- MCLAG link delete: It must not be isolated from peer-link (mlacp_mlag_link_del_handler()).
- MCLAG link state up: If portchannel with the same name in the peer is up, this link must isolated from peer-link, if peer portchannel is down, the isolation must be removed (update_peerlink_isolate_from_lif()). Add MAC entries that are learned from the same named port into ASIC (update_l2_mac_state()). Add ARP entries that are learned from the same named interface into Linux kernel (update_l2_po_state(),update_l3_po_state()).
- MCLAG link state down: If peer-link and portchannel with the same name in the peer are both up, redirect MAC entries that are learned from the same named port to peer-link (update_l2_mac_state()). Delete ARP entries that are learned from the same named interface from Linux kernel (update_l2_po_state(),update_l3_po_state()).
- Peer link state up: If peer link up, set all the MAC entries that point to the peer-link in ASIC.
- Peer link state down: If peer link down, remove all the MAC entries that point to the peer-link from ASIC.

## 13 mlacp_sync_prepare.c

Send information of local switch to peer switch, include:

- System id: The standby will change system id to that of active (mlacp_prepare_for_sys_config()).
- MCLAG enabled portchannel state: Port isolation and MAC redirect  depend on this information (mlacp_prepare_for_Aggport_state()).
- MCLAG enabled portchannel name and MAC address:  they are used for creating peer interface (mlacp_prepare_for_Aggport_config()).
- MAC entries information: All MAC entries in both peers are synced up, no matter  if they are learned from MCLAG enabled ports or orphan ports (mlacp_prepare_for_mac_info_to_peer()).
- ARP entries information: ICCP sync up the ARP entries that are learned from MCLAG enable interfaces or from VLAN interfaces  where MCLAG enable ports are joined (mlacp_prepare_for_arp_info()).
- MCLAG enabled portchannel information: Include mode (L2 or L3 interface), IPv4 address of this portchannel, VLAN id list that this portchannel has joined. These are used for consistency check. (mlacp_prepare_for_port_channel_info())
- Peer link information: Peer link in both  peers must be the same type If the peer link is VXLAN tunnel, the VXLAN tunnel name of peer link must be the same in both peers. These are used for consistency check. (mlacp_prepare_for_port_peerlink_info())
- Warm reboot information: When local switch is doing warm-reboot, it will send a message to peer switch to notify the warm-reboot state. (mlacp_prepare_for_warm_reboot())

## 14 mlacp_sync_update.c

**Receive information from peer switch. Please see the above section.**

## 15 port.c

**Local and peer port events handler, such as create, destroy, add to or remove from vlan, etc.**

## 16 scheduler.c

**The main loop of ICCP code. (scheduler_loop())**

## 17 system.c

**Global information of ICCP system.**

