# Declarative Local User Management

## Revision

| Rev | Date           | Author      | Change Description                                                                                                                                   |
|:---:|:--------------:|:-----------:|:----------------------------------------------------------------------------------------------------------------------------------------------------:|
| 1.0 | June 16, 2025  | Manoharan Sundaramoorthy   | Initial HLD                                                                                                                                          |


## 1. Scope
This document describes the high-level design for a new feature that provides a declarative and persistent method for managing local user accounts on a SONiC device. This feature allows administrators to define local users, including their roles, password hashes, SSH keys, and **security policies** including **login attempt limits**.

This ensures that local user accounts are consistently applied with robust security postures and persist across reboots and upgrades.

## 2. Definitions/Abbreviations

| Abbreviation | Definition                                                                |
|:------------:|:--------------------------------------------------------------------------|
| **`userd`** | The new User Daemon proposed in this design.                              |
| **PAM** | Pluggable Authentication Modules                                          |


## 3. Overview
This feature introduces a new dedicated daemon, **`userd`**, which manages the full lifecycle of local users based on definitions in `CONFIG_DB`. It simplifies management by providing a user-friendly CLI, mapping abstract roles (`administrator`, `operator`) to specific Linux groups, and enforcing security policies. This provides a solution for managing secure, persistent local user accounts.

**Implementation Language:** The `userd` daemon will be implemented in **C++** to ensure optimal memory usage and performance, consistent with other SONiC system daemons.

## 4. Requirements
### 4.1 Functional Requirements
1.  The system must allow an administrator to define a local user account declaratively.
2.  The user definition must support:
    * Username and a pre-hashed password.
    * A role, limited to either **`administrator`** or **`operator`**.
    * Authorized SSH keys (statically defined).
3.  The system must map roles to underlying Linux groups:
    * `administrator`: members of `sudo`, `docker`, `redis` and `admin` groups.
    * `operator`: members of a standard, non-privileged and would belong to `users` group.
4.  The system will **auto-generate** a unique UID for each new user.
5.  There should be atleast one user configured in the role of `administrator`
6.  **Admin User Requirement:**
    * The **`admin`** user (or the user specified during compilation) must NOT be included in the `init_cfg.json` to avoid overwriting existing configurations.
    * Before enabling the feature, users must run `config user import-existing` to import existing Linux users (including admin) into CONFIG_DB.
    * The feature **cannot** be enabled unless at least one administrator user exists in CONFIG_DB.
    * The admin user can be modified or disabled or deleted through standard CONFIG_DB operations once managed.
7.  **Security Policy Requirements:**
    * **Login Attempts:** The system must support configuring a global maximum number of failed login attempts per role before accounts are temporarily locked.
8.  User accounts and their configurations must persist across system reboots and upgrades.
9.  **System Consistency:** On startup, the system must perform a consistency check to ensure Linux users match CONFIG_DB definitions and automatically remove any users that were added directly to Linux (bypassing CONFIG_DB).

## 5. Architecture Design
The architecture centers on the new `userd` daemon. This daemon will now interact with several core Linux subsystems to enforce the configured security policies.

**Feature Control:**
* **Disabled by Default:** The declarative local user management feature is **disabled by default** to ensure no impact on existing SONiC deployments.
* **Feature Flag:** The feature is controlled by the `local_user_management` field in `DEVICE_METADATA|localhost` (values: `enabled` or `disabled`).
* **Daemon Lifecycle:** The `userd` daemon only starts when the feature is explicitly enabled, ensuring zero impact when disabled.

**`userd`'s Points of Interaction (when enabled):**
1.  **CONFIG_DB:** Single source of truth for user configuration and global security policies.
2.  **Core User Files:** `/etc/passwd`, `/etc/shadow`, `/etc/group` for basic user identity.
3.  **PAM Configuration (`/etc/security/faillock.conf`):** To configure failed login attempt thresholds that lock individual user accounts via `pam_faillock`.

