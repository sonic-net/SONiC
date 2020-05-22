
## **SONiC Management Framework CLI 'Show Running Configuration'**



#### High Level Design Document

**Rev 0.1**

#### Table of Contents

-   [[List of Tables]](#list-of-tables)

-   [[Revision]](#revision)

-   [[About This Manual]](#about-this-manual)

-   [[Scope]](#scope)

-   [[Definition/Abbreviation]](#definitionabbreviation)

#### List of Tables

[[Table 1: Abbreviations]](#table-1-abbreviations)

#### About this Manual

This document states the functional requirements and high level design of the new feature to support "show running-configuration" command.

#### Scope

The scope of this document is limited to the functionality described in the
requirements section.

#### Definition/Abbreviation

NA



#### 1 Feature Overview

This feature provides an infrastructure for apps to add
their current system configuration to the output of the "show
running-configuration" command. This command is available at the exec
level on the SONiC management framework CLI.

#### 1.1 Functional requirements

The 'show running-configuration' command will display the  configuration done
through the CLI interface and which is stored on the system.

For this command to show the entire running configuration of the system,
all apps should support configuration through CLI interface.

Any configuration done using GNMI or REST or other management
interface which is stored and has a corresponding CLI
command will be displayed as part of this new command.

The command output can be copied and pasted to be used as
configuration on another SONiC CLI session of the same or another
system.

The order of commands displayed in the "show running-configuration" will be
in accordance to the order of dependency between CLI views.

If configuration default values are stored, they will be shown as
part of "show running-configuration".

The infrastructure will provide functionality to filter and display
the configuration based on the CLI views.

A plugin in form of callback will be provided for apps to do their own database retrieval and
rendering. Apps will return the list of commands to the infra which will then be
added to the final list of commands to be displayed.

#### 1.2 Restrictions

Apps should not use this infrastructure to add configuration to 'show running-configuration' command for which there does not exist a CLI command.

System state information should not be added to this command.

The ordering between commands in the same view or between views is not supported. Hence some set of configuration will not work for copy-paste operation.

#### 1.3 Command syntax

###### 1.3.1 show running-configuration

An exec level command to display the current configuration of the
system.

Example:

sonic\#\>show running-config  
interface Vlan 5  
\!  
interface PortChannel 5 min-links 3 mode active  
\!  
interface Ethernet0  
&nbsp; no shutdown  
&nbsp; mtu 5000  
&nbsp; nat-zone 2  
&nbsp; ip address 10.11.203.35/8  
\!  
interface Ethernet4  
&nbsp; no shutdown  
&nbsp; mtu 5000  
&nbsp; switchport access vlan 5  
&nbsp; switchport trunk allowed vlan 6  
\!  
router bgp 11 vrf VrfBlack  
&nbsp; listen range 8.8.8.0/24 peer-group PG1  
\!  
router bgp 5 vrf VrfBlue  
&nbsp; router-id 6.6.6.6  
&nbsp; graceful-restart enable  
&nbsp; graceful-restart preserve-fw-state  
&nbsp; graceful-restart restart-time 500  
&nbsp; graceful-restart stalepath-time 600  

###### 1.3.2 show configuration

This command displays the configuration pertaining to the view at
which it is executed.

Example:

sonic(conf)\# interface PortChannel 5  
sonic(conf-if-po5)\#show configuration  
no shutdown  
mtu 5000  
switchport access vlan 5  
switchport trunk allowed vlan 6  

#### 2. Design

The design approach is to automate the rendering of the "show
running-configuration" command. The CLI developer does not
have to write a separate jinja template for this purpose. However, for
some cases this is not entirely possible due to way the config data is
stored in DB, or if the CLI command format cannot be directly rendered by this new infra.

For these exceptions two approaches are provided to the developer:

a.  Developer to provide a python callback function or jinja template. The infra will call this
    function with the required DB tables and keys. The
    function will return a list of commands. This list will be
    incorporated into the final command output.
    This can also be done using a jinja template. Python callback is
    recommended for better performance.

b.  Developer to provide a python callback which will retrieve
    data and render. It can retrieve data from DB using any
    interface and run it through its template. It will return the list
    of commands to the infra to be displayed in the final output.

The automation infra retrieves data from DB using the REST
interface and sonic yang model. The developer of CLI has to provide in
the cli xml, the DB table and attribute information related to
every command which it wishes to be displayed in the "show running
configuration" command output. New xml tags are introduced to provide this information.

Applications are required to provide the following information in the
respective config xml using the newly introduced xml tags.

-   sonic-yang table and attributes corresponding to the command
    parameters.

-   Table keys needed to access correct table records on transitioning
    to nested CLI views.

-   For some commands, a direct mapping to DB table attribute does
    not exist. In this case, a separate rendering callback or template(jinja) is
    required. For e.g., switchport trunk allowed Vlans, bgp neighbor etc.

##### 2.1 **New XML tags**
```

1. Attribute        view_keys
  
  Syntax            Multiple keys delimited by ",".
                    Key, value separated by "=".
                    Wildcard key value denoted by "*".
                    Keys for mulitple views separated by "|".
                    
  Example           view_keys="vrf=*"
                    view_keys="vrfname=sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/vr_name, afi-safi=ipv4_unicast,ip_prfx=*"
                    view_keys="ifname=*|vlaname=*"
                    
  Attribute to XML  COMMAND                
  element  

  Explanation       The tag is required when switching to a CLI chid view. The keys are for all the sonic yang tables accessed in the new child view.
                    This is added to the COMMAND statement.
                    For e.g.
                    sonic(config-router-bgp)# address-family ipv4 unicast
                    sonic(config-router-bgp-af)#
                    Here the child view is config-router-bgp-ipv4. 
                    In the child view, tables BGP_GLOBALS_AF, BGP_GLOBALS_AF_AGGREGATE_ADDR are accessed.
  
                    Keys : view_keys= "vrfname =sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/vrf_name,afi-safi=ipv4_unicast, ip_prfx=*"
                    The vrfname is populated from parent view table, hence the entire table path is specified.
                    afi-safi is given with exact value and ip_prfx is wildcard. BGP_GLOBALS_AF_AGGREGATE_ADDR table 
                    has 2 keys, vrf_name and ip_prfx. All prefixes with vrf_name=vrfname are displayed.
                    
                    If a command is denoted by flag "SEP_CLI", where a switch statement has params which contain different views, then view_keys are assigned in the order of the params.
  
  
2. Attribute        view_tables
    
  Syntax            Multiple sonic yang tables separated by  ";".
                    The table name has to specify all its keys.
                    Tables for mulitple views separated by "|"
                    
  Example           view_tables= "sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS_AF/vrf_name={vrfname},afi_safi={afi-safi}"
  
  Attribute to XML  COMMAND
  element
  
  Explanation       This tag lists the sonic yang tables accessed in the child view with its keys.
                    This is added to the COMMAND statement.
                    The key value variable inside parenthese '{}' have to match the key variables in tag "view_keys".
                    For e.g The variable name 'vrfname' for key 'vrf_name' in "view_tables" is the same as variable 'vrfname' in "view_keys".
                    The first table must be the primary table of the view.                                |
                    If a "view_template" attribute is specified in the same command, then all the tables in the view have to be listed here,
                    otherwise only the primary table.
                    For e.g.,  sonic(config-router-bgp)# neighbor 5.5.5.5
                               sonic(config-router-bgp-nbr)#
                               
                    view_tables="sonic-bgp-neighbor:sonic-bgp-neighbor/BGP_NEIGHBOR/vrf_name={vrfname},neighbor={neighbor}"  
                    
                    If a command is denoted by flag "SEP_CLI", in which a switch statement has option params with different views, then view_tables are assigned in the order of the params.
   
3. Attribute        dbpath

  Syntax            Path to sonic yang table attribute with '/'.
                    If exact value of parameter is to be matched then 'param=value'.
                    
  Example           dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/gr_restart/time
                    dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/always_compare_med=true
                    
  Attribute to XML  COMMAND, PARAM
  element
  
  Explanation       This tag is to map the command or param to the corresponding attribute in DB.
                    If the CLI rendering requires some transformation, or if it uses a PTYPE then a python callback will be needed for the command. In this case, dbpath is not relevant.


4.  Attribute       command_tables

  Syntax            Multiple sonic yang tables separate by ";".
                    Tables have to specify all its keys.
                     
  Example           command_tables="sonic-bgp-peergroup:sonic-bgp-peergroup/BGP_GLOBALS_LISTEN_PREFIX/vrf_name={vrf-name},ip_prefix={ip_prfx}"
  
  Attribute to XML  COMMAND
  element
  
  Explanation       This tag specifies the primary table for the command if it is different then view table. The keys are used from tag 'view_keys'.
                    If attributes from more than one table are referenced in the COMMAND (other than the primary table of the view),
                    then this command has to be rendered using command_render_cb.
                    

5.  Attribute       command_render_cb
                    
  Syntax            String
                      
  Example           command_render_cb = 'bgp_confederation '
                      
  Attribute to XML  COMMAND
  element
                      
  Explanation       In case where the CLI COMMAND or PARAM does not have direct mapping to a table attribute in the DB, the CLI developer has the option to form the
                    command in a python callback or jinja template. The developer has to map this tag value to a callback or a template name.
                    The mapping is to be provided in file CLI/acioner/show_config_data.py
                    In most cases, the command rendering is short and can be done efficiently in python. 
                    A jinja template has overhead of loading which increases linearly with file size.
                    For command rendering it is recommended to implement it in python. 


6.  Attribute       view_render_cb

  Syntax            String
  
  Example           view_render_cb = 'bgp_neighbor'
  
  Attribute to XML  COMMAND
  element
  
  Explanation       This tag is to be set if an an enitre CLI view is to be rendered using a jinja template or a python callback. 
                    Inernally developer has to map this tag value to a jinja template or a callback name. 
                    The mapping is to be provided in file CLI/acioner/show_config_data.py
                    

                  
7. Attribute        db_flag

  Syntax            Multiple flags can be defined with ‘|’ acting as separator.
                    
  Example           db_flag = SEP_CLI
  
  Attribute to XML  COMMAND, PARAM 
  element                     
  
  Explanation       Flags currently defined are

                    SEP_CLI - Flag to be used in COMMAND and PARAM tag. Generally there will be one DB entry per command.
                    The SEP_CLI flag is used to split the command and generate multiple entries for the same command.
                    The flag should the placed in the COMMAND tag that needs special handling and also in the PARAM of type switch,
                    so that each tree under the switch node will be generated as separate entry.
                    If a command is denoted by flag "SEP_CLI", where a switch statement has params which contain  different views, then view_tables are assigned in the order of the params.
                    All switch params options have to switch to a different child view.
                    
8. Attribute        data_and_render_cb
   
  Syntax            STRING
   
  Example           data_and_rernder_cb="acl_rules"
   
  Attribute to XML  COMMAND
  element
  
  Explanation       This callback will be implemented by the CLI developer. It will have to retrive data from DB and render it.
                    It will return a list of commands separated by a delimiter ';'. 
                    The tag to internal callback mapping has to be added in file CLI/acioner/show_config_data.pys

   
```
The following link illustrates how the xml tag information
is used for rendering.
![Design](images/design.jpg)


#### 2.2 Container

This feature is implemented within the Management Framework container.

#### 3 User Guide

Following excerpts from bgp.xml show the new tag usage.

###### 3.1 Command with switch to a new view (configure-router-bgp-view)
```
<COMMAND name="router bgp" help="Border Gateway protocol (BGP)" view="configure-router-bgp-view" viewid="instance=${as-num-dot};vrf-name=${vrf-name}"  view_keys="vrf_name=*, ip_prfx=*" view_tables="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/vrf_name={vrf-name}">
  <PARAM name="as-num-dot" help="Autonomous system number" ptype="RANGE_1_4294967295" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/local_asn">
    <PARAM name="vrf" help="VRF Instance" ptype="SUBCOMMAND" mode="subcommand" optional="true">
      <PARAM name="vrf-name" help="Name of VRF (Max size 15, prefixed by Vrf)" ptype="STRING_15" default="default"  dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/vrf_name"/>
    </PARAM>
  </PARAM>
</COMMAND>
```


###### 3.2 Command with tag attribute 'command_template'

The attribute value of param "neighbor' is a string in DB which is either an ip-address or an interface format. Hence using a template for
rendering.

```
<COMMAND name="neighbor" help="Specify a neighbor router" view="configure-router-bgp-nbr-view" viewid="nbr-addr=${ip}${Ethernet}${PortChannel}${Vlan};vrf-name=${vrf-name}" command_template="rn_bgp_neighbor" view_keys="vrf-name=sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/vrf_name,neighbor=*" view_tables="sonic-bgp-neighbor:sonic-bgp-neighbor/BGP_NEIGHBOR/vrf_name={vrf-name},neighbor={neighbor}" dbpath="sonic-bgp-neighbor:sonic-bgp-neighbor/BGP_NEIGHBOR/neighbor">
   <PARAM name="nbopt" help="neighbor router" mode="switch" ptype="SUBCOMMAND">
     <PARAM name="ip" help="Neighbor router" ptype="IPV4V6_ADDR"/>
     <PARAM name="interface" help="Interface name" mode="subcommand" ptype="SUBCOMMAND">
       <PARAM name="iftype" help="interface type" mode="switch" ptype="SUBCOMMAND">
         <PARAM name="Ethernet" help="Ethernet interface" ptype="PHY_INTERFACE" mode="subcommand"/>
         <PARAM name="PortChannel" help="PortChannel interface" ptype="PO_INTERFACE" mode="subcommand"/>
         <PARAM name="Vlan" help="Vlan interface" ptype="VLAN_INTERFACE" mode="subcommand"/>
       </PARAM>
     </PARAM>
   </PARAM>
 </COMMAND>
```

###### 3.3  Command with direct mapping into DB attributes

```
<COMMAND name="timers" help="Adjust routing timers">
  <PARAM name="keepalive-intvl" help="Keepalive interval (default=60)" ptype="RANGE_1_3600" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/keepalive">
    <PARAM name="hold-time" help="Holdtime (default=180)" ptype="RANGE_1_3600" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/holdtime"/>
  </PARAM>
</COMMAND>
```

###### 3.4  Switch statement
```
<COMMAND name="max-med" help="Advertise routes with max-med">
  <PARAM name="maxmedopts" help="MAX_MED admin or startup" mode="switch" ptype="SUBCOMMAND">
    <PARAM name="on-startup" help="Effective on a startup" ptype="SUBCOMMAND" mode="subcommand">
      <PARAM name="stime" help="Time (seconds) period for max-med" ptype="RANGE_5_86400" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/max_med_time">
        <PARAM name="maxmedval" help="Max MED value to be used" ptype="RANGE_0_4294967295" optional="true" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/max_med_val"/>
      </PARAM>
    </PARAM>
    <PARAM name="administrative" help="Administratively applied,  for an indefinite period" ptype="SUBCOMMAND" mode="subcommand" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/max_med_admin=true">
        <PARAM name="maxmedval" help="Max MED value to be used" ptype="RANGE_0_4294967295" optional="true" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/max_med_admin_val"/>
    </PARAM>
  </PARAM>
</COMMAND>
```

###### 3.5  Command mapped to a table different then the view table

This command is in the config-bgp-router view with primary view table
BGP_GLOBALS. However, this command is mapped to 2 tables, the
BGP_GLOBALS_LISTEN_PREFIX and the view table. If more than one command_tables
are used then use command_template for rendering.

```
<COMMAND name="listen" help="Set the prefix range for dynamic peers" command_tables="sonic-bgp-peergroup:sonic-bgp-peergroup/BGP_GLOBALS_LISTEN_PREFIX/vrf_name={vrf-name},ip_prefix={ip_prfx}">
  <PARAM name="listen-opt" help="Listen options" mode="switch" ptype="SUBCOMMAND">
   <PARAM name="range" help="Configure BGP dynamic neighbors listen range" mode="subcommand" ptype="SUBCOMMAND">
     <PARAM name="addr" help="Neighbor prefix" ptype="IPV4_IPV6_NETWORK" dbpath="sonic-bgp-peergroup:sonic-bgp-peergroup/BGP_GLOBALS_LISTEN_PREFIX/ip_prefix">
       <PARAM name="peer-group" help="Member of the peer-group" mode="subcommand" ptype="SUBCOMMAND">
         <PARAM name="pgname" help="Peer-group name" ptype="STRING" dbpath="sonic-bgp-peergroup:sonic-bgp-peergroup/BGP_GLOBALS_LISTEN_PREFIX/peer_group"/>
       </PARAM>
     </PARAM>
   </PARAM>
   <PARAM name="limit" help="maximum number of BGP Dynamic Neighbors that can be created" mode="subcommand" ptype="SUBCOMMAND">
     <PARAM name="lmt-val" help="Limit value" ptype="RANGE_1_5000" dbpath="sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/max_dynamic_neighbors"/>
   </PARAM>
  </PARAM>
</COMMAND>
```

###### 3.6 Multi-view command, Seperate CLI
```
<COMMAND name="interface" help="Select an interface" db_flag="SEP_CLI" view_keys="name=*|name=*" view_tables="sonic-port:sonic-port/PORT/ifname={name}|sonic-vlan:sonic-vlan/VLAN/name={name}" >
   <PARAM name="if-switch" help="Interface commands" mode="switch" ptype="STRING" db_flag="SEP_CLI" >
      <PARAM name="phy-if-name" help="Physical interface" ptype="PHY_INTERFACE" view="configure-if-view" dbpath="sonic-port:sonic-port/PORT/ifname" viewid="iface=${phy-if-name}"/>
      <PARAM name="vlan-if-name" help="Vlan identifier" ptype="VLAN_INTERFACE" view="configure-vlan-view" dbpath="sonic-vlan:sonic-vlan/VLAN/name" viewid="vlan_name=${vlan-if-name}"/>
   </PARAM>
</COMMAND>
```
###### 3.7 Command template rendering 
```
bgp.j2
{% if json_output %}
    {% set vrf_name = json_output['vrf_name'] %}
    {% if view == 'bgp_neighbor' %}
        {% set neighbor = json_output['neighbor'] %}
        {% if neighbor.startswith('Ethernet') %}
            {% set id = neighbor.split('Ethernet') %}
            {{- 'neighbor interface Ethernet ' ~ id[1]}}
        {%- elif neighbor.startswith('Vlan') %}
            {% set id = neighbor.split('Vlan') %}
            {{- 'neighbor interface Vlan ' ~ id[1]}}
        {%- elif neighbor.startswith('PortChannel') %}
            {% set id = neighbor.split('PortChannel') %}
            {{- 'neighbor interface PortChannel ' ~ id[1]}}
        {%- else %}
            {{- 'neighbor ' ~ neighbor }}
	{%- endif %}
    {% endif %}
{% endif %}
```

###### 3.6 View level callback plugin (xml_tag: data_and_rernder_cb)
Infra will call the callback with the arguments provided by the xml tags. 
The tag to internal callback mapping has to be added in file CLI/acioner/show_config_data.pys

Notes:
When introducing a new cli view, it must be added to the view list
in the actioner script (actioner/show_config_data.py). The position of view in the list is critical for correct ordering of commands display. Also, all the child views of the new view must be listed in the right order.

###### 3.7 CLI view based 'show configuration'

'show configuration' command is an application specific requirement. If an application needs to show the configuration at its view level, it has to implement this command in that  CLI view. The actioner must call the API provided by the infra to render the configuration.

The API requires the CLI view name and the keys for the view tables as parameters. The keys are available as view-ids in the current CLI view.

API:  
Module: sonic_cli_show_config
Parameters: func_name, cli-view, keys

 
E.g. bgp.xml
Show configuration under configure-router-bgp-view
```
<COMMAND name="show configuration" help="show bgp configuration">
  <ACTION builtin="clish_pyobj">sonic_cli_show_config show_configuration configure-router-bgp vrf-name=${vrf-name} </ACTION>
</COMMAND>
```

Show configuration under configure-router-bgp-nbr-view
```
<COMMAND name="show configuration" help="show bgp nbr configuration">
  <ACTION builtin="clish_pyobj">sonic_cli_show_config show_configuration configure-router-bgp-nbr vrf-name=${vrf-name} neighbor=${nbr-addr} </ACTION>
</COMMAND>  
```

##### 4 Compilation and testing.

1.  Compile mgmt-framework package and install.
2.  Verify the command output formats.

#### 5 Unit Test and Automation
