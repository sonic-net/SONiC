# Static DNS configuration #

## Table of Content 

### Revision

 |  Rev  | Date  |       Author       | Change Description |
 | :---: | :---: | :----------------: | ------------------ |
 |  0.1  |       | Oleksandr Ivantsiv | Initial version    |

### Scope  

This document is the design document for static DNS configraion in SONiC.

### Definitions/Abbreviations 

| **Term** | **Meaning**        |
| -------- | ------------------ |
| DNS      | Domain Name System |


### Overview 

The access to the DNS in SONiC is organized via the resolver configuration file (/etc/resolv.conf). resolv.conf is the plain text file that contains the human-readable configuration. It is used across various subsystems in the SONiC to translate domain names into IP addresses. 

With the current implementation dynamic DNS configuration can be received from the DHCP server or static configuration can be set manually by the user. However, SONiC doesn't provide any protection for the static configuration. The configuration that is set by the user can be overwritten with the dynamic configuration at any time.

The proposed solution is to add support for static DNS configuration into Config DB. To be able to choose between dynamic and static DNS configurations `resolvconf` package should be used:

```
man resolvconf
The resolvconf package comprises a simple database for run-time nameserver information and a simple framework
for notifying applications of changes in that information. Resolvconf thus sets itself up as the intermediary
between programs that supply nameserver information and applications that use that information.
```

### Requirements

- Provide a possibility to configure static DNS entries via Config DB.
- The default behavior should be preserved if no static DNS entries are configured.
- New CLI command for static DNS configuration.
- DNS configuration should be updated in the host OS and all existing docker containers.

### Architecture Design 

1. CLI is responsible for putting DNS static configuration to Config DB.
2. hostcfgd should be extended to handle static DNS configuration by listening to Config DB change.
3. A new resolv-config.service systemd service should be added to control recolvconf framework.
4. A new resolv.conf.j2 template file should be added to generate resolv.conf file with static DNS configuration.
5. A new resolvconf plugin ("update-containers") should be added to update the DNS configuration inside each existing docker container.

#### CLI flow

![static_dns_cli_flow](/doc/static-dns/images/static_dns_cli_flow.svg)

### Loading configuration from Config DB

![static_dns_init_flow](/doc/static-dns/images/static_dns_init_flow.svg)

### Runtime configuration
#### Hostcfgd initialization
![static_dns_init_hostcfgd](/doc/static-dns/images/static_dns_init_hostcfgd.svg)
#### Runtime configuration changes
![static_dns_runtime_config](/doc/static-dns/images/static_dns_runtime_config.svg)
#### Containers configuration update
`resolvconf` will call the `update-containers` plugin after the DNS configuration update, to notify about the configuration change. `update-containers` plugin will update the DNS configuration in each docker container by copying `/etc/resolv.conf` file into the container filesystem. The plugin will be called regardless if the information was received dynamically from the DHCP server or configured manually by the user via config command.

![static_dns_containers_update](/doc/static-dns/images/static_dns_containers_update.svg)
### High-Level Design 

Changes should be added to sonic-buildimage and sonic-utilities repositories. CLI changes of sonic-utilities will be covered in the chapter "Configuration and management".

#### resolv-config service

The resolv-config is systemd service that runs on the host side of SONiC OS. It is part of the sonic target and should run after "updategraph.service". The service has type "oneshot". The service can be run in the following cases:
1. It can be called once during the sonic target start. Sonic target start can be invoked on system boot or during the config reload.
2. It can be called in the runtime from hostcfgd when the changes are made in the DNS table in Config DB.
3. It can be called by the user using systemctl restart command.

On start, resolv-config service calls resolv-config.sh bash script with no argument. 

#### resolv-config.sh

The script is responsible for controlling resolvconf framework and static DNS configuration rendering. Regardless of how resolv-config service is called the flow inside the bash script will always be the same:

- Get DNS configuration from Config DB.
- If no DNS configuration is available in Config DB enable resolvconf updates to receive dynamic DNS configuration.
- If DNS configuration is available render static DNS configuration with resolv.conf.j2 template, disable resolvconf update to not receive dynamic configuration updates.

#### resolv.conf.j2

resolv.conf.j2 template file will be used to translate DNS configuration from Config DB into a format that resolvconf understands.

#### resolvconf

Resolvconf expects to find the DNS configuration in the `/run/resolvconf/interface/` directory. The dynamic configuration received from the DHCP server on the management interface is stored in `<mgmt-inft>.[ipv6.]dhclient` files. For the convenience, static configuration will be stored in `mgmt-intf.static` file. 

### SAI API 

N/A

### Configuration and management 
#### CLI change
Config static DNS nameservers:
```
config dns nameserver add <ip_address>
config dns nameserver del <ip_address>

Example:
config dns nameserver add 1.1.1.1
config dns nameserver del 1.1.1.1
config dns nameserver add fe80:1000:2000:3000::1
config dns nameserver del fe80:1000:2000:3000::1
```

Show static DNS nameservers:
```
show dns nameserver

Example:
show dns nameserver
NAMESERVER
-----------------------
1.1.1.1
fe80:1000:2000:3000::1
```

#### YANG model Enhancements 

```yang
/* table for static DNS nameservers configuration */
container sonic-dns {

	container DNS_NAMESERVER {

		description "DNS_NAMESERVER part of config_db.json";

		list DNS_NAMESERVER_LIST {
			max-elements 3;
			description "List of nameservers IPs";

			key "ip";

			leaf ip {
				description "IP as DHCP_SERVER";
				type inet:ip-address;
			}
		} /* end of list DNS_NAMESERVER_LIST */

	} /* end of container DNS_NAMESERVER */

} /* end of container sonic-dns */

```

#### Config DB Enhancements  

Config DB will be extended with the following table:
```json
{
	"DNS_NAMESERVER": {
		"1.1.1.1": {},
		"fe80:1000:2000:3000::1": {}
	},
}
```

#### Minigraph Config Enhancements

A new "DnsNameserverResources" property will be added to the Minigraph

```xml
<a:DeviceProperty>
	<a:Name>DnsNameserverResources</a:Name>
	<a:Reference i:nil="true"/>
	<a:Value>"IP addresses list"</a:Value>
</a:DeviceProperty>
```

`sonic-cfggen` will be extended to translate configuration specified in "DnsNameserverResources" property into "DNS_NAMESERVER" Config DB table.

### Warmboot and Fastboot Design Impact  
The feature has no impact on the warmboot and fastboot.

### Config migration
The feature doesn't require special handling during the config migration.

### Restrictions/Limitations  
- Dynamic DNS configuration will not work if management interface uses static IP configuration

### Testing Requirements/Design  

#### Unit Test cases
1. Verify command "config dns nameserver add"
2. Verify command "config dns nameserver del"
3. Verify command "show dns nameserver"
4. Verify the configuration generated by resolv.conf.j2 template
5. Verify the configuration generated from minigraph

#### System Test cases
System test cases should be implemented in sonic-mgmt. A few new test cases should be added:

**TBD**

### Open/Action items - if any 
N/A