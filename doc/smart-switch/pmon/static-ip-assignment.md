# Midplane Interface 

A typical modular chassis includes a midplane-interface to interconnect the Supervisor & line-cards. The same design has been extended in case of a SmartSwitch. The mnic ethernet interface over PCIe which is the midplane-interface, interconnect the Switch Host and the DPUs.

* When DPU card (SLED) or the Supervisor boots and as part of its initialization, midplane interface gets initialized.
* Slot number is used in assigning an IP address to these interfaces.

## 1.    DPU static IP address allocation

The table shows how the DPU-ID is used in assigning IP address to the midplane-interface endpoints for both the host and dpu end.


| DPU_ID | DPU_Endpoint_IP | Host_Endpoint_IP | DPU_Endpoint_MAC | HOST_Endpoint_MAC |
| --- | ---- | ------ | ------------------ | ------------------ |
| 1 | 169.254.dpu_id.1 | 169.254.dpu_id.2 | DPU_MP_MAC1 | HOST_MP_MAC1 |
| 2 | 169.254.2.1 | 169.254.2.2 | DPU_MP_MAC2 | HOST_MP_MAC2 |
| 3 | 169.254.3.1 | 169.254.3.2 | DPU_MP_MAC3 | HOST_MP_MAC3 |
| 4 | 169.254.4.1 | 169.254.4.2 | DPU_MP_MAC4 | HOST_MP_MAC4 |
| 5 | 169.254.5.1 | 169.254.5.2 | DPU_MP_MAC5 | HOST_MP_MAC5 |
| 6 | 169.254.6.1 | 169.254.6.2 | DPU_MP_MAC6 | HOST_MP_MAC6 |
| 7 | 169.254.7.1 | 169.254.7.2 | DPU_MP_MAC7 | HOST_MP_MAC7 |
| 8 | 169.254.8.1 | 169.254.8.2 | DPU_MP_MAC8 | HOST_MP_MAC8 |

* The IP address allocation for the DPUs and the host can be static as in Modular chassis design 
* PCIe interface between the Switch Host and the DPUs act as the midplane interface. 
* For each DPU interface one endpoint is on the NPU side and the other endpoint is on the DPU side 
* When DPU or the Supervisor boots and as part of its initialization, midplane interface gets initialized.
* Slot number is used in assigning an IP and MAC address to these interfaces 
* Example: 
    * We use the subnet "169.254.0.0/16” for midplane-interface
    * Switch Host DPU interface IPs will be: 169.254.dpu_id.2
    * DPU endpoint IPs will be 169.254.dpu_id.1
* The MAC address for each host endpoint will be read from the FPGA and updated into the MID_PLANE_IP_MAC table in the ChassisStateDB
* The MAC address for each DPU endpoint will be updated by the DPU into the MID_PLANE_IP_MAC table in the ChassisStateDB
* Example
    * HOST_MP_MAC1 = BA:CE:AD:D0:C0:01
    * DPU_MP_MAC1 = BA:CE:AD:D0:D0:01

## 2.  ChassisStateDB Schema for MID_PLANE_IP_MAC
```
Table: “MID_PLANE_IP_MAC”

Key: "midplane_interface|dpu0"
            "id”: “1”,
            "host_ip": “169.254.1.2”,
            “host_mac”: “BA:CE:AD:D0:C0:01”, # mac is an example
            "dpu_ip": “169.254.1.1”,
            “dpu_mac”: “BA:CE:AD:D0:D0:01”  # will be updated by the DPU
```


