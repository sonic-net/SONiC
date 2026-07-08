# SSD Wipe HLD

## 1. Revision


| Rev | Date    | Author         | Change Description |
| --- | ------- | -------------- | ------------------ |
| 0.1 | 07/2026 | Shauli Taragin | Initial version.   |


## 2. Scope

This document describes the high-level design for **graceful SSD wipe** on SONiC switches with SED-enabled NVMe storage. The wipe runs as two sequential stages on the same drive:

- **Crypto erase** — SED-level key destruction (fast, key-based wipe).
- **Block erase** — sanitize of user data blocks (slower, data overwrite).

It covers:

- New CLI: `config sed wipe-ssd`
- Common `SedMgmtBase.wipe_ssd()` API, `ssd_erase.sh` orchestrator (including the ramdisk pivot), and `sed_pw_utils.sh` extensions
- Platform API `get_psid()` 

## 3. Definitions/Abbreviations


| Term          | Description                                                                                                            |
| ------------- | ---------------------------------------------------------------------------------------------------------------------- |
| SED           | Self-Encrypting Drive.                                                                                                 |
| TPM           | Trusted Platform Module.                                                                                               |
| NVMe          | Non-Volatile Memory Express.                                                                                           |
| PSID          | Physical Security ID; factory credential required for the crypto-erase PSID revert.                                    |
| Ramdisk pivot | Copy the minimal userspace onto tmpfs and `pivot_root` into it, so the physical OS disk can be unmounted during erase. |


## 4. Overview


### 4.1 Feature Motivation

Provide a controlled, destructive CLI to **securely wipe** the switch boot SSD when hardware-based encryption and sanitization are required.

**Primary use cases:**


| Use case                | Description                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Decommission / disposal | Before permanently removing or scrapping a switch, erase all user and system data so it cannot be recovered, including from physical access to the drive.                                                          |
| RMA / relocation        | Operational scenarios where the switch physically moves — RMA (Return Merchandise Authorization), inter-site transfer, or lab repurposing — and data must be destroyed before the hardware leaves the operator's custody. |
| Runtime TPM bank loss   | If SED TPM password banks are corrupted or out of sync at runtime (risk of lockout on next boot), a controlled wipe resets TPM banks to factory default and clears the drive so the platform can be reprovisioned. |


> **Warning:** Wipe is **irreversible**. After completion the SSD contains no bootable SONiC image, SED locking is disabled, and the drive password is reset to the platform default in TPM banks A/B.


### 4.2 Additions to the SED framework

