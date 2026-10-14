# SSD Wipe HLD

## 1. Revision


| Rev | Date    | Author         | Change Description |
| --- | ------- | -------------- | ------------------ |
| 0.1 | 07/2026 | Shauli Taragin | Initial version.   |
| 0.2 | 09/2026 | Shauli Taragin | CLI moved from `config sed wipe-ssd` to a standalone `ssd-erase` command; ramdisk budget revised down to 4 GiB; secrets now reach `ssd_erase.sh` on stdin instead of argv. |


## 2. Scope

This document describes the high-level design for **graceful SSD wipe** on SONiC switches with SED-enabled NVMe storage. The wipe runs as two sequential stages on the same drive:

- **Crypto erase** — SED-level key destruction (fast, key-based wipe).
- **Block erase** — sanitize of user data blocks (slower, data overwrite).

It covers:

- New CLI: `ssd-erase`
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
| R6  | At least 4 GiB of RAM is free at wipe time (tmpfs pivot budget).                                                                                                                                        |


## 6. Architecture Design

The feature fits the existing SED platform model:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│ ssd-erase       │────▶│ SedMgmtBase      │────▶│ ssd_erase.sh            │
│ (CLI)           │     │ wipe_ssd()       │     │  1. ramdisk pivot       │
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
| CLI              | `src/sonic-utilities/ssd_erase/main.py` (new), `setup.py` (register the console script) |
| Common API       | `src/sonic-platform-common/sonic_platform_base/sed_mgmt_base.py`                   |
| Scripts (common) | `files/image_config/sed_mgmt/ssd_erase.sh` (new), `sed_pw_utils.sh` (extend)       |
| Image install    | `files/build_templates/sonic_debian_extension.j2` (install `ssd_erase.sh`), `build_debian.sh` (add `rsync`) |


### 7.2 Platform API

Two API additions to the existing SED framework: `wipe_ssd()` is implemented once in `SedMgmtBase` and reused by every platform; `get_psid()` is an abstract getter each vendor overrides against its own hardware.

**Common — new for wipe:**


| Method       | Role                                                                                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wipe_ssd()` | Read TPM banks + PSID + default password from the platform getters, then execute `ssd_erase.sh` via `subprocess.run(..., input=..., start_new_session=True)`, handing the two secrets to the script on stdin; block until the script exits; return success / failure. |


**Platform-specific — new for wipe:**


| Method       | Role                                                                                                                                                                                                             |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_psid()` | Abstract getter each vendor overrides and returns the platform-specific PSID string for `sedutil-cli` PSID revert. |


Existing SED getters (`get_default_sed_password()`, `get_tpm_bank_a_address()`, `get_tpm_bank_b_address()`) are reused unchanged.

### 7.3 CLI design

**Command:** `ssd-erase`

The command is standalone because it performs a one-time, irreversible operation rather than changing configuration.

| Step | Behavior                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------- |
| 1    | Get `SedMgmt` via `chassis.get_sed_mgmt()`. If `None`, print "Error: SED management not supported on this platform" and exit. |
| 2    | `click.confirm("This will PERMANENTLY erase the SSD. Continue?", default=False)`.                                         |
| 3    | Print the start banner.                                                                                                   |
| 4    | Call `sed_mgmt.wipe_ssd()`. The Python call **blocks** until `ssd_erase.sh` exits.                                        |
| 5    | Print success or failure.                                                                                                 |


**Start banner:**

```text
=========================================================================
 SSD ERASE STARTED
   * Do NOT power off the switch or interrupt this session.
   * The erase runs from a RAM-disk and will keep going even if SSH drops.
   * Follow progress in syslog: journalctl -f -t ssd_erase.sh
   * When it finishes, reboot with: sudo /sbin/reboot
=========================================================================
```

### 7.4 `ssd_erase.sh` — orchestration script

Single file at `/usr/local/bin/ssd_erase.sh`. Sources `/usr/local/bin/sed_pw_utils.sh` for logging and SED helpers.

