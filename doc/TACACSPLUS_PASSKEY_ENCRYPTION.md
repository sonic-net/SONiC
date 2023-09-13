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
- [Benifits](#benifits)
- [Testing Requirements](#testing-requirements)



### Revision

 | Rev |     Date    |       Author         | Change Description                |
 |:---:|:-----------:|:--------------------:|-----------------------------------|
 | 0.1 |             | Nikhil Moray (nmoray)| Initial version                   |
 | 0.1 |             | Madhu Paluru (madhupalu)| Updated                        |


 ### Scope

This document describes the High Level Design of "TACACS+ Passkey Encryption" feature support in SONiC. It encompasses design and implementation considerations for enhancing the security of TACACS+ (Terminal Access Controller Access-Control System) authentication by introducing an encrypted passkey.


### Abbreviations

 | Term    |     Meaning                                                        |
 |:-------:|:-------------------------------------------------------|
 | TACACS  | Terminal Access Controller Access Control System Plus) |

### Overview

This addition constitutes a substantial improvement in bolstering the security of the TACACS+ authentication protocol. TACACS+ has a well-established reputation as a reliable means of managing access to network devices. However, the previous practice of utilising a sensitive passkey in plaintext during the authentication process posed security concerns. With this enhancement, the vulnerability is effectively mitigated by introducing robust passkey encryption mechanisms (on the client side), ensuring the safeguarding of authentication credentials and an overall strengthening of network security."


### Requirements

The primary objective of this feature is to safeguard the TACACS passkey, which is stored in its plaintext format within CONFIG_DB.


### High-Level Design

In line with the TACACS+ architecture, when a user initiates a SSH connection to a device with TACACS+ authentication enabled, they must utilize the TACACS+ login password. Conversely, the corresponding device must have the passkey provided by the TACACS+ server properly configured within its configDB. Should either of these elements be missing or incorrect, the user will be unable to access the device. Thus to meet the given requirement, passkey will be encrypted is the configuration phase itself.

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
|   +-------------------------+  |  Decrypted passkey                   |  +------------+     |
|   | PAM Configuration Files <------------------------------------------+ |  AAA Config |    |
|   +-------------------------+  |                                      |  +------------+     |
|                                |                                      |                     |
|         +-------------+        |                                      |  HostCfg Enforcer   |
|         |     PAM     |        |                                      +----------^----------+
|         |  Libraries  |        |                                                 |
|         +-------------+        |                                                 | Encrypted passkey
+---------------+----------------+                                                 |
                |                                                                  |
           +----v----+                                                     +-------+--------+
           |         |             Encrypted passkey                       |                |
           |   CLI   +---------------------------------------------------->|    ConifgDB    |
           |         |                                                     |                |
           +---------+                                                     +----------------+
```
This decryption step is crucial because the login or SSH daemon references the PAM config file to verify the TACACS secret / passkey. If it remains encrypted, the SSH daemon will be unable to recognize the passkey, leading to login failures. The depicted block diagram clearly showcase the enhanced capbalities of the existing submodules.


### Implementation details

The implementation stands on three key pillars.
1. OPENSSL toolkit is used for encryption / decryption
2. aes-128-cbc is the encoding format used for encryption / decryption
3. Device MAC address is used as a Password for encryption / decryption


#### Show CLI changes

Furthermore, aside from encrypting the passkey stored within CONFIG_DB, this infrastructure ensures that the passkey itself remains concealed from any of the displayed CLI outputs. Consequently, the passkey field has been eliminated from the "show tacacs" output, and it will now solely indicate the status whether the passkey is configured or not. For instance.

show tacacs
["TACPLUS global passkey configured Yes / No"]


### Benifits

TACACS passkey encryption adds an extra layer of security to safeguard the passkey on each device throughout the network. Moreover, the utilization of MAC address-based encryption ensures that each network device possesses its distinct encrypted passkey. This strategy effectively mitigates the risk of a major network breach in case one of the devices is compromised.

### Limitation
We choose MAC address is unique and better for management, however if the MAC address of the device is known, we could decrypt the key. If we want to use any other ciper we should manage / stored it in the DB, it is again defeating the purpose. So for now we are going ahead with mac as network admins can orchestartion system to use mac address for passkey encryption. However we are open to new ideas and thoughts to hardened the security and we should be able to accomodate with later releases.

### Testing Requirements

Need to add new / update the existing TACACS testcases to incorporate this new feature
Test cases to unit test encrypt and decrypt fucntions 
Test cases to add test the TACACS+ functionality with passkey encryption
Test cases to cover DB migration 
