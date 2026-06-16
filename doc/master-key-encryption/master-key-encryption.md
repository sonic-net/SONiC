# Master Key Encryption Infrastructure for SONiC

## Table of Contents

- [Revision History](#revision-history)
- [Scope](#scope)
- [Definitions and Abbreviations](#definitions-and-abbreviations)
- [Overview](#overview)
- [Motivation](#motivation)
- [Requirements](#requirements)
- [Architecture](#architecture)
- [Master Key Manager Infrastructure](#master-key-manager-infrastructure)
  - [Master Key File](#master-key-file)
  - [Master Key Generation and Provisioning](#master-key-generation-and-provisioning)
  - [Key Rotation](#key-rotation)
  - [Encryption Library](#encryption-library)
  - [ConfigDB Interception Layer](#configdb-interception-layer)
  - [Encryption Registry: Static Configuration](#encryption-registry-static-configuration)
- [CLI: master-key-manager](#cli-master-key-manager)
- [Application: BGP MD5 Password Encryption](#application-bgp-md5-password-encryption)
  - [Registration](#registration)
  - [Operational Workflow](#operational-workflow)
  - [FRR Integration](#frr-integration)
- [Comparison With Prior Proposal](#comparison-with-prior-proposal)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions and Limitations](#restrictions-and-limitations)
- [Test Plan](#test-plan)
- [Future Work](#future-work)

---

## Revision History

| Rev | Date       | Author    | Change Description |
|-----|------------|-----------|--------------------|
| 0.1 | 2026-06-16 | Fred Xia  | Initial draft      |

---

## Scope

This document describes the design of a **Master Key Encryption Infrastructure** for SONiC that enables at-rest encryption of sensitive configuration fields in ConfigDB (Redis). It defines the general infrastructure — master key management, an AES-GCM encryption library, a code-defined encryption registry, and a transparent ConfigDB interception layer — and then describes how BGP MD5 peer authentication passwords are the first application built on top of this infrastructure.

---

## Definitions and Abbreviations

| Term               | Meaning                                                              |
|--------------------|----------------------------------------------------------------------|
| AES-GCM  | Advanced Encryption Standard in Galois/Counter Mode       |
| AAD      | Additional Authenticated Data (used in AES-GCM)          |
| Type-6   | Cisco-compatible password encryption type: reversible AES |
| ConfigDB | SONiC configuration database (Redis)                      |

---

## Overview

SONiC stores all configuration — including protocol passwords such as BGP MD5 authentication passwords, TACACS shared secrets, and RADIUS keys — as cleartext in Redis (ConfigDB) and in the `config_db.json` startup file. Any local account can dump these values with standard Redis tools. This design proposes a general-purpose Master Key Encryption Infrastructure to protect such fields at rest, with BGP MD5 password encryption as its first application.

The infrastructure provides:

1. **A code-defined encryption registry** (`master_key_manager/master_key_encryption_config.py`) that statically declares which tables and fields are subject to automatic encryption. Adding a new encrypted field requires a code change (not a YANG model edit or CLI registration), which is deliberate: any new use of encryption must also involve feature-specific handling code (e.g., decryption in `frrcfgd` before rendering to FRR).
2. **A master key management library and CLI tool** (`master-key-manager`) to provision master keys, activate/deactivate encryption, and inspect status.
3. **An AES-256-GCM encryption library** (`master_key_manager/master_key_encryption.py`) offering authenticated symmetric encryption (Type-6, reversible).
4. **A transparent ConfigDB interception layer** so that standard SONiC tools (`config`, `sonic-cfggen`) automatically encrypt sensitive fields on write without requiring application-level changes.
5. **Extensibility** so that additional features (TACACS, RADIUS, LDAP) can be supported by adding an entry to the registry and the corresponding decrypt/render code in the feature daemon.

---

## Motivation

### At-Rest Security

Community SONiC writes all configuration values to Redis plaintext. An operator or compromised process with read access to the local Redis socket can trivially extract BGP MD5 passwords, TACACS shared secrets, RADIUS keys, and similar credentials. FIPS-compliant deployments and customer security policies require these values to be stored encrypted.

### Industry Precedent

Proprietary vendors address this with a "Type-6" (or equivalent) reversible AES encryption tied to a device-local master key:

- **Cisco IOS**: `password encryption aes` (Type-6). Once enabled, all service passwords and BGP neighbor passwords are stored AES-encrypted.
- **Arista EOS**: `password encryption reversible aes-256-gcm`. Uses a 32-byte master key and AES-256-GCM for at-rest encryption.
- **Dell Enterprise SONiC**: Provides similar master key encryption for BGP and AAA passwords.

Our implementation follows the Type-6 (reversible AES) model, using AES-256-GCM for both confidentiality and integrity.

---

## Requirements

### Functional Requirements

1. **FR-1**: ConfigDB fields designated as sensitive shall be stored encrypted using AES-256-GCM with a device-local master key.
2. **FR-2**: Encryption and decryption shall be transparent to standard SONiC configuration tools (`config load`, `config reload`, `config apply`).
3. **FR-3**: The system shall support master keys supplied by a central controller, enabling enterprise key management integration.
4. **FR-4**: A CLI tool (`master-key-manager`) shall allow the operator to set master keys and activate/deactivate encryption.
5. **FR-5**: When encryption is activated, all plaintext secret fields in registered tables shall be re-encrypted automatically; when deactivated, they shall be decrypted.
6. **FR-6**: Encryption shall apply only to ConfigDB. FRR running configuration continues to use cleartext passwords.
7. **FR-7**: The master key file shall be accessible only to root (mode 0600), protected by filesystem permissions.
8. **FR-8**: The infrastructure shall retain up to 8 historical master keys to enable decryption of values encrypted under a previous key.
9. **FR-9**: BGP MD5 passwords shall be the first feature protected by this infrastructure.
10. **FR-10**: The catalog of tables and fields subject to encryption shall be defined in code (`master_key_encryption_config.py`). Adding encryption to a new table requires a code change, not a YANG model edit or CLI command, because any new encrypted field also requires feature-specific decrypt/render code in the consuming daemon.
11. **FR-11**: A single table may declare multiple encrypted fields (e.g., both `auth_password` and `md5_key`).

### Non-Functional Requirements

1. The master key file format shall be a versioned, human-readable JSON structure for auditability and disaster recovery.
2. Encryption/decryption shall use the Python `cryptography` library — no shell subprocesses.
3. One `MasterKeyManager` instance per master key file, shared across all tables that point to the same file.

---

## Architecture

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    Master Key Encryption Infrastructure                     │
 │                                                                             │
 │  ┌───────────────────────────────────┐   ┌───────────────────────────────┐  │
 │  │    master-key-manager CLI         │   │   Encryption Library          │  │
 │  │                                   │   │ (master_key_manager.py)       │  │
 │  │  set  --master-key-file  <key>    │   │  AES-256-GCM (Type-6)         │  │
 │  │  encrypt --table / decrypt --table│   │  Nonce + CT + GCM tag + AAD   │  │
 │  │  activate / deactivate            │   │  base64-encoded output        │  │
 │  │  status / list                    │   └────────────────┬──────────────┘  │
 │  └──────────────┬────────────────────┘                    │                 │
 │                 │ reads                  ┌────────────────▼──────────────┐  │
 │                 ▼                        │   MasterKeyManager            │  │
 │  ┌───────────────────────────────────┐   │   /etc/<feature>_master_key   │  │
 │  │  master_key_encryption_config.py  │   │   mode 0600, JSON             │  │
 │  │  (code-defined, static registry)  │   │   up to 8 historical keys     │  │
 │  │  • name  (e.g. "BGP")             │   │   enabled flag (on/off state) │  │
 │  │  • master_key_file                │   │   one instance per file       │  │
 │  │  • fields: {TABLE: [field, ...]}  │   └───────────────────────────────┘  │
 │  └──────────────┬────────────────────┘                                      │
 │                 │ read at startup                                           │
 │                 ▼                                                           │
 │  ┌──────────────────────────────────────────────────────────────────────┐   │
 │  │          ConfigDB Interception Layer (Python)                        │   │
 │  │   ConfigDBConnector.set_entry() → encrypt_data() → _set_entry()      │   │
 │  │   ConfigDBConnector.mod_entry() → encrypt_data() → _mod_entry()      │   │
 │  │   ConfigDBConnector.mod_config() → encrypt_config() → _mod_config()  │   │
 │  │   Loaded lazily from master_key_manager.config_db_encryption         │   │
 │  └──────────────────────────────────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
 ┌────────────▼──────────────────┐      ┌─────────────────▼────────────────┐
 │  Application:                 │      │  Future applications:            │
 │  BGP MD5 Password             │      │  TACACS shared secret            │
 │  BGP_NEIGHBOR.auth_password   │      │  RADIUS key                      │
 │  BGP_PEER_GROUP.auth_password │      │  LDAP bind password              │
 └───────────────────────────────┘      └──────────────────────────────────┘
```

---

## Master Key Manager Infrastructure

### Master Key File

The master key file is a JSON document (e.g., `/etc/sonic/bgp_master_key`) with mode 0600 (readable only by root). It holds a named key set and retains up to **8 historical master keys** in descending timestamp order, so that values encrypted under older keys remain decryptable after rotation.

Example:

```json
{
  "key_file": "bgp_master_key",
  "master_keys": [
    {
      "master_key": "my-secret-32-byte-key-padded-to-32",
      "algorithm": "aes-gcm",
      "timestamp": "2026-05-20T10:00:00+00:00"
    }
  ],
  "enabled": false
}
```

Key design points:

- **`key_file`**: The basename of the key file path (e.g., `bgp_master_key`). Used as the AES-GCM AAD to bind each ciphertext blob to its key file.
- **`master_keys`**: A flat list of `MasterKey` objects, newest first. There is no per-feature or per-table sub-keying; one file covers one logical key set regardless of how many tables share it.
- **`enabled`**: Activation state for the feature. Set to `true` by `master-key-manager activate` and `false` by `deactivate`. Stored in the key file rather than in ConfigDB, so no ConfigDB table registry is required.

The file is written atomically: a temporary file is written, its contents are verified, and then it is renamed over the production path to prevent partial writes.

### Master Key Generation and Provisioning

Two modes are supported:

#### 1. Key Distribution from Central Controller (Primary Model)

```
# master-key-manager set --master-key-file /etc/sonic/bgp_master_key <KEY>
Saved master key to /etc/sonic/bgp_master_key
```

The `set` command accepts any string, pads or truncates it to 32 bytes for AES-256, and prepends a new `MasterKey` entry to the list. The previous key remains in history for decryption of older values.

This is the primary model for enterprise deployments where a controller pushes a deterministic key to a fleet of devices.

#### 2. Local Random Key (Ad-hoc)

For standalone devices without a central key management system, the operator can supply any high-entropy string:

```
# master-key-manager set --master-key-file /etc/sonic/bgp_master_key $(openssl rand -hex 32)
Saved master key to /etc/sonic/bgp_master_key
```

### Key Rotation

When a new master key is set with `set`, the old key is retained in the history list. To re-encrypt all ConfigDB values with the new key:

```
# master-key-manager deactivate
# master-key-manager activate
```

Deactivation decrypts all fields back to plaintext, then activation re-encrypts them with the current (newest) master key. Because FRR reads decrypted passwords via the interception layer, no BGP flap occurs during rotation.

### Encryption Library

File: `sonic-utilities/utilities_common/master_key_encryption.py`

The library implements **AES-256-GCM** encryption, referred to as **Type-6** in this document, consistent with Cisco's designation for reversible AES password storage.

#### Data Structures

```python
@dataclass
class MasterKey:
    master_key: str         # plaintext key string (padded to 32 bytes for AES-256)
    algorithm: AlgorithmName   # currently only "aes-gcm"
    timestamp: datetime     # creation time (UTC)

@dataclass
class MasterKeyConfig:
    key_file: str           # basename of the key file path; used as AES-GCM AAD
    master_keys: list[MasterKey]   # newest first, max 8 entries
    enabled: bool           # whether encryption is currently active for this key set
```

#### Encrypted Password Format

An encrypted value is a base64-encoded blob with the following internal layout:

```
      [ 12-byte nonce ][ ciphertext (N bytes) ][ 16-byte GCM tag ][ 16-byte AAD ]
        └────────────────────────────────────────────────────────────────────┘
                       base64-encoded into a printable string
```

- **Nonce** (12 bytes): Randomly generated per encryption operation.
- **Ciphertext**: The encrypted plaintext, same length as the original.
- **GCM Tag** (16 bytes): AEAD authentication tag; detects tampering and key mismatch.
- **AAD** (16 bytes, zero-padded): The table name (e.g., `BGP_NEIGHBOR`) used as Additional Authenticated Data. This binds the encrypted blob to its table, preventing cross-table replay.

#### Detecting Encrypted Values

Whether a stored value is already encrypted is determined by runtime probing — no separate flag field is needed:

1. Check if the value is valid base64.
2. Attempt AES-GCM decryption with the current master key.
   - If decryption succeeds (GCM tag validates): the value is **encrypted**.
   - If decryption fails: treat as **cleartext**.

The GCM authentication tag provides cryptographically strong assurance: the probability of a cleartext string accidentally passing both checks is negligible.

#### API Reference

```python
# Singleton per filename — one instance shared across all callers for the same file
mgr = MasterKeyManager("/etc/sonic/bgp_master_key")

# Store a new master key (prepends to history)
mgr.update_master_key("my-secret-key")          # returns bool

# Encrypt (AAD is the key_file basename from MasterKeyConfig, e.g. "bgp_master_key")
encrypted = mgr.encrypt_string("plaintext")

# Decrypt (AAD is read from the blob — no need to pass it)
plaintext = mgr.decrypt_string(encrypted)

# Check if already encrypted with the current master key
already_enc = mgr.is_encrypted(value)           # returns bool

# Historical key access (for cross-key decryption)
plaintext = mgr.decrypt_string(encrypted, key_idx=1)

# Activation state — stored in the key file, not in ConfigDB
mgr.is_enabled()                                # returns bool
mgr.set_enabled(True)                           # returns bool
```

#### Singleton Pattern

`MasterKeyManager` uses a singleton pattern keyed by filename. Multiple tables pointing to the same `master_key_file` share one `MasterKeyManager` instance, avoiding redundant file reads and lock contention.

### ConfigDB Interception Layer

File: `sonic-utilities/master_key_manager/config_db_encryption.py`

`ConfigDBEncryptor` is loaded lazily by `ConfigDBConnector` on first write. It reads `master_key_registries()` from `master_key_encryption_config.py` at construction time to discover which tables and fields require encryption. Encryption on/off is controlled by the `enabled` flag in each master key file (`MasterKeyConfig.enabled`), not by a ConfigDB table.

#### Encryptor API

```python
class ConfigDBEncryptor:

    def is_loaded(self) -> bool: ...

    def entry_need_encryption(self, table, key, data) -> bool:
        """True when encryption is enabled (key file enabled=true) for table
        and any registered field in data is plaintext."""

    def encrypt_data(self, table, key, data) -> dict:
        """Return a new dict with all registered secret fields in data encrypted.
        Does not write to the database — caller is responsible for the write."""

    def encrypt_config(self, data) -> dict:
        """Return data (or a deep copy if anything was changed) with all registered
        plaintext secret fields encrypted.  Returns original dict unchanged if no
        encryption is needed (lazy copy — avoids deep-copying large route tables)."""
```

#### ConfigDBConnector Interception (both py-swsssdk and swss-common)

```python
def set_entry(self, table, key, data):
    encryptor = ConfigDBConnector.load_encryptor(self)
    if encryptor.is_loaded() and encryptor.entry_need_encryption(table, key, data):
        data = encryptor.encrypt_data(table, key, data)
    self._set_entry(table, key, data)

def mod_entry(self, table, key, data):
    encryptor = ConfigDBConnector.load_encryptor(self)
    if encryptor.is_loaded() and encryptor.entry_need_encryption(table, key, data):
        data = encryptor.encrypt_data(table, key, data)
    self._mod_entry(table, key, data)

def mod_config(self, data):
    encryptor = ConfigDBConnector.load_encryptor(self)
    if encryptor.is_loaded():
        data = encryptor.encrypt_config(data)   # lazy copy — no-op if nothing to encrypt
    self._mod_config(data)
```

The encryptor is loaded lazily and cached as a class variable (`ConfigDBConnector.db_encryptor`). If `master_key_manager.config_db_encryption` is not installed, a no-op placeholder is used.

#### Lazy Deep Copy in `encrypt_config`

When `mod_config()` is called with a large data dict (e.g., a full route table with thousands of entries), `encrypt_config` avoids an unconditional `deepcopy`. Instead, it makes a copy only on the first field that actually needs encryption. If no table has encryption activated, the original dict is returned unchanged — zero copy overhead.

### Encryption Registry: Static Configuration

File: `sonic-utilities/master_key_manager/master_key_encryption_config.py`

The catalog of CONFIG DB tables and fields subject to encryption is defined as a static Python data structure — not a YANG model and not a ConfigDB table. The rationale is that adding encryption to a new use case always requires at least two code changes:

1. An entry in `_MasterKeyEncryptionRegistries` (to register the table and field).
2. Feature-specific decrypt/render code in the consuming daemon (e.g., `frrcfgd` for BGP auth passwords).

Because a YANG-model-only change would leave the framework unaware of how to decrypt and consume the value, a purely config-driven approach was considered insufficient. By requiring a code change for registration, reviewers are reminded to add the corresponding decrypt handling.

#### Registry Format

```python
BGP_MASTER_KEY_FILE = "/etc/sonic/bgp_master_key"

_BGP_REGISTRY = {
    "name": "BGP",
    "master_key_file": BGP_MASTER_KEY_FILE,
    "fields": {
        "BGP_NEIGHBOR":   ["auth_password"],
        "BGP_PEER_GROUP": ["auth_password"],
    },
}

_MasterKeyEncryptionRegistries = [ _BGP_REGISTRY ]
```

Each registry entry has:
- **`name`**: Human-readable label for the group (e.g., `"BGP"`).
- **`master_key_file`**: Absolute path to the master key file shared by all tables in this group.
- **`fields`**: A `dict` mapping CONFIG DB table names to a list of field names whose values are subject to encryption.

Key design points:
- **Multiple fields per table**: A table can list more than one encrypted field (e.g., `["auth_password", "md5_key"]`).
- **Shared key file**: `BGP_NEIGHBOR` and `BGP_PEER_GROUP` share `/etc/sonic/bgp_master_key`.
- **No YANG model changes needed**: Adding a new encrypted field does not touch `sonic-device_metadata.yang`.
- **Testability**: `set_master_key_registries()` allows tests to inject a custom registry at runtime without touching the filesystem.

#### Adding a New Encrypted Field

Anyone extending encryption coverage must:

1. Add an entry (or extend an existing entry's `fields` dict) in `master_key_encryption_config.py`.
2. Add the corresponding decrypt and render logic in the feature daemon. For example, a new AAA table would need the daemon that reads that table to call `MasterKeyManager.decrypt_string()` before using the value.

---

## CLI: master-key-manager

The CLI reads the encryption registry from `master_key_encryption_config.py` at startup. There is no `register` command — tables and fields are defined in code, not configured at runtime.

The CLI can operate against:
- A live Redis instance (default) via `sonic-cfggen`.
- A local JSON file via `--config-file` (used in testing and offline provisioning).

```
Usage: master-key-manager [--config-file <JSON>] [--registry-config <JSON>]
                          [-s <socket>] [-v] [--force] COMMAND

Commands:
  set --master-key-file <PATH> <KEY>
      Provision or rotate the master key stored in the given key file.
      The key is padded/truncated to 32 bytes for AES-256 and prepended
      to the key history (up to 8 entries).
      Example:
        master-key-manager set --master-key-file /etc/sonic/bgp_master_key mySecretKey

  encrypt --table <TABLE> [-o <OUTPUT>]
      Read all entries of <TABLE> from ConfigDB (or --config-file),
      encrypt every registered secret field, and print the result as JSON
      (or write to -o).  Table must appear in the encryption registry.

  decrypt --table <TABLE> [-o <OUTPUT>]
      Read all entries of <TABLE>, decrypt every registered secret field,
      and print the result as JSON (or write to -o).

  activate
      Activate encryption for all registered tables:
        1. Verify every registered table has a master key provisioned.
        2. Bulk-encrypt all plaintext secret fields in each registered table
           by reading from ConfigDB, encrypting, and writing back.
        3. Set enabled=true in each affected master key file.

  deactivate
      Deactivate encryption: decrypt all registered tables back to plaintext,
      then set enabled=false in each affected master key file.

  status
      Print JSON status per registered table:
        {
          "BGP_NEIGHBOR": {
            "master_key_file": "/etc/sonic/bgp_master_key",
            "master_key_configured": true,
            "encryption_enabled": true
          },
          "BGP_PEER_GROUP": {
            "master_key_file": "/etc/sonic/bgp_master_key",
            "master_key_configured": true,
            "encryption_enabled": true
          }
        }

  list
      Print master key metadata (timestamps and algorithm, not key values)
      for all registered tables.

Options:
  --config-file  <JSON FILE>   Read/write CONFIG DB tables from a JSON file
                               instead of live Redis (useful for testing)
  --registry-config <JSON>     Override the built-in encryption registry with
                               a custom JSON list (for testing only)
  -s, --socket-path <PATH>     Unix domain socket path for Redis server
  -v, --verbose                Verbose logging
  --force                      Force remove master key file lock
```

---

## Application: BGP MD5 Password Encryption

BGP MD5 authentication (RFC 2385) requires a shared plaintext secret between BGP peers. Currently SONiC stores this in `BGP_NEIGHBOR.auth_password` and `BGP_PEER_GROUP.auth_password` as cleartext. This section describes how the master key infrastructure protects those passwords.

### Registration

BGP password encryption is registered statically in `master_key_manager/master_key_encryption_config.py` — no CLI command is needed. The relevant entries are:

```python
BGP_MASTER_KEY_FILE = "/etc/sonic/bgp_master_key"

_BGP_REGISTRY = {
    "name": "BGP",
    "master_key_file": BGP_MASTER_KEY_FILE,
    "fields": {
        "BGP_NEIGHBOR":   ["auth_password"],
        "BGP_PEER_GROUP": ["auth_password"],
    },
}

_MasterKeyEncryptionRegistries = [ _BGP_REGISTRY ]
```

Both tables share the same key file. `master-key-manager activate/deactivate` iterates over the registry to bulk-encrypt or decrypt all entries.

The decrypt-and-render step for FRR is handled explicitly in `frrcfgd`. The function `_decrypt_bgp_auth_password()` is called from `bgp_neighbor_handler` before the data dict is passed into the FRR command pipeline:

```python
def _decrypt_bgp_auth_password(data):
    from master_key_manager import MasterKeyManager, BGP_MASTER_KEY_FILE
    key_mgr = MasterKeyManager(BGP_MASTER_KEY_FILE)
    val = data.get("auth_password")
    if val and key_mgr.is_encrypted(val):
        decrypted = key_mgr.decrypt_string(val)
        if decrypted:
            data["auth_password"] = decrypted

def bgp_neighbor_handler(self, table, key, data):
    if data is not None and "auth_password" in data:
        _decrypt_bgp_auth_password(data)
    self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

This is why registration must be a code change: any new encrypted field requires the consuming daemon to have corresponding decrypt logic. A YANG-model-only change would leave the daemon unable to render the value.

### Operational Workflow

#### Initial State (No Encryption)

ConfigDB stores passwords in cleartext. `DEVICE_METADATA_FEATURE_ENCRYPTION` has no entry for `BGP_NEIGHBOR` (defaults to `encryption_activated: false`).

```json
"BGP_NEIGHBOR": {
    "10.0.0.1": { "auth_password": "abcde" }
}
```

#### Step 1: Provision the Master Key

```
# master-key-manager set --master-key-file /etc/sonic/bgp_master_key mySecretKey
Saved master key to /etc/sonic/bgp_master_key
```

#### Step 2: Activate Encryption

```
# master-key-manager activate
```

The `activate` command:
1. Verifies a master key exists in `/etc/sonic/bgp_master_key`.
2. Reads all `BGP_NEIGHBOR` and `BGP_PEER_GROUP` entries from ConfigDB, encrypts each `auth_password`, and writes back.
3. Sets `enabled=true` in `/etc/sonic/bgp_master_key` (the `MasterKeyConfig.enabled` field).

After activation the ConfigDB data looks like:

```json
"BGP_NEIGHBOR": {
    "10.0.0.1": {
        "auth_password": "MTIzNAAAAAAAAAAA8RfAsN/Kw8AGBaVz5hPC7Wd8..."
    }
}
```

#### Step 3: New BGP Neighbor Configured

When the operator runs:

```
# config bgp neighbor add 10.0.0.33 remote-as 65001 password mysecret
```

The `config` command uses `ConfigDBConnector.mod_entry()`, which is intercepted. Because `encryption_activated=true` for `BGP_NEIGHBOR`, the interceptor encrypts `mysecret` before writing to Redis.

Similarly, `config load`, `config reload`, and `config apply` all go through `mod_config()`, which calls `encrypt_config()`. The lazy-copy optimization means there is no deep-copy overhead when loading large config files that contain no registered secret tables.

#### Step 4: Encryption Status Check

```
# master-key-manager status
{
  "BGP_NEIGHBOR": {
    "master_key_file": "/etc/sonic/bgp_master_key",
    "master_key_configured": true,
    "encryption_enabled": true
  },
  "BGP_PEER_GROUP": {
    "master_key_file": "/etc/sonic/bgp_master_key",
    "master_key_configured": true,
    "encryption_enabled": true
  }
}
```

#### Step 5: Key Rotation

```
# master-key-manager set --master-key-file /etc/sonic/bgp_master_key newKey2026
Saved master key to /etc/sonic/bgp_master_key

# master-key-manager deactivate
# master-key-manager activate
```

Deactivation decrypts all `auth_password` fields to plaintext; activation re-encrypts them with the new key. BGP sessions are unaffected during rotation.

### FRR Integration

`frrcfgd` reads `BGP_NEIGHBOR.auth_password` from ConfigDB and may receive an encrypted blob when encryption is active. The function `_decrypt_bgp_auth_password()` (added to `frrcfgd.py`) decrypts the value in-place before the data dict is passed to the FRR command pipeline:

```python
def bgp_neighbor_handler(self, table, key, data):
    if data is not None and "auth_password" in data:
        _decrypt_bgp_auth_password(data)   # no-op if not encrypted or key file absent
    self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

The ConfigDB interception layer (`ConfigDBEncryptor`) only encrypts on **write**; it does not intercept reads. Daemons that read encrypted fields must therefore decrypt explicitly, as `frrcfgd` does above.

The FRR running configuration will always show the cleartext password in `vtysh`:

```
router bgp 65100
  neighbor 10.0.0.1 password abcde
```

This is intentional: the password is in cleartext only within the FRR container memory, protected by container isolation. It is never written back to ConfigDB in cleartext by FRR.

---

## Comparison With Prior Proposal

A separate proposal (`sonic-py-common/sonic_py_common/security_cipher.py`) was submitted to encrypt TACACS shared secrets using a different approach. This section compares the two designs.

### Design Comparison

**Encryption algorithm**
- *Prior*: AES-128-CBC via `openssl` subprocess.
- *This HLD*: AES-256-GCM using the Python `cryptography` library — stronger cipher, no subprocess.

**Authentication / integrity**
- *Prior*: None. A corrupted or tampered ciphertext decrypts silently to garbage.
- *This HLD*: AES-GCM authentication tag (AEAD) — any tampering or key mismatch is detected and rejected.

**Encryption flag**
- *Prior*: A separate `key_encrypt: "true"` field must be present in the ConfigDB entry to signal that the value is encrypted.
- *This HLD*: Inferred at runtime by attempting decryption; no extra flag field needed.

**Master key source**
- *Prior*: The original HLD used the device MAC address as the AES encryption password — a non-secret, publicly visible value. After review feedback this was revised to an admin-provided string, but still with no fleet distribution model.
- *This HLD*: Operator-provisioned via `master-key-manager set`; designed to accept a key pushed from a central controller.

**Key history and rotation**
- *Prior*: Single key per feature. `set_feature_password()` silently refuses to overwrite an existing key; `rotate_feature_passwd()` is required and re-encrypts all entries in one shot with no key history.
- *This HLD*: Up to 8 historical keys retained. `master-key-manager set` always accepts and prepends the new key so old ciphertexts remain decryptable during a rolling rotation.

**Key distribution from a central controller**
- *Prior*: No clean path. A controller cannot simply push a new key; it must first call `rotate_feature_passwd()`, which requires decrypting all existing entries with the old key.
- *This HLD*: `master-key-manager set` unconditionally stores the new key. A controller can push a key to a fresh device or rotate it at any time with a single command.

**Config portability**
- *Prior*: Encrypted blobs are device-specific because the key is stored only locally. A pre-baked encrypted `config_db.json` cannot be pushed fleet-wide; each device must have its passkeys re-set individually after copying the config.
- *This HLD*: If all devices share the same controller-distributed master key, encrypted config snippets are fully portable across the fleet.

**Key file write safety**
- *Prior*: `_save_registry()` does a plain `open(..., 'w')` write with no file lock and no atomic rename. Concurrent writers can corrupt `cipher_pass.json`.
- *This HLD*: Exclusive `fcntl.flock` held for the duration of the write, data written to a temp file, content verified, then atomically renamed over the target path.

**Key file blast radius**
- *Prior*: A single `/etc/cipher_pass.json` holds the master keys for all features (TACACS, RADIUS, LDAP…). One corrupt file is a systemic failure.
- *This HLD*: One key file per feature group. A corrupt BGP key file does not affect AAA features.

**Activation and deactivation scope**
- *Prior*: `rotate_feature_passwd()` processes only the specific `TABLE|entry` pairs explicitly registered, one at a time, with the field name `"passkey"` hard-coded.
- *This HLD*: `activate`/`deactivate` scan entire CONFIG DB tables generically, handling multiple tables and multiple fields per table as declared in the registry.

**Hard-coded field names**
- *Prior*: Field names `"passkey"` and `"key_encrypt"`, and the `"TABLE|entry"` string split, are scattered as literals throughout the code.
- *This HLD*: Field names are declared once in `master_key_encryption_config.py`; no field-specific code exists in the framework.

**ConfigDB interception**
- *Prior*: Not implemented. Each caller must invoke encryption/decryption explicitly.
- *This HLD*: Transparent via `ConfigDBConnector` hooks — standard tools (`config`, `sonic-cfggen`) encrypt on write automatically.

**Registration**
- *Prior*: Runtime API calls (`register` / `deregister`) that write to `cipher_pass.json`.
- *This HLD*: Code-level entry in `master_key_encryption_config.py`; no runtime registration step.


---

## Warmboot and Fastboot Design Impact

- The master key file (`/etc/sonic/bgp_master_key`) is a host filesystem file. It persists across warmboot/fastboot cycles; no special handling is required.
- During warmboot, `bgpcfgd`/`frrcfgd` start and read ConfigDB. The interception layer decrypts passwords transparently. No warmboot-specific code path is needed.
- If the master key file is missing or corrupted during boot, decryption will fail and `frrcfgd` will use the raw (encrypted) string as the BGP password, resulting in BGP authentication failures. Operators should include the master key file in backup/restore procedures.

---

## Restrictions and Limitations

1. **Python-only interception**: Encryption is transparent only for Python callers using `ConfigDBConnector`. Tools that bypass Python and write directly to Redis (`redis-cli`, `sonic-db-cli`, native C++ or Rust applications) will not have passwords encrypted automatically. From an operational standpoint this is acceptable because network admins configure the switch via `config` or `sonic-cfggen`. C++ and Rust interception is noted as future work.

2. **FRR cleartext in container**: Passwords are decrypted before being passed to FRR. The FRR container's running configuration and memory contain cleartext passwords. FRR container isolation provides the boundary.

3. **No per-peer per-key mapping**: All BGP peers share the same master key (one key file for all tables registered to it). Per-peer keys are not supported.

4. **Master key is not itself encrypted**: The master key is stored in plaintext in the key file, protected only by filesystem permissions (mode 0600). Physical/root access to the host can expose the master key. A TPM-backed or HSM-backed key store is out of scope for this version.

5. **Config file (`config_db.json`) at rest**: When the running configuration is saved to `config_db.json` (e.g., via `config save`), the encrypted values from Redis are written to the file. The file therefore contains encrypted (not cleartext) passwords, which is the desired behavior.

---

## Test Plan

### Unit Tests

| Test File | Description |
|-----------|-------------|
| `tests/master_key_encryption_test.py` | AES-GCM deterministic test vectors; `MasterKeyManager` key update, encrypt, decrypt, history; max 8 keys; file permission enforcement |
| `tests/config_db_encryptor_test.py` | `ConfigDBEncryptor` interception: `set_entry`, `mod_entry`, `mod_config` hooks; encryption activated/deactivated; multiple field names |
| `tests/master_key_manager_test.py` | All CLI subcommands: `set`, `encrypt --table`, `decrypt --table`, `activate`, `deactivate`, `status`, `list`; custom registry via `--registry-config` |

### System Tests (Testbed)

| Test | Description |
|------|-------------|
| No BGP flap on activation | Activate encryption on live switch; confirm no BGP session reset |
| No BGP flap on key rotation | Rotate master key; confirm no BGP session reset |
| FRR password delivery | Activate encryption; confirm FRR receives cleartext via `vtysh show running-config` |
| Redis dump confidentiality | After activation, `redis-cli HGETALL BGP_NEIGHBOR:10.0.0.1` shows encrypted blob |
| Boot persistence | Reboot with encryption active; confirm BGP sessions re-establish |
| Missing key file | Remove master key file; reload; confirm BGP auth fails gracefully (no crash) |
| Two tables, one key file | Register both `BGP_NEIGHBOR` and `BGP_PEER_GROUP`; confirm both encrypted by single `activate` |
| Large config load performance | Load config with 10,000 route entries; confirm no deep-copy overhead (lazy copy) |

---

## Future Work

1. **C++ and Rust ConfigDB interception**: Extend the C++ `ConfigDBConnector` in `sonic-swss-common` to load an encryption plugin. This is required before any C++ or Rust daemon is trusted to write sensitive ConfigDB fields.

2. **TACACS, RADIUS, LDAP integration**: Each feature adds an entry to `master_key_encryption_config.py` and adds `MasterKeyManager.decrypt_string()` calls in its consuming daemon. Key management, rotation, and ConfigDB interception are inherited from the framework at zero framework cost.

3. **TPM-backed master key**: For highest-assurance deployments, the master key could be sealed to a TPM's Platform Configuration Registers (PCRs), ensuring it is accessible only when the system boots into a trusted state.

4. **Key distribution protocol**: A controller-facing gRPC or RESTCONF endpoint could push master keys to devices on demand, integrating with enterprise key management systems (HashiCorp Vault, AWS KMS, etc.).

5. **Audit log**: Record encrypt/decrypt events (timestamp, table, key index) to a tamper-evident log for compliance reporting.
