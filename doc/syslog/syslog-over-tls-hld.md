# SONiC Remote Syslog over TLS

## High Level Design document

## Table of contents

- [Revision](#revision)
- [About this manual](#about-this-manual)
- [Scope](#scope)
- [Abbreviations](#abbreviations)
- [1. Introduction](#1-introduction)
  - [1.1. Feature overview](#11-feature-overview)
  - [1.2. Requirements](#12-requirements)
- [2. Design](#2-design)
  - [2.1. Overview](#21-overview)
  - [2.2. Trust material and SSL profiles](#22-trust-material-and-ssl-profiles)
  - [2.3. Configuration model](#23-configuration-model)
  - [2.4. rsyslog rendering and apply](#24-rsyslog-rendering-and-apply)
  - [2.5. Operational state](#25-operational-state)
  - [2.6. CLI and Generic Config Updater](#26-cli-and-generic-config-updater)
  - [2.7. YANG model](#27-yang-model)
  - [2.8. Host image changes](#28-host-image-changes)
  - [2.9. Security properties](#29-security-properties)
  - [2.10. Multi-ASIC and containers](#210-multi-asic-and-containers)
- [3. Test plan](#3-test-plan)

## Revision

| Rev | Date       | Author        | Description        |
|:---:|:----------:|:-------------:|:-------------------|
| 0.1 | 13/10/2026 | (initial)     | Initial version    |

## About this manual

This document describes the high-level design for forwarding SONiC host syslog to remote collectors over TLS. It extends the remote syslog capabilities documented in [syslog-design.md](syslog-design.md) (UDP/TCP, source IP, VRF, filter, severity) with a `tls` transport option backed by rsyslog’s OpenSSL stream driver.

## Scope

**In scope:**

1. Remote syslog from the **host** rsyslog instance to one or more collectors over **TLS** (TCP + rsyslog `ossl`).
2. CONFIG_DB schema, YANG validation, CLI (`config` / `show`), and Generic Config Updater validation.
3. Rendering `/etc/rsyslog.conf` via `rsyslog-config` and `rsyslog.conf.j2`.
4. Use of SSL profile material under `/etc/sonic/ssl-certs/<profile_id>/`, installed by gNSI **Certz** or placed there manually by the operator.
5. STATE_DB visibility of whether TLS forwarding was actually applied.

**Out of scope:**

1. TLS for syslog **reception** on the switch (containers still ship logs to the host over existing UDP/RELP paths).
2. Per-container remote syslog over TLS (only the host aggregates and forwards).
3. Certificate provisioning (rotation, CSR); see [gNSI Certz](../mgmt/gnmi/gnsi.md).
4. Mutual TLS with client certificate **authentication enforced by the collector** beyond installing client PEMs for the TLS handshake (client certs are configured; collector policy is external).

## Abbreviations

| Term   | Meaning                                              |
|:-------|:-----------------------------------------------------|
| SONiC  | Software for Open Networking in the Cloud            |
| CONFIG_DB | Redis configuration database (DB 4)               |
| STATE_DB  | Redis operational state database (DB 6)           |
| Certz  | gNSI certificate rotation service                    |
| PEM    | Privacy-Enhanced Mail encoding for X.509 keys/certs  |
| omfwd  | rsyslog forwarding module (UDP/TCP/TLS)              |
| ossl   | rsyslog OpenSSL stream driver                        |

## 1. Introduction

### 1.1. Feature overview

Operators often centralize switch logs on a SIEM or syslog collector. Plain UDP/TCP syslog is easy to deploy but offers no confidentiality or integrity on the wire. This feature lets each `SYSLOG_SERVER` entry use `protocol` `tls` so the host rsyslog daemon opens a **TLS** session to the collector (default port **6514**), authenticates the server with **x509/name** against a configured permitted-peer list, and uses CA/client material from an **SSL profile** directory (installed by Certz or stored manually).

Design principles:

- **Fail closed for TLS**: If TLS is requested but profile PEMs are missing, `tls_permitted_peers` is unset, or rendering/restart fails, that server is **omitted** from generated config. The implementation does **not** fall back to cleartext TCP/UDP for that destination.
- **Reuse the SSL profile layout**: The same profile directory layout used elsewhere on the switch (`ca-bundle.pem`, `cert.pem`, `key.pem`) avoids a parallel PKI stack for syslog. The PEMs may come from Certz or be copied in manually; syslog only checks that the files exist under the profile directory.
- **Operator feedback**: STATE_DB fields report whether TLS forwarding is active and why not, surfaced in `show syslog`.

### 1.2. Requirements

#### 1.2.1. Functionality

1. Support `protocol` values `udp`, `tcp`, and `tls` on `SYSLOG_SERVER` (existing behaviors unchanged for `udp`/`tcp`).
2. For `tls` (or `transport_security` `true`):
   - Require `tls_profile_id` and `tls_permitted_peers`.
   - Default port **6514** when not specified.
   - Map to rsyslog `omfwd` with `Protocol="tcp"`, `StreamDriver="ossl"`, `StreamDriverMode="1"`, `StreamDriverAuthMode="x509/name"`, and profile paths under `/etc/sonic/ssl-certs/<tls_profile_id>/`.
3. Forbid using the `gnxi` profile id (reserved for the gNMI listener).
4. Preserve existing per-server options: `source`, `vrf`, `filter` / `filter_regex`, `severity`, and global format/severity from `SYSLOG_CONFIG|GLOBAL`.
5. Publish `applied_transport_security` and `failure_reason` in STATE_DB after each `rsyslog-config` run.

#### 1.2.2. Command interface

- `config syslog add <server> --protocol tls --tls-profile-id <id> --tls-permitted-peers <names>` (optional `--port`, `--source`, `--vrf`).
- `show syslog` extended columns: TLS profile, permitted peers, TLS applied, failure reason.
- Generic Config Updater: reject invalid TLS combinations; restart `rsyslog-config` when `SYSLOG_SERVER` changes.

#### 1.2.3. Error handling

| Condition | Config accepted? | Forwarding behavior | `failure_reason` |
|-----------|------------------|---------------------|------------------|
| `protocol` `tls` without profile or peers | No (CLI/YANG/GCU) | N/A | N/A |
| Profile id set but PEMs missing on disk | Yes | Server skipped in rsyslog.conf | `NO_CERTIFICATE` |
| `tls_permitted_peers` empty in DB | No (CLI/YANG) | Server skipped if only in partial config | `NO_PERMITTED_PEERS` |
| `rsyslog.conf` install/restart fails | Yes | Previous or no config | `RSYSLOG_APPLY_FAILED` |
| TLS fully applied | Yes | omfwd TLS action present | `NONE` (`applied_transport_security` `true`) |

Non-TLS servers: `TLS APPLIED` / `FAILURE REASON` show `N/A` in `show syslog`.

## 2. Design

### 2.1. Overview

End-to-end flow:

```mermaid
sequenceDiagram
    participant Op as Operator / GCU
    participant CDB as CONFIG_DB
    participant CLI as sonic-utilities
    participant RCfg as rsyslog-config
    participant CfgGen as sonic-cfggen
    participant RS as rsyslog (host)
    participant SDB as STATE_DB
    participant Coll as Remote collector

    Op->>CLI: config syslog add (tls options)
    CLI->>CDB: SYSLOG_SERVER|&lt;ip&gt;
    CLI->>RCfg: systemctl restart rsyslog-config
    RCfg->>RCfg: Scan /etc/sonic/ssl-certs/*/ PEMs
    RCfg->>CfgGen: rsyslog.conf.j2 + CONFIG_DB + ssl_profiles
    CfgGen->>RCfg: rendered rsyslog.conf
    RCfg->>RS: restart or SIGHUP
    RCfg->>SDB: applied_transport_security, failure_reason
    RS->>Coll: TLS syslog (omfwd ossl)
```

Logging path on the switch is unchanged at a high level: container rsyslog instances forward to the host; the **host** `rsyslog.conf` applies remote `omfwd` actions, including TLS destinations.

### 2.2. Trust material and SSL profiles

Profile directories are populated in one of two ways:

1. **Certz** (or host-services integrating Certz) installs them.
2. **Manually**: the operator creates `/etc/sonic/ssl-certs/<profile_id>/` and stores the three PEM files there. This is useful for labs and for deployments that do not use Certz.

Either way the layout is:

```text
/etc/sonic/ssl-certs/<profile_id>/
    ca-bundle.pem
    cert.pem
    key.pem
```

Syslog does not care how a profile was created. A manually stored profile is used exactly like a Certz-installed one: reference it with `tls_profile_id` / `--tls-profile-id`. The same rules apply: all three PEMs must be present, the profile id must match `[A-Za-z0-9._-]+`, and `gnxi` is not allowed.

For a manually stored profile, make the directory and files readable by the `syslog` user through group `ssl-certs`. For example:

```text
sudo mkdir -p /etc/sonic/ssl-certs/<profile_id>
sudo cp ca-bundle.pem cert.pem key.pem /etc/sonic/ssl-certs/<profile_id>/
sudo chown -R root:ssl-certs /etc/sonic/ssl-certs/<profile_id>
sudo chmod 750 /etc/sonic/ssl-certs/<profile_id>
sudo chmod 640 /etc/sonic/ssl-certs/<profile_id>/*.pem
```

PEMs are scanned each time `rsyslog-config.sh` runs, so after adding, replacing or removing files by hand, re-render with `sudo systemctl restart rsyslog-config` to apply the change. Manually stored profiles are not rotated by Certz; the operator is responsible for renewing them.

Image build creates `/etc/sonic/ssl-certs` owned by `root:ssl-certs` mode `0750`, and adds the `syslog` user to group `ssl-certs` so rsyslog can read keys.

`rsyslog-config.sh` builds a JSON map `ssl_profiles` of profile ids that have all three PEMs present. The Jinja template only emits a TLS `omfwd` block when:

- `protocol` is `tls` or `transport_security` is true, **and**
- `tls_profile_id` is set, **and**
- `tls_permitted_peers` is set, **and**
- `ssl_profiles[tls_profile_id]` is true.

Otherwise a comment is written and **no** action line is generated for that server.

**Permitted peers:** `tls_permitted_peers` is a comma-separated list of DNS names (optional leading `*.` on one label). It maps to rsyslog `StreamDriverPermittedPeers`. With rsyslog 8.2504 and earlier, wildcard entries match only the certificate **subject CN**, not SAN DNS names; operators should list exact SAN names when possible.

> **Note:** SONiC images based on Debian **trixie** only support rsyslog **8.2504**; no newer rsyslog is available from the distribution. The wildcard behaviour above therefore applies to all trixie-based images, and exact DNS names should be used for `tls_permitted_peers`.

### 2.3. Configuration model

#### 2.3.1. CONFIG_DB: `SYSLOG_SERVER|<server_address>`

New or extended fields:

| Field | Description |
|-------|-------------|
| `protocol` | `udp`, `tcp`, or `tls` |
| `transport_security` | When `true`, equivalent to `tls` (OpenConfig mapping) |
| `tls_profile_id` | Certz profile id (not `gnxi`) |
| `tls_permitted_peers` | Comma-separated permitted server certificate names |
| `port` | Default `514` for udp/tcp; default `6514` for tls |

Example:

```json
{
    "SYSLOG_SERVER": {
        "10.0.0.5": {
            "port": "6514",
            "protocol": "tls",
            "transport_security": "true",
            "tls_profile_id": "siem-east",
            "tls_permitted_peers": "syslog-east.example.com"
        }
    }
}
```

See also [Configuration.md](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/doc/Configuration.md) in sonic-yang-models for the canonical field descriptions.

#### 2.3.2. Generated rsyslog fragment (TLS)

For a ready TLS server, the template emits (conceptually):

```text
*.notice
action(type="omfwd" Target="<server>" Port="6514" Protocol="tcp" Template="<SONiC template>"
  StreamDriver="ossl" StreamDriverMode="1" StreamDriverAuthMode="x509/name"
  StreamDriverPermittedPeers="<peers>"
  StreamDriver.CAFile="/etc/sonic/ssl-certs/<profile>/ca-bundle.pem"
  StreamDriver.CertFile="/etc/sonic/ssl-certs/<profile>/cert.pem"
  StreamDriver.KeyFile="/etc/sonic/ssl-certs/<profile>/key.pem"
  ... optional Address= / Device= for source and VRF ...)
```

Severity and filter lines follow the same rules as UDP/TCP in [syslog-design.md](syslog-design.md).

### 2.4. rsyslog rendering and apply

**Components:** `rsyslog-config.service` runs `files/image_config/rsyslog/rsyslog-config.sh`, which:

1. Resolves `udp_server_ip` / `docker0_ip` (unchanged; multi-ASIC / bridged features).
2. Scans SSL profile directories into `ssl_profiles` JSON (via `jq` for safe encoding).
3. Invokes `sonic-cfggen -d -t /usr/share/sonic/templates/rsyslog.conf.j2` with extra arguments including `ssl_profiles`.
4. Writes `/etc/rsyslog.conf` only when content changes, then `systemctl restart rsyslog`; if unchanged, sends **SIGHUP** (or restarts on multi-ASIC for docker0 bind). This avoids expensive systemd sandbox teardown on no-op applies.
5. Calls `publish_syslog_tls_apply_state` to refresh STATE_DB.

Template input sanitization strips newlines/quotes from values embedded in rsyslog directives; JSON arguments to cfggen are built with `jq` to avoid injection from CONFIG_DB content.

**Package dependency:** Host image installs `rsyslog-openssl` alongside `rsyslog` and `rsyslog-relp`.

### 2.5. Operational state

**STATE_DB** key: `SYSLOG_SERVER|<server_address>` (same key shape as CONFIG_DB).

| Field | Values |
|-------|--------|
| `applied_transport_security` | `true` / `false` for TLS-configured servers |
| `failure_reason` | `NONE`, `NO_PROFILE`, `NO_PERMITTED_PEERS`, `NO_CERTIFICATE`, `RSYSLOG_APPLY_FAILED` |

Stale STATE_DB keys for servers removed from CONFIG_DB are deleted on each publish pass.

`show syslog` reads CONFIG_DB for the table body and STATE_DB for TLS apply columns.

### 2.6. CLI and Generic Config Updater

**config syslog add**

- `--protocol tls` requires `--tls-profile-id` and `--tls-permitted-peers`.
- TLS profile id must match `[A-Za-z0-9._-]+` and cannot be `gnxi`.
- Peers validated per name; whitespace around commas is normalized.
- On success, restarts `rsyslog-config` (and resets failed units for `rsyslog-config` / `rsyslog`).

**show syslog**

- Additional columns: TLS profile id, permitted peers, TLS applied, failure reason.

**Generic Config Updater** (`services_validator.rsyslog_validator`):

- Enforces TLS field presence and consistency on `SYSLOG_SERVER` updates.
- Restarts `rsyslog-config` when the syslog server table changes.

### 2.7. YANG model

Module: `sonic-syslog.yang` (`sonic-yang-models`).

- `rsyslog-protocol` enum extended with `tls`.
- Leaves: `transport_security`, `tls_profile_id`, `tls_permitted_peers`.
- `must` constraints: TLS requires profile and peers; `gnxi` profile forbidden; mgmt VRF rules unchanged.

YANG revision `2026-08-21` documents the TLS extension.

### 2.8. Host image changes

| Area | Change |
|------|--------|
| `build_debian.sh` | Add `rsyslog-openssl`; create `ssl-certs` group and `/etc/sonic/ssl-certs` (rsyslog is limited to 8.2504 on Debian trixie) |
| `rsyslog.conf.j2` | TLS `omfwd` blocks, `ssl_profiles` gating |
| `rsyslog-config.sh` | Profile scan, jq-encoded cfggen args, STATE_DB publish |
| `sonic-config-engine` tests | Jinja tests for TLS render, skip missing profile/peers |

### 2.9. Security properties

- **Confidentiality / integrity on the wire:** Provided by TLS between host and collector (TLS version/ciphers per system OpenSSL and rsyslog build).
- **Server authentication:** `x509/name` with explicit permitted peers; no anonymous TLS to syslog collectors.
- **No cleartext fallback** for destinations configured for TLS.
- **Client identity:** Client cert/key from the profile are offered to the collector; authorization is collector-side.
- **Key storage:** Keys live under `/etc/sonic/ssl-certs` with group-readable semantics for the `syslog` user; profile `gnxi` is blocked from syslog use to avoid reusing the gNMI listener identity.

### 2.10. Multi-ASIC and containers

- Remote TLS forwarding is configured only on the **host** rsyslog instance; per-namespace container rsyslog behavior is unchanged.
- Multi-ASIC: `rsyslog-config` may restart rsyslog when config is unchanged but docker0 binding requires it (existing behavior); TLS state publish still runs.

## 3. Test plan

### 3.1. Unit tests

| Component | Coverage |
|-----------|----------|
| `sonic-config-engine` | `test_rsyslog_conf_tls_two_profiles_and_skip_missing`, `test_rsyslog_conf_tls_without_profiles_skips_all_tls` |
| `sonic-yang-models` | `tests/yang_model_tests/tests/syslog.json` TLS valid/invalid cases |
| `sonic-utilities` | `tests/syslog_test.py` TLS CLI validation, show output with STATE_DB |
| `sonic-utilities` | `generic_config_updater/service_validator_test.py` GCU TLS rules |

### 3.2. Manual / lab validation

1. Provision a collector listening on TCP 6514 with a server cert whose SAN/CN matches `tls_permitted_peers`.
2. Install a non-`gnxi` profile, either with Certz or by manually copying `ca-bundle.pem`, `cert.pem` and `key.pem` into `/etc/sonic/ssl-certs/<id>/` (owner `root:ssl-certs`, readable by the group); verify the PEMs are present.
3. `config syslog add <collector-ip> --protocol tls --tls-profile-id <id> --tls-permitted-peers <name>`.
4. `show syslog`: `TLS APPLIED` `true`, `FAILURE REASON` `NONE`.
5. Confirm messages arrive at the collector; packet capture shows TLS (not cleartext syslog).
6. Remove PEMs or use wrong peer name: `TLS APPLIED` `false`, appropriate `failure_reason`; confirm no cleartext fallback to that IP.
7. Regression: existing UDP/TCP servers still forward; `config syslog del` removes destination and STATE_DB key.

### 3.3. Out of scope for automated VS/PTF

Data-plane PTF is not required: the feature is host management-plane forwarding. VS images can run config-engine and CLI unit tests; full TLS handshake validation remains a lab test with a real or containerized collector.

## References

- [SONiC Syslog Source IP design](syslog-design.md)
- [SONiC Syslog rate limit design](syslog-rate-limit-design.md)
- [gNSI Certz](../mgmt/gnmi/gnsi.md)
- Implementation (syslog-tls branch): `sonic-buildimage` (rsyslog template, YANG, image), `sonic-utilities` (CLI/show/GCU)