## 6. High-Level Design

### 6.1 `userd` Daemon
The `userd` daemon's logic will be expanded to manage security configurations idempotently.

**Startup Consistency Check:**
* **System Reconciliation:** On startup, `userd` will perform a consistency check to ensure that all local users in the Linux system (`/etc/passwd`, `/etc/shadow`, `/etc/group`) match the definitions in CONFIG_DB.
* **Cleanup of Unmanaged Users:** Any users found in the Linux system that are not defined in CONFIG_DB (except for system users like `root`, `daemon`, etc.) will be automatically removed to maintain consistency. Note: Only local users that are managed will be cleaned up. This is achieved by making the managed users part of a special group `local_mgd`, ensuring that other users are not intentionally removed.
* **CONFIG_DB as Source of Truth:** This ensures that CONFIG_DB remains the single source of truth for user management and prevents configuration drift.

**Feature Enablement Process:**
* **Initial State:** When the feature is disabled (default), existing SONiC user management continues unchanged.
* **Required Workflow:**
  1. Run `config user import-existing --dry-run` to preview what will be imported
  2. Run `config user import-existing` to import existing users into CONFIG_DB (preserving passwords and configurations)
  3. Review imported users with `show user` command
  4. Verify at least one administrator user exists in CONFIG_DB
  5. Enable the feature with `config user feature enabled`
  6. The `userd` daemon starts and begins managing the imported users
* **Prerequisite:** The feature **cannot** be enabled unless at least one administrator user exists in CONFIG_DB. The `config user import-existing` command must successfully import at least one user with administrator role (users in sudo/admin groups) before feature enablement is allowed.

**Admin User Requirement:**
* **Prerequisite for Enablement:** At least one administrator user must exist in CONFIG_DB before the feature can be enabled.
* **Import Process:** Run `config user import-existing` to import existing users (including admin) into CONFIG_DB, preserving their current configurations (passwords, SSH keys, etc.).
* **Standard Management:** Once imported into CONFIG_DB, the admin user is managed through the same CONFIG_DB interface as other users.

**User Management Process:**
* **Group Membership:** All users managed by `userd` are automatically added to the special group `local_mgd` to identify them as managed users.
* **Lifecycle Management:** When users are created, modified, or imported, they are added to the `local_mgd` group to ensure proper tracking and cleanup operations.

**Configuration File Hierarchy:**
* **`init_cfg.json`:** Contains `DEVICE_METADATA|localhost` with `local_user_management` field set to `disabled` by default. Does NOT include any LOCAL_USER entries to avoid overwriting existing user configurations (e.g., changed passwords) during feature enablement.
* **`golden_config_db.json`:** Optional site-specific configuration file that can enable the feature and provide initial user configurations when used with `config load_minigraph --override_config`.
* **Configuration Precedence:** When both files are present, `golden_config_db.json` takes precedence over `init_cfg.json` during minigraph reload operations with override enabled.
* **Feature Enablement Workflow:** To enable the feature, users must first import existing users with `config user import-existing`, then enable the feature with `sudo config user feature enabled`. This ensures existing user configurations (including password changes) are preserved.

**User Account Management:**
* **Account Status Control:** `userd` will monitor the `enabled` attribute for each user. When `enabled` is `false`, it will change the user's shell to `/usr/sbin/nologin` to completely disable the account. When `enabled` is `true`, it will set the shell to `/bin/bash`.
* **User Directory and Shell Configuration:** Users have home directory `/home/<username>/` and default shell `/bin/bash`.
* **Home Directory Management:** When users are deleted, home directories are preserved (standard `userdel` behavior). Administrators can manually remove home directories if needed.

**Migration and Import Logic:**

