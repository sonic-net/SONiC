<!-- omit in toc -->
# High Level Design Document

***Revision***

|  Rev  | Date           | Author      | Change Description |
| :---: | :------------: | :---------: | ------------------ |
|  0.1  |   08/25/2023   | Sachin Naik | Initial version    |

<!-- omit in toc -->
## Table of Contents
- [About this Manual](#about-this-manual)
- [Abbreviation](#abbreviation)
- [1 Requirements Overview](#1-requirements-overview)
- [2 Overview](#2-Overview)
- [3 UEFI components](#3-UEFI-components)
  - [3.1 UEFI keys](#31-UEFI-keys)
  - [3.2 UEFI key management](#32-UEFI-key-management)
  - [3.3 Authenticated variable](#33-Authenticated-variable)
- [4 UEFI key management](#4-UEFI-key-management)
  - [4.1 Generation of keys](#41-Generation-of-keys)
  - [4.2 Enrollment of keys](#42-Enrollment-of-keys)
  - [4.3 Modify key database](#43-Modify-key-database)
  - [4.4 Revoke keys](#44-Revoke-keys)
  - [4.5 Show keys](#45-Show-keys)  
- [5 SONIC implementation](#5-SONIC-implementation)
  - [5.1 Plugin class](#51-Plugin-class)
  - [5.2 OVMF based platform can use Linux implementation to access UEFI variable](#52-OVMF-based-platform-can-use-Linux-implementation-to-access-UEFI-variable)
- [6 SONiC CLI commands](#6-SONiC-CLI-commands)
- [7 Test considerations](#7-Test-considerations)


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


## 1 Requirements
Sonic is the most popularly growing open-source network operating system and runs on switching hardware from multiple vendors. Some of this modern switching hardware implements a hardware root of trust and UEFI firmware which helps establish a secure boot in the system. Most of the system owners would like to manage their own UEFI keys according to their own policy such as periodically changing the secure boot keys, changing ownership, etc. This requires SONiC to access UEFI keys to perform the following primitive actions.
1. Show secure boot keys
2. Add, remove, and revoke secure boot keys.

## 2 Overview
The UEFI secure boot feature is introduced in UEFI spec version 2.3.1 onwards. The UEFI secure boot provides a mechanism to securely verify the image integrity and authenticity before loading the image into the system. The spec also provides general details about how UEFI keys should be managed. The implementation may vary for different UEFI firmware. 

## 3 UEFI components

### 3.1 UEFI firmware
Typically the UEFI is a modern replacement for traditional BIOS. The UEFI implementation may vary from system to system but it has to follow the core principles mentioned in the UEFI spec. This document references the OVMF(Open Virtual Machine Firmware) UEFI implementation, which is the open UEFI firmware available for virtual machines like QEMU and KVM.

### 3.2 UEFI keys
UEFI keys are types of UEFI variables. These are cryptographic keys used in Unified Extensible Firmware Interface (UEFI) firmware. These are asymmetric cryptographic keys that come with public and private key pairs. The private keys are used for signing data and public keys are enrolled in the UEFI device for verifying signed data. 

There are multiple keys involved in the UEFI secure boot implementations. The platform owner sets the policies around these keys. 

![image](https://github.com/sacnaik/SONiC/assets/25231205/fdf6a164-6153-4c14-ba6d-b8d30475e390)

**1.	Platform Key(PK):** The PK is used for establishing a trust relationship between the platform owner and the platform UEFI firmware. The enrollment of the public PK key to the device happens early in manufacturing or initial provisioning time. The private part of the PK.key is used later to change the platform ownership and manage other keys in the UEFI firmware.

**2.	Key Exchange Key(KEK)**: KEK is used for establishing trust between NOS and the platform. It is used for enrolling NOS secure boot keys in the allowed key database(Db). The public part of the KEK is enrolled in the device and the private part is used for authorizing access to the signature key database(Db).
   
**3.	Signature Database (Db):** It contains secure boot verification keys that are used to verify the signed image artifacts during system boot(Ex: bootloader and kernel). 
   
**4.	Forbidden Signature Database(Dbx):** These contain keys that are revoked. These keys are used during the secure boot process to prevent the booting of certain bootloaders or images which are signed by the private part of these keys.

### 3.3 Authenticated variable
These are a special type of UEFI variable that supports cryptographic authentication and integrity verification. The authenticates variable enables a secure way of storing and accessing UEFI variables within the UEFI environment and ensures that the UEFI variable remains tamper-proof and authentic.  Since authenticated variables are signed objects, the UEFI firmware can verify them before accessing or updating them.

## 4 UEFI key management

The key management involves following the functional area
1. Generation of keys and authenticated variable
2. Add the key to the UEFI database
3. Remove the key to the UEFI database
4. Revoke keys
5. Show key list from UEFI database

### 4.1 Generation of keys and authenticated variable
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
```
Sample example of authenticated variable creation:

uuidgen --random > GUID.txt

**PK authenticated variable:**
openssl x509 -outform DER -in PK.crt -out PK.cer
cert-to-efi-sig-list -g "$(< GUID.txt)" PK.crt PK.esl
sign-efi-sig-list -g "$(< GUID.txt)" -k PK.key -c PK.crt PK PK.esl PK.auth

**KEK authenticated variable:**
openssl x509 -outform DER -in KEK.crt -out KEK.cer
cert-to-efi-sig-list -g "$(< GUID.txt)" KEK.crt KEK.esl
sign-efi-sig-list -g "$(< GUID.txt)" -k PK.key -c PK.crt KEK KEK.esl KEK.auth

**Db authenticated variable:**
openssl x509 -outform DER -in db.crt -out db.cer
cert-to-efi-sig-list -g "$(< GUID.txt)" db.crt db.esl
sign-efi-sig-list -g "$(< GUID.txt)" -k KEK.key -c KEK.crt db db.esl db.auth
```

### 4.2 Enrollment of authenticated variables into the device
The enrollment interface depends on where the keys are stored. The UEFI keys enrollment follows a specific policy. UEFI keys are PK, KEK, db and dbX. The enrollment of PK depends on access over UEFI FW's mode(e.g.: Setup mode, User mode, etc.). Then the owner of PK can enroll KEK since KEK enrollment requires authenticated variables signed by PK. 
1. Copy the generated authenticated variable(Ex. KEK.auth, db.auth) to the device
2. Use CLI to send the authenticated variable to UEFI firmware.
3. UEFI firmware checks the trust source and integrity of authenticated variables and enrolls into UEFI database.
4. The system requires a reboot to activate the keys for use.

### 4.3 Remove keys from UEFI database
For removal of keys requires the removal of an authenticated variable outside of the system. 

````
Sample example of authenticated variable creation for removal of the key from the signature database list:
E.g The UEFI database has 3 entries of keys and one of them to be removed here

1. Read the db key list from UEFI DB. 
   efi-readvar -v Db -o DB-orig.esl 
2. Convert signature list to individual certs. This command extracts DB-orig-1.der DB-orig-2.der DB-orig-3.der so on key files
   sig-list-to-certs DB-orig.esl DB-orig
3. Convert each of the certs into pem format
   openssl x509 -inform der -in db-orig-1.der -out db-orig-1.pem
   openssl x509 -inform der -in db-orig-2.der -out db-orig-2.pem
   openssl x509 -inform der -in db-orig-3.der -out db-orig-3.pem
4. Removal of db-orig-2.pem to be discarded
5. Convert db-orig-1.pem and db-orig-3.pem to esl format
   cert-to-efi-sig-list -g <GUID> db-orig-1.pem db-orig-1.esl
   cert-to-efi-sig-list -g <GUID> db-orig-3.pem db-orig-3.esl
6. Concatenate these two esl files 
   cat db-orig-1.esl db-orig-3.esl > DB-new.esl
7. Create authenticated variable and sign it
   sign-efi-sig-list -g "<GUID>" -k KEK.key -c KEK.crt db DB-new.esl DB-new.auth
8. Copy DB-new.auth to the system and use CLI to update UEFI database

````

### 4.4 Revoke keys
Revoking a key from the UEFI database is done when the previously trusted key is no longer trustworthy. This action is taken when a key's security has been compromised.
It is achieved by inserting the authenticated variable for the compromised key into the forbidden key list(DBx). 

```
Sample example:
If db-orig-1.pem is compromised the generate an authenticated variable for db-orig-1.pem
1. Convert ESL of pem cert.
   cert-to-efi-sig-list -g <GUID> db-orig-3.pem db-orig-3.esl
2. Create authenticated variable
   sign-efi-sig-list -g "<GUID>" -k KEK.key -c KEK.crt dbx db-orig-3.esl DB-revoke.auth
3. Copy DB-revoke.auth to the system and use CLI to update the UEFI database
```

### 4.5 Show keys
This is to display the PK, KEK, DB, and DBx key lists.

## 5 SONIC implementation
The access of UEFI variables may vary from platform to platform depending on the specific implementation of UEFI firmware. Sonic will provide a common layer for accessing these variables and vendors can implement platform-specific parts. The SONIC will provide a plugin Python for vendors to implement these APIs and integrate them with the SONiC generic layer.

### 5.1 Plugin class

![image](https://github.com/sacnaik/SONiC/assets/25231205/a42cd039-0675-4a71-84e0-bce00eb2ca9d)

### 5.2 OVMF based platform can use Linux implementation to access UEFI variable
The Linux kernel provides a standard mechanism to interact with UEFI variables. It provides efivarfs filesystem that exposes the EFI runtime variables as a file. In order to manage these efi variables over sysfs requires mounting efivarfs filesystem. This enables users to access these UEFI variables like a file.


<img src="https://github.com/sacnaik/SONiC/assets/25231205/1566c4d1-098f-4bde-b830-289e793e168d" width="400" hight="400">


```
sudo mount -t efivarfs none /sys/firmware/efi/efivars

Ex: UEFI key variables represented as sysfs file

/sys/firmware/efi/efivars/PK-<GUID>
/sys/firmware/efi/efivars/KEK-<GUID>
/sys/firmware/efi/efivars/DB-<GUID>
/sys/firmware/efi/efivars/DBX-<GUID>
```
The platform plugin for this OVMF type UEFI can use either sysfs or efi-readvar and efi-updatevar to implement getVariable() and setVariable() methods.   
   

## 6 SONiC CLI commands
```
1. show platform security uefi variables all
2. show platform security uefi variables pk
3. show platform security uefi variables kek
4. show platform security uefi variables db
5. show platform security uefi variables dbx

1. platform security uefi variables update pk  <file>
2. platform security uefi variables update kek <file>   
3. platform security uefi variables update db  <file>
4. platform security uefi variables update dbx <file>  
```

## 7 Test considerations
The sonic-mgmt can cover UEFI key management such as adding, updating, removing, and revoking UEFI keys.



