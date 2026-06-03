# PON gNMI Streaming Telemetry Paths

Paths use SONiC gNMI Redis format: `/<TABLE>/<key>` (composite keys are `|`-separated).
Specify the target database with `--target STATE_DB` or `--target COUNTERS_DB`.

Example:
```
gnmic -a <host>:8080 --insecure -u admin -p admin subscribe --path '/PON_OLT_INTF_STATE/{olt-name}|{port-id}' --mode stream --stream-mode on-change --encoding JSON_IETF --target STATE_DB
```

## STATE_DB Paths

### Controller

| Use case | path |
|---|---|
| The list of ONUs currently performing firmware upgrades on the PON Controller | /PON_CONTROLLER_ONU_FW_UPGRADE_STATE/{name}\|{onu-id} |
| List of PON Controllers | /PON_CONTROLLER_STATE/{name} |
| The list of OLTs currently registered on this PON Controller | /PON_CONTROLLER_SYSTEM_STATUS_OLT/{controller-name}\|{mac-address} |
| The list of ONUs currently registered on this OLT | /PON_CONTROLLER_SYSTEM_STATUS_OLT_ONU/{name}\|{mac-address}\|{onu-serial-number} |

### OLT Interface

| Use case | path |
|---|---|
| List of the NNI Networks configured on the OLT | /PON_OLT_INTF_NETWORK_STATE/{olt-name}\|{vlan-id} |
| The MAC address learning table for this uplink port | /PON_OLT_INTF_NNI_NETWORK_LEARNING_TABLE_STATE/{olt-name}\|{network-id}\|{mac-address} |
| The list of ONUs currently performing firmware upgrades on the OLT | /PON_OLT_INTF_ONU_FW_UPGRADE_STATE/{olt-name}\|{onu-serial-number} |
| Consolidated list of ONUs with their operational state | /PON_OLT_INTF_ONU_OPERATIONAL_STATE/{olt-name}\|{id} |
| List of OLT GEM ports | /PON_OLT_INTF_ONU_SERVICE_GEMPORT_STATE/{olt-name}\|{onu-serial-number}\|{service-port-id} |
| List of OLT Service ports | /PON_OLT_INTF_ONU_SERVICE_TCONT_STATE/{olt-name}\|{onu-serial-number}\|{service-port-id} |
| ONU related status | /PON_OLT_INTF_ONU_STATE/{olt-name}\|{onu-serial-number} |
| List of ONUs not currently seen by the Standby OLT | /PON_OLT_INTF_PROTECTION_UNDETECTED_ONU_STATE/{olt-name}\|{id} |
| List of OLTs | /PON_OLT_INTF_STATE/{olt-name}\|{port-id} |

### OLT Plug (uOLT)

| Use case | path |
|---|---|
| The version of firmware in the 4 banks on the OLT | /PON_OLT_PLUG_FW_BANK_VERSION_STATE/{name}\|{bank-id} |
| Firmware upgrade status | /PON_OLT_PLUG_FW_UPGRADE_STATUS/{name} |
| List of OLT plug state entries | /PON_OLT_PLUG_STATE/{name} |

### ONU

| Use case | path |
|---|---|
| Current firmware contents of ONU banks | /PON_ONU_FW_BANK_VERSION_STATE/{onu-name}\|{bank-id} |
| Mapping entry that classifies VLAN CoS bit values to a desinstation GPON XGEM Port or E... | /PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_MAP_STATE/{onu-name}\|{olt-service-id}\|{priority} |
| Downstream QoS Map | /PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE/{onu-name}\|{olt-service-id} |
| List of C-VLAN IDs through the service flow List of PON VLAN network through service flow | /PON_ONU_OLT_SERVICE_NETWORK_STATE/{onu-name}\|{olt-service-id}\|{network-id} |
| The OLT provisioned services for this ONU | /PON_ONU_OLT_SERVICE_STATE/{onu-name}\|{olt-service-id} |
| List of ONUs | /PON_ONU_STATE/{onu-name} |
| List of CPE MAC addresses learned on the UNI port | /PON_ONU_UNI_LEARNED_ADDRESSES_STATE/{onu-name}\|{port-id} |
| Status of the UNI ports on the ONU | /PON_ONU_UNI_STATE/{onu-name}\|{port-id} |

### Firmware

| Use case | path |
|---|---|
| PON_FIRMWARE_FILENAME_STATE configuration | /PON_FIRMWARE_FILENAME_STATE/{filename} |

---

## COUNTERS_DB Paths

### OLT Statistics