* **User Discovery and Import:**
    * `userd` will scan `/etc/passwd` for users within the configurable UID range (default: 1000-60000)
    * For each discovered user, it will read the password hash from `/etc/shadow`
    * Role assignment is determined by group membership analysis:
      - Users in `sudo`, `docker`, `redis`, or `admin` groups are assigned `administrator` role
      - All other users are assigned `operator` role
    * SSH keys are imported from `~/.ssh/authorized_keys` if present
    * System users (UID < 1000) and users already in CONFIG_DB are skipped

* **Migration Safety Features:**
    * **Dry-run Mode:** Preview import results without making changes
    * **UID Range Filtering:** Only import users within specified UID ranges
    * **Conflict Detection:** Skip users already managed by CONFIG_DB
    * **Validation:** Ensure at least one administrator user exists after import
    * **Rollback Capability:** Import can be undone by disabling the feature

**New Logic for Security Policies:**

* **To enforce Login Attempts:**
    * `userd` will manage the PAM configuration file at `/etc/security/faillock.conf`.
    * For role-based limits (e.g., administrators with limit of 5), it will configure different thresholds based on user group membership.
    * When a user exceeds their role's failed attempt limit, `pam_faillock` will lock that specific user account.
    * `userd` will be responsible for ensuring the PAM stack is configured to use `pam_faillock` with role-based policies.
    * **PAM vs SSH Configuration:** The `pam_faillock` configuration in `/etc/security/faillock.conf` differs significantly from SSH's `MaxAuthTries` in `/etc/ssh/sshd_config`:

      **SSH MaxAuthTries (`/etc/ssh/sshd_config`):**
      - Controls attempts **per SSH connection session** before dropping the connection
      - Default value is typically 6 attempts
      - Only affects SSH connections, not console or other login methods
      - Connection-scoped: user can immediately reconnect and get another set of attempts
      - No persistent account lockout - just drops the current connection

      **PAM faillock (`/etc/security/faillock.conf`):**
      - Controls **total failed attempts across all login methods** (SSH, console, serial, etc.)
      - Provides **persistent account lockout** that survives connection drops and reboots
      - Account remains locked until administrator intervention or timeout expires
      - System-wide enforcement regardless of login method
      - Can be configured with different policies per user group/role

      **How they work together:**
      - SSH may drop a connection after `MaxAuthTries` failed attempts
      - But `pam_faillock` tracks total failures for each individual user across all connections and methods
      - Once `pam_faillock` threshold is reached, that specific user account is locked even for new SSH connections
      - This provides layered security: connection-level (SSH) + account-level (PAM) protection

## 7. SAI API
No SAI API changes are required.

## 8. Configuration and Management
### 8.1 Config DB Enhancements
The `LOCAL_USER` table schema is defined for individual user accounts, and a new `LOCAL_ROLE_SECURITY_POLICY` table is added for global role-based security policies.

**Schema:**
```json
// Example for CONFIG_DB
{
    "FEATURE": {
        "LOCAL_USER_MANAGEMENT": {
            "state": "disabled"
        }
    },
    "LOCAL_USER": {
        "admin": {
            "role": "administrator",
            "password_hash": "$6$salt$hash_of_YourPaSsWoRd",
            "ssh_keys": ["ssh-rsa AAA..."],
            "enabled": true
        },
        "newadmin": {
            "role": "administrator",
            "password_hash": "hashed_password",
            "ssh_keys": ["ssh-rsa BBB..."],
            "enabled": true
        },
        "showuser": {
            "role": "operator",
            "password_hash": "hashed_password",
            "ssh_keys": ["ssh-rsa CCC..."],
            "enabled": false
        }
    },
    "LOCAL_ROLE_SECURITY_POLICY": {
        "administrator": {
            "max_login_attempts": 5
        },
        "operator": {
            "max_login_attempts": 3
        }
    }
}
```

**DEVICE_METADATA Table (localhost entry):**
* `local_user_management` (string, optional): `enabled` or `disabled`. Controls whether the declarative local user management feature is active. Defaults to `disabled` if not specified.

