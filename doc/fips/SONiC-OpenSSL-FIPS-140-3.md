# SONIC OpenSSL 140-3 HLD

## Revision

|  Rev  | Date       | Author     | Change Description |
| :---: | :--------: | :--------: | ------------------ |
|  0.1  | 2022-02-22 | Xuhui Miao | Initial version    |

## Table of Contents
- [Abbreviation](#abbreviation)
- [Requirement](#requirement)
- [The cryptographic modules in SONiC](#the-cryptographic-modules-in-SONiC)
- [OpenSSL FIPS 140-3](#OpenSSL-FIPS-140-3)
  * [OpenSSL Engine](#OpenSSL-Engine)
  * [SymCrypt OpenSSL Engine](#symCrypt-openSSL-engine)
  * [OpenSSL configuration for SymCrypt Engine](#OpenSSL-configuration-for-SymCrypt-Engine)
  * [OpenSSL configuration enhancement](#OpenSSL-configuration-enhancement)
  * [SymCrypt OpenSSL Engine debian package](#SymCrypt-OpenSSL-Engine-debian-package)
- [Kerberos Cryptographic Module](#Kerberos-Cryptographic-Module)
- [Golang Cryptographic Module](#Golang-Cryptographic-Module)
- [SONiC FIPS Configuration](#SONiC-FIPS-Configuration)
  * [Enable FIPS on system level](#Enable-FIPS-on-system-level)
  * [Enable FIPS on application level](#Enable-FIPS-on-application-level)


## Abbreviation

| Abbreviation | Description                                  |
| ------------ | -------------------------------------------- |
| CAVP         | Cryptographic Algorithm Validation Program   |
| CST          | Cryptographic and Security Test              |
| CMVP         | Cryptographic Module Validation Program      |
| FIPS         | Federal Information Processing Standard      |

## Requirement
SONiC only uses cryptographic modules validated by FIPS 140-3, Make SONiC compliant with FIPS 140-3.

## The cryptographic modules in SONiC

| Module   | Use Scenarios | Description                                                |
| -------------------- | --------------- | -------------------------------------------- |
| OpenSSL              | Python, OpenSSH | Cyptography and SSL/TLS ToolKit              |
| Kerberos             | OpenSSH         | Kerboros contains builtin crypto module      |
| Golang               | sonic-restapi   | Golang contains builtin crypto module         |
| Libgcrypto           | GPG             | A general purpose cryptographic library originally based on code from GnuPG |
| Kernel Crypto        | --              | Linux crypto kernel module |

## Scopes:
In Scopes:
1. OpenSSL
2. Kerberos
3. Golang

Out of Scopes:
1. Linux Kernel
2. Libgcrypt


## OpenSSL FIPS 140-3

![FIPS Overview](images/fips-overview.png)

### OpenSSL Engine
OpenSSL supports engine cryptographic modules in the form of engine objects, and provides a reference-counted mechanism to allow them to be dynamically loaded in and out of the running application. An engine object can implement one or all cryptographic algorithms.

### SymCrypt OpenSSL Engine
The [SymCrypt engine for OpenSSL (SCOSSL)](https://github.com/microsoft/SymCrypt-OpenSSL) allows the use of OpenSSL with [SymCrypt](https://github.com/microsoft/SymCrypt) as the provider for core cryptographic operations. It leverages the OpenSSL engine interface to override the cryptographic implementations in OpenSSL's libcrypto. The primary motivation for this is to support FIPS certification, as OpenSSL 1.1.1 does not have a FIPS-certified cryptographic module. Microsoft will submit the FIPS 140-3 reports for SymCrypt to CMVP.

The SymCrypt Engine is one of the implementation to support FIPS, The [wolfSSL engine](https://github.com/wolfSSL/wolfEngine) is another option.

### OpenSSL configuration for SymCrypt Engine

/usr/lib/ssl/openssl-fips.cnf 
```
openssl_conf = openssl_init
[ openssl_init ]
engines = engine_section

[ engine_section ]
symcrypt = symcrypt_section

[ symcrypt_section ]
engine_id = symcrypt
dynamic_path = /usr/lib/x86_64-linux-gnu/libsymcryptengine.so
default_algorithms = ALL
```

### OpenSSL configuration enhancement
When fips=1 is set in /proc/cmdline, the OpenSSL default config file is changed to "/usr/lib/ssl/openssl-fips.cnf", otherwise, the config file "/usr/lib/ssl/openssl-fips.cnf" is used.

### SymCrypt OpenSSL Engine debian package
Provide SymCrypt OpenSSL debian package.
Package name: symcrypt-openssl
Current version: 0.1

Package file name example: symcrypt-openssl_0.1_amd64.deb
Files in the packages:
```
/usr/lib/ssl/openssl.cnf
/usr/lib/ssl/openssl-fips.cnf
/usr/lib/x86_64-linux-gnu/libsymcrypt.so
/usr/lib/x86_64-linux-gnu/libsymcryptengine.so
```

## Kerberos Cryptographic Module
Kerberos will use the builtin cryptographic module by default, but it allows to change the build option to use OpenSSl, see [MIT Kerberos features](https://web.mit.edu/kerberos/krb5-1.13/doc/mitK5features.html). SONiC will change the build option to use OpenSSL instead of the builtin one. It is not configurable to use the Kerberos builtin cryptographic module when OpenSSL used.

## Golang Cryptographic Module
Golang has its own cryptographic module (see [crypto](https://github.com/golang/go/tree/master/src/crypto)) without FIPS supports. There are some branches with branch name starting with "dev.boringcrypto" (see [golang branches](https://github.com/golang/go/branches/all?query=dev.boringcrypto)), changing the Golang cryptographic APIs' referenece to use [BoringSSL](https://github.com/google/boringssl). Although BoringSSL is an open source project, but it used by Google only, not intened for general use.

To support FIPS for Golang, RedHat offers an alternative solution (see [here](https://developers.redhat.com/blog/2019/06/24/go-and-fips-140-2-on-red-hat-enterprise-linux)), it builds on top of the Golang's dev.bringcrypt branches, has ability to call into OpenSSL, not BoringSSL. SONiC can reuse the RedHat sulotion, one difference is that RedHat supports FIPS for OpenSSL directly, SONiC uses OpenSSL Engine.

How OpenSSL Engine works in Golang?
![Golang API](images/golang-api.png)

When FIPS enabled, both of the BoringSSL Enable Option and the SymCrypt Enabled option will be set.

## SONiC FIPS Configuration
### Enable FIPS on system level
Add the Linux System parameter fips=1, in grub config, one of implemetation as below:

cat /etc/grub.d/99-fips.cfg
```
GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT fips=1"
```

To validate the FIPS enabled, grep 'fips=1' /proc/cmdline.

### Enable FIPS on application level
```
export ENABLE_FIPS=1
```

Alternative option for the golang applications only:
```
export GOLANG_FIPS=1
```

Alternative option for the OpenSSL applications only:

see https://www.openssl.org/docs/manmaster/man7/openssl-env.html
```
export OPENSSL_CONFIG=/usr/lib/ssl/openssl-fips.cnf
```