Wipe builds on the SED framework from [change_sed_password_hld.md](https://github.com/sonic-net/SONiC/blob/master/doc/sed/change_sed_password_hld.md), adding:

- `SedMgmtBase.wipe_ssd()` and abstract `get_psid()`
- `ssd_erase.sh` orchestrator (ramdisk pivot + crypto/block erase)
- `check_sed_crypto_erase_prereqs` extension in `sed_pw_utils.sh`
- `rsync` added to the image


## 5. Requirements


| ID  | Requirement                                                                                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Platform exposes `get_sed_mgmt()` returning an object with wipe support; `None` → CLI reports "not supported" and exits with a non-zero status.                                                         |
| R2  | SED is enabled on the OS NVMe controller (OPAL 2.0 support, `LockingEnabled = Y`).                                                                                                                      |
| R3  | PSID is retrievable from the platform via `SedMgmt.get_psid()`.                                                                                                                                         |
| R4  | Platform default SED password is retrievable via existing `SedMgmt.get_default_sed_password()`.                                                                                                         |
| R5  | TPM banks A/B are configured in `/etc/sonic/sed_config.conf`.                                                                                                                                           |
| R6  | At least 6 GiB of RAM is free at wipe time (tmpfs pivot budget).                                                                                                                                        |


## 6. Architecture Design

The feature fits the existing SED platform model:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│ config sed      │────▶│ SedMgmtBase      │────▶│ ssd_erase.sh            │
│ wipe-ssd        │     │ wipe_ssd()       │     │  1. ramdisk pivot       │
│                 │     │                  │     │  2. crypto erase        │
│                 │     │                  │     │  3. block erase         │
└─────────────────┘     └────────┬─────────┘     └───────────┬─────────────┘
                                 │                           │
                                 ▼                           ▼
                        ┌───────────────────┐         ┌──────────────────┐
                        │ SedMgmt           │         │ sed_pw_utils.sh  │
                        │ (platform)        │         │ sedutil, nvme,   │
                        │ get_psid()        │         │ tpm2-tools       │
                        │ get_default_sed…  │         └──────────────────┘
                        └───────────────────┘
```


## 7. High-Level Design


### 7.1 Repositories / paths changed


| Area             | Path                                                                               |
| ---------------- | ---------------------------------------------------------------------------------- |
| CLI              | `src/sonic-utilities/config/sed.py`                                                |
| Common API       | `src/sonic-platform-common/sonic_platform_base/sed_mgmt_base.py`                   |
| Scripts (common) | `files/image_config/sed_mgmt/ssd_erase.sh` (new), `sed_pw_utils.sh` (extend)       |
| Image install    | `files/build_templates/sonic_debian_extension.j2` (install `ssd_erase.sh`), `build_debian.sh` (add `rsync`) |


### 7.2 Platform API

Two API additions to the existing SED framework: `wipe_ssd()` is implemented once in `SedMgmtBase` and reused by every platform; `get_psid()` is an abstract getter each vendor overrides against its own hardware.

**Common — new for wipe:**


| Method       | Role                                                                                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wipe_ssd()` | Read TPM banks + PSID + default password from the platform getters, then execute `ssd_erase.sh` via `subprocess.check_call(..., start_new_session=True)`; block until the script exits; return success / failure. |


**Platform-specific — new for wipe:**


| Method       | Role                                                                                                                                                                                                             |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_psid()` | Abstract getter each vendor overrides and returns the platform-specific PSID string for `sedutil-cli` PSID revert. |


Existing SED getters (`get_default_sed_password()`, `get_tpm_bank_a_address()`, `get_tpm_bank_b_address()`) are reused unchanged.

### 7.3 CLI design

**Command:** `config sed wipe-ssd`


| Step | Behavior                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------- |
| 1    | Get `SedMgmt` via `chassis.get_sed_mgmt()`. If `None`, print "SED management is not supported on this platform" and exit. |
| 2    | `click.confirm("This will PERMANENTLY erase the SSD. Continue?", default=False)`.                                         |
| 3    | Print the start banner.                                                                                                   |
| 4    | Call `sed_mgmt.wipe_ssd()`. The Python call **blocks** until `ssd_erase.sh` exits.                                        |
| 5    | Print success or failure.                                                                                                 |


**Start banner:**

```text
=========================================================================
 SSD ERASE STARTED
   * Do NOT power off the switch or interrupt this session.
   * The wipe runs from a RAM-disk and will keep going even if SSH drops.
   * Follow progress in syslog: journalctl -f -t ssd_erase.sh
   * When it finishes, reboot with: sudo /sbin/reboot
=========================================================================
```

### 7.4 `ssd_erase.sh` — orchestration script

Single file at `/usr/local/bin/ssd_erase.sh`. Sources `/usr/local/bin/sed_pw_utils.sh` for logging and SED helpers.

**Arguments:** `-a <tpm_bank_a> -b <tpm_bank_b> -p <default_password> -s <psid>`

**Sequence (NVMe only):**

| Step | Action                                                                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Validate prereqs, stop SONiC services, pivot root to a tmpfs, and unmount the OS disk. Abort before any erase if the unmount fails.                |
| 2    | `store_sed_pwd_in_tpm` **bank A** ← `default_pw`.                                                                                                  |
| 3    | `sedutil-cli --yesIreallywanttoERASEALLmydatausingthePSID <psid> <nvme_ctrl>` — crypto erase.                                                      |
| 4    | `store_sed_pwd_in_tpm` **bank B** ← `default_pw` (log and continue on failure).                                                                    |
| 5    | `nvme sanitize <disk> --sanact=0x02` — block erase.                                                                                                |
| 6    | Poll `nvme sanitize-log`.                                                                                                                          |
| 7    | Exit; no reboot (operator's step).                                                                                                                 |

PSID revert destroys the drive's Media Encryption Key (MEK) and resets the drive password to the platform default.

### 7.5 `sed_pw_utils.sh` extensions

One new helper: `check_sed_crypto_erase_prereqs` — validates PSID / default password / required tools, reuses the existing `check_sed_ready` for the shared TPM/SED/locking checks, then verifies the boot disk is NVMe with sanitize support. On success exports `psid_val`, `nvme_disk_name` (controller), and `default_pw` for the orchestrator. All other helpers (logging, TPM writes, disk discovery) are reused unchanged from the change-password framework.

## 8. CLI Reference


### 8.1 Wipe SSD CLI

Securely erase the boot SSD (crypto erase + NVMe block erase). Irreversible.

```
admin@sonic:~$ config sed wipe-ssd --help
Usage: config sed wipe-ssd [OPTIONS]

  Securely wipe the boot SSD (SED PSID revert + NVMe sanitize).
  This operation is IRREVERSIBLE: after wipe the switch cannot boot
  until re-imaged.

Options:
  -y, --yes       Skip the interactive confirmation (for automation).
  -?, -h, --help  Show this message and exit.
```

Example (interactive):

```
admin@sonic:~$ config sed wipe-ssd
This will PERMANENTLY erase the SSD. Continue? [y/N]: y
=========================================================================
 SSD ERASE STARTED
   * Do NOT power off the switch or interrupt this session.
   * The wipe runs from a RAM-disk and will keep going even if SSH drops.
   * Follow progress in syslog: journalctl -f -t ssd_erase.sh
   * When it finishes, reboot with: sudo /sbin/reboot
=========================================================================
SSD wipe completed successfully. Reboot now with `sudo /sbin/reboot`.
```


## 9. Testing


### 9.1 Unit tests


| Layer              | Test file                                                    | Coverage                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SedMgmtBase`      | `src/sonic-platform-common/tests/sed_mgmt_base_test.py`      | `wipe_ssd()` returns `False` on missing PSID / default password / TPM banks; calls `ssd_erase.sh` with the right args and `start_new_session=True` on success. |
| CLI                | `src/sonic-utilities/tests/sed_test.py`                      | `config sed wipe-ssd` returns non-zero when `get_sed_mgmt()` is `None`; passes `--yes` to bypass the prompt; propagates the exit code from `wipe_ssd()`.       |


### 9.2 Manual tests

Two-phase validation on a switch (the wipe destroys the image):


| Phase | Command / action                                                                             | Expected outcome                                                                                                            |
| ----- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| A     | `ssd_erase.sh -a … -b … -p … -s … --dry-run` (prereq check only; dev-only flag, not shipped) | Prereqs pass; script exits 0 without touching the disk. Confirms PSID parsing, memory budget, tool availability on the DUT. |
| B     | `config sed wipe-ssd` end-to-end.                                                            | Crypto erase + block erase both succeed.                                                                                    |


