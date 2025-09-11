# FIPS 140-3 compliance for SONiC MACsec

## Table of Contents

### 1\. Revision

| Rev   |   Date     |     Author         | Change Description |
| ----- | ---------  | -----------------  |  ----------------- |
| 0.1   | 2025-07-31 | Rajshekhar Biradar |  Initial version   |

### 2\. Scope

SONiC requires Federal Information Processing Standards (FIPS) 140-3 compliance for MACsec deployments in high-security environments. This includes:

- Secure Key Management: Centralized KEK (Key Encryption Key) distribution for MACsec SAK (Secure Association Key) encryption  
- FIPS POST: Pre-Operational Self-Test (POST) validation for cryptographic and Random Number Generator (RNG) modules

This document covers the design, implementation, and integration aspects of KMS and FIPS POST within the SONiC ecosystem. Switch level SONiC FIPS POST is already covered in separate HLD [here](https://github.com/sonic-net/SONiC/pull/2034/files).

### 3\. Definitions/Abbreviations

| Term | Definition |
| :---- | :---- |
| KMS | Key Management Service |
| KEK | Key Encryption Key \- Master key used to encrypt other keys |
| SAK | Secure Association Key \- Used in MACsec for data encryption |
| MACsec | Media Access Control Security (IEEE 802.1AE) |
| IPC | Inter-Process Communication |
| HSM | Hardware Security Module |
| TPM | Trusted Platform Module |
| GCM | Galois/Counter Mode \- Authenticated encryption mode |
| IV | Initialization Vector |
| TAG | Authentication tag for GCM mode |
| FIPS | Federal Information Processing Standards |
| RNG | Random Number Generator |
| DRBG | Deterministic Random Bit Generator |
| POST | Pre-Operational Self-Test  |

### 4\. Overview

The SONiC MACsec FIPS HLD defines a comprehensive security framework that enables FIPS 140-3 compliance for MACsec deployments in SONiC network devices. The primary goal is to establish a validated cryptographic infrastructure that meets federal security standards through secure key management, cryptographic module validation, and operational compliance monitoring. 

KMS is a generic library which provides a secure key management infrastructure for SONiC network devices. The primary goal is to protect sensitive cryptographic material (example MACsec SAKs) by centralizing key operations within the library using client server architecture. KMS is required to achieve FIPS compliance in SONiC FIPS mode by ensuring cryptographic keys are never stored in plaintext outside of the secure boundary.

POST compliance ensures that cryptographic modules in SONiC meets FIPS 140-3 requirements before processing any MACsec operations. The primary goal is to validate the integrity and functionality of cryptographic hardware and software components during system initialization, preventing the use of potentially compromised or non-compliant crypto modules. 

### 5\. Requirements

#### 5.1. KMS Requirements:

- Secure encryption/decryption of key material using KEK  
- Support for multiple concurrent client connections  
- Unix domain socket communication for IPC  
- KEK must never be exposed outside process (server/client mode)  
- All cryptographic operations use AES-256-GCM for encryption/decryption  
- All random number generation use CTR\_DRBG/HASH\_DRBG/HMAC\_DRBG with security strength 256bits  
- Secure memory handling using madvise(), mlock(), and explicit\_bzero()  
- Authentication of all client-server communications  
- Secure handling of process termination and zeroization

#### 5.2. FIPS POST Requirements:

- MACsec configuration must be blocked until POST validation passes.  
- Use FIPS POST results provided by OpenSSL/SymCrypt for KMS and MACsec control-plane POST.  
- Use SAI FIPS POST results from the switch for data-plane POST.  
- Log the outcome of FIPS POST operations via syslog.

### 6\. Architecture Design

KMS and FIPS POST integrate into the existing SONiC architecture without requiring fundamental changes to the core system. It operates as a supporting library and service that enhances security for existing components.

#### 6.1. KMS Architecture Integration  Integration methods

- KMS operates as a shared library linked into existing processes  
- syncd process runs in server-mode (hosts the KEK and server thread)  
- Multiple wpa\_supplicant processes in macsec container run in client-mode  
- Communication via Unix domain sockets (standard Linux IPC mechanism)  
- Single server supports multiple concurrent client connections

KMS fits into the existing SONiC architecture as follows:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SONiC Host System                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌────────────────────────────────────────────────┐  │
│  │   syncd         │    │               macsec                           │  │
│  │   Container     │    │              Container                         │  │
│  │                 │    │                                                │  │
│  │ ┌─────────────┐ │    │ ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │ │   syncd     │ │    │ │ wpa_supplicant  │  │  wpa_supplicant     │   │  │
│  │ │   process   │ │    │ │   process #1    │  │    process #2       │   │  │
│  │ │             │ │    │ │  (Ethernet0)    │  │   (Ethernet4)       │   │  │
│  │ │ ┌─────────┐ │ │    │ │                 │  │                     │   │  │
│  │ │ │libkms   │ │ │    │ │ ┌─────────────┐ │  │ ┌─────────────────┐ │   │  │
│  │ │ │(SERVER) │ │ │    │ │ │   libkms    │ │  │ │     libkms      │ │   │  │
│  │ │ │         │ │ │    │ │ │  (CLIENT)   │ │  │ │    (CLIENT)     │ │   │  │
│  │ │ │ ┌─────┐ │ │ │    │ │ └─────────────┘ │  │ └─────────────────┘ │   │  │
│  │ │ │ │ KEK │ │ │ │    │ └─────────────────┘  └─────────────────────┘   │  │
│  │ │ │ │Store│ │ │ │    │                                                │  │
│  │ │ │ └─────┘ │ │ │    │ ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │ │ │ ┌─────┐ │ │ │    │ │ wpa_supplicant  │  │  wpa_supplicant     │   │  │
│  │ │ │ │Srvr │ │ │ │    │ │   process #3    │  │    process #N       │   │  │
│  │ │ │ │Thrd │ │ │ │    │ │  (Ethernet8)    │  │   (EthernetX)       │   │  │
│  │ │ │ └─────┘ │ │ │    │ │                 │  │                     │   │  │
│  │ │ └─────────┘ │ │    │ │ ┌─────────────┐ │  │ ┌────────────────┐  │   │  │
│  │ └─────────────┘ │    │ │ │   libkms    │ │  │ │     libkms     │  │   │  │
│  └─────────────────┘    │ │ │  (CLIENT)   │ │  │ │    (CLIENT)    │  │   │  │
│           │             │ │ └─────────────┘ │  │ └────────────────┘  │   │  │
│           │             │ └─────────────────┘  └─────────────────────┘   │  │
│           │             └─────────────────────────────────────────────── ┘  │
│           │                                      │                          │
│           └──────────────────────────────────────┘                          │
│                                                                             │
│                    Unix Domain Socket (supports multiple clients)           │
└─────────────────────────────────────────────────────────────────────────────┘
```


#### 6.2. POST Architecture Integration

The POST validation logic will be integrated into the KMS library and will be triggered as part of the library initialization process.

                    
```
  ┌──────────────────────────────────────────────────────────────┐  
  │                    MACsec/Syncd                              │  
  │    ┌─────────────────────────────────────────────────────┐   │  
  │    │                   KMS Library                       │   │  
  │    │  ┌───────────────────┐    ┌───────────────────────┐ │   │  
  │    │  │ **FIPS POST**     │    │  Cryptographic Key    │ │   │  
  │    │  │ **Validation**    │    |  Management and       │ │   │  
  │    │  |                   |    |  Distribution API's   | │   │  
  │    │  └───────────────────┘    └───────────────────────┘ │   │  
  │    └─────────────────────────────────────────────────────┘   │  
  └──────────────────────────────────────────────────────────────┘
```

### 7\. High-Level Design

#### 7.1. Key Management Service

KMS is a Key Management Service library that provides secure key distribution for SONiC MACsec implementations. The library uses a client-server architecture where syncd acts as the KMS server hosting KEKs, while wpa\_supplicant processes act as clients that receive KEKs for SAK encryption. KMS server generates KEK on the first client request and uses the same KEK for subsequent requests. The library implements multiple layers of memory protection including mmap allocation, mlock to prevent swapping, and madvise to exclude sensitive data from core dumps. All sensitive memory is explicitly zeroed using explicit\_bzero before deallocation. Communication occurs through UNIX domain sockets with restricted permissions and message integrity validation. Encrypt and decrypt functionality is implemented using OpenSSL APIs backed by the SymCrypt cryptographic provider.

##### 7.1.1. SONiC Component Changes

**Syncd Changes**:

- Link with KMS  
- Initialize KMS server during syncd startup  
- Replace direct SAK handling with KMS decrypt API calls

**WPA\_Supplicant Changes**:

- Link with KMS  
- Initialize KMS client during startup and fetch the KEK from KMS server  
- Use KEK for SAK encryption   
- Store encrypted SAK into the redisDB

##### 7.1.2. Database Schema Changes

**Database Schema Impact**:

- **APP\_DB**: MACsec SA entries will store encrypted SAK \+ IV \+ TAG instead of plaintext SAK  
- **ASIC\_DB**: MACsec SA entries will store encrypted SAK \+ IV \+ TAG instead of plaintext SAK

**Current Schema**:

```json
// APP_DB MACsec SA entry (current):
"MACSEC_EGRESS_SA_TABLE:Ethernet1:5254008f4f1c0001:1": {
    "sak": "1EC8572B75A840BA6B3833DC550C620D2C65BBDDAD372D27A1DFEB0CD786671B",
    "auth_key": "35FC8F2C81BCA28A95845A4D2A1EE6EF",
    "next_pn": "1",
    "ssci": "0",
    "salt": "000000000000000000000000"
}

"MACSEC_INGRESS_SA_TABLE:Ethernet1:525400edac5b0001:1": {
    "active": "true",
    "sak": "1EC8572B75A840BA6B3833DC550C620D2C65BBDDAD372D27A1DFEB0CD786671B",
    "auth_key": "35FC8F2C81BCA28A95845A4D2A1EE6EF",
    "lowest_acceptable_pn": "1",
    "ssci": "0",
    "salt": "000000000000000000000000"
}
```

**Modified Schema (with KMS)**:

```json
// APP_DB MACsec SA entry (with KMS):
"MACSEC_EGRESS_SA_TABLE:Ethernet1:5254008f4f1c0001:1": {
    "sak": "60_byte_hex_string",
    "auth_key": "35FC8F2C81BCA28A95845A4D2A1EE6EF",    // unchanged
    "next_pn": "1",                                    // unchanged
    "ssci": "0",                                       // unchanged
    "salt": "000000000000000000000000"                 // unchanged
}

"MACSEC_INGRESS_SA_TABLE:Ethernet1:525400edac5b0001:1": {
    "active": "true",                                  // unchanged
    "sak": "60_byte_hex_string",
    "auth_key": "35FC8F2C81BCA28A95845A4D2A1EE6EF",  // unchanged
    "lowest_acceptable_pn": "1",                       // unchanged
    "ssci": "0",                                       // unchanged
    "salt": "000000000000000000000000"                 // unchanged
}
```

**Key Changes**:

- Encrypted SAK will be 60 bytes long and will contain IV(12) | Ciphertext (32) | Tag (16) 

**Rationale**: If KMS is used, then SAK field will be 60 bytes & will contain IV|Ciphertext|Tag. Similarly in non FIPS mode, SAK field will have 32 bytes of plaintext value. All other MACsec metadata remains unchanged, ensuring minimal impact on existing SONiC components. 

#### 

##### 7.1.3. Sequence Diagrams for KMS integration

**MACsec SAK Flow \- Complete Database Pipeline**:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐
│ wpa_supp    │  │   APP_DB    │  │ MACsec      │  │  ASIC_DB    │  │           syncd process         │
│ (macsec     │  │   (Redis)   │  │ orchagent   │  │  (Redis)    │  │  ┌─────────┐  ┌─────────────┐   │
│ container)  │  │             │  │             │  │             │  │  │ syncd   │  │   libkms    │   │
│ ┌─────────┐ │  │             │  │             │  │             │  │  │ main    │  │  (SERVER)   │   │
│ │ libkms  │ │  │             │  │             │  │             │  │  │ thread  │  │             │   │
│ │(CLIENT) │ │  │             │  │             │  │             │  │  └─────────┘  │ ┌─────────┐ │   │
│ └─────────┘ │  │             │  │             │  │             │  │               │ │   KEK   │ │   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │               │ │ Storage │ │   │
       │                │                │                │         │               │ └─────────┘ │   │
       │                │                │                │         │               │ ┌─────────┐ │   │
       │                │                │                │         │               │ │ Server  │ │   │
       │ Get KEK for    │                │                │         │               │ │ Thread  │ │   │
       │ encryption     │                │                │         │               │ └─────────┘ │   │
       │ ───────────────────────────────────────────────────────────│──────────────>│             │   │
       │                │                │                │         │               │             │   │
       │ KEK            │                │                │         │               │             │   │
       │<───────────────────────────────────────────────────────────│────────────── │             │   │
       │                │                │                │         │               │             │   │
       │──┐             │                │                │         │               │             │   │
       │  │ Local AES-  │                │                │         │               │             │   │
       │  │ 256-GCM     │                │                │         │               │             │   │
       │  │ Encryption  │                │                │         │               │             │   │
       │  │ using KEK   │                │                │         │               │             │   │
       │<─┘             │                │                │         │               │             │   │
       │                │                │                │         │               │             │   │
       │ Store encrypted│                │                │         │               │             │   │
       │ SAK in APP_DB  │                │                │         │               │             │   │
       │───────────────>│                │                │         │               │             │   │
       │                │                │                │         │               │             │   │
       │                │ Read encrypted │                │         │               │             │   │
       │                │ SAK from APP_DB│                │         │               │             │   │
       │                │<───────────────│                │         │               │             │   │
       │                │                │                │         │               │             │   │
       │                │ Write encrypted│                │         │               │             │   │
       │                │ SAK to ASIC_DB │                │         │               │             │   │
       │                │────────────────────────────────>│         │               │             │   │
       │                │                │                │         │               │             │   │
       │                │                │                │ Read encrypted SAK      │             │   │
       │                │                │                │ from ASIC_DB            │             │   │
       │                │                │                │<────────                │             │   │
       │                │                │                │         │               │             │   │
       │                │                │                │         │ Get KEK for   │             │   │
       │                │                │                │         │ decryption    │             │   │
       │                │                │                │         │──────────────>│             │   │
       │                │                │                │         │               │             │   │
       │                │                │                │         │ KEK (internal)│             │   │
       │                │                │                │         │<──────────────│             │   │
       │                │                │                │         │               │             │   │
       │                │                │                │         │──┐            │             │   │
       │                │                │                │         │  │ Local AES- │             │   │
       │                │                │                │         │  │ 256-GCM    │             │   │
       │                │                │                │         │  │ Decryption │             │   │
       │                │                │                │         │  │ using KEK  │             │   │
       │                │                │                │         │<─┘            │             │   │
       │                │                │                │         │               │             │   │
       │                │                │                │         │ Program       │             │   │
       │                │                │                │         │ plaintext SAK │             │   │
       │                │                │                │         │ to ASIC       │             │   │
       │                │                │                │         │──┐            │             │   │
       │                │                │                │         │  │ SAI API    │             │   │
       │                │                │                │         │<─┘            │             │   │
```


#### 

##### 7.1.4. Warm Reboot and Fastboot Requirements

**No impact.**

##### 7.1.5.  SAI API

**No impact.**

#### 7.2. FIPS POST

The KMS library will fetch FIPS POST results from OpenSSL/SymCrypt during initialization to ensure the required FIPS compliance. The library will be usable or enabled only if the validation succeeds. A failure will force the library to move into a disabled state. In this state, any subsequent API calls will fail.

The POST status can be published in the *‘POST\_STATUS\_TABLE’* table, referenced in SONiC FIPS POST support HLD using a separate key POST\_STATUS\_OPENSSL to capture the results of control plane POST validation.

##### High-Level Block Diagram

```
  ┌─────────────────┐  
  │ MACsec/Syncd    │  
  │ Service Startup │  
  └─────────┬───────┘  
            │  
            ▼  
  ┌─────────────────────┐  
  │ Call                │  
  │ KMS Initialization  │  
  └─────────┬───────────┘  
            │  
            ▼  
  ┌─────────────────┐  
  │ KMS Library     │  
  │ Query OpenSSL   │  
  │ FIPS POST       │  
  └─────────┬───────┘  
            │  
            ▼  
       ┌─────────┐       YES    ┌─────────────────┐  
       │ POST    │─────────────▶│ Initialize KMS  │  
       │ PASS?   │              │ Key Management  │  
       └────┬────┘              └─────────┬───────┘  
            │ NO                          │  
            ▼                             ▼  
  ┌─────────────────┐           ┌─────────────────┐  
  │     Disable     │           │ MACsec Service  │  
  │ MACsec Service  │           │   Ready for     │  
  │                 │           │   Operations    │  
  └───────┬─────────┘           └────────┬────────┘  
          │                              │  
          ▼                              ▼  
  ┌───────────────────────────────────────────────┐  
  │          Publish POST STATUS.                 │  
  └───────────────────────────────────────────────┘
```

### 8\. Open/Action Items

None

### 9\. Conclusion

The implementation enhances security for SONiC MACsec deployments and enables FIPS compliance while maintaining compatibility with existing SONiC functionality. The design provides:

- **Security**: KEK isolation and encrypted key storage throughout the database pipeline  
- **FIPS POST Compliance**: Required for SONiC FIPS mode operation with FIPS 140-3 approved algorithms


  