**LOCAL_USER Table (only active when feature is enabled):**
* `role` (string, required): `administrator` or `operator`.
* `password_hash` (string, optional): The hashed password. Defaults to `"!"` (no password).
* `ssh_keys` (optional): List of SSH public keys for the user. No limits are imposed on the number of SSH keys.
* `enabled` (boolean, optional): Whether the user account is enabled. Defaults to `true` if not specified. When `false`, user shell is set to `/usr/sbin/nologin`.
* **Validation:** Each user must have either a valid password hash (not starting with `"!"`) or at least one SSH key.

**LOCAL_ROLE_SECURITY_POLICY Table (only active when feature is enabled):**
* **`max_login_attempts`** (integer, optional): Number of failed login attempts before accounts with this role are locked.

**Notes:**
* Session timeouts are managed by the system's default timeout policy and are not configurable per user.
* **Password Hash Generation:** Password hashes can be generated using `mkpasswd` command-line utility or programmatically using libraries like `passlib` in Python for NETCONF/RESTCONF implementations. **Note:** Modern Debian 12 systems use **Yescrypt** as the default hash function.
* **Integration with Password Hardening:** For CLI-created passwords (using `--password-prompt`), the system will validate that passwords meet any configured password hardening requirements before hashing and storing. When a pre-computed hash is provided (using `--password-hash`), it is the administrator's responsibility to ensure the original password met hardening requirements, as the hash cannot be reverse-validated.
* **Password Security and Logging:** **IMPORTANT:** All password handling must ensure passwords are never logged in plaintext:
  - CLI commands must not echo passwords to terminal or log them in bash history
  - Syslog and auth logs must never contain plaintext passwords
  - Memory containing plaintext passwords must be cleared immediately after hashing
* **CONFIG_DB Security:** To prevent unauthorized access to password hashes:
  - `/etc/sonic/config_db.json` file permissions changed from `644` to `640` (root:redis)
  - Password hashes only visible in show commands when run with `sudo` privileges
  - `show user` displays usernames only, `sudo show user` displays hashes
  - `show runningconfiguration` redacts password_hash fields unless run with `sudo`
* The CLI provides both `--password-hash` (for pre-hashed passwords) and `--password-prompt` (for interactive secure password entry) options for improved security and usability.
* **CONFIG_DB as Source of Truth:** On startup, `userd` performs a consistency check and removes any users that were added directly to Linux (bypassing CONFIG_DB) to ensure CONFIG_DB remains the authoritative source for user management.
* **User Account Status:** When `enabled` is set to `false`, `userd` will change the user's shell to `/usr/sbin/nologin` to completely disable the account. When `enabled` is `true` (default), the shell is set to `/bin/bash`.
* **Complete Account Disabling:** Disabled accounts cannot login via any method (password, SSH keys, console) providing complete security when accounts need to be temporarily deactivated.
* **Role-Based Security Policies:** Security policies are applied per role (administrator/operator) rather than per user for simplified management, consistent security posture, and scalability.
* **Account Disabling Use Cases:** The `enabled: false` feature supports real operational needs including temporary leave, security incidents, onboarding/offboarding workflows, and compliance requirements.
* **Administrator Availability:** At least one administrator user must remain enabled at all times to prevent complete loss of administrative access. This constraint is enforced by the Yang model.
* **Admin User Requirement:** The `admin` user is NOT included in `init_cfg.json` to avoid overwriting existing configurations. Users must follow the proper enablement sequence: (1) run `config user import-existing` to import existing users including admin (preserving any password changes), (2) enable the feature with `sudo config user feature enabled`. The feature **cannot** be enabled unless at least one administrator user exists in CONFIG_DB. This ensures existing user configurations are never lost during feature enablement.
* **TACACS+/RADIUS Compatibility:** This local user management feature operates independently of and is fully compatible with existing TACACS+ and RADIUS authentication systems. Local users are managed through standard Linux PAM authentication stack, which can coexist with remote authentication methods. The authentication order and fallback behavior are controlled by existing AAA configuration in CONFIG_DB.

