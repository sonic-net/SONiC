```mermaid
sequenceDiagram
    title Auto-FEC in the case of DPB 

    participant user as User
    participant dpb_cli as today's DPB CLI
    participant auto_fec as auto-FEC module/API
    participant plat_json as platform.json
    participant config_db as CONFIG_DB
    participant syncd as SYNCD

    user ->>+ dpb_cli: breakout on a port
    note over dpb_cli: run today's logic
    dpb_cli ->>+ dpb_cli: generate the config(speed/num_lanes/etc) for new sub ports
    note over dpb_cli: run added logic
    dpb_cli ->>+ auto_fec: call API determine_fec(port_speed, num_lanes, optics_type=None)
    auto_fec ->>+ plat_json: read FEC matrix section
    plat_json -->>- auto_fec: return
    auto_fec -->>- dpb_cli: return FEC mode calculated based on FEC matrix

    dpb_cli ->>+ config_db: Add new port in PORT table with proper FEC
    config_db -->>- dpb_cli: Done

    dpb_cli -->>- user: Done
    config_db ->>+ syncd: notify for new port 

```

```mermaid
sequenceDiagram
    title Auto-FEC in the case of non-DPB

    participant user as User
    participant fec_correct_cli as FEC correction CLI <BR> (just a wrapper)
    participant auto_fec as auto-FEC module/API
    participant plat_json as platform.json
    participant state_db as STATE_DB
    participant config_db as CONFIG_DB
    participant syncd as SYNCD

    user ->>+ fec_correct_cli: auto-correct FEC mode for all ports
    fec_correct_cli ->>+ auto_fec: call API correct_fec_for_all_ports()

    auto_fec ->>+ state_db: read optics_type from TRANSCEIVER_INFO table
    state_db -->>- auto_fec: return

    auto_fec ->>+ auto_fec: call API determine_fec(port_speed, num_lanes, optics_type)
    auto_fec ->>+ plat_json: read FEC matrix section
    plat_json -->>- auto_fec: return
    auto_fec -->>- auto_fec: calculate FEC mode based on FEC matrix
    auto_fec ->>+ config_db: update FEC if needed
    config_db -->>- auto_fec: Done
    auto_fec -->>- fec_correct_cli: Done
    fec_correct_cli -->>- user: Done

    config_db ->>+ syncd: notify for FEC update 

```

FEC matrix in platform.json:
```
{
"fec_matrix": [
    {
        "port_speed": 10,
        "num_lanes": 4,
        "fec": ["none", "kr"]
    },
    {
        "port_speed": 20,
        "num_lanes": 2,
        "fec": ["none"]
    },
    {
        "port_speed": 25,
        "num_lanes": 2,
        "fec": ["none", "rs(kp4/kr4)"]
    },
    {
        "port_speed": 25,
        "num_lanes": 4,
        "fec": ["none", "rs(kp4/kr4)"]
    },
    {
        "port_speed": 25,
        "num_lanes": 8,
        "fec": ["rs kp4"]
    },
    {
        "port_speed": 50,
        "num_lanes": 1,
        "fec": ["rs(kp4/kr4)"]
    },
    {
        "port_speed": 50,
        "num_lanes": 4,
        "fec": ["rs(kp4)"]
    },
    {
        "port_speed": 50,
        "num_lanes": 8,
        "fec": ["rs(kp4)"]
    },
    {
        "port_speed": 50,
        "num_lanes": 16,
        "fec": ["rs(kp4)"]
    },
    {
        "port_speed": 50,
        "num_lanes": 2,
        "fec": ["rs(kp4/kr4/kp4_fi)"]
    }
]
}
```