**Arguments:** `-a <tpm_bank_a> -b <tpm_bank_b>`

**Secrets (stdin, not argv):** the default SED password and the PSID are read from stdin as
`SED_DEFAULT_PW=<pw>` and `SED_PSID=<psid>` lines.

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

One new helper: `check_sed_crypto_erase_prereqs` — discovers the boot disk, reuses the existing `check_sed_ready` for the shared TPM/SED/locking checks, derives the NVMe controller name, and verifies sanitize support. Secret and tool validation remains in `ssd_erase.sh`. All other helpers (logging, TPM writes, disk discovery) are reused unchanged from the change-password framework.

## 8. CLI Reference


### 8.1 `ssd-erase` CLI

Securely erase the boot SSD (crypto erase + NVMe block erase). Irreversible.

```
admin@sonic:~$ ssd-erase --help
Usage: ssd-erase [OPTIONS]

  Securely erase the boot SSD (SED PSID revert + NVMe sanitize).

  IRREVERSIBLE: after erase the switch cannot boot until re-imaged.

Options:
  -y, --yes  Skip the interactive confirmation prompt.
  --help     Show this message and exit.
```

Example (interactive):

```
admin@sonic:~$ sudo ssd-erase
This will PERMANENTLY erase the SSD. Continue? [y/N]: y
=========================================================================
 SSD ERASE STARTED
   * Do NOT power off the switch or interrupt this session.
   * The erase runs from a RAM-disk and will keep going even if SSH drops.
   * Follow progress in syslog: journalctl -f -t ssd_erase.sh
   * When it finishes, reboot with: sudo /sbin/reboot
=========================================================================
SSD erase completed successfully. Reboot now with `sudo /sbin/reboot`.
```


## 9. Testing


### 9.1 Unit tests


| Layer                  | Test file                                                        | Coverage                                                                                                                                                                                                 |
| ---------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SedMgmtBase`          | `src/sonic-platform-common/tests/sed_mgmt_base_test.py`          | Missing PSID, default password and TPM banks; successful invocation; script failure; secrets excluded from argv and passed on stdin; newline rejection; preservation of quotes and backslashes.          |
| Platform `SedMgmt`     | `platform/mellanox/mlnx-platform-api/tests/test_sed_mgmt.py`     | PSID retrieval from VPD, missing and invalid PSID data, TPM bank getters, default-password retrieval, and end-to-end wiring into `wipe_ssd()`.                                                           |
| `ssd-erase` CLI        | `src/sonic-utilities/tests/ssd_erase_test.py`                     | Interactive confirmation and abort, `--yes`, supported and unsupported platforms, successful and failed erase results, and unexpected exceptions.                                                       |


### 9.2 Manual tests

The final phase destroys the image, so non-destructive validation is completed first.


| Phase | Action                                                                                                              | Expected outcome                                                                                                                     |
| ----- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| A     | Run unit tests on the switch against the installed platform module.                                                | Platform getters and `wipe_ssd()` wiring pass against the installed software.                                                       |
| B     | Exercise CLI abort paths by declining confirmation and closing stdin.                                               | The command exits without invoking `ssd_erase.sh`; the SED state remains unchanged.                                                 |
| C     | Exercise prerequisite checks with unsupported and nonexistent devices.                                              | Checks fail before services stop, the ramdisk pivot, or either erase operation.                                                     |
| D     | Run the ramdisk pivot with both erase operations stubbed, then restart services and reboot.                         | Root runs from tmpfs, the SSD unmounts, and the switch reboots into the untouched image.                                             |
| E     | Set the ramdisk cap below the copied filesystem size.                                                                | Copying fails before `pivot_root`, leaving the switch bootable.                                                                     |
| F     | Run `sudo ssd-erase` end to end on a disposable test switch.                                                         | PSID revert and block erase complete, sanitize status reports success, and the SSD no longer contains a bootable image.             |