### 8.2 Yang Model Enhancements
```
module sonic-user {
    yang-version 1.1;
    namespace "http://sonicproject.com/sonic-user";
    prefix "sonic-user";

    import sonic-ext {
        prefix "sonic-ext";
    }

    // Common typedef for user roles
    typedef user-role {
        type enumeration {
            enum "administrator" {
                description "Grants administrative privileges (e.g., member of sudo, docker groups).";
            }
            enum "operator" {
                description "Grants operator-level (read-only or limited) privileges.";
            }
        }
        description "User role that determines group memberships, privileges, and applicable security policies.";
    }

    // Top-level container for the User feature
    container sonic-user {
        description "Top-level container for local user management configuration";

        list LOCAL_USER_LIST {
            key "username";
            description "List of declaratively managed local users.";

            must "count(../LOCAL_USER_LIST[role='administrator' and (not(enabled) or enabled='true')]) >= 1" {
                error-message "At least one administrator user must remain enabled.";
            }

            leaf username {
                type string {
                    pattern '[a-z_][a-z0-9_-]*[$]?' {
                        error-message "Invalid username. Must start with a lowercase letter or underscore, followed by lowercase letters, numbers, underscores, or hyphens.";
                    }
                    must ". != 'root'" {
                        error-message "Username cannot be 'root'.";
                    };
                    length 1..32;
                }
                description "The username for the local account.";
            }

            leaf role {
                type user-role;
                mandatory true;
                description "The role assigned to the user, which determines their group memberships and privileges.";
            }

            leaf password_hash {
                type string;
                default "!";
                description "The hashed password string for the user, as found in /etc/shadow. Defaults to '!' (no password). Password hashes can be generated using 'mkpasswd' utility or programmatically using libraries like 'passlib'. To disable an account, use the 'enabled' attribute instead of prepending '!' to the password hash.";
            }

            leaf-list ssh_keys {
                type string;
                description "A list of full public SSH key strings.";
            }

            leaf enabled {
                type boolean;
                default true;
                description "Whether the user account is enabled. When false, the user shell is set to /usr/sbin/nologin to completely disable the account.";
            }

            must "not(starts-with(password_hash, '!')) or count(ssh_keys) > 0" {
                error-message "User must have either a valid password hash (not starting with '!') or at least one SSH key.";
            }
        }

        list LOCAL_ROLE_SECURITY_POLICY_LIST {
            key "role";
            description "Global security policies applied to users based on their role.";

            leaf role {
                type user-role;
                description "The role for which this security policy applies.";
            }

            leaf max_login_attempts {
                type uint32 {
                    range "1..1000";
                }
                description "Maximum number of failed login attempts before accounts with this role are locked. If not set, system defaults apply.";
            }
        }
    }
}
```

### 8.3 CLI Enhancements
The CLI is enhanced with user management and global security policy commands.

**Feature Control Commands:**
```
sudo config user feature enabled
sudo config user feature disabled
```
* Enable or disable the declarative local user management feature
* **Important:** Before enabling, users must first run `config user import-existing` to import existing users into CONFIG_DB
* When disabling, the feature stops managing users but doesn't remove existing Linux users

**Migration Commands:**
```
config user import-existing [--dry-run] [--uid-range <min>-<max>]
```
* Import existing Linux users into CONFIG_DB LOCAL_USER table
* `--dry-run`: Show what would be imported without making changes
* `--uid-range`: Specify UID range to import (default: 1000-60000)
* Automatically detects user roles based on group membership:
  - Users in `sudo`, `docker`, `redis`, or `admin` groups → `administrator` role
  - Other users → `operator` role
* Preserves existing password hashes from `/etc/shadow`
* Skips system users (UID < 1000) and users already in CONFIG_DB

