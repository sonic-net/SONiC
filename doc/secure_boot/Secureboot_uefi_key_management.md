<!-- omit in toc -->
# High Level Design Document

***Revision***

|  Rev  | Date           | Author      | Change Description |
| :---: | :------------: | :---------: | ------------------ |
|  0.1  |   08/25/2023   | Sachin Naik | Initial version    |
|  0.2  |   11/05/2026   | Sachin Naik | Ownership claim. Community reference is OVMF: efi-readvar / efi-updatevar, enroll needs no reboot, SecureBoot=1 on next boot |


<!-- omit in toc -->
## Table of Contents
- [Abbreviation](#abbreviation)
- [1 Requirements](#1-requirements)
- [2 Overview](#2-overview)
- [3 UEFI components](#3-uefi-components)
  - [3.1 UEFI firmware](#31-uefi-firmware)
  - [3.2 UEFI keys](#32-uefi-keys)
  - [3.3 Authenticated variable](#33-authenticated-variable)
  - [3.4 UEFI modes and Secure Boot flag](#34-uefi-modes-and-secure-boot-flag)
- [4 Factory default state](#4-factory-default-state)
- [5 Ownership](#5-ownership)
  - [5.1 Ownership model](#51-ownership-model)
  - [5.2 Claim workflow](#52-claim-workflow)
  - [5.3 Enroll keys in Setup Mode](#53-enroll-keys-in-setup-mode)
  - [5.4 Verify ownership claim](#54-verify-ownership-claim)
- [6 UEFI key management](#6-uefi-key-management)
  - [6.1 Generation of keys and authenticated variable](#61-generation-of-keys-and-authenticated-variable)
  - [6.2 Enrollment of authenticated variables into the device](#62-enrollment-of-authenticated-variables-into-the-device)
  - [6.3 Remove keys from UEFI database](#63-remove-keys-from-uefi-database)
  - [6.4 Revoke keys](#64-revoke-keys)
  - [6.5 Show keys](#65-show-keys)
- [7 SONIC implementation](#7-sonic-implementation)
- [8 SONiC CLI commands](#8-sonic-cli-commands)
- [9 Test considerations](#9-test-considerations)


## Abbreviation

| Abbreviation | Description                                  |
| ------------ | -------------------------------------------- |
| PK           | Platform Key.                                |
| KEK          | Key Exchange Key                             |
| db           | UEFI Signature Key Database                  |
| dbx          | Forbidden Signature Key Database              |
| UEFI         | Unified Extensible Firmware Interface        |
| RoT          | Root of Trust                                |
| TPM          | Trusted platform module                      |
| SetupMode    | UEFI global: 1 = Setup Mode, 0 = User Mode   |
| SecureBoot   | UEFI global: 1 = enforcement on, 0 = off     |
| AUTH2        | `EFI_VARIABLE_AUTHENTICATION_2` (timestamp + PKCS#7 + ESL) |
| ESL          | `EFI_SIGNATURE_LIST`                         |


## 1 Requirements
SONiC runs on switching hardware from multiple vendors. Some of this hardware implements a hardware root of trust and UEFI firmware, which helps establish Secure Boot. The hardware vendor ships the machine. The **platform owner** must be able to take ownership of that machine: enroll their own Platform Key, constrain boot to owner-trusted images, and later manage PK, KEK, db, and dbx under their own policy (rotate keys, add signers, revoke compromised keys).

This requires SONiC to access UEFI Secure Boot variables for:
1. Ownership claim (enroll dbx, db, KEK, then PK while the device is in Setup Mode).
2. Show enrolled PK, KEK, db, and dbx, and show `SetupMode` / `SecureBoot`.
3. Add, replace, remove, and revoke those keys after claim (AUTH2).

## 2 Overview
The UEFI Secure Boot feature is introduced in UEFI spec version 2.3.1 onwards. It verifies image integrity and authenticity before load. The spec also describes how UEFI keys are managed.

**This community HLD follows the OVMF model** (Open Virtual Machine Firmware: the open UEFI implementation for QEMU/KVM). Key access is `efi-readvar`, `efi-updatevar`, and efivarfs. There is no vendor plugin in this revision. Platforms that cannot use that path are out of scope here.

TPM measured boot is out of scope.

## 3 UEFI components

### 3.1 UEFI firmware
Typically the UEFI is a modern replacement for traditional BIOS. This HLD uses **OVMF** (Open Virtual Machine Firmware) as the reference UEFI: open firmware for QEMU/KVM that implements UEFI Authenticated Variables, Setup Mode / User Mode, and `SecureBoot` as specified. Behavior called out below (including when `SecureBoot` becomes 1) is the OVMF behavior.

### 3.2 UEFI keys
UEFI keys are types of UEFI variables. These are cryptographic keys used in Unified Extensible Firmware Interface (UEFI) firmware. These are asymmetric cryptographic keys that come with public and private key pairs. The private keys are used for signing data and public keys are enrolled in the UEFI device for verifying signed data.

There are multiple keys involved in the UEFI secure boot implementations. The platform owner sets the policies around these keys.

![image](https://github.com/sacnaik/SONiC/assets/25231205/fdf6a164-6153-4c14-ba6d-b8d30475e390)

**1.	Platform Key(PK):** The PK establishes trust between the **platform owner** and UEFI firmware. The owner enrolls the public PK during ownership claim (section 5), not before the VM is provisioned. The PK private key stays with the owner and is used to authorize later PK and KEK AUTH2 updates.

**2.	Key Exchange Key(KEK)**: KEK authorizes changes to db and dbx. The owner enrolls the public KEK (unsigned ESL during claim; AUTH2 signed by PK after claim). The KEK private key stays with the owner and is used to authorize db and dbx AUTH2 updates, including NOS signing keys.

**3.	Signature Database (Db):** It contains secure boot verification keys that are used to verify the signed image artifacts during system boot(Ex: bootloader and kernel).

**4.	Forbidden Signature Database(Dbx):** These contain keys that are revoked. These keys are used during the secure boot process to prevent the booting of certain bootloaders or images which are signed by the private part of these keys.

### 3.3 Authenticated variable
These are a special type of UEFI variable that supports cryptographic authentication and integrity verification. The authenticated variable enables a secure way of storing and accessing UEFI variables within the UEFI environment and ensures that the UEFI variable remains tamper-proof and authentic. Since authenticated variables are signed objects, the UEFI firmware can verify them before accessing or updating them.

UEFI Secure Boot databases (PK, KEK, db, dbx) are time-based authenticated variables. An update is an AUTH2 object: a timestamp, a PKCS#7 signature, and the new signature list (ESL). Firmware verifies the signature against the currently enrolled trust source, then writes the ESL. Unsigned writes are accepted only in Setup Mode (no PK). That is the factory and claim path (sections 4 and 5).

Once a PK is enrolled, the platform is in User Mode. From that point, **any** add, replace, remove, or revoke of PK, KEK, db, or dbx **must** be an AUTH2 authenticated variable. Firmware must reject unsigned ESL, raw certificates, and any payload that does not verify.

| Variable | After claim, AUTH2 must be signed by |
| -------- | ------------------------------------ |
| PK       | Current PK                           |
| KEK      | Current PK                           |
| db       | A currently enrolled KEK             |
| dbx      | A currently enrolled KEK             |

Private keys never go on the DUT. openssl / `sign-efi-sig-list` stay on the owner host. The switch only runs `efi-readvar` / `efi-updatevar` on the file the owner copies in.

### 3.4 UEFI modes and Secure Boot flag
UEFI Secure Boot is controlled by two global variables. They are independent: enrolling a Platform Key changes the mode; turning enforcement on or off is the Secure Boot flag.

| Variable | Role | Values |
| -------- | ---- | ------ |
| `SetupMode` | Whether a Platform Key is enrolled | `1` = Setup Mode (no PK). `0` = User Mode (PK present) |
| `SecureBoot` | Whether firmware verifies boot images against db/dbx | `1` = enforcing. `0` = not enforcing |

**Setup Mode** (`SetupMode=1`): No PK is enrolled. This is the factory and provisioning state. Firmware accepts PK, KEK, db, and dbx updates as unsigned signature lists (no AUTH2). `SecureBoot` is `0`. Firmware does not reject unsigned boot images.

**User Mode** (`SetupMode=0`): A PK is enrolled. Updates to PK and KEK must be AUTH2 objects signed by the current PK. Updates to db and dbx must be AUTH2 objects signed by a KEK. Enrolling the platform owner's PK is the standard UEFI transition from Setup Mode to User Mode. That PK enrollment is the ownership claim: the owner's PK becomes the root of the key hierarchy.

**Secure Boot flag**: `SecureBoot` is not the same variable as `SetupMode`. User Mode does not by itself mean images are verified. While `SecureBoot=0`, keys may already be present but unsigned images are still loaded.

In the OVMF model, `SetupMode` flips to `0` as soon as PK is accepted. `SecureBoot` is computed at POST, so it stays `0` until the **next reboot**. Image verification against db/dbx also starts on that boot. The running OS is not re-checked. Enroll of dbx/db/KEK/PK does **not** require a reboot between those writes.

Enforcing Secure Boot is both flags together after that reboot: `SetupMode=0` and `SecureBoot=1`.

## 4 Factory default state
OVMF factory default is Setup Mode with empty PK/KEK/db/dbx so the owner can enroll keys. The platform is not yet constrained to owner-signed images. Do not enroll a PK before claim if the owner is expected to claim with unsigned ESL (section 5.3).

| Attribute | Factory default |
| --------- | --------------- |
| UEFI mode | Setup Mode (`SetupMode = 1`) |
| Secure Boot | Disabled (`SecureBoot = 0`) |
| PK, KEK, db, dbx | Not enrolled (empty) |
| Firmware | OVMF (unsigned or test-signed as shipped with the VM) |
| SONiC / bootloader | A bootable image so the claim path can run. Install the owner-signed image before PK. |

There is no end-user CLI that only enables Secure Boot in the factory state. Secure Boot is enabled as part of the one-time ownership claim (section 5).

`efi-readvar` lists PK, KEK, db, and dbx. It does not print `SetupMode` or `SecureBoot`. Read those from efivarfs. The first four bytes are attributes; the following byte is the value (`1` or `0`).

```bash
efi-readvar PK            # expect empty / length 0

od -An -tu1 -j4 -N1 \
  /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c
# expect 1  Setup Mode

od -An -tu1 -j4 -N1 \
  /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c
# expect 0  Secure Boot disabled
```

## 5 Ownership

### 5.1 Ownership model
OVMF provides the UEFI variable store. The platform owner owns the VM after claim.

| Role | Responsibility |
| ---- | -------------- |
| **Firmware (OVMF)** | Starts in **Setup Mode** with empty PK/KEK/db/dbx. Implements standard Authenticated Variables. Does not retain the owner's private keys. |
| **Platform owner** | Generates PK, KEK, and db (and dbx) off the device. Holds private keys. Signs ONIE and SONiC. Builds ESL/AUTH2. Enrolls keys. Sets boot policy in db/dbx. |
| **SONiC** | CLI to show variables and apply the owner's ESL (Setup Mode) or AUTH2 (User Mode) with `efi-readvar` / `efi-updatevar`. Does not generate or store owner private keys. |

This HLD is the **owner-provisioned PK** model on OVMF: factory is Setup Mode, owner PK is last during claim.

Ownership claim is one ordered procedure. PK is last. Enrolling PK leaves Setup Mode and enters User Mode immediately (`SetupMode=0`). `SecureBoot=1` and db/dbx image checks apply on the **next reboot**, not during the enroll writes. Enrolling PK against an ONIE or SONiC image that db will not verify can leave the VM unbootable on that reboot.

### 5.2 Claim workflow
Do these steps **in order**. Stay in Setup Mode until PK is written.

```
  Off device
    1. Generate PK, KEK, db (and dbx) as in 6.1
    2. Sign ONIE / SONiC with a key that will be enrolled in db
  On device  (Setup Mode)
    3. Confirm SetupMode = 1, SecureBoot = 0, PK empty
    4. Install the owner-signed OS that db will trust
    5. Enroll dbx, db, KEK, then PK (no reboot between these writes)
  After PK
    6. Verify SetupMode = 0 and keys present
    7. Reboot, then verify SecureBoot = 1
```

1. **Generate keys** off the device (section 6.1). Private keys stay on the owner host. Only public certificates are written to the device.

2. **Sign boot artifacts** with a private key whose certificate will be in db: ONIE and the owner's SONiC. In the secure-upgrade path the same db key signs shim and the SONiC image; `sonic-installer` / ONIE verify the new image against db before write.

3. **Confirm factory default** on the device (section 4): `SetupMode = 1`, `SecureBoot = 0`, PK empty.

4. **Install owner-signed ONIE and SONiC** before PK. Once SONiC is running, `sonic-installer` can replace the image (verify against db before write). USB is only if SONiC is not running.

5. **Enroll keys.** dbx, db, KEK, then PK. No reboot between these writes. PK last: that write enters User Mode (`SetupMode = 0`) immediately.

6. **Verify NVRAM.** `SetupMode = 0` and PK / KEK / db present. `SecureBoot` is still `0` until reboot.

7. **Reboot once.** Then `SecureBoot = 1` and OVMF verifies shim / OS against db. This is when claim enforcement starts.

### 5.3 Enroll keys in Setup Mode
Firmware accepts unsigned ESL while `SetupMode = 1`. Enroll **dbx, db, KEK, then PK**. PK is last, and it is still an unsigned ESL. There is no enrolled PK yet, so a PKCS#7-signed AUTH2 cannot be used for this write.

```
  Setup Mode
       │  1. DBx.esl  →  dbx
       │  2. DB.esl   →  db
       │  3. KEK.esl  →  KEK
       │  4. PK.esl   →  PK   (last, unsigned `-e`, same as the others)
       ▼
  User Mode (SetupMode = 0) immediately
  SecureBoot = 1 and image check on next reboot
```

**Owner host — build ESLs:**

```bash
uuidgen --random > GUID.txt
SIGNATURE_OWNER="$(< GUID.txt)"
cert-to-efi-sig-list -g "$SIGNATURE_OWNER" PK.crt  PK.esl
cert-to-efi-sig-list -g "$SIGNATURE_OWNER" KEK.crt KEK.esl
cert-to-efi-sig-list -g "$SIGNATURE_OWNER" db.crt  DB.esl
```

dbx may be empty or a SHA-256 ESL of a revoked digest. Concatenate multiple KEK or db certificates into one ESL before enroll if the owner has more than one.

**Device — enroll** (Setup Mode, unsigned ESL). Use `-e` for all four variables, including PK:

```bash
efi-updatevar -e -f DBx.esl dbx
efi-updatevar -e -f DB.esl  db
efi-updatevar -e -f KEK.esl KEK
efi-updatevar -e -f PK.esl  PK
```

`-e` prepends an empty AUTH2 header (no PKCS#7) and writes the ESL. That is not a signed AUTH2. Do not run `sign-efi-sig-list` on the first PK, and do not enroll a PK-signed `PK.auth` during claim.

After PK is written, further PK/KEK/db/dbx changes must be AUTH2 as in section 6. A reboot is not required to finish the four enroll writes. A reboot is required before `SecureBoot=1` and before OVMF enforces db on the bootloader.

### 5.4 Verify ownership claim
Immediately after PK (no reboot required for this check):

```bash
od -An -tu1 -j4 -N1 \
  /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c
# expect 0  User Mode

efi-readvar PK
efi-readvar KEK
efi-readvar db
```

If PK is missing, the platform is still in Setup Mode. Do not treat KEK/db enrollment alone as a completed claim.

Then reboot. OVMF computes `SecureBoot` at POST:

```bash
od -An -tu1 -j4 -N1 \
  /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c
# expect 1  Secure Boot enabled
```

## 6 UEFI key management

This section is **after ownership claim** (User Mode). Setup Mode claim enrollment is section 5.3. Private keys stay on the owner host. Only public certificates (ESL / AUTH2) are written to the device.

The key management involves following the functional area
1. Generation of keys and authenticated variable
2. Add the key to the UEFI database
3. Remove the key to the UEFI database
4. Revoke keys
5. Show key list from UEFI database

### 6.1 Generation of keys and authenticated variable
#### asymmetric key creations
The secure boot key and authenticate variable creation happens outside of the device.

```
Sample example of key creation:

openssl req -newkey rsa:2048 -nodes -keyout PK.key -new -x509 -sha256 -days 365 -subj "/CN=Platform key/" -out PK.crt
openssl req -newkey rsa:2048 -nodes -keyout KEK.key -new -x509 -sha256 -days 365 -subj "/CN=Key Exchange Key/" -out KEK.crt
openssl req -newkey rsa:2048 -nodes -keyout db.key -new -x509 -sha256 -days 365 -subj "/CN=Database key/" -out db.crt
```
The private keys are kept secretly and used during image signing. The public keys are used to verify images signed by private keys. Public keys are wrapped in the x509 format of the certificate. These public certificates are enrolled in the UEFI key database by the platform owner.

#### Authenticated variable creation
After claim, User Mode writes are AUTH2. `cert-to-efi-sig-list -g` is the owner-chosen **SignatureOwner**. `sign-efi-sig-list -g` is the UEFI **VendorGuid** for that variable (`EFI_GLOBAL_VARIABLE` `8be4df61-93ca-11d2-aa0d-00e098032b8c` for PK/KEK; `EFI_IMAGE_SECURITY_DATABASE` `d719b2cb-3d3a-4596-a3bc-dad00e67656f` for db/dbx).

```
Sample example of authenticated variable creation:

uuidgen --random > GUID.txt
SIGNATURE_OWNER="$(< GUID.txt)"
VENDOR_GUID_GLOBAL=8be4df61-93ca-11d2-aa0d-00e098032b8c
VENDOR_GUID_IMAGE=d719b2cb-3d3a-4596-a3bc-dad00e67656f

**PK authenticated variable:**
cert-to-efi-sig-list -g "$SIGNATURE_OWNER" PK.crt PK.esl
sign-efi-sig-list -g "$VENDOR_GUID_GLOBAL" -k PK.key -c PK.crt PK PK.esl PK.auth

**KEK authenticated variable:**
cert-to-efi-sig-list -g "$SIGNATURE_OWNER" KEK.crt KEK.esl
sign-efi-sig-list -g "$VENDOR_GUID_GLOBAL" -k PK.key -c PK.crt KEK KEK.esl KEK.auth

**Db authenticated variable:**
cert-to-efi-sig-list -g "$SIGNATURE_OWNER" db.crt db.esl
sign-efi-sig-list -g "$VENDOR_GUID_IMAGE" -k KEK.key -c KEK.crt db db.esl db.auth
```

### 6.2 Enrollment of authenticated variables into the device
After claim, copy only the AUTH2 file to the device. Do not copy `PK.key` or `KEK.key`.

1. Copy the generated authenticated variable (Ex. KEK.auth, db.auth) to the device
2. Use CLI / `efi-updatevar -f` to send the authenticated variable to UEFI firmware.
3. UEFI firmware checks the trust source and integrity of authenticated variables and enrolls into UEFI database.
4. The system requires a reboot to activate the keys for boot verification.

### 6.3 Remove keys from UEFI database
Removal of a certificate is an AUTH2 **update** of the remaining list, built off the device. Signing uses `KEK.key` on the owner host. Only `DB-new.auth` is copied to the DUT.

**Warning:** Removing a db certificate that currently signs the running bootloader (shim) is potentially destructive if `SecureBoot=1`. The next reboot will fail OVMF image verification. The running NOS is not killed immediately. Linux CLI cannot recover that state. Recovery is OVMF Setup (clear PK / enroll from firmware Setup). Do not remove the only signer of the installed bootloader until a replacement signer is in db.

```
Sample example of authenticated variable creation for removal of the key from the signature database list:
E.g The UEFI database has 3 entries of keys and one of them to be removed here

1. Read the db key list from UEFI DB.
   efi-readvar -v db -o DB-orig.esl
2. Convert signature list to individual certs. This command extracts DB-orig-1.der DB-orig-2.der DB-orig-3.der so on key files
   sig-list-to-certs DB-orig.esl DB-orig
3. Convert each of the certs into pem format
   openssl x509 -inform der -in db-orig-1.der -out db-orig-1.pem
   openssl x509 -inform der -in db-orig-2.der -out db-orig-2.pem
   openssl x509 -inform der -in db-orig-3.der -out db-orig-3.pem
4. Removal of db-orig-2.pem to be discarded
5. Convert db-orig-1.pem and db-orig-3.pem to esl format
   cert-to-efi-sig-list -g "$SIGNATURE_OWNER" db-orig-1.pem db-orig-1.esl
   cert-to-efi-sig-list -g "$SIGNATURE_OWNER" db-orig-3.pem db-orig-3.esl
6. Concatenate these two esl files
   cat db-orig-1.esl db-orig-3.esl > DB-new.esl
7. Create authenticated variable and sign it on the owner host
   sign-efi-sig-list -g "$VENDOR_GUID_IMAGE" -k KEK.key -c KEK.crt db DB-new.esl DB-new.auth
8. Copy DB-new.auth to the system and use CLI to update UEFI database
   sudo config platform security uefi update db DB-new.auth
```

### 6.4 Revoke keys
Revoking a key from the UEFI database is done when the previously trusted key is no longer trustworthy. This action is taken when a key's security has been compromised.
It is achieved by inserting the authenticated variable for the compromised key into the forbidden key list (dbx). Firmware checks dbx **before** db. A dbx match refuses the image even if the same cert is still in db.

**Warning:** Revoke is potentially destructive. If that cert or hash currently signs the running boot chain and `SecureBoot=1`, the next reboot will fail OVMF verification. That is not a hardware brick. Linux CLI cannot recover it. Recovery is OVMF Setup (clear PK / enroll from firmware Setup), which returns Setup Mode. After a compromise, prefer: enroll the replacement db cert, then append the old cert/hash to dbx, then remove it from db.

```
Sample example:
If db-orig-1.pem is compromised then generate an authenticated variable for db-orig-1.pem
1. Convert ESL of pem cert.
   cert-to-efi-sig-list -g "$SIGNATURE_OWNER" db-orig-1.pem db-orig-1.esl
2. Create authenticated variable on the owner host
   sign-efi-sig-list -g "$VENDOR_GUID_IMAGE" -k KEK.key -c KEK.crt -a dbx db-orig-1.esl DB-revoke.auth
3. Copy DB-revoke.auth to the system and use CLI to update the UEFI database
   sudo config platform security uefi update dbx DB-revoke.auth
```

### 6.5 Show keys
This is to display the PK, KEK, db, and dbx key lists, and `SetupMode` / `SecureBoot`.

```bash
efi-readvar PK
efi-readvar KEK
efi-readvar db
efi-readvar dbx
```

## 7 SONIC implementation
SONiC talks to OVMF the same way Linux does on QEMU: **efi-readvar**, **efi-updatevar**, and **efivarfs**. No vendor plugin.

- show / export: `efi-readvar` (efivarfs for `SetupMode` / `SecureBoot`)
- enroll in Setup Mode: `efi-updatevar -e` with an unsigned ESL
- append / update / remove / revoke in User Mode: `efi-updatevar -f` with AUTH2

The Linux kernel provides efivarfs, which exposes EFI runtime variables as files. Mount it to access the variables:

```
sudo mount -t efivarfs none /sys/firmware/efi/efivars

Ex: UEFI key variables represented as sysfs file

/sys/firmware/efi/efivars/PK-8be4df61-93ca-11d2-aa0d-00e098032b8c
/sys/firmware/efi/efivars/KEK-8be4df61-93ca-11d2-aa0d-00e098032b8c
/sys/firmware/efi/efivars/db-d719b2cb-3d3a-4596-a3bc-dad00e67656f
/sys/firmware/efi/efivars/dbx-d719b2cb-3d3a-4596-a3bc-dad00e67656f
```

<img src="https://github.com/sacnaik/SONiC/assets/25231205/1566c4d1-098f-4bde-b830-289e793e168d" width="400" hight="400">

On Linux/OVMF, efivarfs files are often `FS_IMMUTABLE`. `efi-updatevar` fails until the immutable bit is cleared. The CLI will clear it around the write when it can; otherwise it returns that error.

## 8 SONiC CLI commands

The CLI is apply-only. It takes a file and calls `efi-readvar` / `efi-updatevar`. It does not create AUTH2, does not take a private key, and does not retry on firmware reject.

Writes need `sudo` / config privilege. Firmware accepts or rejects the payload.

```
show platform security uefi status
show platform security uefi variables all
show platform security uefi variables pk
show platform security uefi variables kek
show platform security uefi variables db
show platform security uefi variables dbx

config platform security uefi enroll <var> <file.esl>
config platform security uefi update <var> <file.auth>
```

`status` prints `SetupMode` and `SecureBoot` (`efi-readvar` does not). `enroll` is Setup Mode unsigned ESL (`efi-updatevar -e`). `update` is User Mode AUTH2 (`efi-updatevar -f`). `<var>` is one of `pk`, `kek`, `db`, `dbx`.

Return values follow normal SONiC CLI:

- success: exit 0. show prints the variables (or SetupMode/SecureBoot for status).
- failure: non-zero exit and an error on stderr. The CLI surfaces the efitools / firmware reason.

Expected failures for enroll/update: missing file; not root; efivarfs not mounted; wrong mode (unsigned ESL after PK, or AUTH2 in Setup Mode); AUTH2 signature rejected (wrong PK/KEK, timestamp not newer, malformed AUTH2); immutable efivarfs; OVMF reject.

## 9 Test considerations
The sonic-mgmt can cover UEFI key management including at least:

1. Factory default: `SetupMode=1`, `SecureBoot=0`, PK empty (section 4).
2. Ownership claim: enroll dbx, db, KEK, then PK with no reboot between writes; `SetupMode=0` and keys present immediately; after reboot `SecureBoot=1` (section 5).
3. After claim, unsigned ESL writes are rejected.
4. Add, update, remove, and revoke AUTH2 for PK, KEK, db, and dbx (section 6).
5. Remove/revoke of an in-use db signer is documented as destructive; next boot fails verification when `SecureBoot=1`.
