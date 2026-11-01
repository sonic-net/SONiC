# Optical Linecard Provisioning

## Requirement

On an OTN whitebox every linecard is hot-pluggable, and different linecard
combinations serve different use cases. Because the actual population of the
chassis is unknown at image build time, SONiC must not come up with a fixed
default configuration. What we need instead is a mechanism that supplies a
*per-slot, per-cardtype* default configuration on demand.

Constraints that follow from this:

- The chassis runs in multi-ASIC mode: one ASIC namespace per slot, with
  `slot_id = asic_id + 1` (`NUM_ASIC` comes from the platform `asic.conf`).
- A slot has no meaningful configuration until the operator (or auto
  provisioning) declares which cardtype is installed there.
- Declaring a cardtype must bring up that slot only, without disturbing the
  other slots.

## How the SONiC-OTN Legacy Branch Handles It

### 1. Default configuration is organised per cardtype

Each device SKU ships the default configuration of every cardtype it supports.
Amplifier cards such as `oa2325` and `oa2335` carry different defaults, and
`ocm8` / `otdr8` each have their own.

A transponder needs one more level, because its configuration depends on the
operational mode — for example `L1_400G_CA_100GE` is a 100GE-to-400G
transponder while `LA_400G_CA_200GE` is a 200GE-to-400G one, and they differ in
client port count. Those cards therefore keep one directory per board mode.

```text
device/alibaba/arm64-obx2000-r0/          # NUM_ASIC=8 -> slots 1..8
├── oa2325/config_db.json.j2
├── oa2335/config_db.json.j2
├── ocm8/config_db.json.j2
└── otdr8/config_db.json.j2

device/alibaba/x86_64-obx1100-r0/         # NUM_ASIC=4 -> slots 1..4
└── p230c/
    ├── config_db.json.j2                 # shared template
    ├── L1_400G_CA_100GE/                 # one directory per board mode
        └── config_db.json.j2 
    ├── LA_400G_CA_200GE/
        └── config_db.json.j2 
    └── LA_200G_CA_100GE_QPSK/
        └── config_db.json.j2 
```

The `.j2` templates are rendered **at build time**, not at provisioning time.
The device `Makefile` (`Make.gen` / `Make.slot`) loops over the slots and
expands each template into a concrete per-slot file, injecting `asic_id`,
`linecard_id` and — for transponders — `board_mode`:

```text
config_db.json.j2  --(j2, per slot)-->  config_db0.json ... config_db7.json
```

The rendered files are packaged into the platform factory-configuration deb and
installed as:

```text
/etc/sonic/factory/<cardtype>[/<board_mode>]/config_db<asic_id>.json
```

### 2. Config engine behaviour at boot

At boot the config engine (`sonic-cfggen`) only builds the host-level
configuration:

```bash
sonic-cfggen -H -k <hwsku> --preset <preset> -j <chassis_temperature_threshold.json> \
    > /etc/sonic/config_db.json
```

No per-slot file is produced. `database@<asic_id>` loads
`/etc/sonic/config_db<asic_id>.json` only if it exists, so every unprovisioned
slot simply starts with an empty `CONFIG_DB`:

```text
/etc/sonic/
├── config_db.json          # host, always generated
└── config_db<N>.json        # per slot, created only by provisioning
```

### 3. Manual provisioning via CLI

Provisioning a slot copies the factory configuration of the requested cardtype
into `/etc/sonic/` and loads it into that slot's Redis instance:

```bash
# obx2000, slot 1 -> asic0
config slot 1 type oa2325
#   /etc/sonic/factory/oa2325/config_db0.json  ->  /etc/sonic/config_db0.json

# obx1100, slot 4 -> asic3, transponder needs a board mode
config slot 4 type p230c L1_400G_CA_100GE
#   /etc/sonic/factory/p230c/L1_400G_CA_100GE/config_db3.json
#       ->  /etc/sonic/config_db3.json
```

The CLI (`otn/slot/slot.py`) performs the following steps:

1. Reject the request unless the slot is empty with no cardtype declared, or is
   currently in `Mismatch` — an in-service card must be set to `NONE` first.
2. Flush every Redis DB of that slot and remove the stale
   `dump.rdb` / `config_db<N>.json` (`power-admin-state` and `empty` are kept).
3. For a transponder, symlink the selected board mode up to the cardtype root
   so the remaining logic is mode agnostic.
4. Run `recover_default_config.py`, which copies the factory file, stops
   `swss@<asic_id>` / `syncd@<asic_id>`, loads the file with
   `sonic-cfggen -j ... -n asic<asic_id> --write-to-db`, and restarts them.
5. Write `linecard-type` into `CONFIG_DB` and persist the result with
   `sonic-cfggen -n asic<asic_id> -d --print-data > /etc/sonic/config_db<N>.json`.

### 4. Auto provisioning

Inserting a card into an unprovisioned slot should trigger the same flow
automatically: PMON detects the card, reads its type from EEPROM and issues the
equivalent of `config slot <slot> type <cardtype>` on the operator's behalf.