**User Add Command:**
```
config user add <username> --role <role>
                          [--password-hash <hash> | --password-prompt]
                          [--ssh-key <key>]
                          [--disabled]
```
* Multiple `--ssh-key` flags can be provided to build a list.
* Use `--password-hash` to provide a pre-hashed password directly.
* Use `--password-prompt` to enter the password securely through an interactive prompt (password will be hashed automatically).
* Use `--disabled` to create the account in disabled state. Accounts are enabled by default.
* If neither password option is provided, the user account will be created with password login disabled (password set to `!`).

**User Delete Command:**
```
config user del <username>
```

**User Modify Commands:**

**Basic Modify:**
```
config user modify <username> [--password-hash <hash> | --password-prompt | --remove-password]
                              [--enabled | --disabled]
```

**SSH Key Management:**
```
config user modify <username> --add-ssh-key <key>
config user modify <username> --remove-ssh-key <key_identifier>
config user modify <username> --clear-ssh-keys
```

**Options:**
* `--password-hash <hash>`: Set a pre-hashed password directly
* `--password-prompt`: Enter password securely through interactive prompt (hashed automatically)
* `--remove-password`: Remove password authentication (sets password_hash to "!")
* `--enabled` / `--disabled`: Change account status
* `--add-ssh-key <key>`: Add a new SSH public key to the user
* `--remove-ssh-key <key_identifier>`: Remove specific SSH key (by key comment/identifier or partial match)
* `--clear-ssh-keys`: Remove all SSH keys from the user

**Examples:**
```bash
# Change password interactively
config user modify alice --password-prompt

# Remove password authentication (SSH keys only)
config user modify alice --remove-password

# Add an SSH key
config user modify alice --add-ssh-key "ssh-rsa AAAAB3... alice@workstation"

# Remove specific SSH key by comment
config user modify alice --remove-ssh-key "alice@workstation"

# Remove specific SSH key by partial key match
config user modify alice --remove-ssh-key "AAAAB3NzaC1yc2E"

# Clear all SSH keys
config user modify alice --clear-ssh-keys

# Disable user account
config user modify alice --disabled
```

**Validation:**
* Users must retain at least one authentication method (password or SSH key)
* Removing the last authentication method will fail with an error
* The `--remove-password` and `--clear-ssh-keys` commands cannot be used together unless adding a new authentication method in the same command

**Security Policy Commands:**
```
config user security-policy <role> --max-login-attempts <count>
```
* Configure global login attempt limits for a specific role (`administrator` or `operator`).

```
show user security-policy [<role>]
```
* Display current security policies for all roles or a specific role.

**Password Prompt Implementation:**
When `--password-prompt` is used, the CLI will:
1. Display a secure password prompt (e.g., "Enter password for user <username>:")
2. Hide password input (no echo to terminal)
3. Prompt for password confirmation (e.g., "Confirm password:")
4. Validate that both entries match
5. Hash the password using the same algorithm as `mkpasswd` (e.g., Yescrypt on Debian 12)
6. Store only the hashed password in CONFIG_DB
7. Clear the plaintext password from memory immediately after hashing

**Security Requirements:**
- Passwords must never appear in bash history, syslog, auth logs, or any log files
- All password handling must use secure memory practices

**Show Commands:**
```
show user [<username>]                    # Shows usernames and roles only
sudo show user [<username>]               # Shows usernames, roles, and password hashes
show user security-policy [<role>]        # Shows security policies
```
* **Security Note:** Password hashes are only displayed when commands are run with `sudo` privileges to prevent unauthorized access to hash values.

## 9. Testing Requirements
### New System Test cases
* **Feature Enablement/Disablement:**
  * Verify the feature is disabled by default and `userd` daemon is not running.
  * Enable the feature and verify `userd` daemon starts and imports existing users.
  * Create local users manually, enable the feature, and verify they are imported into CONFIG_DB.
  * Disable the feature and verify `userd` daemon stops but existing Linux users remain unchanged.
  * Re-enable the feature and verify it resumes management of previously configured users.

