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
| dbx          | Forbidden Signture Key Database              |
| UEFI         | Unified Extensible Firmware Interface        |
| RoT          | Root of Trust                                |
| TPM          | Trusted platform module                      |


## 1 Requirements
SONiC is the most popularly growing open-source network operating system and runs on switching hardware from multiple vendors. Some of this modern switching hardware implements a hardware root of trust and UEFI firmware which helps establish a secure boot in the system. Most of the system owners would like to manage their own UEFI keys according to their own policy such as periodically changing the secure boot keys, changing ownership, etc. This requires SONiC to access UEFI keys to perform the following primitive actions.
1. Show secureboot keys
2. Add, remove, update and revoke secureboot keys.

## 2 Ovierview
How  UEFI secure boot should be implemented is specified in UEFI spec 2.0 onwards. It is widely accepted on various Linux-based distributions including Debian distribution. The UEFI secure boot provides a mechanism to securely verify the image integrity and authenticity before loading into the system. The spec also provides details about how UEFI keys should be managed in the UEFI firmware.

Typically the UEFI is a modern replacement for traditional BIOS. Firmware. The UEFI implementation may vary from system to system but it has to follow the core principles mentioned in the spec. The document references the OVMF UEFI implementation, which is open UEFI firmware available for virtual machines QEMU.

## 3 UEFI components

### 3.1 UEFI firmware
1. UEFI firmware(Ex: UEFI BIOS) is signed and supplied by hardware vendors.
2. Hardware implemented root of trust(Ex: TPM chip etc) that verifies UEFI firmware before running into CPU.
3. Root of trust is the immutable hardware part and it is the most trusted part of the system.
4. UEFI firmware verifies bootloader(shimx64.efi) of SONiC OS image against keys present in UEFI key database.  
5. UEFI firmware manages UEFI keys database and verifies any update to these databases. 

### 3.2 UEFI keys
UEFI keys are cryptographic keys used in Unified Extensible Firmware Interface (UEFI) enabled systems. Typically used for secure boot purposes.  These are asymmetric cryptographic keys that come with public and private key pairs. The private keys are used for signing data and public keys are enrolled in the UEFI device. The device's secure boot uses these public keys to verify the signed bootloader and kernel during system boot time and protect early boot with any malware. Secure boot ensures integrity and trust source of the image.

There are multiple keys involved in the UEFI secure boot implementations. The platform owner sets the policies around these keys. The UEFI firmware and its interface are typically controlled by hardware vendors depending on their UEFI firmware implementations.  However, the platform owner must be able to manage these keys which are enrolled in the UEFI devices in order to securely boot their NOS.

<img src="https://wwwin-github.cisco.com/storage/user/4864/files/250b7543-0356-42a0-a203-02c07e64718c" width="600" hight="800">

**1.	Platform Key(PK):** It’s a root of trust key that signs all other keys in the UEFI to be added. Technically PK is used to establish a trust relationship between the device owner and device UEFI firmware. The public part of the PK is enrolled in the device UEFI firmware. The enrollment happens early in manufacturing or initial provisioning time. The private part of the PK.key is used to change the device ownership by changing the existing PK and also to sign the KEK to enroll or update KEK in the device.

**2.	Key Exchange Key(KEK)**: KEK is used to establish trust between NOS and the device. It is used for enrolling secure boot or some other NOS-specific keys in the allowed key list database(Db). The public part of the KEK is enrolled in the device and the private part is used to sign the keys that are enrolled in the key list database(Db).
   
**3.	Signature Database (Db):** It contains secureboot verification keys that are used to verify the signed image artifacts during system boot(Ex: bootloader and kernel). 
   
**4.	Forbidden Signature Database(Dbx):** These contain keys that are revoked. It is used during the secure boot process to prevent certain bootloaders or images from being loaded if their signature is verified with the keys that are present in this database.

### 3.3 Authenticated variable
These are a special type of UEFI variable that supports cryptographic authentication and integrity verification. The authenticates variable enables a secure way of storing and accessing EFI variables within the UEFI environment and ensures that the UEFI variable remains tamper-proof and authentic.  Since authenticated variables are signed objects, the UEFI firmware can verify them before accessing or updating them.

