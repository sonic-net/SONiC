# MACsec Support in SONiC-VPP — High Level Design

## Revision History

| Date | Author | Description |
|---|---|---|
| 2026-10-19 | taran9999 | Initial version. |
| 2026-10-22 | taran9999 | Review feedback: egress PN exhaustion (§4.6), `interface-output` feature constraints (§4.3.3), `esp_encrypt` buffer-handling parity (§4.2.2). |

---

## Table of Contents

- [Revision History](#revision-history)
1. [Objectives](#1-objectives)
2. [Scope](#2-scope)
3. [Feature Description](#3-feature-description)
    - [3.1 What SONiC MACsec expects from the platform](#31-what-sonic-macsec-expects-from-the-platform)
    - [3.2 MACsec frame format and crypto inputs](#32-macsec-frame-format-and-crypto-inputs)
    - [3.3 How the VS (non-VPP) platform implements MACsec today](#33-how-the-vs-non-vpp-platform-implements-macsec-today)
    - [3.4 What the VPP dataplane provides today](#34-what-the-vpp-dataplane-provides-today)
    - [3.5 Capability gap matrix](#35-capability-gap-matrix)
    - [3.6 Architecture overview](#36-architecture-overview)
4. [Solution](#4-solution)
    - [4.1 Design options and chosen approach](#41-design-options-and-chosen-approach)
    - [4.2 VPP `sonic_ext` MACsec nodes](#42-vpp-sonic_ext-macsec-nodes)
    - [4.3 Feature arc placement and EAPOL handling](#43-feature-arc-placement-and-eapol-handling)
    - [4.4 SAI APIs to implement in vslib/vpp](#44-sai-apis-to-implement-in-vslibvpp)
    - [4.5 Mapping to new VPP APIs](#45-mapping-to-new-vpp-apis)
    - [4.6 SA rotation (rekey) and replay protection](#46-sa-rotation-rekey-and-replay-protection)
    - [4.7 Counters, XPN and stat segment](#47-counters-xpn-and-stat-segment)
    - [4.8 Switch / MACsec capability advertisement](#48-switch--macsec-capability-advertisement)
    - [4.9 MTU and buffer headroom](#49-mtu-and-buffer-headroom)
    - [4.10 Plugin enablement and build](#410-plugin-enablement-and-build)
5. [Implementation Plan](#5-implementation-plan)
6. [SONiC MACsec Configuration Guide (sonic-vpp specifics)](#6-sonic-macsec-configuration-guide-sonic-vpp-specifics)
7. [Test Plan](#7-test-plan)
8. [References](#8-references)
- [Appendix A: File Change Summary](#appendix-a-file-change-summary)
- [Appendix B: MACsec SecTAG and IV Reference](#appendix-b-macsec-sectag-and-iv-reference)

---

## 1. Objectives

Provide IEEE 802.1AE / 802.1AEbw MACsec support on the SONiC-VPP platform,
consistent with the
[SONiC MACsec HLD](https://github.com/sonic-net/SONiC/blob/master/doc/macsec/MACsec_hld.md):

- Per-port MACsec encryption/authentication programmable through the standard
  SONiC `MACSEC_PROFILE` / `PORT|macsec` CONFIG_DB schema and `config macsec ...`
  CLI, without bypassing the standard stack
  (`macsecmgrd` → `wpa_supplicant`/MKA → `macsecorch` → SAI).
- Support the four SONiC cipher suites: `GCM-AES-128`, `GCM-AES-256`,
  `GCM-AES-XPN-128`, `GCM-AES-XPN-256`.
- Correct EAPOL (MKA) transport and bypass so that key agreement converges on a
  protected link.
- SA rotation (rekey) with < 1% packet loss.
- Per-SA counters and `SAI_MACSEC_SA_ATTR_CURRENT_XPN` readable through
  `show macsec` / COUNTERS_DB, and clearable through `sonic-clear macsec`.
- Pass the `sonic-mgmt/tests/macsec` suite on a VPP KVM t0 testbed
  ([sonic-buildimage#26048](https://github.com/sonic-net/sonic-buildimage/issues/26048)).

Non-objectives:

- Hardware/PHY MACsec offload (`gbsyncd`-based MACsec on external PHYs).
- Line-rate crypto performance. sonic-vpp is a KVM/test and software-dataplane
  platform; correctness and test coverage are the goals.
- Changes to CONFIG_DB schema, YANG models, `macsecmgrd`, `macsecorch`,
  `wpa_supplicant`, or `sonic-utilities` CLI.
- MACsec over LAG member ports beyond what `macsecorch` already does per member
  (see §7.4).

---

## 2. Scope

In scope:

- `sonic-sairedis/vslib/vpp/` — a new `SwitchVppMACsec.cpp` translating the SAI
  MACsec object model to VPP, replacing the inherited Linux-kernel-MACsec
  implementation in `vslib/SwitchStateBaseMACsec.cpp` when
  `SAI_VS_SWITCH_TYPE == SAI_VS_SWITCH_TYPE_VPP`.
- `sonic-platform-vpp/vppbld/plugins/sonic_ext/` — new MACsec encrypt/decrypt
  graph nodes, per-port/per-SC/per-SA state, binary API, CLI, and stat-segment
  counters.
- `vppxlate/SaiVppXlate.{h,c}` — new VPP binary API wrappers, including the
  linux_cp EAPOL ethertype registration (§4.3).
- `platform/vpp/` build glue: `sonic_ext` feature selection, `startup.conf`
  template, crypto engine plugin enablement.
- sonic-mgmt / CI enablement for `tests/macsec` on the VPP KVM t0 testbed.
- Verification plan (vslib unit tests, VPP plugin tests, sonic-mgmt regression).

Out of scope:

- Changes to `macsecmgrd`, `macsecorch`, `wpa_supplicant`, CONFIG_DB schema,
  or `sonic-utilities`.
- The `gbsyncd-vpp` / external-PHY MACsec path.
- MACsec on the management port.

---

## 3. Feature Description

### 3.1 What SONiC MACsec expects from the platform

| Layer | Responsibility |
|---|---|
| `config macsec` CLI / sonic-cfggen | Populate `MACSEC_PROFILE` and `PORT\|<port>\|macsec` in CONFIG_DB. |
| `macsecmgrd` (swss) | Start one `wpa_supplicant` per protected port; on MKA convergence write `MACSEC_PORT_TABLE`, `MACSEC_{INGRESS,EGRESS}_SC_TABLE`, `MACSEC_{INGRESS,EGRESS}_SA_TABLE` into APPL_DB. |
| `macsecorch` (orchagent) | Program SAI: create `SAI_OBJECT_TYPE_MACSEC` (per direction), `MACSEC_PORT`, `MACSEC_FLOW`, `MACSEC_SC`, `MACSEC_SA`; create an ACL table/entry per direction with `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW` to activate the flow. |
| Platform SAI | Encrypt/authenticate egress frames per egress SA; validate/decrypt ingress frames per ingress SA; bypass EAPOL; maintain PN/XPN and per-SA counters. |
| `show macsec` / `sonic-clear macsec` | Read/clear SA attributes and `SAI_MACSEC_SA_STAT_*` counters. |

#### 3.1.1 SONiC MACsec component diagram

```
 Operator ---> +--------------------------+
               |  config macsec CLI /     |
               |  sonic-cfggen / YANG     |
               +------------+-------------+
                            |
                            v
               +------------+-------------+
               |        CONFIG_DB         |
               |  MACSEC_PROFILE          |
               |  PORT|<port>|macsec      |
               +------------+-------------+
                            |
                            v
        +-------------------+-------------------+
        |           macsecmgrd (swss)           |
        |  spawns wpa_supplicant per port       |
        +----+-------------------------+--------+
             |                         |
     EAPOL over netdev            CONFIG_DB -> APPL_DB
     (0x888E) to peer                  |
             |                         v
             |            +------------+-------------+
             |            |         APPL_DB          |
             |            |  MACSEC_PORT_TABLE       |
             |            |  MACSEC_*_SC_TABLE       |
             |            |  MACSEC_*_SA_TABLE       |
             |            +------------+-------------+
             |                         |
             |                         v
             |         +---------------+---------------+
             |         |      macsecorch (orchagent)   |
             |         |  MACSEC / MACSEC_PORT /       |
             |         |  MACSEC_FLOW / SC / SA +      |
             |         |  ACL entry MACSEC_FLOW action |
             |         +---------------+---------------+
             |                         | SAI API (serialized)
             |                         v
             |                  +------+-------+
             |                  |   ASIC_DB    |
             |                  +------+-------+
             |                         |
             |                         v
             |                  +------+-------+
             |                  |    syncd     |
             |                  +------+-------+
             |                         | SAI API (libsai.so == vslib)
             |                         v
             |       +-----------------+------------------+
             |       |      Platform SAI driver           |
             |       | (vendor SDK, vslib, or vslib/vpp)  |
             |       +-----------------+------------------+
             |                         |
             |         installs SecY / SC / SA, PN state
             |                         |
             v                         v
      +------+-------------------------+--------+
      |              Dataplane                  |
      |  EAPOL bypass  |  data encrypt/decrypt  |
      +-----------------------------------------+
```

The critical invariant: **EAPOL frames must traverse the port unprotected in
both directions**, otherwise MKA can never converge and no SA is ever installed.
On sonic-vpp this has two distinct requirements, covered in §4.3: EAPOL must be
*transported* across the VPP/linux_cp boundary, and it must *bypass* the MACsec
SecY once one exists.

### 3.2 MACsec frame format and crypto inputs

```
Unprotected:  | DA | SA |      EtherType/payload ...            |

Protected:    | DA | SA | 0x88E5 | TCI/AN | SL | PN | [SCI] | secure data | ICV |
                        \_______________ SecTAG _____________/              16B
                          8 bytes (no SCI) or 16 bytes (with SCI)
```

| Element | Detail |
|---|---|
| EtherType | `0x88E5` |
| TCI/AN | 1 byte: `V(1) ES(1) SC(1) SCB(1) E(1) C(1) AN(2)` |
| SL | Short length (0 if secure data >= 48 bytes) |
| PN | 4-byte packet number (lower 32 bits of XPN when XPN cipher in use) |
| SCI | 8 bytes, present when `SC` bit set (`send_sci = true`) |
| ICV | 16-byte GCM tag appended after the secure data |
| AAD | `DA || SA || SecTAG` when `E=1,C=1` (confidentiality); `DA || SA || SecTAG || user data` when integrity-only (`E=0,C=1`) |
| IV (non-XPN) | `SCI(8) || PN(4)` |
| IV (XPN) | `salt(12) XOR (SSCI(4) || XPN(8))` |

SONiC always uses `confidentiality_offset = 0`, so the full user data is
encrypted when the profile `policy` is `security`, and integrity-only
(`E=0`) when `policy` is `integrity_only`.

### 3.3 How the VS (non-VPP) platform implements MACsec today

`vslib` already has a complete MACsec implementation, but it is built entirely
on the **Linux kernel MACsec driver**:

| Component | File | Role |
|---|---|---|
| SAI object handling | `vslib/SwitchStateBaseMACsec.cpp` | `createMACsecPort/SC/SA`, `setAclEntryMACsecFlowActive`, `loadMACsecAttrsFromACLEntry` |
| Device management | `vslib/MACsecManager.cpp` | Runs `ip link add link <veth> macsec_<veth> type macsec ...`, `ip macsec add ... sa ...`; kernel does the crypto |
| Packet path | `vslib/MACsecForwarder.cpp` | `AF_PACKET` socket on `macsec_<veth>`, bridges to the hostif tap |
| EAPOL bypass | `vslib/MACsecIngressFilter.cpp`, `MACsecEgressFilter.cpp` | Filters inserted into `HostInterfaceInfo`'s veth↔tap userspace forwarding loop |
| PN readback | `vslib/SwitchStateBase.cpp::refresh_macsec_sa_stat` | Scrapes `ip macsec show` for `SAI_MACSEC_SA_ATTR_CURRENT_XPN` only |

Two consequences matter for VPP:

1. Everything keys off `vs_get_veth_name(...)` — the Linux netdev the VS
   dataplane forwards on.
2. Only `SAI_MACSEC_SA_ATTR_CURRENT_XPN` is refreshed; no
   `SAI_MACSEC_SA_STAT_*` counters are produced. `tests/macsec/test_dataplane.py
   ::test_counters` explicitly exempts `asic_type == "vs"` from checking the
   full counter set for this reason.

### 3.4 What the VPP dataplane provides today

`vslib/vpp/` (`SAI_VS_SWITCH_TYPE_VPP`) replaces the VS software forwarder
entirely:

- `SwitchVpp::register_hostif_info()`
  (`vslib/vpp/SwitchVppHostif.cpp`) creates a `HostInterfaceInfo` with
  `m_packet_socket = -1` and **starts no forwarding threads** — the comment in
  the source reads *"VPP uses the TAP directly through Linux CP. No packet
  socket or veth forwarding is needed here."*
- Data plane frames go: host NIC → VPP hwif → VPP graph → linux_cp tap. They
  never enter `HostInterfaceInfo::veth2tap_fun()` / `tap2veth_fun()`, so the
  `MACsecFilter` / `MACsecForwarder` machinery is never consulted.
- `SwitchVpp::create()` / `remove()` / `set()` simply delegate
  `SAI_OBJECT_TYPE_MACSEC_PORT/SC/SA` and
  `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW` to the base `SwitchStateBase`
  implementation, which will attempt to build a kernel MACsec netdev on a veth
  that VPP owns. The SAI calls therefore **succeed without programming
  anything** into the VPP dataplane — a silent-success hazard addressed in
  §4.10.

VPP crypto/feature primitives that *are* available and reusable:

| Capability | Status in VPP |
|---|---|
| AES-GCM 128/256 with arbitrary AAD and 12-byte IV | Yes — `VNET_CRYPTO_ALG_AES_128_GCM` / `AES_256_GCM`, `vnet_crypto_ctx_create()`, `vnet_crypto_ctx_set_cipher_key()`, `vnet_crypto_op_init()`, `vnet_crypto_process_ops()` |
| Crypto engines (SW + accelerated) | Yes — `crypto_engines/native` (AES-NI/PCLMUL), `openssl`, `ipsecmb` |
| Per-interface ingress feature arc | Yes — `device-input` |
| Per-interface egress feature arc | Yes — `interface-output` |
| Host-punt of selected L2 ethertypes | Yes — linux_cp `lcp_ethertype_enable()` / `linux-cp-punt-xc` |
| SONiC-specific plugin for custom nodes | Yes — `vppbld/plugins/sonic_ext/` (already hosts `ip2me_node.c`, `egress_mirror_node.c`) |
| Buffer pre-/append headroom manipulation | Yes — `vlib_buffer_advance()`, `VLIB_BUFFER_PRE_DATA_SIZE` |
| **MACsec (802.1AE) plugin** | **No** — FD.io VPP has no MACsec plugin or node |

`sonic-platform-vpp/TODO.md` lists `SAI_OBJECT_TYPE_MACSEC`,
`SAI_OBJECT_TYPE_MACSEC_PORT`, `..._FLOW`, `..._SC`, `..._SA` under
"Phase 4 — Advanced features ... not yet implemented".

### 3.5 Capability gap matrix

| SONiC requirement | sonic-vpp today | Gap | Resolution |
|---|---|---|---|
| `macsec` feature container + `macsecmgrd` on the DUT | Works — platform-agnostic | None | No change |
| `wpa_supplicant` runs per protected port | Works — `macsecmgrd` starts it and STATE_DB reports `ok` | None | No change |
| **EAPOL (0x888E) transported across the linux_cp boundary** | **Missing** — linux_cp punts only the ethertypes sonic-vpp explicitly registers (LACP `0x8809`, LLDP `0x88cc`, ARP `0x0806`); EAPOL is not among them, so `ethernet-input` has no next node for it | **Yes — gates MKA entirely** | §4.3.1 |
| EAPOL bypass of the MACsec SecY | n/a — no SecY exists yet | Yes | §4.3.2 |
| Egress data frames MACsec-encapsulated + encrypted | Not implemented | Yes | §4.2 `sonic-ext-macsec-encrypt` node |
| Ingress data frames validated + decrypted | Not implemented | Yes | §4.2 `sonic-ext-macsec-decrypt` node |
| `GCM-AES-128` / `GCM-AES-256` | n/a | Yes | VPP `vnet_crypto` AES-GCM |
| `GCM-AES-XPN-128` / `GCM-AES-XPN-256` | n/a | Yes | 64-bit XPN counter + `salt`/`SSCI` IV derivation (§3.2, Appendix B) |
| Replay protection window | n/a | Yes | Per-ingress-SC sliding window (§4.6) |
| Rekey / active egress SA switch, < 1% loss | n/a | Yes | Atomic `encoding_an` flip (§4.6) |
| SAI MACsec object model actually programmed | vslib accepts the full chain without error but programs nothing into VPP | Yes — silent success | §4.4 to implement; §4.10 to fail loudly when the feature is off |
| `SAI_MACSEC_SA_ATTR_CURRENT_XPN` readback | Kernel scrape only; wrong under VPP | Yes | §4.7 — VPP stat segment |
| `SAI_MACSEC_SA_STAT_*` counters | Not produced by any vslib backend | Yes | §4.7 — implement fully; `test_counters` demands them for `asic_type == "vpp"` |
| `sonic-clear macsec` | Depends on counters existing | Yes | §4.7 — `clear_stats` on SA |
| `docker exec syncd ip -j macsec show` (used by `test_mka_session`) | Kernel macsec netdev may or may not exist; unreliable under VPP | Yes | §4.4 — keep a shadow kernel netdev for introspection, or extend the test to read VPP state |
| MACsec capability attributes (`SUPPORTED_CIPHER_SUITE_LIST`, `AVAILABLE_MACSEC_{FLOW,SC,SA}`, `MAX_SECURE_ASSOCIATIONS_PER_SC`) | Partial — only `SCI_IN_INGRESS_MACSEC_ACL` has a refresh hook | Yes (correctness) | §4.8 |
| `test_macsec_pfc.py` (PFC over MACsec) | PFC not modeled in VPP | Yes | Out of initial scope; skip with documented reason |
| FIPS POST (`test_fips_post_status.py`) | `SAI_MACSEC_ATTR_ENABLE_POST` handled generically in `SwitchStateBase::create()` | None | Reuse base handling |

### 3.6 Architecture overview

```
          config macsec CLI
                  |
                  v
          +-------+--------+
          |   CONFIG_DB    |
          +-------+--------+
                  |
                  v
          +-------+--------+          spawn
          |   macsecmgrd   |------------------> wpa_supplicant (per port)
          +-------+--------+                          |
                  |                                   | EAPOL 0x888E
                  v                                   | over Linux tap
          +-------+--------+                          | (linux_cp)
          |    APPL_DB     |                          |
          +-------+--------+                          |
                  |                                   |
                  v                                   |
          +-------+--------+                          |
          |  macsecorch    |                          |
          +-------+--------+                          |
                  | sairedis client API               |
                  v                                   |
          +-------+--------+                          |
          |    ASIC_DB     |  create_macsec_sa, etc.  |
          +-------+--------+                          |
                  |                                   |
                  v                                   |
          +-------+--------+                          |
          |     syncd      |                          |
          +-------+--------+                          |
                  | SAI API (libsai.so == vslib)      |
                  v                                   |
   +--------------+-------------------+               |
   |   sonic-sairedis vslib/vpp       |               |
   |   SwitchVppMACsec.cpp  [NEW]     |               |
   |     createMACsecPort/SC/SA       |               |
   |     setAclEntryMACsecFlowActive  |               |
   |     refresh_macsec_sa_stat       |               |
   |   vppxlate/SaiVppXlate.c [MOD]   |               |
   +--------------+-------------------+               |
                  | VPP binary API                    |
                  v                                   |
   +--------------+----------------------------------+|
   |                    VPP                          ||
   |   sonic_ext plugin [NEW MACsec feature]         ||
   |                                                 ||
   |   device-input arc                              ||
   |     +--------------------------+                ||
   |     | sonic-ext-macsec-decrypt |<-- wire        ||
   |     +------------+-------------+                ||
   |            EAPOL | data                         ||
   |                  v                              ||
   |            ethernet-input -> ... -> lcp tap ----++
   |              (0x888E -> linux-cp-punt-xc)       |
   |                                                 |
   |   interface-output arc (tail)                   |
   |     +--------------------------+                |
   |     | sonic-ext-macsec-encrypt |--> wire        |
   |     +--------------------------+                |
   |        (EAPOL passes through untouched)         |
   |                                                 |
   |   vnet_crypto (AES-GCM 128/256)                 |
   |   stat segment: /macsec/<sa>/...                |
   +-------------------------------------------------+
```

Key points the diagram makes explicit:

- `macsecorch` never calls the platform SAI directly; it writes to ASIC_DB and
  `syncd` replays through `libsai.so`, which on sonic-vpp **is** `vslib`
  compiled with `USE_VPP`.
- MKA/EAPOL never enters the MACsec crypto path. It travels
  `wpa_supplicant` ↔ linux_cp tap ↔ VPP graph ↔ wire as plaintext, bypassing
  both MACsec nodes.
- Per-SA counters live in the VPP stat segment and are pulled by vslib into
  the normal SAI `get_stats` / COUNTERS_DB path.

---

## 4. Solution

### 4.1 Design options and chosen approach

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Kernel-MACsec hairpin** | Keep `MACsecManager` (kernel crypto) but re-plumb the wire path as `VPP hwif ⇄ host tap ⇄ macsec_<if> ⇄ physical veth`. | Reuses all existing vslib MACsec code; `ip macsec show` keeps working, so `test_mka_session` passes unchanged. | Two extra kernel↔VPP crossings per packet; fragile interaction with linux_cp; does not produce `SAI_MACSEC_SA_STAT_*`; not a real dataplane feature. |
| **B. Native VPP MACsec (chosen)** | New encrypt/decrypt graph nodes in the existing `sonic_ext` plugin using `vnet_crypto` AES-GCM. | True dataplane feature; full SA counters; correct SAI semantics; reusable outside KVM. | Largest implementation effort; new VPP code to maintain. |
| **C. Full punt-to-kernel** | Route all traffic on a MACsec-enabled port through the LCP tap and let the kernel macsec device handle it. | Simplest. | Destroys throughput; changes forwarding semantics for a port depending on whether MACsec is on. |

**Chosen: Option B**, staged so that Phase 1 delivers a working single-SA
`GCM-AES-128` datapath and later phases add XPN, replay protection, rekey and
counters. Option A is retained as a documented fallback — see §5 Phase 1 exit
criteria. Note that Option A does **not** avoid the EAPOL transport work in
§4.3.1: the kernel-MACsec hairpin still requires EAPOL to reach
`wpa_supplicant` on the host tap.

The implementation lives in `sonic_ext` rather than a standalone plugin for
the same reason `egress_mirror_node.c` does: it already has the SONiC-specific
buffer-opaque cookie, per-feature enable selection
(`SONIC_EXT_CONFIG=<feature>=on|off`), and a binary API that `vslib/vpp`
already talks to.

### 4.2 VPP `sonic_ext` MACsec nodes

Two nodes plus shared state.

#### 4.2.1 Data model

```c
/* One per (port, direction) SecY. */
typedef struct
{
  u32 sw_if_index;
  u8  enabled;
  u8  direction;          /* SONIC_EXT_MACSEC_{EGRESS,INGRESS} */
  u8  encrypt;            /* policy == security  -> E=1,C=1     */
  u8  send_sci;
  u8  replay_protect;
  u32 replay_window;
  u32 *sc_indices;        /* vec of SC pool indices on this port */
} sonic_ext_macsec_port_t;

/* One per secure channel. */
typedef struct
{
  u64 sci;                /* network byte order on the wire      */
  u32 port_index;
  u8  direction;
  u8  cipher;             /* GCM_AES_{128,256}[_XPN]             */
  u8  encoding_an;        /* egress only: active AN              */
  u32 sa_index[4];        /* AN -> SA pool index, ~0 if absent   */
  /* ingress replay state */
  u64 highest_xpn_seen;
  u64 replay_bitmap_lo, replay_bitmap_hi;
} sonic_ext_macsec_sc_t;

/* One per secure association. */
typedef struct
{
  u32 sc_index;
  u8  an;
  u8  xpn_en;
  u8  salt[12];           /* XPN only */
  u32 ssci;               /* XPN only */
  vnet_crypto_ctx_t *crypto_ctx;   /* AES-GCM key context        */
  u64 next_xpn;           /* egress: next PN to stamp            */
  u64 lowest_acceptable_xpn;       /* ingress                    */
  /* counters -> stat segment, see 4.7 */
  u32 stat_index;
} sonic_ext_macsec_sa_t;
```

SAK installation uses `vnet_crypto_ctx_create(VNET_CRYPTO_ALG_AES_128_GCM)` /
`AES_256_GCM` followed by `vnet_crypto_ctx_set_cipher_key(ctx, sak, len)`.
The 16-byte `auth_key` (`SAI_MACSEC_SA_ATTR_AUTH_KEY`) is derived from the SAK
by MKA and is not needed by GCM — it is accepted and stored for parity with
the SAI model but not used for crypto.

#### 4.2.2 Egress node — `sonic-ext-macsec-encrypt`

```
for each buffer b:
    sfp = per-port state for vnet_buffer(b)->sw_if_index[VLIB_TX]
    if !sfp->enabled                         -> next[0] = passthrough
    ethertype = peek at offset 12
    if ethertype == 0x888E (EAPOL)           -> next[0] = passthrough  /* §4.3 */
    sc  = sfp->egress_sc
    sa  = sc->sa_index[sc->encoding_an]
    if sa == ~0                              -> drop, bump NO_SA error

    if b->flags & VLIB_BUFFER_NEXT_PRESENT   -> drop, bump CHAINED      /* §4.9 */
    if headroom(b) < sectag_len              -> drop, bump NO_HEADROOM
    if tailroom(b) < 16                      -> drop, bump NO_TAILROOM

    xpn = clib_atomic_fetch_add(&sa->next_xpn, 1)
    if !sa->xpn_en && xpn > 0xffffffff       -> drop, bump PN_EXHAUSTED  /* §4.6 */
    build SecTAG (TCI/AN, SL, PN = xpn & 0xffffffff, [SCI])
    build IV  (see Appendix B)
    build AAD = DA || SA || SecTAG   (+ user data if integrity-only)

    vlib_buffer_advance(b, -(sectag_len))    /* open a hole after DA|SA  */
    memmove DA|SA forward over the hole
    write SecTAG
    op.src = secure_data; op.dst = secure_data (in place)
    op.aad = aad; op.aad_len; op.iv = iv
    op.auth = tail; op.auth_len = 16
    op.user_data = bi                        /* map the result back to b  */
    accumulate op

once per frame:
    vnet_crypto_process_ops(vm, ops, n_ops)
    for each op:
        if op.status != VNET_CRYPTO_OP_STATUS_COMPLETED
                                             -> drop, bump CRYPTO_FAILED
        b->current_length += 16              /* ICV */
        bump OUT_PKTS_ENCRYPTED / OCTETS_ENCRYPTED (or *_PROTECTED)
```

Ops are accumulated per frame and a single `vnet_crypto_process_ops()` call is
issued at the end of the node, with `op.user_data` carrying the buffer index so
results can be matched back — the same structure `ipsec`'s `esp_encrypt` uses.

**Buffer-handling parity with `esp_encrypt`.** Prepending the SecTAG and
appending the ICV is the same class of operation as ESP's header/trailer
insertion, so the node inherits ESP's checks rather than assuming the common
case:

| Concern | `esp_encrypt` reference | MACsec node |
|---|---|---|
| ICV does not fit in the last segment's tailroom | `esp_add_footer_and_icv()` allocates and chains a fresh buffer | Phase 1 drops and counts; Phase 3 chains (§4.9) |
| Frame already spans multiple buffers | `esp_encrypt_chain_crypto()` builds `vnet_crypto_op_chunk_t` and sets `VNET_CRYPTO_OP_FLAG_CHAINED_BUFFERS` | Phase 1 rejects `VLIB_BUFFER_NEXT_PRESENT`; Phase 3 adds chunked ops (§4.9) |
| Length bookkeeping across a chain | `total_length_not_including_first_buffer` and `VLIB_BUFFER_TOTAL_LENGTH_VALID` maintained | Same, once chaining lands. `b->current_length` on its own is only correct for single-segment frames |
| Headroom for the prepended header | buffers allocated with sufficient headroom | `VLIB_BUFFER_PRE_DATA_SIZE` is ample but is checked per buffer, not assumed (§4.9) |
| Crypto failure | op status checked, buffer dropped | `CRYPTO_FAILED` counter |

Two places where MACsec deliberately diverges from ESP:

- **No padding.** ESP pads the plaintext to block alignment and carries the pad
  length in its footer. MACsec does not pad — secure data shorter than 48 bytes
  is signalled by the SecTAG `SL` field instead. Only ESP's tailroom and
  chaining logic carries over, not its padding logic.
- **Synchronous crypto only.** Phase 1 uses `vnet_crypto_process_ops()`. ESP
  additionally supports the async path (`vnet_crypto_async_add_to_frame()`);
  adopting it for MACsec is possible later but is not required for a software
  test dataplane and is out of scope here.

#### 4.2.3 Ingress node — `sonic-ext-macsec-decrypt`

```
for each buffer b:
    sfp = per-port state for vnet_buffer(b)->sw_if_index[VLIB_RX]
    if !sfp->enabled                         -> passthrough
    ethertype = peek at offset 12
    if ethertype == 0x888E                   -> passthrough  /* §4.3 */
    if ethertype != 0x88E5:
        if validate == strict                -> drop, IN_PKTS_UNCHECKED/NOT_USING_SA
        else                                 -> passthrough
    parse SecTAG -> TCI/AN, SL, PN, [SCI]
    sc = lookup by SCI if SC bit set, else the port's single ingress SC
    if !sc                                   -> drop, IN_PKTS_NO_SCI
    sa = sc->sa_index[AN]
    if sa == ~0                              -> drop, IN_PKTS_NOT_USING_SA

    xpn = recover_xpn(sc->highest_xpn_seen, PN, sa->xpn_en)   /* Appendix B */
    if replay_protect and replay_check(sc, xpn) fails
                                             -> drop, IN_PKTS_LATE
    build IV / AAD as above
    vnet_crypto_process_ops(...)             /* GCM decrypt + tag verify   */
    if op.status != COMPLETED                -> drop, IN_PKTS_NOT_VALID
    strip SecTAG (memmove DA|SA back) and 16-byte ICV
    replay_advance(sc, xpn)
    bump IN_PKTS_OK / IN_OCTETS_DECRYPTED
    next[0] = passthrough  -> ethernet-input
```

### 4.3 Feature arc placement and EAPOL handling

EAPOL imposes **two separate requirements** on sonic-vpp, at two different
layers. Both must hold or MKA cannot converge.

#### 4.3.1 EAPOL transport across the linux_cp boundary

On sonic-vpp, `wpa_supplicant` runs on the linux_cp host tap (e.g.
`Ethernet112`), so every MKPDU must cross tap → VPP → hwif → wire and back.
In VPP that crossing is performed by the linux_cp **`linux-cp-punt-xc`** node,
which is only reached if the ethertype is registered as `ethernet-input`'s next
node for that type. From `src/plugins/linux-cp/lcp_interface.c`:

```c
int
lcp_ethertype_enable (ethernet_type_t ethertype)
{
  vlib_node_t *node = vlib_get_node_by_name (vm, (u8 *) "linux-cp-punt-xc");
  eti = ethernet_get_type_info (em, ethertype);
  if (!eti) return VNET_API_ERROR_INVALID_VALUE;
  ...
  ethernet_register_input_type (vm, ethertype, node->index);
}
```

A single registration covers **both directions**: `linux-cp-punt-xc`
cross-connects based on the arrival `sw_if_index`, so phy→host and host→phy are
enabled together. VPP's own `test/test_linux_cp.py::TestLinuxCPEthertype`
demonstrates exactly this for LACP and LLDP — before registration both
directions are dropped, after it both pass.

sonic-vpp performs these registrations once, in `init_vpp_client()`
(`vslib/vpp/vppxlate/SaiVppXlate.c`). MACsec requires EAPOL to be added to that
set:

```c
/* Enable LACP punt/xc in linux-cp (no flood) */
vpp_lcp_ethertype_enable(0x8809);
/* Enable LLDP in linux-cp */
vpp_lcp_ethertype_enable(0x88cc);
/* Enable ARP pass through in linux-cp */
vpp_lcp_ethertype_enable(0x0806);
/* Enable EAPOL so wpa_supplicant on the host tap can run MKA */
vpp_lcp_ethertype_enable(0x888e);
```

`0x888e` is a known VPP ethertype (`ethernet_type (0x888e,
802_1X_AUTHENTICATION)` in `src/vnet/ethernet/types.def`), so the registration
is accepted rather than returning `VNET_API_ERROR_INVALID_VALUE`.

> **Do not register `0x88e5` (MACsec) here.** Protected frames arriving from the
> wire must reach the decrypt node, not be punted to the host.

The `sonic_ext` plugin also implements a `host-xc` (host cross-connect)
feature. If tap-originated traffic takes a path that bypasses the normal
`interface-output` arc, the encrypt node must be registered on that path too;
this should be verified during Phase 1.

#### 4.3.2 EAPOL bypass of the SecY

Once SAs exist, EAPOL must additionally **not** be MACsec-encapsulated. Both
nodes short-circuit on ethertype `0x888E` before any state lookup:

- **DUT → peer.** `wpa_supplicant` writes EAPOL to the Linux tap. linux_cp
  cross-connects the tap to the hwif, the frame traverses `interface-output`,
  and `sonic-ext-macsec-encrypt` passes it through untouched.
- **peer → DUT.** The frame arrives on the hwif, `sonic-ext-macsec-decrypt`
  passes it through, `ethernet-input` punts it to linux_cp, and it surfaces on
  the tap where `wpa_supplicant` is listening.

Frames that must also bypass MACsec, covered by the same ethertype check plus
an explicit allow-list: LACP (`0x8809` slow protocols) when the port is a LAG
member.

#### 4.3.3 Arc placement

**Ingress.** `sonic-ext-macsec-decrypt` registers on `device-input`, which
runs before `ethernet-input`, so the node sees the raw L2 frame. It must run
before any other `device-input` feature that parses the ethertype:

```c
VNET_FEATURE_INIT (sonic_ext_macsec_decrypt, static) = {
  .arc_name    = "device-input",
  .node_name   = "sonic-ext-macsec-decrypt",
  .runs_before = VNET_FEATURES ("ethernet-input", "sflow"),
};
```

**Egress.** `sonic-ext-macsec-encrypt` registers at the **tail** of
`interface-output`. MACsec is the wire format, so it must be applied after
everything else — including the Everflow late-clone node, so that a SPAN copy
of a protected port shows the pre-MACsec frame:

```c
VNET_FEATURE_INIT (sonic_ext_macsec_encrypt, static) = {
  .arc_name    = "interface-output",
  .node_name   = "sonic-ext-macsec-encrypt",
  .runs_after  = VNET_FEATURES ("sonic-ext-egress-mirror",
                                "sonic-ext-copp-ifout",
                                "sonic-ext-aggr-tap-redirect"),
  .runs_before = VNET_FEATURES ("interface-output-arc-end"),
};
```

`runs_before` / `runs_after` order features **within a single arc**; a node that
is not registered as a feature on that arc cannot be ordered against. Ordering
against `ip4-rewrite` / `ip6-rewrite` is therefore not expressible here, and is
also unnecessary — those are nodes on the IP forwarding path and have already
built the L2 header by the time the arc is entered, so the encrypt node always
sees a complete frame.

`sonic_ext` already registers three features on `interface-output`, and the
encrypt node must follow all of them:

| Existing feature | Why MACsec must run after it |
|---|---|
| `sonic-ext-egress-mirror` | Clones the wire form for Everflow. Running it first keeps the SPAN copy pre-MACsec, which is what makes a mirrored session readable. |
| `sonic-ext-copp-ifout` | Classifies egress control-plane traffic **by ethertype**. Once the SecTAG is applied every frame reads as `0x88E5` and the classification collapses. |
| `sonic-ext-aggr-tap-redirect` | May rewrite `VLIB_TX` and re-enter the arc. The encrypt node keys off `sw_if_index[VLIB_TX]`, so running first would both encrypt against the pre-redirect port and risk a second encapsulation on the re-entry pass. |

`interface-output-arc-end` is the arc's `last_in_arc` node — the same terminator
`sonic-ext-egress-mirror` already orders against — which is what makes the
registration above mean "run last".

Confirm the resolved order on a running image rather than assuming it:

```
docker exec syncd vppctl show features verbose
```

### 4.4 SAI APIs to implement in vslib/vpp

Add `vslib/vpp/SwitchVppMACsec.cpp` and override the base-class handlers in
`SwitchVpp`, rather than inheriting `SwitchStateBase`'s kernel implementation.

| SAI object / attribute | Action in `SwitchVppMACsec.cpp` |
|---|---|
| `SAI_OBJECT_TYPE_MACSEC` create | Keep base-class bookkeeping (including `SAI_MACSEC_ATTR_ENABLE_POST` → FIPS POST notification, already in `SwitchStateBase::create()`). Record direction. |
| `SAI_OBJECT_TYPE_MACSEC_PORT` create/remove | Resolve `SAI_MACSEC_PORT_ATTR_PORT_ID` → VPP `sw_if_index`. Call `vpp_macsec_port_add_del()`. |
| `SAI_OBJECT_TYPE_MACSEC_FLOW` create/remove | Bookkeeping only — the flow is the join between the ACL entry and the SC. Allocate OID, track `MACSEC_DIRECTION`. |
| `SAI_OBJECT_TYPE_MACSEC_SC` create/remove | Extract `MACSEC_SCI`, `MACSEC_CIPHER_SUITE`, `ENCRYPTION_ENABLE`, `MACSEC_EXPLICIT_SCI_ENABLE`, `MACSEC_REPLAY_PROTECTION_ENABLE/WINDOW`, `CONFIDENTIALITY_OFFSET`. Call `vpp_macsec_sc_add_del()`. |
| `SAI_OBJECT_TYPE_MACSEC_SC` set `ACTIVE_EGRESS_SA_ID` | Rekey. Call `vpp_macsec_sc_set_encoding_an()` (§4.6). |
| `SAI_OBJECT_TYPE_MACSEC_SA` create/remove | Extract `AN`, `SAK`, `SALT`, `AUTH_KEY`, `MACSEC_SSCI`, `CONFIGURED_EGRESS_XPN`, `MINIMUM_INGRESS_XPN`. Call `vpp_macsec_sa_add_del()`. |
| `SAI_OBJECT_TYPE_MACSEC_SA` set `CONFIGURED_EGRESS_XPN` / `MINIMUM_INGRESS_XPN` | Call `vpp_macsec_sa_set_xpn()`. |
| `SAI_OBJECT_TYPE_MACSEC_SA` get `CURRENT_XPN` | Read from VPP stat segment (§4.7). |
| `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW` set | Reuse the base-class attribute-loading helper `loadMACsecAttrsFromACLEntry()` (it is pure SAI-object traversal), but dispatch to `vpp_macsec_*` instead of `MACsecManager`. Enable → activate port/SC/SA; disable → deactivate. Preserve the base class's ordering constraint: **egress SAs before ingress SAs**. |
| `get_stats` / `get_stats_ext` / `clear_stats` on `SAI_OBJECT_TYPE_MACSEC_SA` | Override `SwitchVpp::getStatsExt()` (already exists) to route `SAI_MACSEC_SA_STAT_*` to the stat-segment reader. |
| `SAI_MACSEC_ATTR_*` capability reads | §4.8. |

`SwitchVpp::create()` / `remove()` / `set()` dispatch in
`vslib/vpp/SwitchVpp.cpp` already routes `SAI_OBJECT_TYPE_MACSEC_PORT/SC/SA`
and `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW` — only the bodies change to call
the new file instead of `SwitchStateBase::`.

### 4.5 Mapping to new VPP APIs

New messages in `sonic_ext.api`, wrapped in `vppxlate/SaiVppXlate.{h,c}`:

| vslib call | VPP API |
|---|---|
| `vpp_macsec_port_add_del()` | `sonic_ext_macsec_port_add_del { sw_if_index, direction, is_add, encrypt, send_sci, replay_protect, replay_window }` |
| `vpp_macsec_sc_add_del()` | `sonic_ext_macsec_sc_add_del { sw_if_index, direction, sci, cipher_suite, explicit_sci, confidentiality_offset, is_add }` |
| `vpp_macsec_sc_set_encoding_an()` | `sonic_ext_macsec_sc_set_encoding_an { sw_if_index, sci, an }` |
| `vpp_macsec_sa_add_del()` | `sonic_ext_macsec_sa_add_del { sw_if_index, direction, sci, an, sak[32], sak_len, salt[12], ssci, xpn_en, init_xpn, is_add }` |
| `vpp_macsec_sa_set_xpn()` | `sonic_ext_macsec_sa_set_xpn { sw_if_index, direction, sci, an, xpn }` |
| `vpp_macsec_sa_get_stats()` | Stat-segment read (no binary API), see §4.7 |

CLI for debugging, mirroring `show sflow` / `show interface span`:

```
vpp# show macsec
vpp# show macsec interface <intf>
vpp# show macsec sa
```

SAK material is passed over the VPP binary API shared-memory segment, which is
local to the syncd container and not exposed on any network socket. `show macsec
sa` must **not** print SAK/salt material — only key length, cipher and
counters.

### 4.6 SA rotation (rekey) and replay protection

**Rekey.** MKA installs a new SA on a new AN, then `macsecorch` sets
`SAI_MACSEC_SC_ATTR_ACTIVE_EGRESS_SA_ID` to point at it. The switchover must
be lossless enough for `test_rekey_by_period` (< 1% loss during two rekey
periods):

1. `vpp_macsec_sa_add_del(is_add=1)` installs the new SA on `AN'`; the SC's
   `sa_index[AN']` is published with a release-store. The old `encoding_an`
   is unchanged, so the datapath keeps using the old SA.
2. `vpp_macsec_sc_set_encoding_an(AN')` flips a single `u8` with a
   release-store. Worker threads read it once per packet; there is no window
   in which `sa_index[encoding_an]` is invalid.
3. The old SA is removed only when `macsecorch` deletes it. Removal uses a
   barrier (`vlib_worker_thread_barrier_sync`) before freeing the
   `vnet_crypto_ctx_t`, so no worker can be mid-op on a freed key.

On the ingress side both the old and the new AN's SA are installed
simultaneously, so in-flight frames encrypted under the old SAK still validate.

**Replay protection.** Per ingress SC, a 64-entry (or `replay_window`-sized)
sliding bitmap over the recovered XPN, identical in structure to
`ipsec`'s anti-replay:

- `xpn > highest_seen` → accept, shift window.
- `highest_seen - xpn < window` and bit clear → accept, set bit.
- otherwise → drop, `SAI_MACSEC_SA_STAT_IN_PKTS_LATE`.

When `SAI_MACSEC_SC_ATTR_MACSEC_REPLAY_PROTECTION_ENABLE` is false the check is
skipped but `highest_seen` is still tracked so XPN recovery keeps working.

> **Interop note.** `tests/common/macsec/macsec_helper.py::macsec_send()`
> deliberately inflates the PN it stamps on injected frames
> (`MACSEC_GLOBAL_PN_OFFSET += MACSEC_GLOBAL_PN_INCR`, starting at 1000) so
> that PTF-injected packets are never seen as late. The implementation must
> tolerate large forward PN jumps without resetting state.

**PN exhaustion.** The egress PN counter must never wrap. For the non-XPN
ciphers the PN is 32 bits and the IV is `SCI || PN` (§3.2), so a wrap reuses an
IV under the same SAK — which in GCM is not a degradation but a break: it
discloses the XOR of two plaintexts and exposes the GHASH authentication
subkey, permitting forgery. 802.1AE therefore requires the SecY to stop rather
than repeat a PN.

Exhaustion is resolved by rekeying, and the rekey is driven by MKA rather than
by the dataplane. `wpa_supplicant`'s `ieee802_1x_kay.c` carries a per-cipher
threshold, selected through `cipher_suite_tbl[].pn_exhaustion`:

| Cipher suite | Threshold | Constant |
|---|---|---|
| `GCM-AES-128`, `GCM-AES-256` | `0xC0000000` (75% of 2^32) | `PENDING_PN_EXHAUSTION` |
| `GCM-AES-XPN-128`, `GCM-AES-XPN-256` | `0xC000000000000000` (75% of 2^64) | `PENDING_XPN_EXHAUSTION` |

Only the **Key Server** acts on it, and it does so in two places: against its
own lowest PN while building an MKPDU (`"KaY: My LLPN exhaustion"` /
`"My OLPN exhaustion"`), and against the peer's, learned from the LLPN/OLPN
fields of a received MKPDU (`"KaY: Peer LPN exhaustion"`). Either sets
`participant->new_sak`, and the resulting SA becomes active through the ordinary
`SAI_MACSEC_SC_ATTR_ACTIVE_EGRESS_SA_ID` path described above. The
non-key-server side contributes its PN through the MKPDU and waits.

The value compared is the lowest acceptable PN, derived from the transmit SA's
next PN sampled on the previous `mka_hello_time` tick (`lpn = txsa->next_pn - 1`).
`ieee802_1x_kay.c` notes that this derivation assumes `mka_hello_time` is 2 s.

The dataplane keeps a backstop: if a rekey has not landed by the time a non-XPN
SA reaches `0xFFFFFFFF`, the encrypt node stops transmitting on that SA and
drops with a `PN_EXHAUSTED` counter instead of wrapping.

For the XPN ciphers the 64-bit threshold is not reachable in practice. The
32-bit value **on the wire** still wraps every 2^32 frames, but that is a
receive-side concern handled by `macsec_recover_xpn()` (Appendix B), which
reconstructs the upper 32 bits; it does not address the egress case above.

`clib_atomic_fetch_add` guarantees that each worker thread draws a distinct PN,
but not that frames leave the interface in PN order. Receivers must tolerate
modest reordering, which sets a lower bound on the replay window configured
above.

### 4.7 Counters, XPN and stat segment

Each SA gets a stat-segment entry under `/macsec/sa/<index>/`:

| Direction | SAI counter | VPP stat |
|---|---|---|
| Egress | `SAI_MACSEC_SA_STAT_OUT_PKTS_ENCRYPTED` | `out-pkts-encrypted` |
| Egress | `SAI_MACSEC_SA_STAT_OUT_PKTS_PROTECTED` | `out-pkts-protected` |
| Egress | `SAI_MACSEC_SA_STAT_OCTETS_ENCRYPTED` | `octets-encrypted` |
| Egress | `SAI_MACSEC_SA_STAT_OCTETS_PROTECTED` | `octets-protected` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_OK` | `in-pkts-ok` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_INVALID` | `in-pkts-invalid` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_NOT_VALID` | `in-pkts-not-valid` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_LATE` | `in-pkts-late` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_DELAYED` | `in-pkts-delayed` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_UNCHECKED` | `in-pkts-unchecked` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_NOT_USING_SA` | `in-pkts-not-using-sa` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_PKTS_UNUSED_SA` | `in-pkts-unused-sa` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_OCTETS_DECRYPTED` | `in-octets-decrypted` |
| Ingress | `SAI_MACSEC_SA_STAT_IN_OCTETS_VALIDATED` | `in-octets-validated` |
| Both | `SAI_MACSEC_SA_ATTR_CURRENT_XPN` | `current-xpn` (a gauge, not a stat) |

`SwitchVpp::refresh_macsec_sa_stat()` replaces the base-class kernel scrape and
reads `current-xpn` from the stat segment into the SA object's attribute cache,
so that `SwitchStateBase::refresh_read_only()` keeps working unchanged.

`current-xpn` is not only consumed by `show macsec`. SONiC's MKA reads it back
to drive PN-exhaustion rekey (§4.6), and the path terminates in this exact
COUNTERS_DB field — from `wpa_supplicant`'s `driver_macsec_sonic.c`:

```c
static int macsec_sonic_get_transmit_next_pn(void *priv, struct transmit_sa *sa)
{
    ...
    int ret = sonic_db_get_counter(drv->sonic_manager, COUNTERS_TABLE, key,
                                   "SAI_MACSEC_SA_ATTR_CURRENT_XPN", &pn);
    if (ret == SONIC_DB_SUCCESS)
        sa->next_pn = pn;
    return ret;
}
```

The full loop is therefore `refresh_macsec_sa_stat()` → SA attribute cache →
syncd FlexCounter → COUNTERS_DB → `macsec_sonic_get_transmit_next_pn()` →
`txsa->next_pn` → the `ieee802_1x_kay.c` threshold comparison → rekey.

Note the failure mode. When the counter is absent the driver returns
non-success and leaves `sa->next_pn` **unchanged**, so the LPN never advances
and exhaustion is never detected. A placeholder implementation that reports a
fixed value has the same effect: it silently disables PN-exhaustion rekey.
Any interim stub used to unblock the control-plane tests is therefore a Phase 3
gap to close, not a solution.

`clear_stats` on a `MACSEC_SA` zeroes the `SAI_MACSEC_SA_STAT_*` entries but
**not** `current-xpn` — `test_clear_counters` asserts exactly this
(`counter.startswith('SAI_MACSEC_SA_STAT')` are reset, everything else must be
`>=` its previous value).

`test_counters` currently short-circuits with:

```python
if duthost.facts["asic_type"] == "vs":
    # vsonic only has xpn counter
    return
```

sonic-vpp reports `asic_type == "vpp"`, so the full counter set above is
mandatory. Implementing them is preferred over widening that exemption.

### 4.8 Switch / MACsec capability advertisement

`macsecorch` reads capability attributes off the `SAI_OBJECT_TYPE_MACSEC`
object before creating anything. Today `vslib` only has a refresh hook for
`SAI_MACSEC_ATTR_SCI_IN_INGRESS_MACSEC_ACL`
(`SwitchStateBase::refresh_macsec_sci_in_ingress_macsec_acl`, hardcoded to
`true`). The following must be returned by `SwitchVpp`:

| Attribute | sonic-vpp value |
|---|---|
| `SAI_MACSEC_ATTR_SCI_IN_INGRESS_MACSEC_ACL` | `true` (reuse base hook) |
| `SAI_MACSEC_ATTR_SUPPORTED_CIPHER_SUITE_LIST` | `{ GCM_AES_128, GCM_AES_256, GCM_AES_XPN_128, GCM_AES_XPN_256 }` |
| `SAI_MACSEC_ATTR_PN_32BIT_SUPPORTED` | `true` |
| `SAI_MACSEC_ATTR_XPN_64BIT_SUPPORTED` | `true` |
| `SAI_MACSEC_ATTR_GCM_AES128_SUPPORTED` / `..._AES256_SUPPORTED` | `true` |
| `SAI_MACSEC_ATTR_MAX_SECURE_ASSOCIATIONS_PER_SC` | `4` (`SAI_MACSEC_MAX_SECURE_ASSOCIATIONS_PER_SC_FOUR`) |
| `SAI_MACSEC_ATTR_AVAILABLE_MACSEC_FLOW` / `_SC` / `_SA` | Soft limits minus in-use count, CRM-tracked like nexthops (`vslib/vpp/CRMTracker.cpp`) |
| `SAI_MACSEC_ATTR_SECTAG_OFFSETS_SUPPORTED` | `{ 0 }` |
| `SAI_MACSEC_ATTR_STATS_MODE_READ_SUPPORTED` / `_READ_CLEAR_SUPPORTED` | `true` |
| `SAI_MACSEC_ATTR_SYSTEM_SIDE_MTU` | Port MTU minus 32 (§4.9) |
| `SAI_MACSEC_ATTR_WARM_BOOT_SUPPORTED` | `false` initially |

The exact set `macsecorch` queries should be confirmed during bring-up by
logging unsupported-attribute failures from `syncd`.

### 4.9 MTU and buffer headroom

A protected frame grows by up to **32 bytes** (16-byte SecTAG with SCI +
16-byte ICV). Two consequences:

- **Headroom.** The egress node prepends the SecTAG by moving DA/SA backwards
  into `vlib_buffer_t` pre-data. `VLIB_BUFFER_PRE_DATA_SIZE` (128 by default)
  is ample, but the node must assert it rather than corrupting the buffer.
- **MTU.** VPP's hwif MTU must be >= `port MTU + 32`, otherwise full-size
  frames are dropped after encapsulation. `vpp_macsec_port_add_del()` bumps
  the hwif MTU on enable and restores it on disable, and
  `SAI_MACSEC_ATTR_SYSTEM_SIDE_MTU` reports the reduced system-side value.
- Chained buffers (`VLIB_BUFFER_NEXT_PRESENT`) must be handled or explicitly
  rejected. Phase 1 may reject them with a counter; Phase 3 adds
  `vnet_crypto_op_chunk_t` support, which is what `esp_encrypt` does.

### 4.10 Plugin enablement and build

- `sonic_ext` is already enabled in both `docker-syncd-vpp/conf/startup.conf.tmpl`
  and `docker-sonic-vpp/conf/startup.conf.tmpl`
  (`plugin sonic_ext_plugin.so { enable }`).
- The MACsec feature is gated by the existing per-feature mechanism:
  `SONIC_EXT_CONFIG="macsec=on"` → `vpp_init.sh` emits `macsec on` into the
  `sonic-ext { }` stanza. Default **off** until Phase 3 completes.
- `vslib/vpp` queries `sonic_ext_feature_get { name = "macsec" }` at switch
  create; if the reply is `disabled`, MACsec SAI object creates return
  `SAI_STATUS_NOT_SUPPORTED` rather than silently succeeding. This matters
  because the inherited kernel implementation currently accepts the entire SAI
  MACsec object chain without error while programming nothing (§3.4) — failures
  must be loud and attributable.
- A crypto engine must be loaded. `crypto_native` is built in and probes for
  AES-NI/PCLMUL; on KVM testbeds without those CPU flags exposed, fall back to
  `crypto_openssl`. `vpp_init.sh` should log which engine bound the
  `aes-128-gcm` handler.
- `FEATURE.macsec` is already present in `docker-sonic-vpp/conf/init_cfg.json.j2`;
  the KVM image's t0 config must carry it too.

---

## 5. Implementation Plan

### Phase 1 — EAPOL transport, then a minimal datapath

Goal: MKA converges on a sonic-vpp ↔ sonic-vs protected link, then
`test_server_to_neighbor` passes with a static 128-bit non-XPN SAK.

**Task 1 (critical path, do first) — make EAPOL traverse the DUT.** This gates
everything else in this HLD: no EAPOL → no MKA → no SAK → no SA → nothing for
the §4.2 nodes to encrypt with. It is also the cheapest proof point, requiring
no crypto, no SA and no new graph node.

- Register EAPOL with linux_cp per §4.3.1.
- Verify the `host-xc` path: if tap-originated traffic bypasses the normal
  `interface-output` arc, register the encrypt node there too (§4.3.1).
- **Exit criterion for task 1:** with MACsec configured on both ends and *no*
  MACsec datapath implemented at all, both ends show a populated
  `MACSEC_INGRESS_SC_TABLE` and `MACSEC_EGRESS_SA_TABLE`, and
  `MACSEC_PORT_TABLE` flips to `enable: true`. An ingress SC can only be
  created after an MKPDU is *received*, so this is a precise test of EAPOL
  transport in both directions. At that point
  `test_wpa_supplicant_processes`, `test_appl_db` and probably
  `test_mka_session` pass, and the dataplane tests fail cleanly on *missing
  encryption* rather than on missing keys — which is the signal the §4.2
  design needs in order to be validated.

A fast local check, rather than a full suite run:

```bash
# On the DUT, with MACsec configured on both ends of the link.
sonic-db-cli APPL_DB KEYS 'MACSEC_INGRESS_SC_TABLE:Ethernet112:*'

# Confirm the ethertype registration took:
docker exec syncd vppctl show lcp ethertype          # expect 0x888e

# And/or watch EAPOL directly on both ends simultaneously:
tcpdump -ni Ethernet112 ether proto 0x888e           # DUT, linux_cp tap
tcpdump -ni Ethernet1   ether proto 0x888e           # neighbor
```

Deliverables (remainder):

- `sonic_ext` MACsec feature: data model, `sonic-ext-macsec-encrypt` and
  `sonic-ext-macsec-decrypt` nodes, EAPOL bypass, feature-arc registration.
- `sonic_ext.api` messages for port / SC / SA add-del; `show macsec` CLI.
- `SaiVppXlate` wrappers.
- `vslib/vpp/SwitchVppMACsec.cpp` handling `MACSEC_PORT`, `MACSEC_FLOW`,
  `MACSEC_SC`, `MACSEC_SA`, and `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW`.
- Capability attributes (§4.8) sufficient for `macsecorch` to proceed.
- MTU bump on enable.

Exit criteria:

- MKA converges on a sonic-vpp ↔ sonic-vs protected link
  (`test_wpa_supplicant_processes`, `test_appl_db` pass).
- `tests/macsec/test_dataplane.py::test_server_to_neighbor` and
  `::test_dut_to_neighbor` pass with a `128_SCI` profile.
- `vppctl show macsec` reports non-zero encrypt/decrypt counts.
- **Fallback trigger:** if task 1 cannot be resolved in this phase, switch to
  Option A (§4.1) for the test-enablement milestone and keep Option B as
  follow-up work.

### Phase 2 — XPN, replay protection, rekey

Goal: the `256_XPN_SCI` profile works and SAs rotate without loss.

Deliverables:

- XPN IV derivation and 64-bit PN recovery (Appendix B).
- `salt` / `SSCI` handling from `SAI_MACSEC_SA_ATTR_SALT` /
  `..._MACSEC_SSCI`.
- `GCM-AES-256` key size support.
- Per-ingress-SC replay window, `SAI_MACSEC_SC_ATTR_MACSEC_REPLAY_PROTECTION_*`.
- Atomic `encoding_an` flip on `SAI_MACSEC_SC_ATTR_ACTIVE_EGRESS_SA_ID` set,
  with worker-barrier-protected SA teardown.
- `SAI_MACSEC_SA_ATTR_CONFIGURED_EGRESS_XPN` / `MINIMUM_INGRESS_XPN` set
  handlers.

Exit criteria:

- Full `tests/macsec/test_controlplane.py` passes for both
  `128_SCI` and `256_XPN_SCI` profiles.
- `test_rekey_by_period` reports < 1% loss.
- `test_profile_replace` re-establishes MKA within 60 s.

### Phase 3 — Counters

Goal: `show macsec` reports real per-SA statistics.

Deliverables:

- Stat-segment entries per §4.7.
- `SwitchVpp::refresh_macsec_sa_stat()` and `getStatsExt()` routing for
  `SAI_MACSEC_SA_STAT_*`.
- `clear_stats` support.
- Chained-buffer support via `vnet_crypto_op_chunk_t` (jumbo frames).

Exit criteria:

- `test_counters` and `test_clear_counters` pass **without** widening the
  `asic_type == "vs"` exemption.

### Phase 4 — sonic-mgmt regression and CI

Goal: the MACsec suite runs green in the VPP KVM pipeline.

Deliverables:

- Testbed enablement: the MACsec suite requires **SONiC neighbors**, so the
  VPP t0 testbed must be deployed with vSONiC (KVM) neighbors and the run must
  pass a matching `--neighbor_type`. See §7.3.
- Any sonic-mgmt platform-gating fixes identified during bring-up (e.g.
  `get_macsec_ifname()` platform-string handling, `test_mka_session` gating).
- Make the `macsec` module a standing part of the VPP KVM nightly with
  `--neighbor_type=sonic --enable_macsec --macsec_profile=...`, matching how it
  is already configured for `t0`/`t1-lag` in
  `sonic-mgmt/.azure-pipelines/pr_test_scripts.yaml`.
- Documented skips with justification for
  `test_macsec_pfc.py` (no PFC model in VPP) and any per-interface-profile
  cases that require `--per_interface_macsec`.

Exit criteria:

- `sonic-mgmt/tests/macsec/` green on the VPP KVM t0 testbed with no
  undocumented exclusions.
- Nightly CI job wired up.

### Phase 5 (optional) — hardening

- Warm boot (`SAI_MACSEC_ATTR_WARM_BOOT_SUPPORTED`).
- `test_docker_restart.py`, `test_fault_handling.py`, `test_macsec_recovery.py`
  coverage.
- Upstreaming the MACsec nodes to FD.io VPP as a standalone `macsec` plugin.

---

## 6. SONiC MACsec Configuration Guide (sonic-vpp specifics)

Standard `config macsec` CLI is unchanged. Examples assume a sonic-vpp DUT
with `Ethernet0..Ethernet32`.

### 6.1 Create a profile and bind it to a port

```bash
config macsec profile add \
    --priority 0 \
    --cipher_suite GCM-AES-XPN-256 \
    --primary_cak <64-hex-CAK> \
    --primary_ckn <64-hex-CKN> \
    --policy security \
    --enable_replay_protect \
    --replay_window 0 \
    --send_sci \
    --rekey_period 0 \
    MACSEC_PROFILE

config macsec port add Ethernet0 MACSEC_PROFILE
```

Do not paste production CAK/CKN material into shell history; on a test bed use
the values sonic-mgmt generates from `--macsec_profile`.

### 6.2 Verify

```bash
show macsec
show macsec Ethernet0

# APPL_DB view
sonic-db-cli APPL_DB HGETALL 'MACSEC_PORT_TABLE:Ethernet0'
sonic-db-cli APPL_DB KEYS 'MACSEC_EGRESS_SA_TABLE:Ethernet0:*'

# VPP view (sonic-vpp specific)
docker exec syncd vppctl show macsec
docker exec syncd vppctl show macsec interface <hwif>
docker exec syncd vppctl show macsec sa
docker exec syncd vppctl show lcp ethertype
docker exec syncd vppctl show features verbose    # arc membership and order
```

### 6.3 Confirm MKA converged

```bash
ps aux | grep -w wpa_supplicant | grep -w Ethernet0
```

### 6.4 Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| `wpa_supplicant` running but no SA in APPL_DB | EAPOL not reaching the peer | `vppctl show lcp ethertype` should list `0x888e` (§4.3.1); `tcpdump -i Ethernet0 ether proto 0x888e` on both ends |
| `wpa_supplicant` running, EAPOL on the wire, still no SA | Peer not configured, or CAK/CKN mismatch | Compare `MACSEC_PROFILE` on both ends |
| SAs installed but no traffic passes | Encrypt node not on the path | `vppctl show interface features <hwif>` should list `sonic-ext-macsec-encrypt` on `interface-output` |
| Ping from DUT fails, PTF-injected traffic works | `host-xc` bypasses `interface-output` (§4.3.1) | `vppctl show linux-cp`, trace a tap-originated packet with `vppctl trace add ...` |
| `in-pkts-not-valid` climbing | SAK/IV mismatch | Compare `salt`/`ssci`/cipher in APPL_DB against `vppctl show macsec sa` (key material redacted — compare lengths and cipher only) |
| `in-pkts-late` climbing | Replay window too small, or PN jump | `show macsec <port>` ingress SA `lowest_acceptable_pn` |
| Full-size frames dropped after enabling MACsec | hwif MTU not bumped by 32 | `vppctl show hardware-interfaces <hwif>` |
| MACsec object creates return NOT_SUPPORTED | Feature gated off | `vppctl show sonic-ext features`; set `SONIC_EXT_CONFIG="macsec=on"` |

---

## 7. Test Plan

### 7.1 vslib unit tests

Mirror the existing `unittest/vslib/TestSwitchStateBaseMACsec.cpp` and
`TestMACsecManager.cpp` for the VPP backend, alongside
`unittest/vslib/TestSwitchVpp.cpp`:

| Test | Expectation |
|---|---|
| Create `MACSEC_PORT` on a VPP port | `vpp_macsec_port_add_del(is_add=1)` called with the correct `sw_if_index` and direction |
| Create egress SC then SA, then enable the ACL entry | Egress SA activated before ingress SA (ordering constraint preserved from the base class) |
| Set `ACTIVE_EGRESS_SA_ID` | `vpp_macsec_sc_set_encoding_an()` with the new AN |
| Remove SA while ACL entry still active | Graceful; no orphan VPP state |
| Get `CURRENT_XPN` | Reads stat segment, not `ip macsec show` |
| `clear_stats` on SA | `SAI_MACSEC_SA_STAT_*` reset, `CURRENT_XPN` unchanged |
| MACsec feature disabled in `sonic_ext` | Creates return `SAI_STATUS_NOT_SUPPORTED` |

### 7.2 VPP node tests

Run in the VPP unit-test framework against known-answer vectors:

| Test | Expectation |
|---|---|
| GCM-AES-128 encrypt, `send_sci=1`, `E=1` | Byte-exact SecTAG + ciphertext + ICV against an IEEE/`scapy.contrib.macsec` reference vector |
| GCM-AES-256-XPN encrypt | IV = `salt XOR (SSCI \|\| XPN)`; matches reference |
| Integrity-only (`E=0,C=1`) | Plaintext preserved, AAD includes user data, ICV valid |
| Decrypt round-trip | encrypt→decrypt yields the original frame byte-for-byte |
| Decrypt with corrupted ICV | Dropped, `in-pkts-not-valid` increments |
| Replay: re-send a previously accepted PN | Dropped, `in-pkts-late` increments |
| Replay: large forward PN jump | Accepted, window shifts (matches PTF's PN inflation) |
| EAPOL frame on an enabled port | Passes through unmodified in both directions |
| Non-MACsec frame, `validate strict` | Dropped, `in-pkts-not-using-sa` increments |
| Rekey under load | No drops attributable to the AN flip |
| Max-MTU frame | Encapsulates without buffer overrun; hwif MTU honored |

### 7.3 sonic-mgmt regression (Phase 4)

> **Testbed prerequisite.** The MACsec suite is written against **SONiC**
> neighbors. The t0-vpp testbed must be deployed with vSONiC (KVM) neighbors
> (`testbed-cli.sh -k vsonic`, which requires a separate `start-topo-vms` stage
> and a staged `sonic-vs.img`), and the run must pass a matching
> `--neighbor_type`. cEOS neighbors do not bring up a MACsec interface;
> container-based cSONiC neighbors do not satisfy
> `enable_macsec_feature()`, which probes neighbors with `docker ps`.
>
> **Every module below is gated on MKA convergence.** `load_macsec_info`
> (`tests/common/macsec/__init__.py`) is module-scoped and autouse, and calls
> `request.getfixturevalue('wait_mka_establish')`. Until §4.3.1 is in place,
> all of these report setup errors regardless of the DUT's MACsec datapath.
> `test_fips_post_status.py` is the sole exception; it overrides the autouse
> fixtures with no-ops.

| Test | Behavior covered | HLD section |
|---|---|---|
| `test_controlplane.py::test_wpa_supplicant_processes` | MKA daemon per protected port | §3.1 |
| `test_controlplane.py::test_appl_db` | SC/SA tables consistent DUT↔peer | §4.4 |
| `test_controlplane.py::test_mka_session` | `ip -j macsec show` parity — **platform-gated on `x86_64-kvm_x86_64`**, needs a decision for sonic-vpp | §3.5 |
| `test_controlplane.py::test_rekey_by_period` | SA rotation, < 1% loss | §4.6 |
| `test_controlplane.py::test_profile_replace` | Profile swap re-establishes MKA in 60 s | §4.6 |
| `test_dataplane.py::test_server_to_neighbor` | **End-to-end encryption**; PTF decrypts with the SAK from APPL_DB | §4.2, §4.3 |
| `test_dataplane.py::test_dut_to_neighbor` | DUT-sourced traffic is encrypted (exercises the tap/`host-xc` path) | §4.3.1 |
| `test_dataplane.py::test_neighbor_to_neighbor` | Transit across two protected portchannels | §4.2, §7.4 |
| `test_dataplane.py::test_counters` | Per-SA counters advance; **requires the full `SAI_MACSEC_SA_STAT_*` set for `asic_type == "vpp"`** | §4.7 |
| `test_dataplane.py::test_clear_counters` | `sonic-clear macsec` resets stats but not XPN | §4.7 |
| `test_interop_protocol.py` | LACP / LLDP / BGP / SNMP over a protected link | §4.3.2 |
| `test_fault_handling.py` | Link flap at three timescales; mismatched CAK must not establish | §4.6 |
| `test_deployment.py` | `config_reload` persistence; scale rekey across all links | §4.6 |
| `test_docker_restart.py`, `test_macsec_recovery.py` | `syncd`/`swss` restart recovery; ASIC_DB stale-SAK / stale-AN guards | Phase 5 |
| `test_fips_post_status.py` | `SAI_MACSEC_ATTR_ENABLE_POST` notification | §4.4 (base class) |
| `test_macsec_pfc.py` | PFC over MACsec | **Skip** — no PFC model in VPP |
| `test_per_interface_profile.py` | Per-interface profiles (`--per_interface_macsec`) | Phase 5 |

### 7.4 LAG / port-channel

`macsecorch` binds MACsec per **member port**, not per LAG object, so no
additional VPP work is expected: each member's `sw_if_index` gets its own
SecY, SC and SAs, exactly as for a standalone port. `test_server_to_neighbor`
and `test_neighbor_to_neighbor` both iterate over portchannel members and
therefore cover this. To be confirmed in Phase 1 — in particular that LACP
(`0x8809`) bypasses MACsec (§4.3.2).

### 7.5 Negative / robustness

- Remove a `MACSEC_FLOW` while SAs are still bound — graceful unbind, no VPP
  crash.
- Disable MACsec on a port mid-traffic — hwif MTU restored, traffic continues
  in the clear.
- `syncd` restart with SAs installed — VPP state torn down and rebuilt, no
  orphan SCs.
- All four ANs populated on one SC — `MAX_SECURE_ASSOCIATIONS_PER_SC` honored;
  a fifth returns `SAI_STATUS_INSUFFICIENT_RESOURCES`.
- MACsec + Everflow on the same port — the SPAN clone carries the pre-MACsec
  frame (§4.3.3 arc ordering).

---

## 8. References

- [SONiC MACsec HLD](https://github.com/sonic-net/SONiC/blob/master/doc/macsec/MACsec_hld.md)
- [sonic-buildimage#26048](https://github.com/sonic-net/sonic-buildimage/issues/26048) — `[sonic-vpp][Data Plane][t0] MACsec — Enable data plane testing on VPP KVM testbed`
- IEEE 802.1AE-2018 (MACsec), IEEE 802.1AEbw-2013 (XPN), IEEE 802.1X-2010 (MKA)
- `sonic-mgmt/tests/macsec/` and `sonic-mgmt/tests/common/macsec/`
- `sonic-sairedis/vslib/SwitchStateBaseMACsec.cpp`, `vslib/MACsecManager.cpp` — the existing VS (kernel) implementation
- `sonic-sairedis/vslib/vpp/SwitchVppHostif.cpp` — VPP hostif / linux_cp model
- `sonic-platform-vpp/vppbld/plugins/sonic_ext/` — SONiC VPP extension plugin
- `sonic-platform-vpp/TODO.md` — original gap list including `SAI_OBJECT_TYPE_MACSEC*`
- FD.io VPP `src/vnet/crypto/crypto.h`, `src/crypto_engines/native/aes_gcm.c`
- FD.io VPP `src/plugins/linux-cp/lcp_interface.c`, `src/vnet/ethernet/types.def`,
  `test/test_linux_cp.py` — linux_cp ethertype punt model
- [vpp-sflow.md](./vpp-sflow.md), [vpp-mirror.md](./vpp-mirror.md) — companion sonic-vpp HLDs

---

## Appendix A: File Change Summary

### sonic-sairedis

| File | Change | Description |
|---|---|---|
| `vslib/vpp/SwitchVppMACsec.cpp` | **New** | MACsec port/flow/SC/SA create-remove-set, ACL MACsec-flow activation, stat readback |
| `vslib/vpp/SwitchVpp.h` | Modify | Declare the MACsec overrides and the `m_macsec_*` state maps |
| `vslib/vpp/SwitchVpp.cpp` | Modify | Route `SAI_OBJECT_TYPE_MACSEC_{PORT,FLOW,SC,SA}` and `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW` to `SwitchVppMACsec.cpp`; MACsec capability attributes; `refresh_macsec_sa_stat` override |
| `vslib/vpp/vppxlate/SaiVppXlate.c` | Modify | Register EAPOL (`0x888e`) with linux_cp in `init_vpp_client()` (§4.3.1); implement the `vpp_macsec_*` wrappers over the VPP binary API |
| `vslib/vpp/vppxlate/SaiVppXlate.h` | Modify | `vpp_macsec_port_add_del()`, `vpp_macsec_sc_add_del()`, `vpp_macsec_sc_set_encoding_an()`, `vpp_macsec_sa_add_del()`, `vpp_macsec_sa_set_xpn()`, stat reader |
| `vslib/vpp/CRMTracker.cpp` | Modify | Track MACsec flow/SC/SA usage for `SAI_MACSEC_ATTR_AVAILABLE_*` |
| `vslib/vpp/Makefile.am` | Modify | Add the new source file |
| `unittest/vslib/TestSwitchVppMACsec.cpp` | **New** | §7.1 |
| `unittest/vslib/Makefile.am` | Modify | Register the new test |

### sonic-platform-vpp

| File | Change | Description |
|---|---|---|
| `vppbld/plugins/sonic_ext/macsec.c` | **New** | Port/SC/SA pools, key install via `vnet_crypto`, enable/disable, CLI |
| `vppbld/plugins/sonic_ext/macsec.h` | **New** | Data model (§4.2.1) |
| `vppbld/plugins/sonic_ext/macsec_encrypt_node.c` | **New** | `sonic-ext-macsec-encrypt` on `interface-output` |
| `vppbld/plugins/sonic_ext/macsec_decrypt_node.c` | **New** | `sonic-ext-macsec-decrypt` on `device-input` |
| `vppbld/plugins/sonic_ext/sonic_ext.api` | Modify | MACsec API messages (§4.5) |
| `vppbld/plugins/sonic_ext/sonic_ext_api.c` | Modify | Handlers for the new messages |
| `vppbld/plugins/sonic_ext/sonic_ext.c` | Modify | Register `macsec` as a selectable feature |
| `vppbld/plugins/sonic_ext/CMakeLists.txt` | Modify | Add the new sources |
| `docker-syncd-vpp/scripts/vpp_init.sh` | Modify | Accept `macsec=on\|off` in `SONIC_EXT_CONFIG`; log the bound crypto engine |
| `docker-syncd-vpp/conf/startup.conf.tmpl` | Modify | Ensure a crypto engine plugin is enabled |

### sonic-mgmt

| File | Change | Description |
|---|---|---|
| `tests/common/macsec/macsec_platform_helper.py` | Modify (if required) | Platform-string gating for sonic-vpp |
| `tests/macsec/test_dataplane.py` | Modify (only if Phase 3 slips) | Counter-set exemption for `asic_type == "vpp"` |
| VPP t0 testbed definition / nightly job | Modify | Deploy vSONiC (KVM) neighbors: add a `start-topo-vms` stage, stage `sonic-vs.img`, pass a matching `--neighbor_type` (§7.3) |
| `.azure-pipelines/pr_test_scripts.yaml` | Modify | Add `macsec` to the VPP KVM t0 test set |

---

## Appendix B: MACsec SecTAG and IV Reference

### SecTAG layout

```
 offset  0        1        2        3        4 .. 7      8 .. 15
        +--------+--------+--------+--------+----------+------------+
        | 0x88   | 0xE5   | TCI/AN |   SL   |    PN    |   SCI      |
        +--------+--------+--------+--------+----------+------------+
          EtherType 0x88E5                    4 bytes    8 bytes,
                                                         present iff
                                                         TCI.SC == 1
```

TCI/AN byte:

```
  bit  7   6   5   4   3   2   1   0
       V  ES  SC SCB   E   C  AN1 AN0
```

| Bit | SONiC usage |
|---|---|
| `V` | Always 0 (version 0) |
| `ES` | `SAI_MACSEC_SC_ATTR_USE_ES`; 0 in SONiC |
| `SC` | 1 when `send_sci = true` (`SAI_MACSEC_SC_ATTR_MACSEC_EXPLICIT_SCI_ENABLE`) |
| `SCB` | `SAI_MACSEC_SC_ATTR_USE_SCB`; 0 in SONiC |
| `E` | 1 when `policy = security` (`SAI_MACSEC_SC_ATTR_ENCRYPTION_ENABLE`) |
| `C` | 1 — changed text present (always, since `confidentiality_offset = 0`) |
| `AN` | Association number, 0..3 |

`SL` (short length) is the length of the secure data when it is < 48 bytes,
else 0.

### IV derivation

**Non-XPN (`GCM-AES-128`, `GCM-AES-256`):**

```
IV[0..7]  = SCI          (8 bytes, the transmitting SC's SCI)
IV[8..11] = PN           (4 bytes, big-endian)
```

Note the SCI is used even when `send_sci = false` — it is known implicitly
from the peer's MAC address.

**XPN (`GCM-AES-XPN-128`, `GCM-AES-XPN-256`):**

```
IV = salt XOR ( SSCI || XPN )
       salt : 12 bytes, SAI_MACSEC_SA_ATTR_SALT
       SSCI :  4 bytes, SAI_MACSEC_SA_ATTR_MACSEC_SSCI (big-endian)
       XPN  :  8 bytes, the full 64-bit packet number (big-endian)
```

### 64-bit XPN recovery on ingress

Only the low 32 bits travel on the wire. The receiver reconstructs the upper
32 bits from the highest XPN seen on that SC:

```c
static u64
macsec_recover_xpn (u64 highest_seen, u32 pn_on_wire)
{
  u32 hi = (u32) (highest_seen >> 32);
  u32 lo = (u32) highest_seen;

  /* Standard 802.1AEbw recovery: if the wire PN is far below the current
   * low word, assume the 32-bit counter wrapped. */
  if (pn_on_wire < lo && (lo - pn_on_wire) > (1u << 31))
    hi++;
  else if (pn_on_wire > lo && (pn_on_wire - lo) > (1u << 31) && hi > 0)
    hi--;

  return ((u64) hi << 32) | pn_on_wire;
}
```

### AAD construction

```
confidentiality (E=1, C=1):
    AAD = DA(6) || SA(6) || SecTAG(8 or 16)
    plaintext/ciphertext = user data
    ICV covers AAD + ciphertext

integrity only (E=0, C=1):
    AAD = DA(6) || SA(6) || SecTAG(8 or 16) || user data
    plaintext/ciphertext = empty
    ICV covers AAD
```