| Use case | path |
|---|---|
| OLT PON port statistics | /PON_OLT_STATISTICS_ACCUMULATING/{olt-name} |
| OLT device environmental statistics | /PON_OLT_STATISTICS_ACCUMULATING_ENV/{olt-name} |
| OLT PON Flooding (link) statistics | /PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING/{olt-name}\|{olt-id} |
| List of VLAN Tags identifying the NNI Networks using this PON Flood ID | /PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING_NNI_NETWORK/{olt-name}\|{olt-id} |
| OLT device temperatures | /PON_OLT_STATISTICS_ACCUMULATING_TEMP/{olt-name} |
| OLT PON Flooding (link) statistics | /PON_OLT_STATISTICS_BINNED_PON_FLOODING/{olt-name}\|{olt-stats-id}\|{flood-id} |
| List of VLAN Tags identifying the NNI Networks using this PON Flood ID | /PON_OLT_STATISTICS_BINNED_PON_FLOODING_NETWORK/{olt-name}\|{olt-stats-id}\|{flood-id} |

### OLT Plug Statistics

| Use case | path |
|---|---|
| OLT device environmental statistics | /PON_OLT_PLUG_STATISTICS_BINNED_ENV/{olt-name}\|{olt-stats-id} |
| OLT NNI port statistics | /PON_OLT_PLUG_STATISTICS_BINNED_NNI/{olt-name}\|{olt-stats-id} |
| OLT device temperatures | /PON_OLT_PLUG_STATISTICS_BINNED_TEMP/{olt-name}\|{olt-stats-id} |

### ONU OLT-side Statistics

| Use case | path |
|---|---|
| List containing the statistics history for this device | /PON_OLT_INTF_STATISTICS_BINNED/{olt-name}\|{olt-stats-id} |
| PON statistics for this ONU as represented on the OLT | /PON_ONU_STATISTICS_ACCUMULATING_OLT_PON/{onu-name} |
| GPON: OMCI channel statistics for this ONU as represented on the OLT | /PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_OMCC/{onu-name} |
| OLT-Service Port statistics for this ONU as represented on the OLT | /PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_SERVICE/{onu-name}\|{onu-id} |
| Realtime statistics for the ONU | /PON_ONU_STATISTICS_BINNED/{onu-name}\|{onu-stats-id} |
| PON statistics for this ONU as represented on the OLT | /PON_ONU_STATISTICS_BINNED_OLT_PON/{onu-name}\|{onu-stats-id} |
| GPON: OMCI channel statistics for this ONU as represented on the OLT | /PON_ONU_STATISTICS_BINNED_OLT_PON_OMCC/{onu-name}\|{onu-stats-id} |
| OLT-Service Port statistics for this ONU as represented on the OLT | /PON_ONU_STATISTICS_BINNED_OLT_PON_SERVICE/{onu-name}\|{onu-stats-id}\|{service-port-id} |

### ONU OMCI PM Statistics (accumulating)

| Use case | path |
|---|---|
| GPON: Enhanced TC statistics reported by ONU | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ENHANCED_TC_PM/{onu-name}\|{onu-id} |
| GPON: MAC Bridge Port statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM/{onu-name}\|{onu-id} |
| GPON: MAC Bridge Port 64-bit statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT/{onu-name}\|{onu-id} |
| GPON: Downstream MAC Bridge Service Profile statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM/{onu-name}\|{onu-id} |
| GPON: Upstream MAC Bridge Service Profile statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_UPSTREAM/{onu-name}\|{onu-id} |
| GPON: Ethernet UNI port statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with ethernet messages | /PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM3/{onu-name}\|{onu-id} |
| GPON: FEC statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_ACCUMULATING_ONU_FEC_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with gal ethernet messages | /PON_ONU_STATISTICS_ACCUMULATING_ONU_GAL_ETHERNET_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with gem port network ctp messages | /PON_ONU_STATISTICS_ACCUMULATING_ONU_GEM_PORT_NETWORK_CTP_PM/{onu-name}\|{onu-id} |
| ME collects PM data related to an IP host | /PON_ONU_STATISTICS_ACCUMULATING_ONU_IP_HOST_PERF_MON_HIST_DATA/{onu-name}\|{onu-id} |
| GPON: ME collects PM data related to a mac bridge port | /PON_ONU_STATISTICS_ACCUMULATING_ONU_MAC_BRIDGE_PORT_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with operational messages | /PON_ONU_STATISTICS_ACCUMULATING_ONU_OPERATIONAL_PM/{onu-name}\|{onu-id} |
| PON statistics reported by ONU | /PON_ONU_STATISTICS_ACCUMULATING_ONU_PON/{onu-name} |
| ME collects PM data for a RS232/RS485 interface | /PON_ONU_STATISTICS_ACCUMULATING_ONU_RS232_RS485_PERF_MON_HIST_DATA/{onu-name}\|{onu-id} |
| ME collects PM data related to a TCP or UDP port | /PON_ONU_STATISTICS_ACCUMULATING_ONU_TCP_UDP_PERF_MON_HIST_DATA/{onu-name}\|{onu-id} |
| GPON: Counters associated with downstream PLOAM and OMCI messages | /PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_DOWNSTREAM_MGMT_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with upstream PLOAM and OMCI messages | /PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_UPSTREAM_MGMT_PM/{onu-name}\|{onu-id} |

