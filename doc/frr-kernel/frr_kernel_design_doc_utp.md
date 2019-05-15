
##  FRR-KERNEL RECONCILIATION DESIGN AND UTP

## Table of Contents
- [ 1. Problem Statement](#1-problem-statement)
- [2. Observation](#2-observation)
- [3. Proposed Solution and comparison](#3-proposed-solution-and-comparison)
- [4. Approach Selected](#4-approach-selected)
- [5. Low Level details](#5-low-level-details)
- [6. Code Details](#6-code-details)
- [7. Unit Test Plan](#7-unit-test-plan)
- [8. DB schema](#8-db-schema)
- [9. Flows and SAI APIs](#9-flows-and-sai-apis)
- [10. Debug dump and relevant logs](#10-debug-dump-and-relevant-logs)
- [11. Memory consumption](#11-memory-consumption)
- [12. Performance](#12-performance)
- [13. Error flows handling](#13-error-flows-handling)
- [14. Show handling](#14-show-handling)

##  1. Problem Statement:
> While s/w upgrade to FRR docker or while maintenance FRR docker restart, minimum disturbance to Control Plane Route (i.e Kernel Route) should happen. For some organization, it is critical to keep control plane unreachability less than ~1 secs for critical services to work with switch while FRR docker restart.
>
>Today Zebra can run with -r flag to retain routes in kernel. But during startup:
i.) Without -k flag: Zebra cleans all kernel routes and insert them back if learned via BGPD/OSPF or any other protocol again. This may take 10-15 secs. [Data copied below.]
>
> ii.) With -k flags: Zebra rib contains stale routes, which will not be deleted ever. Also depending on preference calculated by zebra, these stale route result in no update to kernel and FPM.

## 2. Observation:
> Below analysis were done before deciding on the approaches, which can be used to solve above problem.

### 2.1  Zebra restart with -k -r options.
Before restart:
```
B>* 100.1.0.32/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.0/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.1/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.2/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.3/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.4/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
C>* 172.25.11.0/24 is directly connected, eth0
```
After restart:
Zebra has 2 routes per destination. [Behavior may have changed on later Zebra, i.e >=6.0.2]
```
B   100.1.0.32/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:27
K>* 100.1.0.32/32 via 10.0.0.63, Ethernet124
B   172.16.16.0/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:27
K>* 172.16.16.0/32 via 10.0.0.63, Ethernet124
B   172.16.16.1/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:27
K>* 172.16.16.1/32 via 10.0.0.63, Ethernet124
B   172.16.16.2/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:27
K>* 172.16.16.2/32 via 10.0.0.63, Ethernet124
B   172.16.16.3/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:27
K>* 172.16.16.3/32 via 10.0.0.63, Ethernet124
B   172.16.16.4/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:27
K>* 172.16.16.4/32 via 10.0.0.63, Ethernet124
C>* 172.25.11.0/24 is directly connected, eth0
```
Ip monitor: Zebra adds no new route, because it already preferred kernel routes.

----
### 2.2 Kernel static route with same prefix and same NHs.

[Note: Kernel Static route analysis was done in more detail, but is not included in this Design Doc. Because kenrel static routes are not used in detail in SONiC.]

FRR Restart when kernel has extra route same prefix and same NHs but lower matrix than zebra: [Same behavior is observed for high matrix, Zebra always prefere Kernel Route.]

Add Kernel Static route
```
sudo ip route del 172.16.16.2/32 via 10.0.0.63 metric 15
```
Kernel:
```
172.16.16.0     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.1     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.2     10.0.0.63       255.255.255.255 UGH   15     0        0 Ethernet124
172.16.16.3     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.4     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.9     10.0.0.63       255.255.255.255 UGH   0      0        0 Ethernet124
172.25.11.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
240.127.1.0     0.0.0.0         255.255.255.0   U     0      0        0 docker0
```
Frr before restart:
```
B>* 100.1.0.32/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.0/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.1/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.3/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
B>* 172.16.16.4/32 [20/0] via 10.0.0.63, Ethernet124, 00:01:46
K>* 172.16.16.2/32 via 10.0.0.63, Ethernet124
B   172.16.16.2/32 [20/0] via 10.0.0.63, Ethernet124, 00:17:43
C>* 172.25.11.0/24 is directly connected, eth0
```
Ip monitor:
```
sudo ip route add 172.16.16.2/32 via 10.0.0.63
172.16.16.2 via 10.0.0.63 dev Ethernet124
Deleted 172.16.16.2 via 10.0.0.63 dev Ethernet124  proto zebra  metric 20
```
As per IP monitor, Zebra,  after listening about kernel static routes, deletes BGP route from kernel and FPM. For FPM, a code was added to keep protocol inforamtion in APP_DB, which confirm same behavior.

APP_DB before Kernel Static Route:
```
127.0.0.1:6379> HGETALL "ROUTE_TABLE:172.16.16.2"
1) "nexthop"
2) "10.0.0.63"
3) "ifname"
4) "Ethernet124"
5) "protocol"
6) "ZEBRA"
```
After adding kernel Static Routes:
```
127.0.0.1:6379> HGETALL "ROUTE_TABLE:172.16.16.2"
1) "nexthop"
2) "10.0.0.63"
3) "ifname"
4) "Ethernet124"
5) "protocol"
6) "KERNEL"
```
After restart routes remains same as above in kernel and FPM, because no updates was sent from Zebra.

-----
###  2.3 Timing between route deletion in Kernel during Zebra restart and route addition in Kernel, when Zebra runs without option -k. [FRR-3.0.3]
Below start_del_time in Epoch shows when first kernel route was deleted.
1554926630 = Wednesday, April 10, 2019 20:03:50
```
Apr 10 20:04:01.354327 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 1 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:02.485333 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 1001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:03.981137 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 2001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:05.108101 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 3001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:06.417365 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 4001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:07.525413 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 5001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:08.594670 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 6001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:10.048414 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 7001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:11.267177 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 8001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:12.292980 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 9001 routes from zebra, startup_del_time 1554926630
Apr 10 20:04:13.881074 falco-test-dut01 NOTICE zebra[58]: frr-kernel: Added 10001 routes from zebra, startup_del_time 1554926630
```
It ~23 secs between first kernel route deletion and to add 6001 routes.

####  2.3.1 On FRR 6.0.2:
1555633942 = Friday, April 19, 2019 00:32:22
```
Apr 19 00:32:24.747571 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 1 routes. Del time 1555633942
Apr 19 00:32:24.876074 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 1001 routes. Del time 1555633942
Apr 19 00:32:25.055259 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 2001 routes. Del time 1555633942
Apr 19 00:32:25.210264 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 3001 routes. Del time 1555633942
Apr 19 00:32:25.388983 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 4001 routes. Del time 1555633942
Apr 19 00:32:25.527489 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 5001 routes. Del time 1555633942
Apr 19 00:32:25.653258 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 6001 routes. Del time 1555633942
Apr 19 00:32:25.789716 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 7001 routes. Del time 1555633942
Apr 19 00:32:25.951092 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 8001 routes. Del time 1555633942
Apr 19 00:32:28.949341 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 9001 routes. Del time 1555633942
Apr 19 00:32:29.072326 falco-test-dut01 NOTICE bgp#zebra[86]: frr-kernel: Added 10001 routes. Del time 1555633942
```
It ~7 secs between first kernel route deletion and to add 6001 routes.

----
### 2.5 Static ARP Entries Analysis:
Add Static ARP Entry before Zebra Restart:
```
sudo ip -4 neigh add 172.16.16.4 dev Ethernet120 lladdr 00:11:22:33:44:55
1172.16.16.4              ether   00:11:22:33:44:55   CM                    Ethernet120
```
Ip monitor:
```
172.16.16.4 dev Ethernet120 lladdr 00:11:22:33:44:55 PERMANENT
```
Kernel routes:
```
100.1.0.32      10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.0     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.0     0.0.0.0         255.255.255.0   U     0      0        0 Ethernet120
172.16.16.1     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.2     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.3     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
172.16.16.4     10.0.0.63       255.255.255.255 UGH   20     0        0 Ethernet124
```

Zebra Route:
[Zebra does not learn about ARP, In Sonic NeighSyncd listens to netlink and populates APP_DB. So Sonic and Linux kernel both keep route table and Neighbour table seperately. Which suggests if a zebra route has same prefix as ARP\NDP Entry then Conflict happens only in H/W, and it depends on H/W which one will be preferred.]
```
C>* 172.16.16.0/24 is directly connected, Ethernet120
B>* 172.16.16.0/32 [20/0] via 10.0.0.63, Ethernet124, 00:15:13
B>* 172.16.16.1/32 [20/0] via 10.0.0.63, Ethernet124, 00:15:13
B>* 172.16.16.2/32 [20/0] via 10.0.0.63, Ethernet124, 00:15:13
B>* 172.16.16.3/32 [20/0] via 10.0.0.63, Ethernet124, 00:15:13
B>* 172.16.16.4/32 [20/0] via 10.0.0.63, Ethernet124, 00:15:13
```
APP_DB:
```
127.0.0.1:6379> keys *172.16.16.4*
1) "NEIGH_TABLE:Ethernet120:172.16.16.4"
2) "ROUTE_TABLE:172.16.16.4"
127.0.0.1:6379> hgetall "NEIGH_TABLE:Ethernet120:172.16.16.4"
1) "neigh"
2) "00:11:22:33:44:55"
3) "family"
4) "IPv4"
127.0.0.1:6379> hgetall "ROUTE_TABLE:172.16.16.4"
1) "nexthop"
2) "10.0.0.63"
3) "ifname"
4) "Ethernet124"
127.0.0.1:6379>
```
H/W Entries: (Broadcom)
```
admin@falco-test-dut01:~$ sudo bcmcmd "l3 l3table show" | grep 172.16.16.4
admin@falco-test-dut01:~$ sudo bcmcmd "l3 defip show" | grep 172.16.16.4
32782 0        172.16.16.4/32       00:00:00:00:00:00 100015    0     0     0    0 n
admin@falco-test-dut01:~$ sudo bcmcmd "l3 egress show" | grep 100015
100015  52:54:00:92:6c:c0 4087    8   130    0        -1   no   no    6   no
```
Restart Zebra\FRR will have no impact on Neigh_Table.

----

### 2.6 Kernel keeps only one copy of Routes from one source.
This is important because if zebra sends multiple adds to kernel for same route via netlink, where rtm_protocol field is same as before then kernel will only update this entry, but will not add a new entry.
To check this, multiple add\update were sent to kernel from zebra.
```
falco-test-dut01 NOTICE bgp#zebra[85]:  P 0.0.0.0/0 rn 0x556d54234ca0
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.1/32 rn 0x556d5423d780
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.2/32 rn 0x556d5423da00
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.3/32 rn 0x556d5423dc80
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.4/32 rn 0x556d5423df80
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.5/32 rn 0x556d5423e280
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.8/32 rn 0x556d5423ea00
falco-test-dut01 NOTICE bgp#zebra[85]:  P 100.1.0.1/32 rn 0x556d5423d280
falco-test-dut01 NOTICE bgp#zebra[85]:  P 192.168.0.6/32 rn 0x556d5423e500
falco-test-dut01 NOTICE bgp#zebra[85]:  P 100.1.0.2/32 rn 0x556d5423d500
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d54234ca0
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423d780
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423da00
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423dc80
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423df80
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423e280
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423ea00
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d54334390
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423d280
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423e500
falco-test-dut01 NOTICE bgp#zebra[85]: Send Update to kernel rn 0x556d5423d500
```
But kernel react to only those which has some update, and does keep only one copy of route.
Ip monitor:
```
admin@falco-test-dut01:~$ ip monitor
192.168.0.4 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
192.168.0.8 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
192.168.0.9 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
Deleted 192.168.0.7 via 10.0.0.3 dev Ethernet4 proto 186 src 10.1.0.32 metric 20
```

## 3. Proposed Solution and comparison:


| Field | FPMSYNCD | ORCHAGENT | ZEBRA RIB |
| ------ | ------ |------ | ------ |
| Description   | Utilize current approach of DB reconciliation in FPMSyncd. Once reconciliation is done, send the netlink to kernel with add/del/change to APP_DB. | Utilize current approach of DB reconciliation in FPMSyncd. Inside Orchagent, When RouteOrch class processes these APP_DB route entries to update ASIC_DB, same time send the netlink to kernel. | Read kernel Routes while Zebra starts up, and change Zebra RIB calculation to reconcile with old kernel route. After reconciliation , Send an update to kernel and FPM about new route. Also delete stale kernel routes from rib after reconciliation. FpmSyncd DB reconcilation code may go away.  |
|Special handling while System Restart (warm reboot). |     Since Kernel route will be deleted due to restart, FPMSyncd needs to populate kernel routes while restoration process. While restoration FPMSyncd Reads APP_DB Routes in a MAP. |   This approach needs no special handling for this case, since after coming up Orchagent will recompile APP_DB route entries to create new ASIC_DB. Kernel routes will be installed during this compilation. |    During startup Zebra has to read routes from APP_DB for restoration. Which means Many APIs must be exposed to Zebra. This may not be needed, if current APP_DB reconciliation remains in FPMsyncd. But it is good to deprecate FpmSyncd DB reconcilation, with that, kernel route should be populated similar to neigh table from APP_DB after restart. |
| SWSS docker restart | No special case handling. | Orchagent will recompile APP_DB route entries to create new ASIC_DB. Orchagent will send another netlink to kernel.  If no change (or just add\change) in DB, Kernel routes will remain same. Because kernel keeps only one route per prefix from Zebra. If route del in APP_DB was done during swss restart. Orchagent will send netlink del msg to kernel, because events are queued in DB. | No special case handling. |
| OwnerShip |   FPMSyncd will be clear owner of route both in Kernel and DB. May rename as RouteMgrD.|  Source of truth will be APP_DB for kernel Routes. FPMSyncd will add APP_DB route and Orchagent will add kernel Route.    | Similar as today. Zebra will be Routing Manager and owner.|
| If Kernel Netlink fails with ENOMEM.  | No retry mechanism. Should system continue working, as per today No, because Zebra exits in such cases.    | No retry mechanism. Should system continue working, as per today No, because Zebra exits in such cases. | No retry mechanism. Should system continue working, as per today No, because Zebra exits in such cases.|
| Kernel Fails with EAGAIN. |   No retry mechanism. Should system continue working, as per today YES, because Zebra assume it as success case. APP_DB and kernel will not be in sync. | Same |  Same |
| Support More Families like MPLS, CLNS and VRF later. |    FPMSyncd will need Individual deserialization mechanism in place to convert from Netlink to Tuple for each family. With this approach serialization mechanism will be needed in FPMsyncd. | FPMSyncd will need Individual deserialization mechanism in place to convert from Netlink to Tuple for each family. With this approach serialization mechanism will be needed in Orchagent.   | Separate handing per Family is not needed, as of now, Zebra does not support MPLS. |
| EOR Handling. |   EOR must be passed\extended till FPMSyncd, so that  FPMSyncd reconciliation steps can be executed as per EOR arrival. |     EOR must be passed\extended till FPMSyncd, so that  FPMSyncd reconciliation steps can be executed as per EOR arrival.   | EOR processing may remain till Zebra. |
| Knob known to daemon. | FPMSyncd must know about warm reboot knob, frr restart knob and warm restart FRR timer. (Already done). |     Same as today. |    Zebra must have an option to exceute kernel reconciliation at start. |
| When static (or kernel learned) Route is Added before FRR restart. [See Observations section for complete data.]  | When Static Route is added, Zebra learns about it and sends a delete to kernel and FPM. So kernel and FPM keep only one copy of route for this prefix.  After Zebra Restart:  [ADD= Zebra learns same route, Change = Zebra learns same prefix with NH change, DEL = Zebra does not learn same prefix.]  # Case ADD: After restart Zebra will learn kernel static route from kernel while start up. And Zebra will learn same prefix Route via BGP. Zebra will choose kernel route in RIB calculation. Zebra will send no update to APP_DB and kernel. [**This case shows rtm_protocol = RTPROT_ZEBRA in netlink message is necessary, else Zebra would not have considered Static Route in RIB Calculation.] As per current code, it will delete APP_DB Route. [APP_DB reconciliation will not delete Route if rtm_protocol is stored in DB.] # Case Change: Same as ADD. # Case Del: Same as ADD, except Zebra will not learn any BGP Route for same prefix. | Same | Rib Calculation will not change for Static or kernel learned route. It will work fine without FpmSyncd DB reconciliation code. |
| When static (or kernel learned) Route is Added during FRR restart. i.e. Zebra was down when kernel route was added.   | This is hard to recover scenario. Since Zebra is down while static route is added to kernel. No delete message is received by kernel and FPM. As a result kernel has 2 routes for same prefix and APP_DB has zebra route [non static route] in DB. | Same | Same |
| ARP/NDP is learned which has same prefix as zebra route. | After learning, Kernel will add ARP in neigh table which will have pointer from route table, but will not have an entry in route table. So Zebra and FPM will play no role in it because they never know about the ARP entry. From neighsyncd, ARP entry will be installed in APP_DB, then ASIC_DB and then in H/W. So H/W will learn about same prefix as neighbor and as Route. H/W behavior is out of scope because it may vary.
| **Brief Implementation details.** |
| Zebra code changes: | Zebra uses kernel_route_rib() to add/del/change in kernel route. kernel_route_rib() calls netlink_route_multipath(). In netlink_route_multipath(), update must be blocked for single\multi path route to kernel. Propagate EOR down to FPMSyncd after sending routes update to FPMSyncd. Note: Zebra will be started with -r option (Retain kernel Route option) but without -k option. So After restart Zebra will try to delete all Zebra routes from kernel, but due to block in netlink_route_multipath(), no change will go to kernel. This Delete will go to FPM for previous Zebra Routes, but this is fine because FPMSyncd keeps only one entry for each destprefix. So at last the final update will come into effect. | Same as Fpmsyncd | During startup in netlink_route_change_read_unicast(), all stale zebra routes learned from kernel are timestamped while getting added in RIB. After reading all routes from kernel, zebra will record its startup time. This way all routes which are in RIB before zebra startup_time became stale. If a route is learned for same prefix then stale route will be marked for deletion while adding new route in rib_add_multipath(). For remaining stale routes, a sweep function will be called with EOR or with timer. An option will be introduced in Zebra to enable kernel reconcile functionality.|
| FPMSyncd Code changes | RouteTableWarmStartHelper will be inherited from WarmStartHelper class, which will override  WarmStartHelper::reconcile() to send netlink message to kernel while updating DB. FpmSyncd needs to handle EOR message and call reconciliation when arrive. To handle warm reboot case. Similar handler must be called from runRestoration(). Netlink message creation part should be implemented for each family. | FpmSyncd needs to handle EOR message and call reconciliation when arrive. | FpmSyncd DB reconciliation may be deprecated. |
| Orchagent Code Changes |  N/A | In RouteOrch Class functions, whenever SaiRedis API call is done to update ASIC_DB, a call to netlink_kernel_route() must be done to sent netlink msg to kernel. Netlink message creation part should be implemented for each family. | N/A |

## 4. Approach Selected

Approach 3 : Zebra RIB Calculation is chosen to address FRR-Kernel Reconciliation after considering all above comparison points.

## 5. Low Level details:

### 5.1 Before Fix:

![](https://github.com/praveen-li/SONiC/blob/frr_kernel_design_utp_doc/doc/frr-kernel/img/Before%20frr_kernel%20fix.png)

Above image explains the Zebra behavior right now on startup with -k (keep_kernel_mode option.
```
1.) Zebra reads kernel routes including previous instance of Zebra routes.

2.) Zebra pushes these routes in RIB Table as per family of route.

3.) Rnode creation and route_entry creation of old kernel route is done and route_entry is inserted in Rnode of the destprefix.
    Next-hops for this route will be markes as active, since this route is learned from Kernel.
    Note: This will result in call to rib_process, but since Rnode contains only one route which is already in FIB, so rib_process will result in NO_OP.

4.) Bgpd will queue new routes to Zebra after getting first keepalive (implicit EOR) from bgp peer.

5.) Zebra will process new routes and call rib_add() for this route.

6.) A new route_entry will be created and will be inserted in correct Rnode. There may be 2 scenarios here,
    a.) Rnode already contains other routes including old kernel routes or
    b.) new Rnode is created for this route_entry.

7.) Updated Rnode will be queued for rib processing. During rib processing, Zebra will run best route selection,
    which on most of the FRR version will select old kernel route which is already marked as active in FIB.

8.) No update will be sent to Kernel and FPM, which may result in route deletion from APP_DB as per current Fpmsyncd DB reconciliation code.
    Update will be sent only for those route for which stale kernel route is not present.
```

Current behavior will result in:
```

1.) Route deletion from APP_DB.

2.) Stale route in Kernel.

3.) Stale routes in Zebra RIB.
```

### 5.2 After Fix:

![](https://github.com/praveen-li/SONiC/blob/frr_kernel_design_utp_doc/doc/frr-kernel/img/After%20frr_kernel%20fix.png)

```

1.) Zebra will start with an option -K <secs> to specify kernel level graceful restart. Zebra reads kernel routes including previous instance of Zebra routes.

2.) Zebra pushes these routes in RIB Table as per family of route.

3.) Rnode creation and route_entry creation of old kernel route is done and route_entry is inserted in Rnode of the destprefix. Zebra record the timestamp for each route_entry when it is added to RIB.

Next-hops for this route will be markes as active, since this route is learned from Kernel.

Note: This will result in call to rib_process, but since Rnode contains only one route which is already in FIB, so rib_process will result in NO_OP.

Around this time initialization of Zebra concludes. With fix, we record this time as zebra startup_time. This way all routes which were added before zebra startup_time will be treated as stale routes.

After recording zebra startup_time, A timer will start (default 60 secs) to clean stale kernel routes. Within this timer, If same prefix is learned via any protocol, kernel and FPM will be updated gracefully, in this case, similar to rib change.

4.) Bgpd will queue new routes to Zebra after getting first keepalive (implicit EOR) from bgp peer.

5.) Zebra will process new routes and call rib_add() for this route.

6.) A new route_entry will be created and will be inserted in correct Rnode. There may be 2 scenarios here,

a.) Rnode already contains other routes including old kernel routes with rt->uptime before zebra startup_time or

b.) a new Rnode is created for this route_entry.

In first case, if previously exist route is marked with ZEBRA_FLAG_SELF_ROUTE and rt->uptime is before zebra startup_time, then previous route will be marked for deletion.

7.) Updated Rnode will be queued for rib processing. During rib processing, Zebra will run best route selection,

which will select newly learned route since stale kernel route is marked for deletion.

8.) Update will be sent to Kernel and FPM in all cases.

9.) Upon timer expire, a sweep function will mark all reamining stale routes with for deletion.

Eventually rib_process function will free stale route.

10.) This will result in delete update to kernel and FPM.
```

After fix, it will result in:
```
1.) Kernel and FPM getting updated only when (and as soon as) new route is learned.

2.) Stale routes in Kernel and fpm will be cleaned after timeout.

3.) No Stale routes in Zebra RIB.
```

## 6. Code Details:
-  new option to zebra:

A new option -K <secs> is added to zebra. -K is chosed to match with -k (small -k) because both deals with stale kernel routes.

Use Case:

zebra -K 30

(Option -K is for kernel level graceful restart. 30 is timer after which all stale kernel routes will be cleaned. With in 30 mins all newly learned kernel routes will be gracefully updated.)

[doc/user/zebra.rst](https://github.com/FRRouting/frr/pull/4301/files#diff-c6eff7d9eda13578a6894349a4c281cc "doc/user/zebra.rst")

```
.. option:: -K  TIME, --graceful_restart  TIME
When zebra starts up, don't delete old self inserted routes.
If this option is specified, the graceful restart time is TIME seconds.
Zebra, when started, will read in routes. Those routes that Zebra
identifies that it was the originator of will be swept in TIME seconds.
If no time is specified then we will sweep those routes immediately.
```

[zebra/main.c](https://github.com/FRRouting/frr/pull/4301/files#diff-5f27d203124c7836aa67ed78241fdd5d "zebra/main.c")

```
{"retain", no_argument, NULL, 'r'},

+  {"kernel_gr", required_argument, NULL, 'K'},

#ifdef HAVE_NETLINK

{"vrfwnetns", no_argument, NULL, 'n'},

int main(int argc, char **argv)

frr_opt_add(

-  "bakz:e:l:r"

+  "bakz:e:l:r:K"

#ifdef HAVE_NETLINK

"s:n"

#endif

int main(int argc, char **argv)

"  -l, --label_socket  Socket to external label manager\n"

"  -k, --keep_kernel  Don't delete old routes which were installed by zebra.\n"

"  -r, --retain  When program terminates, retain added route by zebra.\n"

+  "  -K, --kernel_gr  Zebra graceful restart at kernel level. Arg: timer to expire stale routes\n"

#ifdef HAVE_NETLINK

"  -n, --vrfwnetns  Use NetNS as VRF backend\n"

"  -s, --nl-bufsize  Set netlink receive buffer size\n"

@@ -311,6 +313,13 @@ int main(int argc, char **argv)

case 'r':

retain_mode = 1;

break;

+  case 'K':

    +  kernel_gr = 1;
    +  kernel_gr_timer = atoi(optarg);
    +  /* Allow all positive values for testing. */
+  if (kernel_gr_timer < 1)
    +  kernel_gr_timer = ZEBRA_KERNEL_GR_TIME;
    +  break;

```

A timer will start (default 60 secs) to clean stale kernel routes.

File: zebra/main.c

```
int main(int argc, char **argv)
/*
 * Initialize NS( and implicitly the VRF module), and make kernel
 * routing socket.
 */

zebra_ns_init((const char *)vrf_default_name_configured);

/*
 * zebra has learned kernel routes on startup. Start a timer to
 * sweep stale kernel route. Within this timer, newly learned
 * routes are updated to kernel gracefully.
 */
if (kernel_gr)
    thread_add_timer(zrouter.master, rib_sweep_stale_rt_kernel_gr,
        RB_MIN(vrf_id_head, (&vrfs_by_id)), kernel_gr_timer, NULL);
```

File: zebra\zebra_rib.c

```
int rib_add_multipath(afi_t afi, safi_t safi, struct prefix *p,

+  /* If kernel_gr is set, then mark Zebra-originated route
+  * for deletion. Zebra learned these routes from kernel while
+  * start up. Now, since we learned new route for same destination,
+  * this is the time to clear stale route, so that both kernel
+  * and FPM are updated while rib_process. This will result in no
+  * traffic loss, if same route->NH is learned after startup.
+ */
+
+  if (kernel_gr && !kernel_stale_rt
+   && (same->uptime < zrouter.startup_time)) {
+   ++zrouter->zebra_stale_rt_del;
+   if (IS_ZEBRA_DEBUG_RIB)
+       rnode_debug(rn, same->vrf_id, "kernel_gr: match, add %lu del %lu rn %p",
+           zrouter->zebra_stale_rt_add, zrouter->zebra_stale_rt_del, rn);
+   kernel_stale_rt = same;
+   continue;
+  }
```

File zebra\zebra_rib.c

```
/* Sweep all RIB tables after the timer if kernel_gr is set. */
int rib_sweep_stale_rt_kernel_gr(struct thread *thread)
{
    struct vrf *vrf = THREAD_ARG(thread);
    struct zebra_vrf *zvrf = NULL;
    zlog_notice("kernel_gr: timer_expire before sweep: add %lu, del %lu",
    zrouter.zebra_stale_rt_add, zrouter.zebra_stale_rt_del);
    if (!kernel_gr)
    return -1;
    do {
        zvrf = vrf->info;
        if (zvrf) {
            /* Break, soon after all kernel routes are swept. */
            IF_ANY_KERNEL_STALE_RT
            rib_sweep_table(zvrf->table[AFI_IP][SAFI_UNICAST]);
            IF_ANY_KERNEL_STALE_RT
            rib_sweep_table(zvrf->table[AFI_IP6][SAFI_UNICAST]);
        }
        vrf = RB_NEXT(vrf_id_head, (vrf));
        /* reschedule after 1 secs, if CPU must yield */
        if (thread_should_yield(thread)) {
            thread_add_timer(zrouter.master, rib_sweep_stale_rt_kernel_gr,
                vrf, 1, NULL);
            return 0;
        }
    } while(vrf);

        zlog_notice("kernel_gr: timer_expire after sweep: add %lu, del %lu",
        zrouter.zebra_stale_rt_add, zrouter.zebra_stale_rt_del);

        zlog_notice("kernel_gr: Reset kernel_gr = 0");
        kernel_gr = 0;

        return 0;
}
```

## 7. Unit Test Plan:

Unit Test Plan includes below 3 test cases: [All 3 test cases will be repeated for IPV4 and IPV6 family]

### 7.1 Test Cases.

#### Test Case 1.) Ping\Fast Ping 3 destinations using PTF from the source address which used BGP Routes. Ping will run continuosly during FRR restart.
    -  Create Ping packet in PTF.
    -  Create Expected Packet.
    -  Sent Ping packet on port 1.
    -  Verify expected Packet on Port 2.

#### Test Case 2.) Test add, change and delete in BGP prefixes across FRR restart.

    - Have 2 BGP peers publishing 5 prefixes each, where 2 prefixes are published from both peers.
    - Observe expected routes in Zebra and Kernel.
    - Stop FRR
    - Add a new prefix to publish in peer1.
    - Add a prefix to publish in peer1 which was published only from peer 2 before.
    - Delete a prefix from peer2 which was published from both peer1 and peer2.
    - Delete a prefix from peer2 which was published only from peer 2 before.
    - Start FRR.
    - Observe Zebra logs, ip monitor, kernel routes and Zebra routes.

#### Test Case 3.) Scaled testing: Perform FRR restart with  > 6 K routes published from at least 4 peers. [6500 routes with 32 peers, as per T1 topology], [6k routes and 4 BGP peers as per T0]

    - Have atleast >3 BGP peers publishing same 6k prefixes. Rest BGP peers can publish 10-15 routes each which are unique.
    - Observe expected routes in Zebra and Kernel.
    - Stop FRR
    - Bring 1 BGP peer down which publishes 6k routes. [Change case ECMP to Non ECMP].
    - Change all published prefixes from 1 BGP peer which publishes 10-15 routes.  [ADD and DELETE case]
    - Start FRR.
    - Observe Zebra logs, ip monitor, kernel routes and Zebra routes.

#### Test case 4.) Add 12 k routes from sharpd and then restart zebra with -K 35 option. After restart,  enter new routes.

#### Test case 5.) Add 14 k routes from sharpd and then restart zebra with -K 55 option secs. After restart add no routes.

#### Test 6: Test with  900 K routes,  with -K 25. Install same 900K routes after restart.

#### Test 7: Test with  900 K routes,  with -K 20.  Do not install any routes after restart.

### 7.2 Details of Test Cases:

#### Test Case 1.) Ping\Fast Ping 3 destinations using PTF from the source address which used BGP Routes in DUT. Ping will run continuosly during FRR restart.

   **Verify expected Packet on Port 2.**

For Example: If installed BGP routes are as below:
```
dut01# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR,
       > - selected route, * - FIB route
B>* 192.168.0.4/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.5/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
  *                       via 10.0.0.3, Ethernet4, 00:00:29
B>* 192.168.0.6/32 [20/0] via 10.0.0.3, Ethernet4, 00:00:29
B>* 192.168.0.8/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.9/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
```

**Create Ping packet in PTF.**

PTF ICMP packet will be:
```
pkt = simple_icmp_packet(pktlen=pktlen,
    eth_dst=self.router_mac,
    eth_src=src_mac,
    ip_src="192.168.0.6",
    ip_dst="10.0.0.0",
    ip_ttl=64)

Packet:
00:e0:ec:7b:ba:bb > 52:54:00:4b:bb:87, ethertype 802.1Q (0x8100), length 102: vlan 1681, p 0, ethertype IPv4, 192.168.0.6 > 10.0.0.0: ICMP echo request, id 19456, seq 9, length 64
```

**Create Expected Packet.**
```
exp_pkt = simple_icmp_packet(pktlen=pktlen,
                eth_src=self.router_mac,
                ip_dst=ip_src,
                icmp_type=0)
```

**Sent Ping packet on port 1.**
```
send_packet(self, src_port, pkt)
```

**Then Verify the Packet on Port 2:**
```
(matched_index, received) = verify_packet_any_port(self, masked_exp_pkt, [2]])
```

####  Test Case 2.) Test add, change and delete in BGP prefixes across FRR restart.

- Have 2 BGP peers publishing 5 prefixes each, where 2 prefixes are published from both peers.

Routes are published to DUT from 2 BGP peers: (Track 192.168.0.* routes)

**Peer1:**
```
ARISTA01T2(config)#show ip route

VRF name: default
Codes: C - connected, S - static, K - kernel,
       O - OSPF, IA - OSPF inter area, E1 - OSPF external type 1,
       E2 - OSPF external type 2, N1 - OSPF NSSA external type 1,
       N2 - OSPF NSSA external type2, B I - iBGP, B E - eBGP,
       R - RIP, I L1 - ISIS level 1, I L2 - ISIS level 2,
       A B - BGP Aggregate, A O - OSPF Summary,
       NG - Nexthop Group Static Route, V - VXLAN Control Service

Gateway of last resort is not set

 C      10.0.0.0/31 is directly connected, Ethernet1
 B E    10.1.0.32/32 [200/0] via 10.0.0.0, Ethernet1
 C      10.10.246.0/24 is directly connected, Ethernet9
 C      100.1.0.1/32 is directly connected, Loopback0
 S      192.168.0.1/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.2/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.3/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.4/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.5/32 [1/0] via 10.10.246.100, Ethernet9
```


**Peer2:**
```
ARISTA02T2(config)#show ip route

VRF name: default
Codes: C - connected, S - static, K - kernel,
       O - OSPF, IA - OSPF inter area, E1 - OSPF external type 1,
       E2 - OSPF external type 2, N1 - OSPF NSSA external type 1,
       N2 - OSPF NSSA external type2, B I - iBGP, B E - eBGP,
       R - RIP, I L1 - ISIS level 1, I L2 - ISIS level 2,
       A B - BGP Aggregate, A O - OSPF Summary,
       NG - Nexthop Group Static Route, V - VXLAN Control Service

Gateway of last resort is not set

 C      10.0.0.2/31 is directly connected, Ethernet1
 B E    10.1.0.32/32 [200/0] via 10.0.0.2, Ethernet1
 C      10.10.246.0/24 is directly connected, Ethernet9
 C      100.1.0.2/32 is directly connected, Loopback0
 S      192.168.0.4/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.5/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.6/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.7/32 [1/0] via 10.10.246.100, Ethernet9
 S      192.168.0.8/32 [1/0] via 10.10.246.100, Ethernet9
```

- Observe expected routes in Zebra and Kernel.

**Zebra DUT:**
```
dut01# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR,
       > - selected route, * - FIB route

B>* 0.0.0.0/0 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
  *                  via 10.0.0.3, Ethernet4, 00:04:30
C>* 10.0.0.0/31 is directly connected, Ethernet0, 00:04:32
C>* 10.0.0.2/31 is directly connected, Ethernet4, 00:04:32
C>* 10.1.0.32/32 is directly connected, lo, 00:04:32
B>* 100.1.0.1/32 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
B>* 100.1.0.2/32 [20/0] via 10.0.0.3, Ethernet4, 00:04:30
C>* 172.25.11.0/24 is directly connected, eth0, 00:04:32
B>* 192.168.0.1/32 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
B>* 192.168.0.2/32 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
B>* 192.168.0.3/32 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
B>* 192.168.0.4/32 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
  *                       via 10.0.0.3, Ethernet4, 00:04:30
B>* 192.168.0.5/32 [20/0] via 10.0.0.1, Ethernet0, 00:04:30
  *                       via 10.0.0.3, Ethernet4, 00:04:30
B>* 192.168.0.6/32 [20/0] via 10.0.0.3, Ethernet4, 00:04:30
B>* 192.168.0.7/32 [20/0] via 10.0.0.3, Ethernet4, 00:04:30
B>* 192.168.0.8/32 [20/0] via 10.0.0.3, Ethernet4, 00:04:30
```


**Kernel Route: route -n**
```
admin@dut01:~$ sudo route -n
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         10.0.0.1        0.0.0.0         UG    20     0        0 Ethernet0
10.0.0.0        0.0.0.0         255.255.255.254 U     0      0        0 Ethernet0
10.0.0.2        0.0.0.0         255.255.255.254 U     0      0        0 Ethernet4
100.1.0.1       10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
100.1.0.2       10.0.0.3        255.255.255.255 UGH   20     0        0 Ethernet4
172.25.11.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
192.168.0.1     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.2     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.3     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.4     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.5     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.6     10.0.0.3        255.255.255.255 UGH   20     0        0 Ethernet4
192.168.0.7     10.0.0.3        255.255.255.255 UGH   20     0        0 Ethernet4
192.168.0.8     10.0.0.3        255.255.255.255 UGH   20     0        0 Ethernet4
240.127.1.0     0.0.0.0         255.255.255.0   U     0      0        0 docker0
```

**Stop FRR**
```
admin@dut01:~$ date
Tue Apr 23 22:05:02 UTC 2019
admin@dut01:~$ sudo service bgp stop
```


**Changes in Published route**
```
Peer1:
ip route 192.168.0.8/32 10.10.246.100  (Change case: NH move from Peer 2 to Peer 1)
ip route 192.168.0.9/32 10.10.246.100  (Absolute add case: New Route)

Peer2:
no ip route 192.168.0.4/32 10.10.246.100  (Change case: from ECMP to non_ecmp)
no ip route 192.168.0.7/32 10.10.246.100  (Delete Case) (Should be deleted after time out)
no ip route 192.168.0.8/32 10.10.246.100  (Change case: )
```

**Start  FRR**
```
admin@dut01:~$ date
Tue Apr 23 22:05:48 UTC 2019
admin@dut01:~$ sudo service bgp start
```

**Zebra logs:
Note: All logs may not be part of final diff**
```
Apr 23 22:05:59.589030 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 1 P 0.0.0.0/0 rn 0x556d54234ca0
Apr 23 22:05:59.589301 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 2 P 192.168.0.1/32 rn 0x556d5423d780
Apr 23 22:05:59.589378 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 3 P 192.168.0.2/32 rn 0x556d5423da00
Apr 23 22:05:59.589691 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 4 P 192.168.0.3/32 rn 0x556d5423dc80
Apr 23 22:05:59.589788 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 5 P 192.168.0.4/32 rn 0x556d5423df80
Apr 23 22:05:59.589859 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 6 P 192.168.0.5/32 rn 0x556d5423e280
Apr 23 22:05:59.589931 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 7 P 192.168.0.8/32 rn 0x556d5423ea00
Apr 23 22:05:59.590001 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 8 P 100.1.0.1/32 rn 0x556d5423d280
Apr 23 22:05:59.590072 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 9 P 192.168.0.6/32 rn 0x556d5423e500
Apr 23 22:05:59.590142 dut01 DEBUG bgp#zebra[85]: kernel_gr: match, A 11 D 10 P 100.1.0.2/32 rn 0x556d5423d500
Apr 23 22:05:59.599051 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d54234ca0
Apr 23 22:05:59.599334 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423d780
Apr 23 22:05:59.599462 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423da00
Apr 23 22:05:59.599533 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423dc80
Apr 23 22:05:59.599665 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423df80
Apr 23 22:05:59.600987 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423e280
Apr 23 22:05:59.600987 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423ea00
Apr 23 22:05:59.600987 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d54334390
Apr 23 22:05:59.600987 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423d280
Apr 23 22:05:59.601044 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423e500
Apr 23 22:05:59.601044 dut01 DEBUG bgp#zebra[85]: Send Update to kernel rn 0x556d5423d500

Apr 23 22:06:12.615442 dut01 NOTICE bgp#zebra[85]: kernel_gr: timer_expire stats before flush: add 11, del 10
Apr 23 22:06:12.615442 dut01 NOTICE bgp#zebra[85]: kernel_gr: sweep, A 11 D 11 P 192.168.0.7/32 rn 0x556d5423e780
Apr 23 22:06:12.615741 dut01 DEBUG bgp#zebra[85]: Send Delete to kernel rn 0x556d5423e780
Apr 23 22:06:12.615824 dut01 NOTICE bgp#zebra[85]: kernel_gr: timer_expire stats after flush: add 11, del 11
Apr 23 22:06:12.615896 dut01 NOTICE bgp#zebra[85]: kernel_gr: Reset kernel_gr = 0
```

**Ip monitor:**
```
admin@dut01:~$ ip monitor
192.168.0.4 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
192.168.0.8 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
192.168.0.9 via 10.0.0.1 dev Ethernet0 proto 186 src 10.1.0.32 metric 20
Deleted 192.168.0.7 via 10.0.0.3 dev Ethernet4 proto 186 src 10.1.0.32 metric 20
```

**Zebra DUT:**
```
dut01# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR,
       > - selected route, * - FIB route

B>* 0.0.0.0/0 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
  *                  via 10.0.0.3, Ethernet4, 00:00:29
C>* 10.0.0.0/31 is directly connected, Ethernet0, 00:00:31
C>* 10.0.0.2/31 is directly connected, Ethernet4, 00:00:31
C>* 10.1.0.32/32 is directly connected, lo, 00:00:31
B>* 100.1.0.1/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 100.1.0.2/32 [20/0] via 10.0.0.3, Ethernet4, 00:00:29
C>* 172.25.11.0/24 is directly connected, eth0, 00:00:31
B>* 192.168.0.1/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.2/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.3/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.4/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.5/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
  *                       via 10.0.0.3, Ethernet4, 00:00:29
B>* 192.168.0.6/32 [20/0] via 10.0.0.3, Ethernet4, 00:00:29
B>* 192.168.0.8/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
B>* 192.168.0.9/32 [20/0] via 10.0.0.1, Ethernet0, 00:00:29
```

**Kernel:**
```
admin@dut01:~$ sudo route -n
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         10.0.0.1        0.0.0.0         UG    20     0        0 Ethernet0
10.0.0.0        0.0.0.0         255.255.255.254 U     0      0        0 Ethernet0
10.0.0.2        0.0.0.0         255.255.255.254 U     0      0        0 Ethernet4
100.1.0.1       10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
100.1.0.2       10.0.0.3        255.255.255.255 UGH   20     0        0 Ethernet4
172.25.11.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
192.168.0.1     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.2     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.3     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.4     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.5     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.6     10.0.0.3        255.255.255.255 UGH   20     0        0 Ethernet4
192.168.0.8     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
192.168.0.9     10.0.0.1        255.255.255.255 UGH   20     0        0 Ethernet0
240.127.1.0     0.0.0.0         255.255.255.0   U     0      0        0 docker0
```


#### Test Case 3.) Scaled testing: Perform FRR restart with  > 6 K routes published from at least 4 peers. [6500 routes with 32 peers, as per T1 topology], [6k routes and 4 BGP peers as per T0]
Steps will be similar to Test case 2.

#### Test case 4.) Add 12 k routes from sharpd and then restart zebra with -K 35 option. After restart,  enter new routes as shown below.

Routes before restart:
——————
sharp install route 10.0.0.0 nexthop 172.25.11.53 6000
sharp install route 20.0.0.0 nexthop 172.25.11.53 6000

Routes after restart:
——————
sharp install route 10.0.0.0 nexthop 172.25.11.43 6000
sharp install route 20.0.0.0 nexthop 172.25.11.53 5000
sharp install route 30.0.0.0 nexthop 172.25.11.53 3000

Expectation:
——————
Prefix 10.0.0.0:   should be update to kernel immediately with new next-hop.
Prefix 20.0..0.0:  5k routes should be updated to kernel with same NH. Extra 1 k routes must be deleted later after around 35 secs.
Prefix 30.0.0.0: routes must be update to kernel immediately.
Zebra log must show that 12k routes were added with Stale flag and 1 were swept after timer expire.

Restart options:
——————
zebra_options="  -r -A 127.0.0.1 -K 35 -s 90000000"

Results:
```
Kernel routes before restart:
——————
Every 5.0s: ./route.sh                                                                                  Fri May  3 22:01:29 2019

Fri May  3 22:01:29 PDT 2019
sudo route -n | grep 10.0 | wc -l
6002
sudo route -n | grep 20.0 | wc -l
6001
sudo route -n | grep 30.0 | wc -l
0

pchaudha@server05:/home/pchaudha/srcCode/pc_frr$ systemctl restart frr
——————

Zebra Logs  and Kernel Routes with timestamp:
——————
May  3 22:01:55 server05 watchfrr[13520]: all daemons up, doing startup-complete notify
May  3 22:01:55 server05 frrinit.sh[13508]:  * Started watchfrr
May  3 22:01:55 server05 systemd[1]: Started FRRouting.…
...

Every 5.0s: ./route.sh                                                                                  Fri May  3 22:02:27 2019

Fri May  3 22:02:11 PDT 2019
sudo route -n | grep 10.0 | wc -l
6003
sudo route -n | grep 20.0 | wc -l
6001
sudo route -n | grep 30.0 | wc -l
3000
…..
Every 5.0s: ./route.sh                                                                                  Fri May  3 22:02:27 2019

Fri May  3 22:02:27 PDT 2019
sudo route -n | grep 10.0 | wc -l
6003
sudo route -n | grep 20.0 | wc -l
6001
sudo route -n | grep 30.0 | wc -l
3000
…..
May  3 22:02:29 server05 zebra[13541]: kernel_gr: timer_expire before sweep: add 12000, del 11000
May  3 22:02:29 server05 zebra[13541]: kernel_gr: timer_expire after sweep: add 12000, del 12000
May  3 22:02:29 server05 zebra[13541]: kernel_gr: Reset kernel_gr = 0
….
[** Stale Flag was added to 12K routes, 11K were learned before timer expires.]
….

Every 5.0s: ./route.sh                                                                                  Fri May  3 22:02:43 2019

Fri May  3 22:02:32 PDT 2019
sudo route -n | grep 10.0 | wc -l
6003
sudo route -n | grep 20.0 | wc -l
5001
sudo route -n | grep 30.0 | wc -l
3000
——————
```

#### Test case 5.) Add 14 k routes from sharpd and then restart zebra with -K 55 option secs. After restart add no routes.

Expectation:
——————
Should delete all routes  from kernel after kernel_gr time expire. Zebra notice level logs must show time and count for routes.
Zebra log must show that 14k routes were added with Stale flag and all 14k were swept after timer expire.

Routes before restart
——————
sharp install route 10.0.0.0 nexthop 172.25.11.43 6000
sharp install route 20.0.0.0 nexthop 172.25.11.53 5000
sharp install route 30.0.0.0 nexthop 172.25.11.53 3000

Restart options:
——————
40 zebra_options="  -r -A 127.0.0.1 -K 55 -s 90000000"

```
pchaudha@server05:/home/pchaudha/srcCode/pc_frr$ systemctl restart frr
——————
Zebra Logs and kernel routes with timestamp:
—————
Fri May  3 22:09:03 PDT 2019
sudo route -n | grep 10.0 | wc -l
6003
sudo route -n | grep 20.0 | wc -l
5001
sudo route -n | grep 30.0 | wc -l
3000
………..
May  3 22:09:04 server05 watchfrr[14963]: all daemons up, doing startup-complete notify
May  3 22:09:04 server05 frrinit.sh[14948]:  * Started watchfrr
May  3 22:09:04 server05 systemd[1]: Started FRRouting.
.....….
Fri May  3 22:09:19 PDT 2019
sudo route -n | grep 10.0 | wc -l
6003
sudo route -n | grep 20.0 | wc -l
5001
sudo route -n | grep 30.0 | wc -l
3000
…………….
May  3 22:09:59 server05 zebra[14985]: kernel_gr: timer_expire before sweep: add 14000, del 0
May  3 22:09:59 server05 NetworkManager[1141]: <info>  [1556946599.5236] platform-linux: netlink: read: too many netlink events. Need to resynchronize platform cache
May  3 22:09:59 server05 NetworkManager[1141]: <info>  [1556946599.5308] platform-linux: netlink: read: too many netlink events. Need to resynchronize platform cache
May  3 22:09:59 server05 NetworkManager[1141]: <info>  [1556946599.5371] platform-linux: netlink: read: too many netlink events. Need to resynchronize platform cache
May  3 22:09:59 server05 NetworkManager[1141]: <info>  [1556946599.5436] platform-linux: netlink: read: too many netlink events. Need to resynchronize platform cache
May  3 22:09:59 server05 zebra[14985]: kernel_gr: timer_expire after sweep: add 14000, del 14000
May  3 22:09:59 server05 zebra[14985]: kernel_gr: Reset kernel_gr = 0
………………
Fri May  3 22:10:02 PDT 2019
sudo route -n | grep 10.0 | wc -l
1
sudo route -n | grep 20.0 | wc -l
0
sudo route -n | grep 30.0 | wc -l
0
```





#### Test 6: Test with  900 K routes,  with -K 25. Install same 900K routes after restart.

Routes before and after restart:
——————
sharp install route 10.0.0.0 nexthop 172.25.11.43 100000
sharp install route 20.0.0.0 nexthop 172.25.11.43 100000
sharp install route 30.0.0.0 nexthop 172.25.11.43 100000
sharp install route 40.0.0.0 nexthop 172.25.11.43 100000
sharp install route 50.0.0.0 nexthop 172.25.11.43 100000
sharp install route 60.0.0.0 nexthop 172.25.11.43 100000
sharp install route 70.0.0.0 nexthop 172.25.11.43 100000
sharp install route 80.0.0.0 nexthop 172.25.11.43 100000
sharp install route 90.0.0.0 nexthop 172.25.11.43 100000

Expectation:
——————
Zebra log must show that 900k routes were added with Stale flag and 0 were swept after timer expire, I.e. all 900K were learned back before timer expire.


ZEbra logs and kernel Routes:
——————
```
Every 3.0s: route -n | wc -l
Fri May  3 22:25:01 2019

900007
…………
May  3 22:25:11 server05 systemd[1]: Started FRRouting.
May  3 22:25:13 server05 systemd[1]: Started CUPS Scheduler.
May  3 22:25:36 server05 zebra[17253]: kernel_gr: timer_expire before sweep: add 900000, del 900000
May  3 22:25:36 server05 zebra[17253]: kernel_gr: timer_expire after sweep: add 900000, del 900000
May  3 22:25:36 server05 zebra[17253]: kernel_gr: Reset kernel_gr = 0
………….
Every 3.0s: route -n | wc -l

Fri May  3 22:25:40 2019

900007
```


#### Test 7: Test with  900 K routes,  with -K 20.  Do not install any routes after restart.

Routes before restart:
——————
sharp install route 10.0.0.0 nexthop 172.25.11.43 100000
sharp install route 20.0.0.0 nexthop 172.25.11.43 100000
sharp install route 30.0.0.0 nexthop 172.25.11.43 100000
sharp install route 40.0.0.0 nexthop 172.25.11.43 100000
sharp install route 50.0.0.0 nexthop 172.25.11.43 100000
sharp install route 60.0.0.0 nexthop 172.25.11.43 100000
sharp install route 70.0.0.0 nexthop 172.25.11.43 100000
sharp install route 80.0.0.0 nexthop 172.25.11.43 100000
sharp install route 90.0.0.0 nexthop 172.25.11.43 100000

Expectation:
——————
Zebra log must show that 900k routes were added with Stale flag and all 900k were swept after timer expire, I.e. all 0 were learned back before timer expire.

ZEbra logs and kernel Routes:
——————
```
Fri May  3 22:27:07 2019

900007
………
May  3 22:27:10 server05 systemd[1]: Started FRRouting.
May  3 22:27:30 server05 zebra[17459]: kernel_gr: timer_expire before sweep: add 900000, del 0
May  3 22:27:31 server05 zebra[17459]: kernel_gr: timer_expire after sweep: add 900000, del 900000
May  3 22:27:31 server05 zebra[17459]: kernel_gr: Reset kernel_gr = 0
………….
Every 3.0s: route -n | wc -l
Fri May  3 22:27:34 2019

7
—————
```

##   8. DB schema
    No Change.
##   9. Flows and SAI APIs
    N/A
##  10. Debug dump and relevant logs
Following logs will appear in Zebra at DEBUG level. For testing LOGs were added at NOTICE level.
```
Apr 23 22:05:59.589030 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 1 P 0.0.0.0/0 rn 0x556d54234ca0
Apr 23 22:05:59.589301 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 2 P 192.168.0.1/32 rn 0x556d5423d780
Apr 23 22:05:59.589378 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 3 P 192.168.0.2/32 rn 0x556d5423da00
Apr 23 22:05:59.589691 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 4 P 192.168.0.3/32 rn 0x556d5423dc80
Apr 23 22:05:59.589788 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 5 P 192.168.0.4/32 rn 0x556d5423df80
Apr 23 22:05:59.589859 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 6 P 192.168.0.5/32 rn 0x556d5423e280
Apr 23 22:05:59.589931 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 7 P 192.168.0.8/32 rn 0x556d5423ea00
Apr 23 22:05:59.590001 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 8 P 100.1.0.1/32 rn 0x556d5423d280
Apr 23 22:05:59.590072 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 9 P 192.168.0.6/32 rn 0x556d5423e500
Apr 23 22:05:59.590142 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: match, A 11 D 10 P 100.1.0.2/32 rn 0x556d5423d500

Apr 23 22:06:12.615442 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: timer_expire stats before flush: add 11, del 10
Apr 23 22:06:12.615442 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: sweep, A 11 D 11 P 192.168.0.7/32 rn 0x556d5423e780
Apr 23 22:06:12.615741 dut01 NOTICE bgp#zebra[85]: Send Delete to kernel rn 0x556d5423e780
Apr 23 22:06:12.615824 dut01 NOTICE bgp#zebra[85]: kernel_reconcile: timer_expire stats after flush: add 11, del 11
```
## 11.  Memory consumption

    Zebra will consume memory similar to -k option till timer with -K expires.

##   12. Performance
```
    Zebra already perform sweep and entire rib list look up. So performance will not change.
```

##   Should call out if any platform specific code will be introduced and why. Need to avoid platform specific code from the design phase
    N/A

##   13. Error flows handling
    Statistics are added to counts all routes for which new flag will be added\removed with -K option. This will be used for verification if Zebra contains any stale kernel routes.

##   14. Show commands
    N/A
## External reference
https://github.com/FRRouting/frr/pull/4197
https://github.com/FRRouting/frr/pull/4301/commits/5e2bb0ffa5c27a1a4116e58d44ea0517ad190efa
Final UTP results will be updated on the PR.
