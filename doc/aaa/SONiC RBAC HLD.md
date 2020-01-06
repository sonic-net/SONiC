

# Authentication and Role-Based Access Control

# High Level Design Document
#### Rev 0.1

# Table of Contents
- [Revision History](#revision-history)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [1 Feature Overview](#1-feature-overview)
  * [1.1 Requirements](#11-requirements)
    + [1.1.1 Functional Requirements](#111-functional-requirements)
      - [1.1.1.1 NBI Authentication](#1111-nbi-authentication)
      - [1.1.1.2 CLI Authentication to REST server](#1112-cli-authentication-to-rest-server)
      - [1.1.1.3 Translib Enforcement of RBAC](#1113-translib-enforcement-of-rbac)
      - [1.1.1.4 Linux Groups](#1114-linux-groups)
      - [1.1.1.5 Certificate-based Authentication for gNMI and REST](#1115-certificate-based-authentication-for-gnmi-and-rest)
      - [1.1.1.6 Local User Management and UserDB Sync](#1116-local-user-management-and-userdb-sync)
    + [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
    + [1.1.3 Scalability Requirements](#113-scalability-requirements)
      - [1.1.3.1 REST Server](#1131-rest-server)
      - [1.1.3.2 gNMI Server](#1132-gnmi-server)
      - [1.1.3.3 Translib](#1133-translib)
    + [1.1.4 Warm Boot Requirements](#114-warm-boot-requirements)
  * [1.2 Design Overview](#12-design-overview)
    + [1.2.1 Basic Approach](#121-basic-approach)
    + [1.2.2 Container](#122-container)
    + [1.2.3 SAI Overview](#123-sai-overview)
- [2 Functionality](#2-functionality)
  * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [2.2 Functional Description](#22-functional-description)
- [3 Design](#3-design)
  * [3.1 Overview](#31-overview)
  * [3.2 DB Changes](#32-db-changes)
    + [3.2.1 CONFIG DB](#321-config-db)
    + [3.2.2 APP DB](#322-app-db)
    + [3.2.3 STATE DB](#323-state-db)
    + [3.2.4 ASIC DB](#324-asic-db)
    + [3.2.5 COUNTER DB](#325-counter-db)
    + [3.2.6 USER DB](#326-user-db)
  * [3.3 Switch State Service Design](#33-switch-state-service-design)
    + [3.3.1 Orchestration Agent](#331-orchestration-agent)
    + [3.3.2 Other Process](#332-other-process)
  * [3.4 SyncD](#34-syncd)
  * [3.5 SAI](#35-sai)
  * [3.6 User Interface](#36-user-interface)
    + [3.6.1 Data Models](#361-data-models)
    + [3.6.2 CLI](#362-cli)
      - [3.6.2.1 Configuration Commands for User Management](#3621-configuration-commands-for-user-management)
      - [3.6.2.2 Show Commands](#3622-show-commands)
      - [3.6.2.3 Debug Commands](#3623-debug-commands)
      - [3.6.2.4 IS-CLI Compliance](#3624-is-cli-compliance)
    + [3.6.3 REST API Support](#363-rest-api-support)
- [4 Flow Diagrams](#4-flow-diagrams)
- [5 Error Handling](#5-error-handling)
  * [5.1 REST Server](#51-rest-server)
  * [5.2 gNMI server](#52-gnmi-server)
  * [5.3 CLI](#53-cli)
  * [5.4 Translib](#54-translib)
- [6 Serviceability and Debug](#6-serviceability-and-debug)
- [7 Warm Boot Support](#7-warm-boot-support)
- [8 Scalability](#8-scalability)
- [9 Unit Test](#9-unit-test)
- [10 Internal Design Information](#10-internal-design-information)

# Revision History
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 10/22/2019  |   Jeff Yin      | Initial version                   |
| 0.2 | 10/30/2019  |   Jeff Yin      | Revision after joint review with Broadcom/Dell |

# About this Manual
This document provides a high-level design approach for authentication and RBAC in the SONiC Management Framework.

For authentication, this document describes how the CLI and programmatic interfaces (REST, gNMI) -- collectively referred to in this document as the northbound interfaces (NBIs) -- will authenticate users and the supported credentials and methods.

For authorization, this document describes a centralized authorization approach to be implemented in the Translib component of the SONiC Management Framework.

# Scope
This document covers the interfaces and mechanisms by which NBIs will authenticate users who wish to access and configure the SONiC system via the Management Framework. It will also cover RBAC enforcement.

This document will NOT extensively cover (or assumes the pre-existence of):
- Implementation of remote authentication and authorization (RADIUS, TACACS+, etc.)
- Public Key Infrastructure management: X.509v3 certificate installation, deletion, trust store management, etc.


# Definitions/Abbreviations

| **Term**                 | **Meaning**                         |
|:--------------------------|:-------------------------------------|
| RBAC                      | Role-Based Access Control                   |
| AAA                       | Authentication, Authorization, Accounting |
| CLI   | Command-Line Interface |
| REST  | REpresentational State Transfer |
| gNMI  | gRPC Network Management Interface |
| NBI    | North-bound Interfaces (CLI, REST, gNMI) |



# 1 Feature Overview

## 1.1 Requirements

- The SONiC Management Framework must support authenticated access for the various supported northbound interfaces (NBIs): CLI, REST, and gNMI. Since the CLI works with the REST server, it must also be authenticated with the REST server.
- The NBIs must pass along the username info to Translib, so that Translib can enforce role-based access (RBAC).
- For RBAC, Linux Groups will facilitate authorization. Initially, two roles will be supported: read/write and read-only. Additionally, remotely-authenticated users who map to a defined role will be authenticated as a static global user on the system. These limitations should be revisited at a later date.
- Local user management: CLIs and APIs for creating and managing local users on the system -- their usernames, passwords, and roles.

### 1.1.1 Functional Requirements

#### 1.1.1.1 NBI Authentication
A variety of authentication methods must be supported:
* **CLI** authentication is handled via the same mechanisms supported by SSH
  - Password-based Authentication
  - Public-key Authentication
* **REST** authentication
  - Password-based Authentication with JWT token-based authentication
  - Certificate-based Authentication with JWT token-based authentication
  - The REST server must be enhanced to accept all types of authentication concurrently
* **gNMI** Authentication
  - Password-based Authentication with Token-based authentication
  - Certificate-based Authentication

#### 1.1.1.2 CLI Authentication to REST server
Given that the CLI module works by issuing REST transactions to the Management Framework's REST server, the CLI module must also be able to authenticate with the REST server when REST authentication is enabled. This can be accomplished via the following steps:
1. When a user is created on the system, a self-signed certificate is generated with the username embedded into the Subject field. That self-signed certificate will be stored in the user's home directory, with access permissions limited to that user only. The self-signed certificate will be used for mutual authentication from the KLISH shell to the REST server.
**Design note:** Certificate-based authentication is desired over password-based authentication for the CLI-to-REST connection because it prevents the need to store and forward any plaintext passwords. Per-user certificates with strict file permissions are desired so as to ensure that users cannot drop into the Linux shell and perform operations as other than themselves (e.g., via `curl` with a shared certificate, or someone else's certificate).
2. When a user logs into the switch, the switch will authenticate the user by using the username and password credentials.
3. When the KLISH process is started, its UID and GID are set to those of the user that was authenticated by `sshd` or `login` (as through the console).
4. When the KLISH shell is spawned, it will create a persistent, local HTTPS connection over an internal socket, and send the REST request to authenticate this KLISH session as the logged-in user, which can be looked up through NSS by using `getpwuid()`. This authentication request will contain the user's client certificate.
5. The REST server will authenticate the user and return a token with the username encoded in it. The KLISH CLI must cache this token and use it for all future requests from this KLISH session. The REST server will also maintain this token to username mapping with it so as to identify all future requests as well. This will also allow the REST server in creating audit logs for all the requests sent from KLISH, as well as pass the username to Translib for RBAC enforcement.
6. KLISH CLI session will store the authentication token, and from then on, KLISH CLI will send REST requests using the persistent connection with the authentication token in the HTTP header to the REST server for all the CLI commands.
7. The KLISH session must be able to cleanly handle ctrl-c breaks while it is busy waiting on a response from the REST server.
8. When the user exits the KLISH CLI session, the HTTP persistent connection is closed. The REST server will clean up the corresponding authentication token for its corresponding KLISH CLI Client.

#### 1.1.1.3 Translib Enforcement of RBAC
The Translib module in the [management framework](https://github.com/project-arlo/SONiC/blob/master/doc/mgmt/Management%20Framework.md) is a central point for all commands, regardless of the interface (CLI, REST, gNMI). Therefore, the RBAC enforcement will be done in Translib library.

The CLI, REST, and gNMI will result in Translib calls with xpath and payload. Additionally, the REST and gNMI server modules must pass the username to the Translib. The RBAC checks will be enforced in the **Request Handler** of the Translib. The Request Handler processes the entire transaction atomically. Therefore, if even one operation in the transaction is not authorized, the entire transaction is rejected with the appropriate "Not authorized" error code. If the authorization succeeds, the transaction is passed to the Common Application module for further ‘transformation’ into the ABNF format. The rest of the flow of the transaction through the management framework is unmodified.

At bootup time of the manageability framework (or gNMI container), it is recommended to cache the [User DB](#326-user-db) if not already cached. This is because every command needs to access the information in the User DB in order to access the information. Alternately, instead of caching the entire User DB, the information can be cached once the record is read from the DB. Additionally, the Translib must listen to change notifications on the User DB in order to keep its cache current.

As described in section [1.1.1.4 Linux Groups](#1114-linux-groups), the enforcement of the users and roles in Linux will be done via the Linux groups. A user can use Linux commands on the Linux shell and create users and Linux groups (which represent the roles). This will mean that the information in the User DB is no longer current. In order to keep the information in the User DB and the Linux `/etc/passwd` file in sync, a service must run on the host (not the container) to keep the databases in sync.

Since Translib is the main authority on authorized operations, this means that the NBIs cannot render to the user what they are and are not allowed to do. The CLI, therefore, renders the entire command tree to a user, even the commands they are not authorized to execute.

#### 1.1.1.4 Linux Groups
Initially, only two roles will be supported:
- `admin` -- can perform read and write functions across all attributes (i.e., GET/PUT/PATCH/etc.)
- `operator` -- can only perform read functions on all attributes (i.e., GET only)
These privileges will be enforced by Translib.

RBAC will be facilitated via Linux Groups:
- Local users
  - Local user with `Operator` role is added into `operator` group
  - Local user with `Admin` role is added into `admin` group and is a `sudoer`.
- Remote users
  - Remote users with `Operator` role are mapped to the same global `remote-user` user who is part of `operator` group
  - Remote users with `Admin` role are mapped to the same global `remote-user-su` user who is part of `admin` group and is a `sudoer`
  - This means that all remote users will share the same accounts on the system, which also means they will share the same /home directory and certificate to log into the REST server.

  In the future, this "global user" approach will be revisited so that remote users are authenticated with their own username so that their activities may be properly audited.

#### 1.1.1.5 Certificate-based Authentication for gNMI and REST
For the initial release, it will be assumed that certificates will be managed outside of the NBIs. That is, no CLIs or REST/gNMI interfaces will be implemented to support public key infrastructure management for certificates and certificate authorities. Certificates will be manually generated and copied into the system via Linux utilities.

The exception to this is the self-signed certificates used for CLI authentication to the REST server. Those certificates will be auto-generated when a user is created on the system. These certificates should be copied to a user's home directory _as well as_ the trust store so that the REST server can use them for authenticating local CLI sessions.

User certificates must be stored in a user's home directory. Their corresponding private keys must also be stored in the user's home directory, albeit with restricted permissions so that they are not readable by other users.

The gNMI server will use a trust store for CA certificates from a location such as `/usr/local/share/ca-certificates`. The trust store itself must be managed by [existing Linux tools](https://manpages.debian.org/jessie/ca-certificates/update-ca-certificates.8.en.html).

The gNMI server must implement a method by which a username can be determined from the presented client certificate, so that the username can thus be passed to Translib for RBAC enforcement. The username will be derived from the Subject field of the X.509v3 certificate.

Users must be informed by way of documentation so that they know how to manage their certificate infrastructure in order to properly facilitate gNMI communication.

The REST server must use the same certificate scheme as the gNMI server to validate client certificates.

#### 1.1.1.6 Local User Management and UserDB Sync
An interface must be developed for local user management, so that administrators can add users and assign passwords and roles to them. Administrators with the appropriate role must be able to add/delete users, modify user passwords, and modify user roles. They must be able to do so through all of the NBIs, meaning that a YANG model and CLI tree must be developed.

Users must be added to the Linux database (`/etc/passwd`, `/etc/group`, and optionally `/etc/shadow`). That's where a user is mapped to a Linux [User Identifier](https://en.wikipedia.org/wiki/User_identifier) (UID) and primary [Group Identifier](https://en.wikipedia.org/wiki/Group_identifier) (GID). When users are created they also need to be assigned roles. Roles are simply defined as Linux groups (`/etc/group`) and assigned to users as [Supplementary GIDs](https://en.wikipedia.org/wiki/Group_identifier#Supplementary_groups).  

When a user is created it also needs to be assigned certificates that will allow them to communicate with the REST server. Finally, all users need to be added to the REDIS database (see [section 3.2.6]()) where additional information about each user can be stored (e.g. *tenant*).

Since these operations (i.e. creating Linux users, assigning certificates, etc.) are non-trivial, the process of creating users will be entrusted to the Host Account Management Daemon (**hamd**).

##### 1.1.1.6.1 Host Account Management Daemon (hamd)

The **hamd** process runs on the host. It is accessed via a DBus interface that provides the ability to access and/or modify the host's Linux database (`/etc/passwd`, `/etc/group`, and optionally `/etc/shadow`). Since DBus is a secured interface we can control which processes will be allowed to access **hamd**. 

The **hamd** process will provide the following DBus APIs to create/modify/delete user and group (role) accounts:

- **useradd**: To create new users (similar to GNU [useradd](http://man7.org/linux/man-pages/man8/useradd.8.html))
- **userdel**: To delete a user (similar to GNU [userdel](http://man7.org/linux/man-pages/man8/userdel.8.html))
- **passwd**: To change a user password (similar to GNU [passwd](http://man7.org/linux/man-pages/man1/passwd.1.html))
- **set_roles**: To set a user's roles (similar to GNU [usermod](http://man7.org/linux/man-pages/man8/usermod.8.html))
- **groupadd**: To create new groups/roles (similar to GNU [groupadd](http://man7.org/linux/man-pages/man8/groupadd.8.html))
- **groupdel**: To delete groups/roles (similar to GNU [groupdel](http://man7.org/linux/man-pages/man8/groupdel.8.html))

##### 1.1.1.6.2 User management with hamd 

Applications that need to manage users (for example **click** or **klish**) can do so by using **hamd**'s DBus **ham.accounts** interface. DBus services such as **hamd** publish their interfaces. This can be retrieved and analyzed at runtime in order to understand the used implementation. The resulting introspection data is in XML format. DBus debug tools such as **qdbus** can be used to retrieve this data. At the time this document was written, the DBus XML definition for the APIs defined in the previous section was:

> ```xml
>   <interface name="ham.accounts">
>       <method name="useradd">
>           <arg direction="in"  type="s"  name="login"/>
>           <arg direction="in"  type="as" name="roles"/>
>           <arg direction="in"  type="s"  name="hashed_pw"/>
>           <arg direction="out" type="(bs)" name="(success, errmsg)" />
>       </method>
>       <method name="userdel">
>           <arg direction="in"  type="s"  name="login"/>
>           <arg direction="out" type="(bs)" name="(success, errmsg)" />
>       </method>
>       <method name="passwd">
>           <arg direction="in"  type="s"  name="login"/>
>           <arg direction="in"  type="s"  name="hashed_pw"/>
>           <arg direction="out" type="(bs)" name="(success, errmsg)" />
>       </method>
>       <method name="set_roles">
>           <arg direction="in"  type="s"  name="login"/>
>           <arg direction="in"  type="as" name="roles"/>
>           <arg direction="out" type="(bs)" name="(success, errmsg)" />
>       </method>
>       <method name="groupadd">
>           <arg direction="in"  type="s" name="group"/>
>           <arg direction="out" type="(bs)" name="(success, errmsg)" />
>       </method>
>       <method name="groupdel">
>           <arg direction="in"  type="s" name="group"/>
>           <arg direction="out" type="(bs)" name="(success, errmsg)" />
>       </method>
>   </interface>
> ```

##### 1.1.1.6.3 The hamctl shell program

A utility program, **hamctl**, is provided to make it easier for operators to interact with **hamd** from a Linux shell (e.g. bash). This is primarily a debug tool and <u>*should not be invoked from other programs*</u>. Programs should use the DBus interface described above. 

Users logged in at a shell terminal can control **hamd** (e.g. ask it to create or delete a user) with **hamctl**. **hamctl** is sell-documented. Simply invoke "**hamctl --help**" to get the list of commands available.

##### 1.1.1.6.4 Name Service Switch

In addition to providing APIs to create/modify/delete user and group (role) accounts, **hamd** also provides APIs to simply read user and group (role) accounts. Here's the list:

- **getpwnam**: To retrieve user credentials (similar to POSIX [getpwnam](http://man7.org/linux/man-pages/man3/getpwnam.3.html))
- **getpwuid**: To retrieve user credentials (similar to POSIX [getpwuid](http://man7.org/linux/man-pages/man3/getpwnam.3.html))
- **getgrnam**: To retrieve group/role credentials (similar to POSIX [getgrnam](http://man7.org/linux/man-pages/man3/getgrnam.3.html))
- **getgrgid**: To retrieve group/role credentials (similar to POSIX [getgrgid](http://man7.org/linux/man-pages/man3/getgrnam.3.html))

These APIs, however, are meant to be invoked through [NSS](https://en.wikipedia.org/wiki/Name_Service_Switch) (name service switch).  That is, applications running in containers can simply continue invoking the standard POSIX APIs (`getpwnam()`, `getgrnam()`, etc) and a Host Account Management NSS module will ensure that the credentials get retrieved from **hamd** running on the host. The HAM NSS module (`libnss_ham.so.2`) need be installed and configured (`/etc/nsswitch.conf`) in the containers that require access to the host's Linux database. 

### 1.1.2 Configuration and Management Requirements
An interface and accompanying CLI must be developed for local user management. Local users should be configurable like any other feature: via CLI, REST, and gNMI. Additionally, users may also be created and managed via Linux commands in the Bash shell. This will add additional complexity and require a service to sync between the Redis DB and the Linux user database.


### 1.1.3 Scalability Requirements
Adding authentication to NBIs will result in some performance overhead, especially when doing operations involving asymmetric cryptography. Care should be taken to leverage performance-enhancing features of a protocol wherever possible.

#### 1.1.3.1 REST Server
- Persistent HTTP connections can be used to preserve TCP sessions, thereby avoiding handshake overhead.
- TLS session resumption can be used to preserve the TLS session layer, thereby avoiding TLS handshake overhead and repeated authentication operations (which can involve expensive asymmetric cryptographic operations)
- Token-based authentication via JSON Web Tokens (JWT) will be used to preserve sessions for users who have already authenticated with password-based authentication, so that they do not need to constantly re-use their passwords.

#### 1.1.3.2 gNMI Server
- TLS session resumption can be used to preserve the TLS session layer, thereby avoiding TLS handshake overhead and repeated authentication operations (which can involve expensive asymmetric cryptographic operations)

#### 1.1.3.3 Translib
- Translib will cache all the user information along with the privilege and resource information to avoid the overhead of querying them every time we receive a request.
- Will rely on notification to update any change in the user information, privilege or resource information

### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach
The code will extend the existing Klish (CLI) and REST Server modules in the sonic-mgmt-framework repository. Klish will be extended to enable authentication to the REST server (depending on the ultimately chosen approach), and the REST Server will need to be extended to map transactions to a user and pass that username data to the Translib.

The gNMI server, which currently exists in the sonic-telemetry repository, needs to support passing the username down to Translib as well.

The Translib code (also in sonic-mgmt-framework) will be extended to support RBAC via Linux Groups. It will receive username data from the REST/gNMI NBIs and perform the Group lookup for a given user.

For user management, a service must run on the host to sync the Redis User DB with the Linux user database and vice-versa.

### 1.2.2 Container
SONiC Management Framework, gNMI Telemetry containers

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Enterprise networks that enforce authentication for their management interfaces.

## 2.2 Functional Description
This feature enables authentication and Role-Based Access Control (RBAC) on the REST and gNMI programmatic interfaces that are provided by the SONiC Management Framework and Telemetry containers. With respect to authentication, these programmatic interfaces will support password-based authentication with tokens, and certificate-based authentication.

Since the Klish CLI in the management framework communicates with the REST server in the back-end, the solution will also be extended to support REST authentication.

RBAC will be enforced centrally in the management framework, so that users accessing the system through varying interfaces will be limited to the same, consistent set of operations and objects depending on their role. Users' roles will be mapped using Linux Groups.

Users and their role (group) assignments may be managed via Linux tools or the NBIs.

# 3 Design
## 3.1 Overview
(TODO/DELL: Draw a picture)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
N/A

### 3.2.2 APP DB
N/A

### 3.2.3 STATE DB
N/A

### 3.2.4 ASIC DB
N/A

### 3.2.5 COUNTER DB
N/A

### 3.2.6 USER DB
A new Redis DB will be introduced to hold RBAC related tables. The User DB will have the following tables :
* **UserTable**

  This table contains the username to role mapping needed for enforcing the authorization checks.  It has the following columns :
    * *user* : This is the username being authorized. This is a string.
    * *tenant* : This contains the tenant with which the user is associated. This is a string
    * *role* : This specifies the role associated with the username in the tenant. This is a comma separated list of strings.
      The UserTable is keyed on <***user, tenant***>.

  **Note**: The UserTable will _not_ store users' salted+hashed passwords due to security concerns surrounding access restrictions to the DB; instead, that information will be maintained in `/etc/shadow` as per Linux convention.

* **PrivilegeTable**

  This table has provides the information about the type of operations that a particular role is authorized to perform. The authorization can be performed at the granularity of a feature, feature group, or the entire system. The table has the following columns :
    * *role* : The role associated with the user that is being authorized. This is a string.
    * *feature* : This is feature that the role is being authorized to access. The granularity of the feature can be :
        * *feature* - A logical grouping of multiple commands. If the user is authorized to access a particular feature, the column contains the tag associated with that feature. (More on tagging later. This will be implemented in Phase 2 of RBAC.)
        * *feature-group* - A logical grouping of multiple features. If the user is authorized to a feature-group, the column contains the name of the feature-group. (More on feature-group later. This will be implemented in Phase 2 of RBAC.)
        * *entire-system* - If the user is being granted access to the entire system, the column contains *all*
    * *permissions* : Defines the permissions associated with the role. This is a string.
        * *none* - This is the default permissions that a role is created with. A role associated with *none* permission cannot access any resources on the system to read, or to modify them.
        * *read-only* - The role only has read access to the resources associated with the *feature*.
        * *read-write* - The role has permissions to read and write (create, modify and delete) the resources associated with the *feature*.
  The PrivilegeTable is keyed on <***role, feature***>

* **ResourceTable**
  (To be implemented in Phase 2)
  Though the resources are statically tagged with the features that they belong to, a ResourceTable is still needed so as to allow for future extensibility. It is possible that in the future, a customer wants a more granular control over the authorization and wants to either sub partition the features or override the default tagging associated with a feature. The ResourceTable will allow for this support in the future. In the Phase 2, this table will be create using the default tagging associated with the resources.
    * *resource* : The xpath associated with the resource being accessed. This is a string.
    * *feature-name* : The tag of the feature this resource belongs to.
  The ResourceTable is keyed on <***resource, feature***>

* **TenantTable**
  (To be implemented in Phase 3 or when Multi-tenancy is introduced)
  In most systems today, a single SONiC system will serve multiple tenants. A tenant is a group of users who have a different privileges for resource instances. As SONiC becomes multitenant, RBAC needs to account for this when authorizing users. The TenantTable is needed to enable this and has the following columns :
    * *resource* : The xpath associated with the resource being accessed. This is a string.
    * *tenant* : The tenant for which the resource partitioning is being done. This is a string.
    * *instances* : The instances of the *resource* allocated to this *tenant*. This is a list of instances.
  The TenantTable is keyed on <***resource, tenant***>

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
N/A

### 3.3.2 Other Process
N/A

## 3.4 SyncD
To facilitate the sync between users in the UserDB and with users in Linux, a service must run on the host that listens for both changes to `/etc/passwd` and changes to UserDB, since users can be created via either interface (UserDB via NBIs / Linux commands).

This service runs a process that uses the POSIX [inotify APIs](http://man7.org/linux/man-pages/man7/inotify.7.html) to register for file system events like changes to `/etc/passwd` and/or `/etc/shadow`.
Another approach would be to have a process started by `systemd` on changes to `/etc/passwd` or `/etc/group`, and that process would simply reconcile the Redis DB with what is found in those files. `systemd` allows starting processes based on file create/delete/modify.

A user can be created either via CLI or REST. It is the responsibility of this service to ensure that when the user information is added to the User DB, the appropriate user and groups are also created in the `/etc/passwd` and `/etc/groups` files.
This way, the User DB information and the Linux groups information is always in sync.

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models
TBD from developer
(TODO/DELL)

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands for User Management
Users may be managed via Linux tools like `useradd`, `usermod`, `passwd`, etc. They may also be managed via configuration.

##### username
`username <name> password <password-string> role <role-string>` -- Configures a user on the system with a given name, password, and role.
* **name** is a text string of 1-32 alphanumeric characters
* **password-string** is a text string of 1-32 alphanumeric characters
* **role-string** is a text string consisting of a role name. In the initial release, the user is recommended to use "admin" and "operator" roles, as other roles will not be supported. A text string is desired instead of keywords so that in the future, more roles may be implemented and expanded.
* Configuring another a user with the same **name** should result in modification of the existing user.

`no username <name>` -- Deletes a user from the system.
* **name** is a text string of 1-32 alphanumeric characters

#### 3.6.2.2 Show Commands
N/A

#### 3.6.2.3 Debug Commands
N/A

#### 3.6.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support
Ability to configure local users via REST API.

# 4 Flow Diagrams
N/A

# 5 Error Handling
## 5.1 REST Server
The REST server should return standard HTTP errors when authentication fails or if the user tries to access a forbidden resource or perform an unauthorized activity.

## 5.2 gNMI server
The gNMI server should return standard gRPC errors when authentication fails.

## 5.3 CLI
Authentication errors will be handled by SSH. However, the CLI must gracefully handle authorization failures from the REST server (the authorization failure would originate from Translib of course). While the CLI will render all of the available commands to a user, the user will actually only be able to execute a subset of them. This limitation is a result of the design decision to centralize RBAC in Translib. Nevertheless, the CLI must inform the user when they attempt to execute an unauthorized command.

## 5.4 Translib
Translib will authorize the user and when the authorization fails will return appropriate error string to the REST/gNMI server.

If a user authenticates but is not part of one of the pre-defined groups, they will not be allowed to do anything at all on the system.

# 6 Serviceability and Debug
All operations performed by NBIs (CLI commands, REST/gNMI operations) should be logged/audited with usernames attached to the given operation(s) performed.

Initially, users who are remotely authenticated will share a common role-specific username, so there will be a limitation here.  

# 7 Warm Boot Support
N/A

# 8 Scalability
See previous section 1.1.3: Scalability Requirements

# 9 Unit Test

### Table 3: Test Cases
| **Test Case**                 | **Description**                         |
|:--------------------------|:-------------------------------------|
| REST with password | Authenticate to REST server with username/password and perform some operations |
| REST with token | Perform subsequent operations with token, ensure username/password are not re-prompted |
| REST authorized RBAC | Perform authorized operations as both `Admin` and `Operator` via REST |
| REST unauthorized RBAC | Attempt unauthorized operations as both `Admin` and `Operator` via REST |
| CLI with password | SSH to the system with username/password and execute some commands |
| CLI with RSA | SSH to the system with pubkey and execute some commands |
| CLI authorized RBAC | SSH to the system and perform authorized commands |
| CLI unauthorized RBAC | SSH to the system and perform unauthorized commands |
| RBAC no-group | Create a user and assign them to a non-predefined group; make sure they can't perform any operations |
| gNMI authentication | Test the same authentication methods as REST, but for gNMI instead |
| gNMI authorization | Test the same authorization as REST, but for gNMI instead |