* **Migration and Import Testing:**
  * Create test users with `useradd` and `usermod` commands with different group memberships.
  * Run `config user import-existing --dry-run` and verify correct role assignment preview.
  * Run `config user import-existing` and verify users are correctly imported into CONFIG_DB.
  * Verify administrator users (in sudo/admin groups) get `administrator` role.
  * Verify other users get `operator` role.
  * Test UID range filtering with `--uid-range` parameter.
  * Verify system users (UID < 1000) are not imported.
  * Test import of SSH keys from `~/.ssh/authorized_keys` files.
  * Verify users already in CONFIG_DB are skipped during import.

* **Global Login Attempts Policy:**
  * Configure `administrator` role with `max_login_attempts` of 5 and `operator` role with 3.
  * Create users with both roles and verify that login attempt limits are enforced according to their role.
  * Attempt to log in with incorrect passwords and verify accounts are locked based on their role's policy.
  * Verify `faillock --user <username>` shows the correct state for users of different roles.

* **Password Management:**
  * Test user creation with `--password-hash` option and verify the hash is stored correctly.
  * Test user creation with `--password-prompt` option and verify the password is hashed and stored securely.
  * Verify that passwords entered via prompt are not logged in command history.
  * Test password modification using both hash and prompt methods.
  * Attempt to create a user with a password hash starting with `!` and verify it fails with an appropriate error message.

* **Account Status Management:**
  * Create a user with `--disabled` and verify the user shell is set to `/usr/sbin/nologin`.
  * Enable a disabled user and verify the shell is set to `/bin/bash`.
  * Test that disabled users cannot login via any method (password, SSH keys, console).
  * Verify that the `enabled` attribute defaults to `true` when not specified.
  * Test that disabled users receive informative "This account is currently not available" message.

* **Administrator Availability Constraint:**
  * Attempt to disable the last remaining enabled administrator user and verify it fails with an appropriate error.
  * Verify that at least one administrator user can always be enabled when multiple administrators exist.
  * Test that the constraint is enforced during user deletion of administrator accounts.

* **Admin User Requirement:**
  * Verify that `init_cfg.json` does NOT contain any LOCAL_USER entries.
  * Attempt to enable the feature without any administrator users in CONFIG_DB and verify it fails with an appropriate error.
  * Change the admin user password, run `config user import-existing`, enable the feature, and verify the password change is preserved.
  * Verify the `admin` user can be modified, disabled, or deleted through standard CONFIG_DB operations once managed.
  * Test the complete workflow: import existing users → verify admin exists in CONFIG_DB → enable feature → verify `userd` manages the imported admin user.

* **Startup Consistency Check:**
  * Create a user directly in Linux using `useradd` (bypassing CONFIG_DB).
  * Restart the `userd` daemon and verify the manually created user is automatically removed.
  * Verify that users defined in CONFIG_DB are preserved and properly configured.
  * Ensure system users (root, daemon, etc.) are not affected by the cleanup process.

* **User Management:** Create users with different roles and verify all security policies are enforced correctly based on role-based policies.

## 10. Future Enhancements

### 10.1 Remote SSH Key Management
Support for dynamically fetching SSH keys from remote URLs could be added in future versions to enable centralized SSH key management.

### 10.2 User Authentication Statistics and Telemetry
Future versions could include comprehensive user authentication statistics and telemetry features:
* **Login Attempt Tracking:** Record successful and failed login attempts per user with timestamps
* **Security Policy Violations:** Track and log security policy violations (e.g., account lockouts, failed attempts)
* **User Activity Metrics:** Monitor user session durations, command usage patterns, and access patterns
* **Telemetry Integration:** Export user management metrics to existing SONiC telemetry infrastructure for monitoring and alerting
* **Audit Logging:** Enhanced audit trails for user management operations and authentication events

## 11. Open/Resolved Issues

None
