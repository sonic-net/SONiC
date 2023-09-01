#### Flow For Breakout And Non-Breakout Use Cases

```mermaid
sequenceDiagram
    title Auto-FEC in the case of breakout

    actor user as User
    participant dpb_cli as today's DPB CLI
    participant auto_fec as auto-FEC module
    participant config_db as CONFIG_DB
    participant syncd as SYNCD


    user ->>+ dpb_cli: do breakout on a port
    note over dpb_cli: run today's logic per port:
    dpb_cli ->>+ dpb_cli: generate the config(speed/lanes/etc) for each new port

    alt FEC mapping section exists in platform.json
        note over dpb_cli,auto_fec: run below additional logic per port:
        dpb_cli ->>+ auto_fec: call API determine_fec(lane_speed, num_lanes) per port
        auto_fec ->>+ auto_fec: calculate FEC mode based on FEC mapping obtained from platform.json
        auto_fec -->>- dpb_cli: return FEC mode
    end

    dpb_cli ->>+ config_db: Add new ports in PORT table (today's workflow), <BR> additionally with proper FEC if determined above <BR> instead of FEC=none as default

    par
        config_db -->>- dpb_cli: Done
    and
        config_db ->>+ syncd: notify for new port creation
    end

    dpb_cli -->>- user: Done
```

```mermaid
sequenceDiagram
    title Auto-FEC in the case of non-breakout

    actor user as User
    participant fec_correct_cli as FEC correction CLI <BR> (just a wrapper)
    participant auto_fec as auto-FEC module
    participant state_db as STATE_DB
    participant config_db as CONFIG_DB
    participant syncd as SYNCD

    user ->>+ fec_correct_cli: auto-correct FEC mode for all ports
    fec_correct_cli ->>+ auto_fec: call API correct_fec_for_all_ports()

    alt FEC mapping table exists in platform.json
        loop every port
            auto_fec ->>+ state_db: read optics_type from TRANSCEIVER_INFO table
            state_db -->>- auto_fec: return optics_type
            auto_fec ->>+ auto_fec: internally call API determine_fec(lane_speed, num_lanes, optics_type) <BR> which calculates FEC mode based on FEC mapping obtained from platform.json
        end

        auto_fec ->>+ config_db: update FEC if needed

        par
            config_db -->>- auto_fec: Done
        and
            config_db ->>+ syncd: notify for FEC update
        end
    end

    auto_fec -->>- fec_correct_cli: Done
    fec_correct_cli -->>- user: Done

```

> [!NOTE]
> In the above usecases, user needs to save config, so that changed FEC modes can be saved to config_db.json, and persists across config/system reload.

#### API design
```
def determine_fec(lane_speed: int, num_lanes: int, optics_type: Optional[str] = None) -> str:
    """
    Determines the appropriate Forward Error Correction (FEC) type based on lane speed, number of lanes, and optics type for a specific port.
    This logic is based on FEC mapping rules defined in platform.json.

    Parameters:
    - lane_speed (int): The speed of each lane in GB.
    - num_lanes (int): The total number of lanes.
    - optics_type (Optional[str]): The type of optics in use. Can be None if not applicable.

    Returns:
    - str: The recommended FEC type based on the rules in platform.json.
           If no matched entry is found in the rules or no rules are defined in platform.json, return None.

    Example:
    >>> determine_fec(25, 4, "100G-SR4")
    "rs"

    """
```

#### (optional) Platform Prequisite

FEC mapping rules are defined in platform.json:
1. For now, there are two mapping rules
    - ```fec_mapping_based_on_speed_lane```: This will be looked up if lane_speed and num_lanes are provided in parameters of determine_fec API.
    - ```fec_mapping_based_on_optics_type```: This will be looked up if optics_type is provided in parameters of determine_fec API.
2. In ```fec_mapping_based_on_speed_lane```, if there are multiple FEC values (e.g. ```rs``` and ```none```) in the field of ```fec```, preferably choose the first value (in this example, ```rs```).
3. If a port has matched FEC entry in both ```fec_mapping_based_on_speed_lane``` and ```fec_mapping_based_on_optics_type```, then prefers FEC entry in ```fec_mapping_based_on_optics_type```, which is the first mapping rule defined in platform.json.
```
{
"fec_mapping_based_on_optics_type": [
    {
        "optics_type": "100G-DR",
        "fec": ["none"]
    },
    {
        "optics_type": "100G-FR",
        "fec": ["none"]
    }
    ....
],
"fec_mapping_based_on_speed_lane": [
    {
        "lane_speed": 10,
        "num_lanes": 4,
        "fec": ["kr", "none"]
    },
    {
        "lane_speed": 20,
        "num_lanes": 2,
        "fec": ["none"]
    },
    {
        "lane_speed": 25,
        "num_lanes": 2,
        "fec": ["rs(kp4/kr4)", "none"]
    },
    {
        "lane_speed": 25,
        "num_lanes": 4,
        "fec": ["rs(kp4/kr4)", "none"]
    },
    {
        "lane_speed": 25,
        "num_lanes": 8,
        "fec": ["rs kp4"]
    },
    {
        "lane_speed": 50,
        "num_lanes": 1,
        "fec": ["rs(kp4/kr4)"]
    },
    {
        "lane_speed": 50,
        "num_lanes": 4,
        "fec": ["rs(kp4)"]
    },
    {
        "lane_speed": 50,
        "num_lanes": 8,
        "fec": ["rs(kp4)"]
    },
    {
        "lane_speed": 50,
        "num_lanes": 16,
        "fec": ["rs(kp4)"]
    },
    {
        "lane_speed": 50,
        "num_lanes": 2,
        "fec": ["rs(kp4/kr4/kp4_fi)"]
    }
]
}
```
