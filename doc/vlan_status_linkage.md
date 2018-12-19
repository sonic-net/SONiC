{\rtf1\ansi\ansicpg936\cocoartf1671
{\fonttbl\f0\fmodern\fcharset0 Courier;\f1\fnil\fcharset134 PingFangSC-Regular;}
{\colortbl;\red255\green255\blue255;\red38\green38\blue38;}
{\*\expandedcolortbl;;\cssrgb\c20000\c20000\c20000;}
\paperw11900\paperh16840\margl1440\margr1440\vieww10800\viewh8400\viewkind0
\deftab720
\pard\pardeftab720\sl320\partightenfactor0

\f0\fs28 \cf2 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 #SONiC vlan status linkage community document\
\
##Catalogue\
\
- 1.Overview\
- 2.Terminology\
- 3.Vlanmgrd introduction\
- 4.Problem Description\
- 5.Target\
- 6.High-Level Design\
- 7.Detailed Design\
- 8.Unit testing\
\
##1. Overview\
\
This document points out the problem of VLAN status in SONiC and puts forward a method to solve it.\
\
##2. Terminology\
\
- admin_status
\f1 \'a3\'ba
\f0 Configuration status of vlan-interface. Set by users through CLI command or config.json. Default value is \'93up\'94. This value is stored in CONFIG_DB. Vlan\'92s field of admin_status in config_db.json will not change.\
- member_status: New status representing the operating status of member ports of vlan-interface. Value is \'93up\'94 when at least one of the member ports\'92s oper_status is \'93up\'94, and \'93down\'94 when one of the following condition is match:\
  a) All member port\'92s oper_status is \'93down\'94. \
  b) No member port for this vlan-interface.\
\
\
This value is stored in APPL_DB.\
- oper_status: New status representing the operating status of the vlan-interface. It\'92s also the status of Vlanxx in Linux kernel, set via Linux command \'93ip link set Vlanxx <up|down>\'94. This value is stored in APPL_DB.\
\
##3. Vlanmgrd introduction\
\
Vlanmgrd implements the functions such as adding, deleting, updating and managing for vlan in Linux kernel. Vlanmgrd subscribes to the VLAN table and the VLAN_MEMBER table of CONFIG_DB:\
- VLAN table stores the vlan-id,member port,admin_status and mtu of VLAN\
- VLAN_MEMBER table stores tagging_mod of VLAN members.\
\
Vlanmgrd create/delete vlan , add/delete vlan member, create and configure admin_status and mtu of vlan according to VLAN table and the VLAN_MEMBER table in CONFIG_DB, and write the configuration to  VLAN_TABLE and VLAN_MEMBER_TABLE in APPL_DB. Portsorch subscribes to these two tables in APPL_DB and sync the configuration to ASIC_DB, which is finally write to ASIC.\
Vlanmgrd use \'93ip link set\'94 command to configure status of vlan in linux kernel. In the current implementation, admin_status of CONFIG_DB is directly used, without considering oper_status of member ports.\
      The vlanmgrd structure is as follows
\f1 \'a3\'ba
\f0 \
![image](https://github.com/caesarkof97/SONiC/blob/jihaix/images/vlan_status_linkage_vlanmgrd_structure.png)\
<center>Figure 3-1 vlanmgrd structure</center>\
\
##4. Problem Description\
\
When user set the vlan-interface status through config_db.json by editing the value of admin_status, the member_status of this vlan-interface is not considered. \
Consider the following situation, if user create an vlan-interface with admin_status set to \'93up\'94, but no member port assigned, or none of its member ports is \'93up\'94, SONiC will still bring up the vlan-interface in linux kernel by executing \'93ip link set VlanXXX up\'94. This will bring some unexpected behaviors for upper APP. For example:\
- Routing protocols cannot quickly detect link state change and update routes to peers.\
- The upper protocol module still sends messages to the port, but the actual message cannot be transmitted.\
\
##5. Target\
\
SONiC need to consider the member_status before setting oper_status for VlanXXX in linux kernel. When member_status changed, SONiC can update oper_status automatically.\
\
##6. High-Level Design\
\
###6.1 Use oper_status to indicating the status of VlanXX in linux kernel.\
\
Introduce oper_status to represent the status of VlanXX in linux kernel, and admin_status to represent the value in config_db.json. \
When user set the admin_status, SONiC will check the member_status, and set oper_status according to the logic shown as follow:\
```\
if (member_status == \'93up\'94) && (admin_status == \'93up\'94) \{\
    oper_status = \'93up\'94;\
\} else \{\
    oper_status = \'93down\'94;\
\}\
```\
\
###6.2 Timing when oper_status will be updated\
\
a)	When vlan-interface is created.\
b)	When member ports changed, either member add/remove, or member\'92s oprt_status changed.\
c)	When admin_status changed, as the result of configuration changed.\
\
###6.3 Add CLI command to set admin_status\
\
Add a CLI command for user to  change admin_status of vlan-interface.\
```\
    config vlan admin_status <up|down>\
```\
This command will set the admin_status stored in CONFIG_DB, and trigger an update of oper_status. Please be advised, this command will not change the value stored in config_db.json.\
\
##7. Detailed Design\
\
###7.1 New entry is added to VLAN_TABLE in APPL_DB\
\
- member_status\
- oper_status\
\
###7.2 UML Sequence \
\
\
![image](https://github.com/caesarkof97/SONiC/blob/jihaix/images/vlan_status_linkage_CLI_UML.jpg)\
<center>Figure 5-1 CLI command sequence diagram</center>\
\
\
![image](https://github.com/caesarkof97/SONiC/blob/jihaix/images/vlan_status_linkage_port_state_change_UML.jpg)\
<center>Figure 5-2 port state change sequence diagram</center>\
\
##8. Unit testing\
\
###8.1 Test steps\
1
\f1 \'a1\'a2
\f0   The oper_status of Ethernet32 and Ethernet36 is in the "up" state,The oper_status of  Ethernet28 and Ethernet40 is in the " down " state, Configure the VLAN and VLAN_MEMBER of |config_db.json and run the config reload command. View Vlan100 and Vlan200 and their respective member ports oper_status. The configuration is as follows:\
```\
"VLAN": \{\
        "Vlan100": \{\
            "vlanid": "100",\
            "mtu": "9100",\
            \'93admin_status\'94: \'93up\'94,\
            "members":[\
                "Ethernet28",\
                "Ethernet32"\
            ]\
        \},\
        "Vlan200": \{\
            "vlanid": "200",\
            "mtu": "9100",\
            "admin_status": "down",\
            "members":[\
                "Ethernet36",\
                "Ethernet40"\
            ]\
\
        \}\
\}\
"VLAN_MEMBER":\{\
        "Vlan100|Ethernet28":\{\
            "tagging_mod": "untagged"\
        \},\
        "Vlan100|Ethernet32":\{\
            "tagging_mod": "untagged"\
        \},\
        "Vlan200|Ethernet36":\{\
            "tagging_mod": "untagged"\
        \},\
        "Vlan200|Ethernet40":\{\
            "tagging_mod": "untagged"\
        \}\
    \}\
```\
2
\f1 \'a1\'a2
\f0 	Run \'93config vlan member del 100 Ethernet32\'94,and then run \'93show vlan config\'94 to check whether the member Ethernet32 of Vlan100 has been deleted,run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
3
\f1 \'a1\'a2
\f0 	Run \'93config vlan member add 100 Ethernet32\'94,and then run \'93show vlan config\'94 to check whether the member Ethernet32 of Vlan100 has been added,run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
4
\f1 \'a1\'a2
\f0 	Run Command \'93ip link set Ethernet32 down\'94, and then run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
5
\f1 \'a1\'a2
\f0 	Run Command \'93ip link set Ethernet32 up\'94, and then run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
6
\f1 \'a1\'a2
\f0 	Run Command \'93ip link set Ethernet28 down\'94,and then run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
7
\f1 \'a1\'a2
\f0 	Run Command \'93ip link set Ethernet28 up\'94,and then run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
8
\f1 \'a1\'a2
\f0 	Run Command \'93config vlan admin-status 100 down\'94, and then check  admin_status of VLAN|Vlan100 of CONFIG_DB, then run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
9
\f1 \'a1\'a2
\f0 	Run Command \'93config vlan admin-status 100 up\'94, admin_status of VLAN|Vlan100 of CONFIG_DB, then run \'93ip link show Vlan100\'94 to check oper_status of Vlan100\
###8.2 Expected results\
1
\f1 \'a1\'a2
\f0 	Result of step 1
\f1 \'a3\'ba
\f0  oper_status of  Vlan100
\f1 \'a1\'a2
\f0 Ethernet32
\f1 \'a1\'a2
\f0 Ethernet36 are up,oper_status of  Vlan200
\f1 \'a1\'a2
\f0 Ethernet28
\f1 \'a1\'a2
\f0 Ethernet40  are down\
2
\f1 \'a1\'a2
\f0 	Result of step 2
\f1 \'a3\'ba
\f0 Vlan100 member Ethernet32 was delete successfully, oper_status of Vlan100 is down\
3
\f1 \'a1\'a2
\f0 	Result of step 3
\f1 \'a3\'ba
\f0 Vlan100 member Ethernet32 was delete successfully, oper_status of Vlan100 is up\
4
\f1 \'a1\'a2
\f0 	Result of step 4
\f1 \'a3\'ba
\f0  oper_status of Vlan100 is down\
5
\f1 \'a1\'a2
\f0 	Result of step 5
\f1 \'a3\'ba
\f0 oper_status of Vlan100 is up\
6
\f1 \'a1\'a2
\f0 	Result of step 6
\f1 \'a3\'ba
\f0 oper_status of Vlan100 is up\
7
\f1 \'a1\'a2
\f0 	Result of step 7
\f1 \'a3\'ba
\f0 oper_status of Vlan100 is up\
8
\f1 \'a1\'a2
\f0 	Result of step 8
\f1 \'a3\'ba
\f0 admin_status of VLAN|Vlan100 of CONFIG_DB is down,oper_status of Vlan100 is down\
9
\f1 \'a1\'a2
\f0 	Result of   step 9
\f1 \'a3\'ba
\f0 admin_status of VLAN|Vlan100 of CONFIG_DB is up,oper_status of Vlan100 is up\
###8.3 Actual results\
1
\f1 \'a1\'a2
\f0 	Result of step 1
\f1 \'a3\'ba
\f0 Pass\
2
\f1 \'a1\'a2
\f0 	Result of step 2
\f1 \'a3\'ba
\f0 Pass\
3
\f1 \'a1\'a2
\f0 	Result of step 3
\f1 \'a3\'ba
\f0 Pass\
4
\f1 \'a1\'a2
\f0 	Result of step 4
\f1 \'a3\'ba
\f0 Pass\
5
\f1 \'a1\'a2
\f0 	Result of step 5
\f1 \'a3\'ba
\f0 Pass\
6
\f1 \'a1\'a2
\f0 	Result of step 6
\f1 \'a3\'ba
\f0 Pass\
7
\f1 \'a1\'a2
\f0 	Result of step 7
\f1 \'a3\'ba
\f0 Pass\
8
\f1 \'a1\'a2
\f0 	Result of step 8
\f1 \'a3\'ba
\f0 Pass\
9
\f1 \'a1\'a2
\f0 	Result of step 9
\f1 \'a3\'ba
\f0 Pass\
}