```
Sample example how authenticated variables supports secure way of add, update, remove and revoke UEFI keys.

uuidgen --random > GUID.txt

**PK authenticated variable:**
openssl req -newkey rsa:4096 -nodes -keyout PK.key -new -x509 -sha256 -days 3650 -subj "/CN=Platform key/" -out PK.crt
openssl x509 -outform DER -in PK.crt -out PK.cer
cert-to-efi-sig-list -g "$(< GUID.txt)" PK.crt PK.esl
sign-efi-sig-list -g "$(< GUID.txt)" -k PK.key -c PK.crt PK PK.esl PK.auth

**KEK authenticated variable:**
openssl req -newkey rsa:4096 -nodes -keyout KEK.key -new -x509 -sha256 -days 3650 -subj "/CN=Key Exchange Key/" -out KEK.crt
openssl x509 -outform DER -in KEK.crt -out KEK.cer
cert-to-efi-sig-list -g "$(< GUID.txt)" KEK.crt KEK.esl
sign-efi-sig-list -g "$(< GUID.txt)" -k PK.key -c PK.crt KEK KEK.esl KEK.auth

**Db authenticated variable:**
openssl req -newkey rsa:4096 -nodes -keyout db.key -new -x509 -sha256 -days 3650 -subj "/CN=Database key/" -out db.crt
openssl x509 -outform DER -in db.crt -out db.cer
cert-to-efi-sig-list -g "$(< GUID.txt)" db.crt db.esl
sign-efi-sig-list -g "$(< GUID.txt)" -k KEK.key -c KEK.crt db db.esl db.auth
```
Using above example one should able to create authenticated variable to add, remove, update and revoke UEFI keys from the UEFI database.

## 4 UEFI key management

The key management involves following functional area
1. Generation of keys
2. Enroll keys into Machine
3. Update, remove and add new keys into the key database.
4. Revoke keys
5. Show keys from the machine.

### 4.1 Generation of keys
The secure boot key creation happens outside of the device via openSSL or some other key generation. 
```
openssl req -newkey rsa:4096 -nodes -keyout PK.key -new -x509 -sha256 -days 3650 -subj "/CN=Platform key/" -out PK.crt
openssl req -newkey rsa:4096 -nodes -keyout KEK.key -new -x509 -sha256 -days 3650 -subj "/CN=Key Exchange Key/" -out KEK.crt
openssl req -newkey rsa:4096 -nodes -keyout db.key -new -x509 -sha256 -days 3650 -subj "/CN=Database key/" -out db.crt
```
The private keys are kept secretly and used during image signing. The public keys are used to verify images signed by private keys. Public keys are wrapped with x509 format of certificate. These public certificates are enrolled in the SHIM or UEFI key database by the machine owner.

### 4.2 Enrollment of keys
The enrollment interface depends on where the keys are stored. The UEFI keys enrollment follows specific policy. UEFI keys are PK, KEK, db and dbX. The enrollment of PK depends on access over UEFI FW's mode(Ex: Setup mode, User mode etc.). Then the owner of PK can enroll KEK since KEKs enrollment requires that KEK and create authenticated variables and it by PK.

````
Ex: Enroll KEK
sign-efi-sig-list -t "$(date --date='1 second' +'%Y-%m-%d %H:%M:%S')" -k PK.key -c PK.crt KEK KEK.esl KEK.auth

Use the hardware vendor provided interface to enroll KEK.auth
````
Similar principle used for enrolling DB keys. The DB enrollment variable should be created then signed either by PK and KEK. Typically KEK is used to avoid frequent access to PK private keys.

### 4.3 Modify key database
For UEFI key database modification, requires authenticated variables to modify.
````
Examples: 

To add  DB key in UEFI database following are typical workflow followed

       # Create key:
       openssl req -subj "/CN=SecBoot db cert/"  -new -x509 -newkey rsa:2048 -nodes -days 730 -outform PEM -keyout "db.key"  -out "db.pem"
       
       # Conver to signature list 
       cert-to-efi-sig-list -g <GUID> db.pem  db.esl
       
       # Sign keys using KEK
       sign-efi-sig-list -g <GUID> -c KEK.pem -k KEK.key db  db.esl  db.auth
       
       # Update UEFI database
       efi-updatevar -k KEK.key -g <GUID> -f db.auth  db
 
````

### 4.4 Revoke keys

The revoke key is a mechanism to permanently disallow any image signed by the private key whose public key is present in DBx of UEFI database.

### 4.5 Show keys
This is to display the PK, KEK, DB and DBx key lists.

## 5 SONIC implementation
The access of UEFI variables may vary from platform to platform depending on the specific implementation of UEFI firmware. Sonic will provide a common layer for accessing these variables and vendors can implement platform specific parts. The SONIC will provide a plugin Python for vendors to implement these APIs and integrate them with the SONiC generic layer.

### 5.1 Plugin class

<img src="https://wwwin-github.cisco.com/storage/user/4864/files/2591894f-22f6-4275-9a8f-1e5ca241753b" width="150" height="150">
 

### 5.2 OVMF based platform can use Linux implementation to access UEFI variable
The Linux kernel provides a standard mechanism to interact with UEFI variables. It provides efivarfs filesystem that exposes the EFI runtime variables as a file. In order to manage these efi variables over sysfs requires mounting efivarfs filesystem. This enables users to access these UEFI variables like a file.

![image](https://wwwin-github.cisco.com/storage/user/4864/files/8739b223-6b2a-4f96-b42c-7fa0deec5707)

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
The sonic-mgmt can cover UEFI keymanagement such as add, update, remove and revoke UEFI keys.