### ONU OMCI PM Statistics (binned)

| Use case | path |
|---|---|
| GPON: Enhanced TC statistics reported by ONU | /PON_ONU_STATISTICS_BINNED_ONU_ENHANCED_TC_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: MAC Bridge Port statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: MAC Bridge Port 64-bit statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Downstream MAC Bridge Service Profile statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_DOWNSTREAM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Upstream MAC Bridge Service Profile statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_UPSTREAM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Ethernet UNI port statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Counters associated with ethernet messages | /PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM3/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: FEC statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_BINNED_ONU_FEC_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Counters associated with gal ethernet messages | /PON_ONU_STATISTICS_BINNED_ONU_GAL_ETHERNET_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Counters associated with gem port network ctp messages | /PON_ONU_STATISTICS_BINNED_ONU_GEM_PORT_NETWORK_CTP_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| ME collects PM data related to an IP host | /PON_ONU_STATISTICS_BINNED_ONU_IP_HOST_PERF_MON_HIST_DATA/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: ME collects PM data related to a mac bridge port | /PON_ONU_STATISTICS_BINNED_ONU_MAC_BRIDGE_PORT_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Counters associated with operational messages | /PON_ONU_STATISTICS_BINNED_ONU_OPERATIONAL_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| PON statistics reported by ONU | /PON_ONU_STATISTICS_BINNED_ONU_PON/{onu-name}\|{onu-stats-id} |
| ME collects PM data for a RS232/RS485 interface | /PON_ONU_STATISTICS_BINNED_ONU_RS232_RS485_PERF_MON_HIST_DATA/{onu-name}\|{onu-stats-id}\|{me-id} |
| ME collects PM data related to a TCP or UDP port | /PON_ONU_STATISTICS_BINNED_ONU_TCP_UDP_PERF_MON_HIST_DATA/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Counters associated with downstream PLOAM and OMCI messages | /PON_ONU_STATISTICS_BINNED_ONU_XG_PON_DOWNSTREAM_MGMT_PM/{onu-name}\|{onu-stats-id}\|{me-id} |
| GPON: Counters associated with upstream PLOAM and OMCI messages | /PON_ONU_STATISTICS_BINNED_ONU_XG_PON_UPSTREAM_MGMT_PM/{onu-name}\|{onu-stats-id}\|{me-id} |

### ONU OMCI PM Statistics (streaming)

| Use case | path |
|---|---|
| GPON: Enhanced TC statistics reported by ONU | /PON_ONU_STATISTICS_STREAMING_ONU_ENHANCED_TC_PM/{onu-name}\|{onu-id} |
| GPON: Downstream MAC Bridge Service Profile statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM/{onu-name}\|{onu-id} |
| GPON: Upstream MAC Bridge Service Profile statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_UPSTREAM/{onu-name}\|{onu-id} |
| GPON: Ethernet UNI port statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_PM/{onu-name}\|{onu-id} |
| GPON: FEC statistics reported by ONU through OMCI | /PON_ONU_STATISTICS_STREAMING_ONU_FEC_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with gal ethernet messages | /PON_ONU_STATISTICS_STREAMING_ONU_GAL_ETHERNET_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with gem port network ctp messages | /PON_ONU_STATISTICS_STREAMING_ONU_GEM_PORT_NETWORK_CTP_PM/{onu-name}\|{onu-id} |
| ME collects PM data for a RS232/RS485 interface | /PON_ONU_STATISTICS_STREAMING_ONU_RS232_RS485_PERF_MON_HIST_DATA/{onu-name}\|{onu-id} |
| GPON: Counters associated with downstream PLOAM and OMCI messages | /PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_DOWNSTREAM_MGMT_PM/{onu-name}\|{onu-id} |
| GPON: Counters associated with upstream PLOAM and OMCI messages | /PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_UPSTREAM_MGMT_PM/{onu-name}\|{onu-id} |

---

## Subscription Modes

| Mode | Use |
|---|---|
| `ON_CHANGE` | STATE_DB paths |
| `SAMPLE` | COUNTERS_DB paths |
| `ONCE` | Firmware state, counter snapshot |
