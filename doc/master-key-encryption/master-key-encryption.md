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
  - [Operational Workflow](#operational-workflow)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions and Limitations](#restrictions-and-limitations)
- [Future Work](#future-work)

---

## Revision History

| Rev | Date       | Author    | Change Description |
|-----|------------|-----------|--------------------|
| 0.1 | 2026-06-16 | Fred Xia  | Initial draft      |
| 0.2 | 2026-08-06 | Fred Xia  | Second draft       |
| 0.4 | 2026-08-10 | Fred Xia  | Third draft        |

---

## Scope

This document describes the design of a **Master Key Encryption Infrastructure** for SONiC. The purpose is to enable at-rest encryption of sensitive configuration fields in ConfigDB (Redis). It defines the general infrastructure — master key management, an AES-GCM encryption library, a code-defined encryption registry, and a transparent ConfigDB interception layer — and then describes how BGP MD5 peer authentication passwords are the first application built on top of this infrastructure.

---

## Definitions and Abbreviations

| Term               | Meaning                                         |
|--------------------|-------------------------------------------------|
| AES-GCM  | Advanced Encryption Standard in Galois/Counter Mode       |
| AAD      | Additional Authenticated Data (used in AES-GCM)           |
| ConfigDB | SONiC configuration database (Redis)                      |

---

## Overview

SONiC stores all configuration — including protocol passwords such as BGP MD5 authentication passwords, TACACS shared secrets, and RADIUS keys — as **cleartext** in Redis (ConfigDB) and in the `config_db.json` startup file. Any local account can dump these values with standard Redis tools. This design proposes a general-purpose Master Key Encryption Infrastructure to protect such fields at rest with symmetric encryption.

The infrastructure provides:

1. **A code-defined registry** that statically declares which tables and fields are subject to automatic encryption.
2. **A master key management library and CLI tool** (`master-key-manager`) to provision master keys, activate/deactivate encryption, and inspect status.
3. **An AES-256-GCM encryption library** offering authenticated symmetric encryption (a.k.a Type-6).
4. **A transparent ConfigDB interception layer** so that standard SONiC tools (`config`, `sonic-cfggen`) automatically encrypt sensitive fields on write without requiring application-level changes.
5. **Extensibility** so that additional features (TACACS, RADIUS, LDAP) can be supported by adding an entry to the registry and the corresponding decrypt/render code in the feature daemon.

---

## Motivation

### At-Rest Security

Community SONiC writes all configuration values to Redis plaintext. An operator or compromised process with read access to the local Redis socket can trivially extract BGP MD5 passwords, RADIUS keys, and similar credentials. FIPS-compliant deployments and customer security policies require these values to be stored encrypted. Our implementation follows the prevailing industry practices, using AES-256-GCM for both confidentiality and integrity.

---

## Requirements

### Functional Requirements

1. **FR-1**: ConfigDB fields designated as sensitive shall be stored encrypted using AES-256-GCM with a device-local master key.
2. **FR-2**: Encryption and decryption shall be transparent to standard SONiC configuration tools (`config load`, `config reload`, `config apply`, `sonic-cfggen`).
3. **FR-3**: The system shall support master encryption keys either supplied by a central controller or generated locally.
4. **FR-4**: A CLI tool (`master-key-manager`) shall allow the operator to set the master key and activate/deactivate encryption.
5. **FR-5**: When encryption is activated, all plaintext secret fields in registered tables shall be re-encrypted automatically; when deactivated, they shall be decrypted automatically.
6. **FR-6**: Encryption shall apply only to ConfigDB. Code specific to each subsystem, e.g. FRR, is responsible to determine when and where to decrypt the encrypted data.
7. **FR-7**: The master key file shall be accessible only to root (mode 0600), protected by filesystem permissions.
8. **FR-8**: The infrastructure shall maintain two master key slots in the master key file: `active_key`, for the key most recently activated, and `candidate_key`, a staged key not yet applied; plus a boolean `enabled` field that is the actual on/off switch for encryption.
9. **FR-9**: The catalog of tables and fields subject to encryption shall be defined in code. No Yang model changes are needed.
10. **FR-10**: A single table may declare multiple fields requiring encryption.

### Non-Functional Requirements

1. The master key file format shall be a versioned, human-readable JSON structure for auditability and disaster recovery.
2. The master key file shall reside in a directory that is persistent across boot partitions in order to support upgrades.

---

## Architecture

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    Master Key Encryption Infrastructure                     │
 │                                                                             │
 │  ┌───────────────────────────────────┐   ┌───────────────────────────────┐  │
 │  │    master-key-manager CLI         │   │   Encryption Library          │  │
 │  │                                   │   │ (master_key_manager.py)       │  │
 │  │  set --key <KEY> | --generate     │   │  AES-256-GCM (Type-6)         │  │
 │  │  encrypt/decrypt --file|--string  │   │  Nonce + CT + AAD             │  │
 │  │  activate / deactivate            │   │  base64-encoded output        │  │
 │  │  status / list                    │   └────────────────┬──────────────┘  │
 │  └──────────────┬────────────────────┘                    │                 │
 │                 │ reads                  ┌────────────────▼──────────────┐  │
 │                 ▼                        │   MasterKeyManager            │  │
 │  ┌───────────────────────────────────┐   │   /host/security_cipher/...   │  │
 │  │  master_key_encryption_config.py  │   │   mode 0600, JSON             │  │
 │  │  (code-defined, static registry)  │   │   active_key / candidate_key  │  │
 │  │  • master_key_file                │   │   enabled: bool               │  │
 │  │  • fields: {TABLE: [field, ...]}  │   │   one instance per file       │  │
 │  └──────────────┬────────────────────┘   └───────────────────────────────┘  │
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

The master key file is a JSON document (e.g., `/host/security_cipher/master_encryption_key`) with mode 0600 (readable only by root). It holds two `MasterKey` slots — `active_key`, the key that protects data at rest when encryption is on, and `candidate_key`, a staged key not yet applied — plus an `enabled` boolean that is the actual on/off switch for encryption. There is no per-feature or per-table sub-keying; one file covers one logical key set regardless of how many tables share it.

Example:

```json
{
  "key_file": "master_encryption_key",
  "active_key": null,
  "candidate_key": {
    "master_key": "my-secret-32-byte-key-padded-to-32",
    "algorithm": "aes-gcm",
    "timestamp": "2026-05-20T10:00:00+00:00"
  },
  "enabled": false
}
```

Key design points:

- **`key_file`**: The basename of the key file path (e.g., `master_encryption_key`). Used as the AES-GCM AAD to bind each ciphertext blob to its key file.
- **`active_key`**: The key most recently activated, or `null` if `activate` has never been run. Only `master-key-manager activate` writes this field — it moves `candidate_key` into it (see [Key Rotation](#key-rotation)). `deactivate` does **not** clear it — it stays in place so the same key is available if encryption is turned back on.
- **`candidate_key`**: The key most recently staged by `set`, or `null` if none is staged. Cleared back to `null` once `activate` moves it into `active_key`.
- **`enabled`**: Whether encryption is currently applied. Set to `true` by a successful `activate` and to `false` by a successful `deactivate`. This is the field the ConfigDB interception layer actually checks — `active_key` can be non-null while `enabled` is `false` (right after a `deactivate`), in which case ConfigDB values are cleartext.

`set` never touches `active_key` or `enabled` — it only writes a new key into `candidate_key`, overwriting whatever was staged there before. The file is written atomically: a temporary file is written, its contents are verified, and then it is renamed over the production path to prevent partial writes.

### Master Key Generation and Provisioning

Two modes are supported:

#### 1. Key Distribution

```
# master-key-manager set --key <KEY>
Saved master key to candidate_key of /host/security_cipher/master_encryption_key
```

The `set` command accepts any string, pads or truncates it to 32 bytes for AES-256, and writes it as a new `MasterKey` into `candidate_key`, timestamped with the time of the `set` call. This always overwrites whatever was previously staged in `candidate_key` — calling `set` twice before running `activate` discards the first of the two keys. `active_key` is never touched by `set`.

#### 2. Local Random Key

For standalone devices without a central key management system, the operator can supply any high-entropy string, or let `set` generate one with `--generate`:

```
# master-key-manager set --generate
Saved master key to candidate_key of /host/security_cipher/master_encryption_key
```

`--generate` is mutually exclusive with `--key <KEY>`; the two are alternative ways to supply the same argument. It produces a random master key equivalent to running `openssl rand -hex 32`.

A central controller may choose either modes to set the master encryption key on a switch. For example, a ZTP mechanism may use a script to invoke `master-key-manager` to generate a encryption key locally after the image is installed.

### Key Rotation

`set` only stages a new key in `candidate_key`; it has no effect on encrypted data until `activate` is run:

```
# master-key-manager set --key newKey2026
# master-key-manager activate
```

`activate` performs the entire rotation as one atomic step:

1. Requires `candidate_key` to be present; fails if nothing has been staged with `set`.
2. If `enabled` is `true`, decrypts all registered fields using current `active_key`. Otherwise the fields are assumed to already be cleartext.
3. Re-encrypts all of those fields using `candidate_key`'s key material.
4. On success, moves `candidate_key` into `active_key` — with its timestamp updated to the time `activate` completed, clears `candidate_key` back to `null`, and sets `enabled` to `true`.

`deactivate` is available to turn encryption off entirely: it decrypts all registered fields back to plaintext using `active_key` and then sets `enabled` to `false`. `deactivate` moves `active_key` to `candidate_key` if there is no current `candidate_key` for staging. Otherwise `active_key` is cleared, since next `activate` will use the new `candidate_key`.

### Encryption Library

The library implements **AES-256-GCM** encryption, consistent with industry standard for reversible AES password storage.

#### Data Structures

```python
@dataclass
class MasterKey:
    master_key: str            # plaintext key string (padded to 32 bytes for AES-256)
    algorithm: AlgorithmName   # currently only "aes-gcm"
    timestamp: datetime        # time this key was written into its slot

@dataclass
class MasterKeyConfig:
    key_file: str                       # basename of the key file path; used as AES-GCM AAD
    active_key: Optional[MasterKey]     # key most recently activated; None until `activate` first runs
    candidate_key: Optional[MasterKey]  # staged by `set`, not yet applied; None if none staged
    enabled: bool                       # on/off switch for encryption; True after `activate`, False after `deactivate`
```

#### Encrypted Password Format

An encrypted value is a base64-encoded blob with the following internal layout:

```
      [ 12-byte nonce ][ ciphertext (N bytes) ][ 16-byte AAD ]
        └───────────────────────────────────────────┘
          base64-encoded into a printable string
```

- **Nonce** (12 bytes): Randomly generated per encryption operation.
- **Ciphertext**: The encrypted plaintext, same length as the original.
- **AAD** (16 bytes, zero-padded): The key-file basename (e.g., `master_encryption_key`) is used as Additional Authenticated Data. This binds each ciphertext blob to its master key file, so a blob encrypted under one key file cannot be decrypted (GCM tag will not validate) under a different key file.

#### Detecting Encrypted Values

Whether a stored value is already encrypted is determined by runtime probing — no separate flag field is needed:

1. Check if the value is valid base64.
2. Attempt AES-GCM decryption with `active_key`.
   - If decryption succeeds (GCM tag validates): the value is **encrypted**.
   - If decryption fails: treat as **cleartext**.

If `active_key` is `None`, there is no key to test against, so `is_encrypted()` returns `False` unconditionally. The GCM authentication tag provides cryptographically strong assurance: the probability of a cleartext string accidentally passing both checks is negligible.

#### API Reference

```python
# Singleton per filename — one instance shared across all callers for the same file
mgr = MasterKeyManager("/host/security_cipher/master_encryption_key")

# Stage a new master key into candidate_key. Does not touch active_key.
mgr.update_master_key("my-secret-key")          # returns bool

# Encrypt with active_key
# (AAD is the key_file basename from MasterKeyConfig, e.g. "master_encryption_key")
encrypted = mgr.encrypt_string("plaintext")

# Decrypt with active_key (AAD is read from the blob)
plaintext = mgr.decrypt_string(encrypted)

# Check if already encrypted with active_key
already_enc = mgr.is_encrypted(value)           # returns bool

# Activation state — stored in the key file, not in ConfigDB
mgr.is_enabled()                                # returns the `enabled` field

# Rotation: requires candidate_key to be present; migrates all consumers' data
# to it via the caller-supplied re-encrypt callback, then moves candidate_key
# into active_key (timestamped to completion time) and clears candidate_key.
mgr.activate(reencrypt_callback)                # returns bool
```

### ConfigDB Interception Layer

Currently Redis interception logic is added to an abstract python ConfigDBConnector classes in both `sonic-swss-common` and `sonic-py-swsssdk`. An instance of the implementor subclass of `ConfigDBEncryptor` in master key manager library is loaded lazily by `ConfigDBConnector` on first write.

#### Encryptor API

```python
class ConfigDBEncryptor:

    def is_loaded(self) -> bool: ...

    def entry_need_encryption(self, table, key, data) -> bool:
        """True when encryption is active (key file enabled is True) for
        table and any registered field in data is plaintext."""

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

#### Lazy Deep Copy in `encrypt_config`

When `mod_config()` is called with a large data dict (e.g., a full route table with thousands of entries), `encrypt_config` avoids an unconditional `deepcopy`. Instead, it makes a copy only on the first field that actually needs encryption. If no table has encryption activated, the original dict is returned unchanged — zero copy overhead.

### Encryption Registry: Static Configuration

The catalog of CONFIG DB tables and fields subject to encryption is defined as a static Python data structure — not a YANG model and not a ConfigDB table. The rationale is that adding encryption to a new use case likely requires at least two code changes:

1. Adding the table and field to the registry
2. Feature-specific decrypt/render code in the consuming daemon (e.g., `frrcfgd` for BGP auth passwords).

BGP is the first application to use this infrastructure, and any future application (e.g., TACACS) adds its own tables and fields to the same registry rather than defining a separate one.

#### Registry Format

```python
DEFAULT_MASTER_KEY_FILE = "/host/security_cipher/master_encryption_key"

_DEFAULT_REGISTRY = {
    "master_key_file": DEFAULT_MASTER_KEY_FILE,
    "fields": {
        "BGP_NEIGHBOR":   ["auth_password"],
        "BGP_PEER_GROUP": ["auth_password"],
    },
}

_MasterKeyEncryptionRegistries = [ _DEFAULT_REGISTRY ]
```

The registry is stored as a list (`_MasterKeyEncryptionRegistries`) for future extensibility, e.g. if there is a need to use a different master encryption key for a group tables and fields.

Each registry entry has:
- **`master_key_file`**: Absolute path to the master key file shared by all registered tables.
- **`fields`**: A `list` mapping CONFIG DB table names to a list of field names whose values are subject to encryption.

---

## CLI: master-key-manager

```
Usage: master-key-manager [-s <socket>] [-v] [--force] COMMAND

Commands:
  set (--key <KEY> | --generate)
      Stage a new master key in the master key file configured in the
      registry (master_key_encryption_config.py), without changing which
      key is currently protecting data at rest.
      The key itself is either given with --key <KEY> or generated with
      --generate, which are mutually exclusive; one of them is required.
      --generate produces a random key equivalent to `openssl rand -hex 32`
      (32 random bytes as 64 hex characters), generated in-process via
      Python's `secrets.token_hex(32)` rather than an openssl subprocess.
      The key is padded/truncated to 32 bytes for AES-256 and written into
      candidate_key, overwriting whatever key was previously staged there.
      Run `activate` to rotate to the newly-staged key.
      Examples:
        master-key-manager set --key mySecretKey
        master-key-manager set --generate

  encrypt (--file <JSON> | --string <STRING>)
      Two mutually exclusive forms:
      --file <JSON>
          Read a CONFIG DB JSON file, encrypt every registered secret field
          present in it, and print the resulting JSON to stdout. The input
          file is not modified. If no master key is provisioned, the file
          is printed back unchanged with a warning.
      --string <STRING>
          Encrypt a single string with the registry's master key and print
          the resulting blob to stdout.

  decrypt (--file <JSON> | --string <STRING>)
      Same two forms, decrypting instead: a CONFIG DB JSON file back to
      plaintext, or a single encrypted blob back to its plaintext string.
      Both forms print the result to stdout.

  activate
      Rotate to the staged key and activate encryption for the registry:
        1. Requires candidate_key to be present; fails if nothing has been
           staged with `set`.
        2. Bulk re-encrypt all secret fields in the registry's tables: read
           from ConfigDB, decrypt with active_key (or treat as already-
           cleartext if enabled is false), re-encrypt with candidate_key's
           key material, and write back.
        3. Move candidate_key into active_key, timestamped to the completion
           time of this command, clear candidate_key, and set enabled=true
           in the master key file. The master key previously in active_key
           is erased.

  deactivate
      Deactivate encryption: decrypt all of the registry's tables back to
      plaintext using active_key, then set enabled=false in the master key
      file. active_key and candidate_key are left untouched.

  status
      Print JSON status for the registry:
        {
          "master_key_file": "/host/security_cipher/master_encryption_key",
          "tables": ["BGP_NEIGHBOR", "BGP_PEER_GROUP"],
          "enabled": true,
          "candidate_key_staged": false
        }

  list
      Print master key metadata (timestamp and algorithm for active_key and
      candidate_key, not key values) for all registered tables.

Options:
  -s, --socket-path <PATH>     Unix domain socket path for Redis server
  -v, --verbose                Verbose logging
  --force                      Force remove master key file lock
```

---

## Application: BGP MD5 Password Encryption

BGP MD5 authentication (RFC 2385) requires a shared plaintext secret between BGP peers. SONiC stores this in `BGP_NEIGHBOR.auth_password` and `BGP_PEER_GROUP.auth_password`. The decrypt-and-render step for FRR is handled explicitly in `frrcfgd`.

Before master key encryption:

```python
    def bgp_neighbor_handler(self, table, key, data):
        self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

With master key encryption:

```python
def bgp_neighbor_handler(self, table, key, data):
    if data:
        try:
            from master_key_manager import MasterKeyManager, master_key_registry
            registry = master_key_registry()
            if table in registry["fields"]:
                key_mgr = MasterKeyManager(registry["master_key_file"])
                for field in registry["fields"][table]:
                    val = data.get(field, None)
                    if val and key_mgr.is_encrypted(val):
                        decrypted = key_mgr.decrypt_string(val)
                        if decrypted:
                            data[field] = decrypted
        except Exception as ex:
            syslog.syslog(syslog.LOG_WARNING,
                          "[bgp cfgd] decryption failed: %s" % str(ex))
    self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

While the encryption of data before writing to CONFIG DB is automatic and transparent, it is the responsiblity of each subsystem to decide when and where to perform the decryption of data, for the following reasons:

1. It is likely that only a small portion of application logic needs to use decrypted data. Automatically decrypting data carries performance overhead without much benefit.
2. By requiring developer to intentionally perform data decryption at place of use, it reduces the chances of decrypted data being left unattended and/or accidentally saved to persistent files.

### Operational Workflow

#### Initial State (No Encryption)

ConfigDB stores passwords in cleartext.

```json
"BGP_NEIGHBOR": {
    "10.0.0.1": { "auth_password": "abcde" }
}
```

#### Step 1: Provision the Master Key

```
# master-key-manager set --key mySecretKey
Saved master key to candidate_key of /host/security_cipher/master_encryption_key
```

`active_key` and `candidate_key` both start unset, so this fills `candidate_key`. Optionally `master-key-manager` can generate master encryption key locally using the `openssl` library.

#### Step 2: Activate Encryption

```
# master-key-manager activate
```

The `activate` command:
1. Confirms `candidate_key` is present — it is, from Step 1.
2. Reads all `BGP_NEIGHBOR` and `BGP_PEER_GROUP` entries from ConfigDB, encrypts each `auth_password` with `candidate_key`'s key material (the fields are cleartext, since `enabled` was `false`), and writes back.
3. Moves `candidate_key` into `active_key` — timestamped to the completion of this `activate` call — clears `candidate_key`, and sets `enabled` to `true`.

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

The `config` command uses `ConfigDBConnector.mod_entry()`, which is intercepted. Because `enabled` is `true` for the registry, the interceptor encrypts `mysecret` with `active_key` before writing to Redis. Similarly, `config load`, `config reload`, and `config apply` all go through `mod_config()`, which calls `encrypt_config()`. The lazy-copy optimization means there is no deep-copy overhead when loading large config files that contain no registered secret tables.


#### Step 4: Key Rotation

```
# master-key-manager set --key newKey2026
Saved master key to candidate_key of /host/security_cipher/master_encryption_key

# master-key-manager activate
```

`set` stages `newKey2026` into `candidate_key`; nothing in ConfigDB changes yet, and the existing `active_key` keeps protecting data. `activate` then decrypts all `auth_password` fields using `active_key`, re-encrypts them using `candidate_key`'s key material, and moves `candidate_key` into `active_key` (erasing the old one). BGP sessions are unaffected during rotation.

---

## Warmboot and Fastboot Design Impact

- The master key file is a host filesystem file. It persists across warmboot/fastboot cycles; no special handling is required.
- For BGP, during warmboot, `bgpcfgd`/`frrcfgd` start and read ConfigDB. The interception layer decrypts passwords transparently. No warmboot-specific code path is needed.
- If the master key file is missing or corrupted during boot, decryption will fail and `frrcfgd` will use the raw (encrypted) string as the BGP password, resulting in BGP authentication failures. Operators should include the master key file in backup/restore procedures.

---

## Restrictions and Limitations

1. **Python-only interception**: Encryption is transparent only for Python callers using `ConfigDBConnector`. Tools that bypass Python and write directly to Redis (`redis-cli`, `sonic-db-cli`, native C++ or Rust applications) will not have passwords encrypted automatically. From an operational standpoint this is acceptable because network admins configure the switch via `config` or `sonic-cfggen`. C++, Go and Rust interception is noted as future work.

2. **FRR cleartext in container**: Passwords are decrypted before being passed to FRR. The FRR container's running configuration and memory contain cleartext passwords. FRR container isolation provides the boundary.

3. **Master key is not itself encrypted**: The master key is stored in plaintext in the key file, protected only by filesystem permissions (mode 0600). Physical/root access to the host can expose the master key. A TPM-backed or HSM-backed key store is out of scope for this version.

---

## Future Work

1. **C++, Go and Rust ConfigDB interception**: Extend encryption hook to other languages, for use cases such as gNMI.

2. **TACACS, RADIUS, LDAP integration**: Each feature adds an entry to and add calls in its consuming daemon. Key management, rotation, and ConfigDB interception are inherited from the framework at zero framework cost.

3. **TPM-backed master key**: For highest-assurance deployments, the master key could be sealed to a TPM's Platform Configuration Registers (PCRs), ensuring it is accessible only when the system boots into a trusted state.

4. **Key distribution process**: Integration with centralized switch upgrade and maintenance processes, e.g. **ZTP** based image installation and activation.

5. **Audit log**: Record encrypt/decrypt events (timestamp, table, key index) to a tamper-evident log for compliance reporting.
