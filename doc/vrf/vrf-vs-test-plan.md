# VRF feature vs test plan

## overview

Vrf vs test plan are used to verify the function of the swss by checking the content of the APP_DB/ASIC_DB/kernel. FRR and SAI function will be covered by ansible pytest test cases.

## test cases

No|Test case summary
---------|----------
1|Verify that the vrf entry from config is pushed correctly by vrfmgrd to APP_DB and linux kernel.
2|Verify that the Orchagent is pushing the vrf entry into ASIC_DB by checking the contents in the ASIC_DB.
3|Verify that the random combination of vrf attributes can successfully configured by checking the contents in the APP_DB and ASIC_DB.
4|Verify that the vrf attribute can be updated successfully after vrf is created by checking the contents in the ASIC_DB
5|Verify that the vrf entries can be successfully removed from the CONFIG_DB, APP_DB and ASIC_DB.
6|Verify that the maximum number of vrf entries be created can reach to 1K.
7|Verify that the interface entry from config is pushed correctly by intfmgrd to APP_DB and linux kernel.
8|Verify that the Orchagent is receiving interface creation and deletion from APP_DB.
9|Verify that the Orchagent is pushing the interface entry into ASIC_DB by checking the contents in the ASIC_DB.
10|Verify that the port interface bind IPv4 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
11|Verify that the port interface bind IPv4 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
12|Verify that the different port interface bound to different vrf can configure the same IPv4 Address by checking the APP_DB and ASIC_DB.
13|Verify that the IPv4 address is removed successfully from the port interface by checking the contents in the APP_DB and ASIC_DB
14|Verify that the port interface bind IPv6 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
15|Verify that the port interface bind IPv6 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
16|Verify that the IPv6 address is removed successfully from the port interface by checking the contents in the APP_DB and ASIC_DB
17|Verify that the lag interface bind IPv4 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
18|Verify that the lag interface bind IPv4 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
19|Verify that the IPv4 address is removed successfully from the lag interface by checking the contents in the APP_DB and ASIC_DB
20|Verify that the lag interface bind IPv6 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
21|Verify that the lag interface bind IPv6 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
22|Verify that the IPv6 address is removed successfully from the lag interface by checking the contents in the APP_DB and ASIC_DB
23|Verify that the vlan interface bind IPv4 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
24|Verify that the vlan interface bind IPv4 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
25|Verify that the IPv4 address is removed successfully from the vlan interface by checking the contents in the APP_DB and ASIC_DB
26|Verify that the vlan interface bind IPv6 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
27|Verify that the vlan interface bind IPv6 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
28|Verify that the IPv6 address is removed successfully from the vlan interface by checking the contents in the APP_DB and ASIC_DB
29|Verify that the loopback interface bind IPv4 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
30|Verify that the loopback interface bind IPv4 address with vrf correctly by checking the contents in the APP_DB and ASIC_DB.
31|Verify that the IPv4 address is removed successfully from the loopback interface by checking the contents in the APP_DB and ASIC_DB.
32|Verify that the loopback interface bind IPv6 address without vrf correctly by checking the contents in the APP_DB and ASIC_DB.
33|Verify that the IPv6 address remove successfully from the loopback interface by checking the contents in the APP_DB and ASIC_DB.
34|Verify that the neighsyncd pushed neighbor entries to APP_DB correctly by checking the contents in the APP_DB.
35|Verify that the Orchagent is pushing the neighbor entry into ASIC_DB by checking the contents in the ASIC_DB.
36|Verify that the IPv4 neighbor create and delete successfully by checking the contents in the APP_DB and ASIC_DB.
37|Verify that the IPv6 neighbor create and delete successfully by checking the contents in the APP_DB and ASIC_DB.
38|Verify that the different interface with different vrf can add the same IPv4 neighbor address by checking the APP_DB and ASIC_DB.
39|Verify that the fpmsyncd pushed route entries to APP_DB correctly by checking the contents in the APP_DB.
40|Verify that the Orchagent is pushing the route entry into ASIC_DB by checking the contents in the ASIC_DB.
41|Verify that the IPv4 route entry  add successfully by checking the contents in the ASIC_DB.
42|Verify that the IPv4 route entry delete successfully by checking the contents in the APP_DB and ASIC_DB.
43|Verify that the IPv6 route entry  add successfully by checking the contents in the ASIC_DB.
44|Verify that the IPv6 route entry  delete successfully by checking the contents in the APP_DB and ASIC_DB.
45|Verify that the IPv4 route entry with vrf add successfully by checking the contents in the ASIC_DB.
46|Verify that the IPv4 route entry with vrf delete successfully by checking the contents in the APP_DB and ASIC_DB.
47|Verify that the IPv6 route entry with vrf add successfully by checking the contents in the ASIC_DB.
48|Verify that the IPv6 route entry with vrf delete successfully by checking the contents in the APP_DB and ASIC_DB.
49|Verify that the route entry can point to a nexthop in different vrf.
50|Verify that the acl packet action is redirect to a nexthop, the acl entry add correctly by checking the contents in the ASIC_DB.
51|Verify that the kernel vrf config keep the same during vrfmgrd warm-reboot.
52|Verify that the VIRTUAL_ROUTER/ROUTE_ENTRY/NEIGH_ENTRY in ASIC_DB keep the same during vrfmgrd warm-reboot by monitoring the object changes in ASIC_DB.
53|Verify that the vrfmgrd work well after warm-reboot by checking that the new config is pushed correctly to APP_DB and ping work well via vrf port interfaces.
