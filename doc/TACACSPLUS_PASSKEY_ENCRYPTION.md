# TACACS+ Passkey Encryption #
## Table of Contents
- [Revision](#revision)
- [Scope](#scope)
- [Abbreviations](#abbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [High-Level Design](#high-level-design)
- [Implementation Details](#implementation-details)
        - [Show CLI changes](@show-cli-changes)
- [Benefits](#benefits)
- [Testing Requirements](#testing-requirements)
### Revision
 | Rev |     Date    |       Author            | Change Description                |
 |:---:|:-----------:|:-----------------------:|:----------------------------------|
 | 0.1 |             | Nikhil Moray (nmoray)   | Initial version                   |
 | 0.1 |             | Madhu Paluru (madhupalu)| Updated                           |
 | 0.1 |   11/09/2023| Madhu Paluru (madhupalu)| Addressed review comments         |
 ### Scope
This document describes the High Level Design of "TACACS+ Passkey Encryption" feature support in SONiC. It encompasses design and implementation considerations for enhancing the security of TACACS+ (Terminal Access Controller Access-Control System) authentication by introducing an encrypted passkey.
### Abbreviations
 | Term    |     Meaning                                            |
 |:-------:|:-------------------------------------------------------|
 | TACACS  | Terminal Access Controller Access Control System Plus) |
### Overview
This addition constitutes a substantial improvement in bolstering the security of the TACACS+ authentication protocol. TACACS+ has a well-established reputation as a reliable means of managing access to network devices. However, the previous practice of utilising a sensitive passkey in plaintext during the authentication process posed security concerns. With this enhancement, the vulnerability is effectively mitigated by introducing robust passkey encryption mechanisms (on the client side), ensuring the safeguarding of authentication credentials and an overall strengthening of network security.
### Requirements
The primary objective of this feature is to safeguard the TACACS passkey, which is stored in its plaintext format within CONFIG_DB.
### High-Level Design
In line with the TACACS+ architecture, when a user initiates a SSH connection to a device with TACACS+ authentication enabled, they must utilize the TACACS+ login password. Conversely, the corresponding device must have the passkey provided by the TACACS+ server properly configured within its configDB. Should either of these elements be missing or incorrect, the user will be unable to access the device. Thus to meet the given requirement, the passkey will be encrypted in the configuration phase itself.
The current data flow among the various TACACS modules operates in the following manner.
1. When a user configures the TACACS passkey using the SONIC CLI, it is initially stored in the CONFIG_DB.
2. Subsequently, the same key is retrieved by the HostCfg Enforcer module to update the PAM configuration file(s). This configuration file is inherently included in the authentication processes for login or SSH within the Linux operating system.
3. When TACACS+ Authentication is activated on the device, a new PAM configuration file (common-auth-sonic) is generated and substituted in the login and SSH daemons. Importantly, the pre-existing configuration file remains unchanged.
The revised data handling procedure among the modules is outlined as follows:
1. When a user configures the TACACS passkey using the SONIC CLI, it will now be securely stored in encrypted format instead of plaintext.
2. Subsequently, the HostCfg Enforcer module retrieves this encrypted key. However, before writing it into the PAM configuration file(s), the hostCfgd module decrypts it.
```
       +-------+  +---------+
       |  SSH  |  | Console |
       +---+---+  +----+----+
           |           |   
+----------v-----------v---------+                                      +---------------------+
| AUTHENTICATION                 |                                      |                     |
|   +-------------------------+  |         Decrypted passkey            |  +------------+     |
|   | PAM Configuration Files    <------------+       +-----------------+  | AAA Config |     |
|   +-------------------------+  |            |       |                 |  +------------+     |
|                                |            |       |                 |                     |
|         +-------------+        |         +--------------+             |  HostCfg Enforcer   |
|         |     PAM     |        |         |              |   key-store +----------^----------+
|         |  Libraries  |        |    +---->  Master key  |    __                 |
|         +-------------+        |    |    |   Manager    |---|r |                | Encrypted passkey
+---------------+----------------+    |    |securitycipher|   |o |                |
                |                     |    +-------------+    |o |                |
           +----v----+                |           |           |t |         +------+--------+
           |         |                |           |            --          |                |
           |   CLI   +----------------+           +------------------------>    ConfigDB    |
           |         |                                  Encrypted passkey  |                |
           +---------+                                                     +----------------+
```
This decryption step is crucial because the login or SSH daemon references the PAM config file to verify the TACACS secret / passkey. If it remains encrypted, the SSH daemon will be unable to recognize the passkey, leading to login failures. The depicted block diagram clearly showcases the enhanced capabilities of the existing submodules.


### Approach
1. A runtime flag (via config_db) for Enable / disable feature: "key_encrypt"
2. CLI will ask for a encryption master key/password while configuring the TACACS passkey and at the backend it will be stored at /etc/cipher_pass file which is accessible to only root user with read only permissions
3. Same file will be read while decrypting the passkey at hostcfgd
4. The infra (encrypt/decrypt and master key/password storage & retrieval) will be common for all the features like TACACS, RADIUS, LDAP etc..
   
### Implementation details
The implementation as follows
1. OPENSSL toolkit is used for encryption / decryption.
2. base64 is the encoding format used for encryption / decryption.
4. sonic_utilities extended to passkey encyption using the master key/passwd manager.
5. User has to enter master key/passwd at the time of configuring the passkey, this is mandatory requirement only if "key_encrypt" run time flag is enabled.
6. The encrypted passkey stored in config_db 
7. The master key/paswd used for encryption/decryption and will be stored in the same device with root access previleges (/etc/cipher_pass).
8. HostCfg will use the master key/passwd to decrypt the encrypted passkey and further store it in PAM configuration files. 

#### CLI Changes 
config tacacs passkey TEST1 --encrypt
Password: 

Note: It will ask for a master key/password only when '--encrypt' flag is set.

#### Show CLI changes
Furthermore, aside from encrypting the passkey stored within CONFIG_DB, this infrastructure ensures that the passkey itself remains concealed from any of the displayed CLI outputs. Consequently, the passkey field has been eliminated from the "show tacacs" output, and it will now solely indicate the status whether the passkey is configured or not. For instance,
show tacacs
["TACPLUS global passkey configured Yes / No"]

### Yang Changes 
Increase existing passkey leaf length to 256.
Create a new leaf for newly introduced run time flag 'key_encrypt'.

### Config DB changes 
A new run time flag to enable/disable the tacacs passkey encryption feature - "key_encrypt".

### Schema changes 
```
"TACPLUS": {
        "global": {
            "auth_type": "login",
            "key_encrypt": "true",
            "passkey": "<Entrypted_Passkey>"
        }
    }
```
### Benefits
TACACS passkey encryption adds an extra layer of security to safeguard the passkey on each device throughout the network. Furthermore, the implementation of master key/password manager encryption ensures that encrypted passkeys can be reused across network nodes without any complications. Consequently, there are no obstacles when it comes to utilizing the config_db.json file from one device on another. Additionally, the use of a root protected config file effectively reduces the risk of exposing the encryption/decryption master key/passwd since it is only accessible to root users and remains inaccessible to external entities.

### Testing Requirements
Need to add new / update the existing TACACS test cases to incorporate this new feature
Test cases to unit test encrypt and decrypt functions
Test cases to add test the TACACS+ functionality with passkey encryption

