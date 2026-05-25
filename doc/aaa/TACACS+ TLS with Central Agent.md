# TACACS+ TLS and Central Client Agent

## Table of Content

- [TACACS+ TLS and Central Client Agent](#tacacs-tls-and-central-client-agent)
  - [Table of Content](#table-of-content)
  - [1. Revision](#1-revision)
  - [2. Scope](#2-scope)
  - [3. Definitions/Abbreviations](#3-definitionsabbreviations)
  - [4. Overview](#4-overview)
  - [5. Requirements](#5-requirements)
    - [5.1 Functional Requirements](#51-functional-requirements)
    - [5.2 Security Requirements](#52-security-requirements)
    - [5.3 Configuration and Management Requirements](#53-configuration-and-management-requirements)
    - [5.4 Scalability and Performance Requirements](#54-scalability-and-performance-requirements)
    - [5.5 Backward Compatibility Requirements](#55-backward-compatibility-requirements)
    - [5.6 Serviceability Requirements](#56-serviceability-requirements)
    - [5.7 Exemptions and Not Supported Items](#57-exemptions-and-not-supported-items)
  - [6. Architecture Design](#6-architecture-design)
    - [6.1 Existing SONiC TACACS+ Architecture](#61-existing-sonic-tacacs-architecture)
    - [6.2 Proposed Architecture](#62-proposed-architecture)
    - [6.3 Component Responsibilities](#63-component-responsibilities)
    - [6.4 Repositories and Modules](#64-repositories-and-modules)
  - [7. High-Level Design](#7-high-level-design)
    - [7.1 Feature Type](#71-feature-type)
    - [7.2 TACACS+ TLS Transport](#72-tacacs-tls-transport)
    - [7.3 TLS Credential Choices](#73-tls-credential-choices)
    - [7.4 Single Connection Model](#74-single-connection-model)
    - [7.5 Ordered Failover and Recovery](#75-ordered-failover-and-recovery)
    - [7.6 Local IPC Interface](#76-local-ipc-interface)
    - [7.7 SONiC ConfigDB Integration](#77-sonic-configdb-integration)
    - [7.8 Secret and Certificate Material](#78-secret-and-certificate-material)
    - [7.9 Error Handling](#79-error-handling)
    - [7.10 Serviceability and Debug](#710-serviceability-and-debug)
    - [7.11 Linux Packaging and Runtime Dependencies](#711-linux-packaging-and-runtime-dependencies)
  - [8. SAI API](#8-sai-api)
  - [9. Configuration and Management](#9-configuration-and-management)
    - [9.1 Manifest](#91-manifest)
    - [9.2 CLI/YANG Model Enhancements](#92-cliyang-model-enhancements)
    - [9.3 Config DB Enhancements](#93-config-db-enhancements)
    - [9.4 Logs, Counters, and Show Commands](#94-logs-counters-and-show-commands)
  - [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
    - [10.1 Warmboot and Fastboot Performance Impact](#101-warmboot-and-fastboot-performance-impact)
  - [11. Memory Consumption](#11-memory-consumption)
  - [12. Restrictions/Limitations](#12-restrictionslimitations)
  - [13. Testing Requirements/Design](#13-testing-requirementsdesign)
    - [13.1 Unit Test Cases](#131-unit-test-cases)
    - [13.2 System Test Cases](#132-system-test-cases)
    - [13.3 Security Test Cases](#133-security-test-cases)
    - [13.4 sonic-mgmt Test Plan](#134-sonic-mgmt-test-plan)
    - [13.5 Backward Compatibility and Regression Tests](#135-backward-compatibility-and-regression-tests)
  - [14. Open/Action Items](#14-openaction-items)
  - [15. References](#15-references)

## 1. Revision

| Rev | Date | Author | Change Description |
| --- | --- | --- | --- |
| 0.1 | 2026-05-14 | Rodney Persky | Initial split HLD for TACACS+ TLS, single connection mode, and central client agent architecture. |

## 2. Scope

This document describes the high-level design for adding TACACS+ over TLS and a central TACACS+ client agent to SONiC. The goal is to improve management-plane TACACS+ transport security and efficiency while preserving the existing SONiC TACACS+ configuration model and operational behavior.

The scope includes the following items:

- Support TACACS+ over TCP and TACACS+ over TLS 1.3, with TLS mode following [RFC 9887](https://datatracker.ietf.org/doc/rfc9887/).
- Support TACACS+ over TLS 1.3 using server certificate validation, mutual TLS, or TLS 1.3 pre-shared keys.
- Support a single connection model where a central agent reuses an upstream TACACS+ connection for multiple TACACS+ sessions when supported by the server.
- Preserve a dedicated per-request connection mode for compatibility with existing TACACS+ deployments.
- Introduce a host-local central TACACS+ client agent per SONiC compute device that owns upstream transport, TLS state, connection reuse, failover, and Unix domain socket IPC.
- Reuse existing SONiC `TACPLUS|global` and `TACPLUS_SERVER|*` CONFIG_DB rows and add optional backward-compatible parameters for TLS and connection behavior that map toward the [RFC 9950](https://datatracker.ietf.org/doc/rfc9950/) TACACS+ YANG model.
- Define configuration, management, serviceability, testing, and approval requirements for an Alpha-stage feature.

This document does not propose changes to authentication, command authorization, or accounting coverage.

## 3. Definitions/Abbreviations

| Term | Meaning |
| --- | --- |
| AAA | Authentication, Authorization, and Accounting. |
| CONFIG_DB | SONiC Redis-backed configuration database, database index 4. |
| gRPC | Google Remote Procedure Call framework used here only for host-local IPC over UDS. |
| IPC | Inter-process communication. |
| mTLS | Mutual TLS, where both client and server present TLS certificates. |
| protobuf | Protocol Buffers schema language and encoding used for the local IPC contract. |
| PSK | Pre-shared key. In this document it means TLS 1.3 PSK unless otherwise specified. |
| SAI | Switch Abstraction Interface. |
| Single connection | TACACS+ operating model where one upstream transport connection carries multiple sessions identified by TACACS+ session ID. |
| TACACS+ | Terminal Access Controller Access-Control System Plus, as specified by RFC 8907. |
| Central TACACS+ client agent | A host service that owns TACACS+ server configuration, upstream connections, TLS state, failover, and local Unix domain socket IPC for one SONiC compute device. |
| TLS | Transport Layer Security. |
| Transport-security mode | The selected TACACS+ server connection mode over TCP: plain TCP/shared-secret, TLS server authentication, mTLS, or TLS PSK. |
| UDS | Unix domain socket. |
| YANG | Data modeling language used for network configuration models. |

## 4. Overview

SONiC already supports TACACS+ for device administration workflows. Existing TACACS+ support is sufficient for current shared-secret deployments, but it does not provide a complete design for modern TACACS+ over TLS operation.

TLS introduces two design requirements:

1. TACACS+ clients need configuration references for the selected TLS identity and trust material, including trust anchors, client certificates, private keys, PSK identities, and protected secret references.
2. TACACS+ clients should avoid a full TCP and TLS handshake for every request because per-request TLS handshakes add latency and server load.

This HLD proposes a central TACACS+ client agent that owns upstream connections and exposes a local Unix domain socket interface to host consumers on the same SONiC compute device. Local consumers do not need to implement TACACS+ transport, TLS, failover, or reconnect behavior themselves. The agent reads SONiC TACACS+ configuration from CONFIG_DB and provides a compatibility baseline for host-side TACACS+ consumers.

The TLS design treats server certificate validation, mutual TLS, and TLS PSK as TLS credential choices available through the same configuration and management model. A SONiC implementation of this feature must include the TLS library support needed for the credential choices, PSK key exchange policy, and PSK-DHE group configuration accepted by configuration.

The first delivery stage is proposed as an Alpha-stage SONiC feature. It should be disabled by default, preserve existing TACACS+ operation when disabled, and advance only after sonic-mgmt test coverage and community review are complete.

## 5. Requirements

### 5.1 Functional Requirements

- The implementation shall support existing TACACS+ shared-secret operation for compatibility with current TACACS+ deployments.
- The implementation shall support TACACS+ over TLS 1.3 for upstream server communication.
- The implementation shall support TLS credential choices for server certificate verification using configured trust anchors, mutual TLS using client certificate material, and TLS 1.3 PSK using a PSK identity, protected secret reference, and PSK key exchange policy.
- The implementation shall include TLS library support for every TLS credential choice, PSK key exchange policy, and configured PSK-DHE group that the configuration accepts.
- The implementation shall validate the populated TLS credential choice and reject incomplete TLS identity or trust material.
- The implementation shall support multiple TACACS+ servers using the priority order configured through existing SONiC TACACS+ CLI and CONFIG_DB semantics.
- The implementation shall prefer the first healthy server and fail over to later servers when the preferred server is not reachable.
- The implementation shall periodically probe the preferred server while failed over and return traffic to it when it recovers.
- The implementation shall support a single connection model where one daemon-owned upstream connection can carry multiple TACACS+ sessions.
- The implementation shall support a dedicated connection mode for deployments that require one upstream connection per request.
- The implementation shall expose a local Unix domain socket IPC interface for host consumers to issue TACACS+ requests without each consumer owning upstream TLS and failover behavior.
- The implementation shall read existing SONiC TACACS+ configuration from CONFIG_DB.

### 5.2 Security Requirements

- TLS connections shall authenticate the upstream TACACS+ server according to the configured TLS credential choice.
- Certificate verification shall be disabled only when an explicitly unsafe diagnostic option is selected.
- The design shall not store raw TLS private keys or raw PSK material in plaintext CONFIG_DB fields.
- The feature shall define how certificates, trust anchors, private keys, and PSK material are referenced and protected on the device.
- The daemon IPC endpoint shall be protected by Unix socket permissions on Linux.
- Unsafe TLS options, such as disabling certificate verification, shall be explicit in configuration and visible in logs and show output.
- Sensitive values such as shared secrets, private keys, PSK values, and user passwords shall not be logged or displayed.

### 5.3 Configuration and Management Requirements

- The feature shall be controlled by CONFIG_DB and disabled by default during Alpha maturity.
- Existing `TACPLUS|global` and `TACPLUS_SERVER|*` configuration shall remain valid.
- New TLS-related fields shall be backward compatible and optional.
- The agent shall validate stored SONiC TACACS+ configuration against the TACACS+ model used by the implementation before runtime use.
- New stored CONFIG_DB fields should map cleanly into the TACACS+ YANG model where practical, but compatibility with existing SONiC TACACS+ rows has priority for the first phase.
- CLI changes shall preserve save and restore compatibility with configurations from previous releases.
- CLI commands that change a TACACS+ server between TCP, certificate-based TLS, mTLS, and PSK shall validate the resulting effective server configuration before committing the change.
- The active stored configuration for a TACACS+ server shall map to one valid YANG security and credential choice. Redundant fields from another credential choice shall be rejected rather than ignored.
- YANG model changes shall describe TLS transport, single connection mode, and secret/certificate references, aligned with the TACACS+ YANG model in [RFC 9950](https://datatracker.ietf.org/doc/rfc9950/).
- YANG model changes shall preserve SONiC TACACS+ server priority ordering, using a SONiC extension to RFC 9950 when needed.
- The management model shall allow operators to choose TCP or TLS, and for TLS to configure one credential choice: server certificate validation, mTLS, or PSK. For PSK, the model shall default to PSK-DHE with approved TLS groups, allow optional group constraints, and allow explicit PSK-only interop mode.
- The management model shall allow operators to select persistent connection reuse or dedicated per-request connections.

### 5.4 Scalability and Performance Requirements

- The agent shall avoid a new TCP or TLS handshake for every TACACS+ request when persistent single connection mode is enabled.
- The agent shall serialize reconnect attempts per server so concurrent local clients do not create a connection storm.
- The agent shall debounce CONFIG_DB updates, re-read TACACS+ configuration, validate the complete effective configuration, and hot-reload affected upstream server state without requiring a service restart.
- TLS and failover behavior shall not be in the switching data plane path.
- The feature shall not add SAI dependencies or data plane dependencies.

### 5.5 Backward Compatibility Requirements

- Existing TACACS+ authentication, authorization, accounting, and local fallback configuration shall continue to operate when the central TACACS+ client agent is disabled.
- Existing `TACPLUS|global` and `TACPLUS_SERVER|*` rows shall map to shared-secret TACACS+ behavior when no TLS fields are present.
- Existing SONiC CLI commands shall continue to work unless explicitly changed and documented.
- Device administrators shall be able to disable the central TACACS+ client agent and return to the existing SONiC TACACS+ path.
- Configuration save and restore across upgrade and downgrade paths shall be documented and tested.

### 5.6 Serviceability Requirements

- The agent shall log upstream connection state changes, failover decisions, TLS validation failures, configuration parse errors, and IPC errors.
- The feature shall provide show commands or equivalent diagnostics for daemon health, configured server state, active failover target, and counters.
- The feature shall expose enough information for sonic-mgmt tests to determine whether TCP, TLS credential choices, PSK key exchange and group selection, failover, and single connection paths are active.

### 5.7 Exemptions and Not Supported Items

- This HLD does not propose any SAI API change.
- This HLD does not require switch ASIC or platform vendor API changes.
- This HLD does not remove the existing SONiC TACACS+ implementation in the first phase.
- This HLD does not change command authorization coverage.
- This HLD does not introduce shell command interception or host session enforcement.
- Raw public key TLS server authentication is not supported in the first phase.

## 6. Architecture Design

### 6.1 Existing SONiC TACACS+ Architecture

Existing SONiC TACACS+ workflows integrate with Linux login services and SONiC AAA configuration. In simplified form, host-side TACACS+ consumers use TACACS+ settings derived from CONFIG_DB to communicate with configured TACACS+ servers.

```text
+----------+        +--------------------+        +--------------+
| PAM/AAA  | -----> | SONiC TACACS+      | -----> | TACACS+      |
| consumer |        | configuration      |        | server       |
+----------+        +--------------------+        +--------------+
```

This architecture continues to work for existing shared-secret deployments and remains the compatibility baseline.

### 6.2 Proposed Architecture

The proposed architecture adds a central TACACS+ client agent between host-side consumers and upstream TACACS+ servers.

```text
+----------+       local UDS      +----------------------+       TCP/TLS      +--------------+
| PAM/AAA  | -------------------> | central TACACS+      | =================> | TACACS+      |
| consumer |                      | client agent         | <================= | server       |
+----------+                      +----------+-----------+                    +--------------+
                                             |
                                             | CONFIG_DB read/subscribe
                                             v
                                +-------------------------+
                                | TACPLUS and FEATURE     |
                                | tables in CONFIG_DB     |
                                +-------------------------+
```

The central agent can serve multiple local consumers without each local consumer opening its own upstream TACACS+ connection.

### 6.3 Component Responsibilities

| Component | Responsibility | Lifetime |
| --- | --- | --- |
| Central TACACS+ client agent | Reads TACACS+ configuration, opens upstream TCP/TLS connections, performs ordered failover, exposes local UDS IPC. | Long-running systemd service. |
| Local TACACS+ consumer | Sends TACACS+ requests over local UDS IPC. Examples include PAM, AAA, CLI, or test clients as applicable. | Existing service or one-shot process. |
| Configuration model mapper | Parses and validates TACACS+ YANG or CONFIG_DB input and maps it into runtime server configuration. | Library or service module. |
| SONiC CONFIG_DB adapter | Maps SONiC CONFIG_DB `TACPLUS` tables into the runtime configuration model. | Library or service module. |
| Diagnostic TACACS+ client | Sends test TACACS+ requests directly or through the agent. | One-shot command. |

### 6.4 Repositories and Modules

The expected SONiC implementation requires changes in the following areas:

| Repository or area | Expected change |
| --- | --- |
| SONiC doc repository | This HLD and any related test plan documentation. |
| sonic-buildimage | Integrate the selected Debian package source or package feed, and provide systemd unit, feature table entry, and build or installation integration. |
| sonic-utilities | CLI changes for configuration and show commands, if accepted by review. |
| sonic-yang-models | YANG changes for TLS transport fields, single connection mode, secret/certificate references, and SONiC priority-order preservation. |
| sonic-mgmt | Test plan and automated tests for configuration, TLS, failover, and rollback. |
| Implementation repository | Source for daemon, local IPC contract, ConfigDB mapping, tests, and SONiC integration assets. The source can remain in a separate repository if SONiC consumes it through a reviewed source import, submodule, or approved package source. |

## 7. High-Level Design

### 7.1 Feature Type

The proposed first phase is a built-in optional SONiC host service controlled by the SONiC `FEATURE` table and TACACS+ CONFIG_DB state. It is packaged as a Debian package and runs on the SONiC host. It is not a SAI feature and does not require changes to switch ASIC programming.

The service scope is one central agent per SONiC compute device or SONiC OS instance. It is not a chassis-wide singleton across multiple compute devices and is not a per-ASIC service. The first phase assumes the agent runs where the local Redis-backed CONFIG_DB and credential provisioning mechanisms, such as ACMS or equivalent protected credential storage, are available.

The remaining packaging integration question is whether SONiC CI builds the Debian package from source integrated into sonic-buildimage, such as a submodule or source import, or installs it from an approved package source. In either case, the runtime artifact is a Debian package with declared dependencies.

### 7.2 TACACS+ TLS Transport

The central TACACS+ client agent uses TCP for all upstream TACACS+ server communication. This HLD uses transport-security mode to distinguish plain TACACS+ over TCP from TACACS+ over TLS 1.3 on TCP:

1. Plain TACACS+ over TCP using the [RFC 8907](https://datatracker.ietf.org/doc/rfc8907/) shared-secret obfuscation model.
2. TACACS+ over TLS 1.3 on TCP using the [RFC 9887](https://datatracker.ietf.org/doc/rfc9887/) profile. TLS can use server certificate validation, mTLS, or TLS 1.3 PSK.

When certificate-backed TLS is enabled, the agent validates the server certificate using configured trust anchors and the configured server name. SNI is independent of the selected TLS credential choice and shall be sent when enabled and when a server domain name is configured, including TLS PSK deployments where the server uses SNI for virtual hosting or PSK selection.

The TLS transport design shall include these configuration inputs:

| Input | Purpose |
| --- | --- |
| `transport` or equivalent | Select plain TCP or TLS over TCP. |
| `tcp_port` | Select the TCP port for the target transport-security mode. TLS examples in this HLD use port 449. |
| `domain_name` | Server name for certificate verification when certificates are used and for SNI when enabled. |
| `sni_enabled` | Enable or disable SNI. |
| `trust_anchor_ref` | Reference to a trusted CA bundle or certificate object. |
| `certificate_verify` | Enable or disable certificate verification. Unsafe disablement is diagnostic only. |
| `single_connection` | Request persistent connection reuse when the server supports it. |
| `psk_key_exchange` | Optional interop override for TLS 1.3 PSK key exchange policy when PSK is active. |
| `psk_key_exchange_groups` | Optional approved TLS group list for PSK-DHE; providing groups implies TLS 1.3 `psk_dhe_ke`. |

The existing shared-secret `passkey` remains valid for plain TCP and for deployments where the TACACS+ server still requires a TACACS+ shared secret inside the TLS-protected channel.

### 7.3 TLS Credential Choices

The central agent derives the TLS credential choice from the server configuration shape. The design shall use SONiC credential references or protected file paths for certificate, key, and PSK material rather than raw sensitive values in CONFIG_DB. The working assumption is that ACMS or another SONiC-approved credential provisioning flow places the required material on disk, and the TACACS+ configuration stores references or paths to that protected material.

The configuration model shall make these modes explicit:

| Mode | Required material |
| --- | --- |
| TLS server authentication | Server address, optional domain name, trust anchor file or profile reference. |
| mTLS | TLS server authentication material plus client certificate reference and client private key reference. |
| TLS PSK | PSK identity, protected PSK symmetric key file or credential reference, and optional PSK-DHE group policy. |

The PSK key exchange policy is a PSK sub-mode, not a separate TLS credential choice. The default PSK behavior shall be PSK with ephemeral Diffie-Hellman key exchange, matching TLS 1.3 `psk_dhe_ke`, using a SONiC-approved default TLS group list. Operators may constrain the offered DHE groups with `psk_key_exchange_groups` or an equivalent CLI option such as `--psk-key-exchange-groups`; providing groups implies `psk_dhe_ke`. An explicit `psk-only` mode, matching TLS 1.3 `psk_ke`, exists only for interoperability with servers that require PSK-only TLS 1.3 handshakes.

The implementation shall reject incomplete or ambiguous TLS configurations. For example, a client certificate without a private key, a PSK identity without a PSK symmetric key reference, or a server row containing both mTLS client identity fields and PSK identity fields shall fail validation.

### 7.4 Single Connection Model

In single connection mode, the central agent reuses an upstream connection for multiple TACACS+ sessions. TACACS+ packets are routed by session ID so simultaneous local clients can share a connection without opening a new TCP or TLS connection for every request.

```text
+----------+      local UDS       +------------------+      one TLS connection
| client A | -------------------> |                  | =======================>
+----------+                      | central TACACS+  |      TACACS+ server
+----------+      local UDS       | client agent     | <=======================
| client B | -------------------> |                  |      multiplexed by
+----------+                      +------------------+      session ID
```

Dedicated connection mode remains available. In dedicated mode, a request uses its own upstream connection. This mode is required for compatibility with servers or deployments that do not support persistent single connection operation.

### 7.5 Ordered Failover and Recovery

The agent maintains upstream server state. The preferred server is the first healthy server in the priority order configured by existing SONiC TACACS+ CLI and CONFIG_DB behavior. When the agent maps SONiC TACACS+ rows into the RFC 9950-based model used internally, the implementation must preserve that SONiC priority order, using a SONiC YANG extension when the base RFC 9950 model does not carry the needed ordering field. If the preferred server fails, the agent tries the next server. While using a backup server, the agent periodically probes the preferred server and moves traffic back when it recovers.

The agent shall serialize reconnect attempts for each server. If multiple local requests arrive while a reconnect is in progress, one reconnect attempt is performed and the other requests wait for the result.

### 7.6 Local IPC Interface

Local clients communicate with the central TACACS+ client agent through gRPC over a Unix domain socket. The default Linux endpoint is expected to be a protected path such as `/run/tacacs.sock` or a SONiC-approved equivalent. Network IPC between compute devices is out of scope for the first phase.

The IPC schema shall be defined with protobuf so clients can be written in the language most natural for each SONiC component. gRPC is used only as a host-local IPC mechanism in this design; the upstream TACACS+ server protocol remains TACACS+ over TCP or TACACS+ over TLS on TCP.

The first IPC service exposes unary request/response methods for TACACS+ accounting and authorization operations. Each request carries the local user/session context and operation-specific fields, such as command accounting arguments or authorization arg-value pairs. The agent selects an upstream server, opens or reuses the upstream TACACS+ connection, applies failover, and returns either the TACACS+ server response or a structured service error with retry guidance.

The first IPC contract has the following shape:

```text
service TacacsAgent
  Accounting(AccountingRequest)       -> AccountingReply
  Authorization(AuthorizationRequest) -> AuthorizationReply

AccountingRequest
  user, port, remote_address, command, command_arguments[]

AccountingReply
  result = AccountingResponse { server, status, server_message, data }
         | ServiceError { message, server, retriable }

AuthorizationRequest
  user, port, remote_address, privilege_level, args[]

AuthorizationReply
  result = AuthorizationResponse { server, status, server_message, args[], data }
         | ServiceError { message, server, retriable }

AuthorizationArg
  name, mandatory, value
```

The socket permissions shall restrict access to trusted local users or groups. Host-side consumers, such as SONiC AAA integration modules, CLI diagnostic tools, or test clients, use this IPC surface so they do not need to implement upstream TACACS+ packet framing, TLS handling, single connection negotiation, or failover. When the `tacacs-agent` feature is disabled, existing SONiC TACACS+ paths continue to use the current implementation and do not connect to the agent.

### 7.7 SONiC ConfigDB Integration

The central TACACS+ client agent shall map existing SONiC `TACPLUS|global` and `TACPLUS_SERVER|*` rows into its runtime server configuration model.

Existing rows such as the following remain valid:

```text
TACPLUS|global
    auth_type   "pap"
    timeout     "5"
    passkey     "shared-secret"
    src_intf    "Management0"

TACPLUS_SERVER|192.0.2.10
    priority    "1"
    tcp_port    "49"
    timeout     "10"
    passkey     "server-secret"
```

TLS support requires additional schema review. The mapping is expected to extend the per-server row with fields such as domain name, SNI, transport, single connection mode, trust anchor reference, client certificate reference, PSK identity, and PSK symmetric key reference. Fields for a TLS credential choice are required only when that choice is selected for a server.

The design keeps two configuration views:

| View | Purpose |
| --- | --- |
| SONiC stored view | CLI and management interfaces update existing `TACPLUS` and `TACPLUS_SERVER` rows using SONiC ConfigDB conventions. |
| Agent runtime view | The central agent validates those rows against the TACACS+ model it uses for credential references, priority order, and connection setup. |

The SONiC CLI is not required to expose the full TACACS+ YANG tree directly. CLI and management changes update the stored SONiC TACACS+ rows, and the agent validates and maps those rows before use. This HLD does not propose replacing Redis-backed ConfigDB storage with RFC 7951 JSON or another YANG-backed datastore. The compatibility mapping preserves existing `TACPLUS|global` and `TACPLUS_SERVER|*` behavior.

The agent model should follow `ietf-system-tacacs-plus` concepts used by the implementation configuration library, including server entries, `server-authentication`, `client-identity`, `client-credentials`, `server-credentials`, and credential references. SONiC-specific extensions are expected where the base RFC 9950 model does not describe existing SONiC behavior, such as TACACS+ server priority ordering. The agent preserves references for reporting and resolves them only when building runtime connection settings.

The agent reads CONFIG_DB at startup and observes TACACS+ key changes through Redis keyspace notifications. It debounces related changes, re-reads the complete effective TACACS+ configuration, validates it, and hot-reloads affected upstream server state. If the new configuration is invalid, the agent keeps the previous valid runtime state when one exists, logs the validation error, and reports the configuration failure in diagnostics.

### 7.8 Secret and Certificate Material

The first implementation should follow the existing SONiC credential pattern used by gNMI and gRPC clients: configuration stores references or paths, while private material is provisioned as protected files on disk. ACMS, gNSI Certz/Credentialz, or another SONiC-approved credential provisioning flow is expected to place trust bundles, client certificates, private keys, and TLS PSK symmetric key material in a root-owned credential location. Existing SONiC examples use locations such as `/etc/sonic/credentials/`, `/etc/sonic/telemetry/`, and service-specific certificate paths; the final TACACS+ directory or profile naming shall be reviewed with platform and security owners.

CONFIG_DB shall not contain raw private key or raw PSK contents. The TACACS+ server row shall contain only references that the central agent resolves at runtime:

| Reference | Runtime material |
| --- | --- |
| `trust_anchor_ref` | CA bundle, trust bundle, or credential profile used for server certificate validation. |
| `client_certificate_ref` | Client certificate file or credential profile used for mTLS. |
| `client_private_key_ref` | Root-protected client private key file or credential profile used for mTLS. |
| `psk_secret_ref` | Root-protected file or credential object containing the TLS PSK symmetric key material. |

Referenced files shall be root-owned, writable only by the provisioning authority, and readable only by the central TACACS+ client agent or the least-privileged group required for operation. The agent shall validate that referenced material exists and has acceptable permissions before using it. Missing files, unreadable files, unsafe permissions, or mismatched certificate/key pairs shall cause configuration validation or connection setup to fail.

Credential rotation should be compatible with ACMS or gNSI-style update semantics. A new credential may be staged outside the active TACACS+ server row, validated by the provisioning flow, then referenced by an atomic TACACS+ configuration update. If a file path remains stable and ACMS replaces the file contents atomically, the agent shall rebuild affected connections through the same hot-reload path used for ConfigDB changes.

The implementation shall prevent sensitive values from appearing in show command output, syslog, debug logs, crash dumps where practical, and generated configuration reports. File paths, credential object names, certificate thumbprints, certificate expiry timestamps, and TLS PSK identities may be shown when useful for troubleshooting, but raw private key material, PSK values, shared secrets, and user passwords shall always be masked or omitted.

### 7.9 Error Handling

The agent shall return structured errors to local clients. Errors that may succeed after reconnect or failover shall be marked retriable. Errors caused by invalid configuration, missing TLS credential material, or failed TLS validation shall be non-retriable until configuration changes.

Expected error behavior:

| Condition | Behavior |
| --- | --- |
| Preferred TACACS+ server unreachable | Try next server in priority order. |
| All TACACS+ servers unreachable | Return retriable error to local client. |
| TLS certificate validation failure | Reject connection and log validation failure without exposing secrets. |
| Incomplete TLS credential configuration | Reject the new configuration and keep the previous valid state when available. |
| CONFIG_DB parse failure | Keep previous valid state when available, otherwise keep feature inactive. |
| IPC endpoint unavailable | Local clients receive a retriable local service error. |

### 7.10 Serviceability and Debug

The implementation shall provide logs and counters for operational troubleshooting. Counter names and semantics shall align at minimum with the RFC 9950 TACACS+ YANG statistics leaves for each configured server. Expected diagnostics include:

- Agent startup and active configuration source.
- Current preferred TACACS+ server and failover state.
- Active TLS credential mode and non-secret identity details. Certificate-backed TLS sessions shall report the validated server certificate SHA-256 thumbprint and certificate expiry timestamp in ISO 8601/RFC 3339 UTC format. mTLS sessions shall also report the configured client certificate SHA-256 thumbprint and expiry timestamp in the same format. TLS 1.3 PSK sessions shall report the configured PSK identity, effective PSK key exchange policy, and DHE group selection when DHE is active, not the PSK value.
- RFC 9950 per-server statistics: `connection-opens`, `connection-closes`, `connection-aborts`, `connection-failures`, `connection-timeouts`, `messages-sent`, `messages-received`, `errors-received`, `sessions`, and `cert-errors`.
- TLS handshake failures and certificate validation errors, mapped to the appropriate RFC-aligned counters and logs.
- IPC request failures and reconnect attempts.
- CONFIG_DB parse and validation failures.

Raw public key TLS server authentication is not supported in the first phase, so raw-public-key status and counters are not shown.

Show commands should present status without exposing sensitive values.

### 7.11 Linux Packaging and Runtime Dependencies

The proposed SONiC deployment should follow the standard SONiC Debian package flow. The central agent and related tools are installed as Debian packages that declare runtime dependencies through package metadata so `apt` installs the required libraries and supporting packages. The package that owns the daemon shall also install and register the systemd unit, including the required service ordering, restart policy, and feature enablement integration.

SONiC may choose to build the package in sonic-buildimage from an approved source import or git submodule, or consume the package from an approved apt source. In either model, the runtime behavior on the device is the same: a host service managed by systemd and controlled by the SONiC `FEATURE` table.

The package split should allow SONiC images or operators to install only the desired components, such as the central daemon, local client integration modules, diagnostic tools, or operator CLI support, using the normal package selection and `apt` installation mechanisms.

The following packaging and runtime dependencies are expected:

| Dependency or package item | Purpose |
| --- | --- |
| Source submodule, source import, or package source | Provide the selected implementation to SONiC CI or image builds through a reviewed source or package integration path. |
| Debian package metadata | Declare runtime dependencies, package ownership, configuration files, and maintainer scripts through the standard SONiC packaging path. |
| systemd unit | Register and manage the central agent service through the package installation flow. |
| TLS library package | Provide TLS 1.3 client support for certificate validation, mutual TLS, and PSK credential choices. |
| Redis client package or library | Provide CONFIG_DB integration. |
| Diagnostic and operator tooling packages | Install supporting tools through `apt` when they are not part of the central agent package. |
| Implementation build dependencies | Build dependencies for the selected implementation are part of the SONiC package build path or external package build path; they are not device runtime dependencies. |

## 8. SAI API

No SAI API changes are required for this feature.

This feature is a control-plane AAA and host-service feature. It does not add or modify ASIC_DB objects, does not require new SAI attributes, and does not require switch ASIC vendor implementation.

## 9. Configuration and Management

### 9.1 Manifest

This design proposes a built-in optional SONiC host service. No manifest is required.

### 9.2 CLI/YANG Model Enhancements

CLI changes shall be reviewed with sonic-utilities maintainers. The exact command syntax is subject to review, but the following capabilities are required:

The CLI is the operator workflow. It should provide stable SONiC commands that update stored TACACS+ configuration without requiring operators to understand the full TACACS+ YANG tree. The central agent validates the stored configuration before using it.

When the CLI changes a server from plain TCP/shared-secret operation to TLS, or changes the TLS credential shape for a TLS server, it shall validate the effective server configuration before writing the new state. The CLI shall support a transition workflow from one valid transport-security mode to another without requiring a duplicate server entry. It should do this through a destination-mode operation, such as `config tacacs server change-transport-security <server> <tls|mtls|psk|plain>`, that replaces the active transport, credential fields, and port with the target fields in one commit. `plain` means existing TACACS+ over TCP/shared-secret behavior. Operators may also stage credential objects outside the active server row and then atomically update the server reference.

The stored server row shall remain valid after every committed change. The CLI shall not leave an active server row containing fields from multiple credential choices. For example, when the destination mode is `psk`, the CLI reads the current row, merges the supplied PSK fields, clears incompatible mTLS client certificate and key fields, and validates the resulting PSK row before committing. Likewise, when the destination mode is `mtls`, the CLI clears incompatible PSK identity, secret, and PSK key exchange fields before validating the resulting mTLS row. When the destination mode is `plain`, the CLI clears TLS-only fields and validates the resulting TCP/shared-secret row. The transition command must fail with a clear error if required target fields are missing, the target configuration is internally inconsistent, or the final row would be ambiguous.

The agent shall repeat validation when reading stored configuration so direct ConfigDB updates, config reload, or restored configuration cannot bypass the same checks.

- Enable or disable the central TACACS+ client agent feature.
- Select plain TCP or TLS over TCP for a TACACS+ server.
- Select plain TCP/shared-secret operation, certificate-based TLS server authentication, mTLS, or PSK by naming the destination transport-security mode and writing the corresponding valid target fields.
- Set the TCP port that corresponds to the selected transport-security mode.
- Configure server domain name and SNI behavior.
- Configure references to trust anchors, client certificates, client private keys, PSK identity, and protected PSK symmetric key material.
- Configure single connection mode or dedicated connection mode.
- Display daemon health, upstream connection state, failover state, and counters.

Candidate CLI examples:

```bash
config feature state tacacs-agent enabled

# Add a TACACS+ server using existing TCP/shared-secret behavior.
config tacacs add 192.0.2.10 --port 49 --timeout 10 --key shared-secret --type pap --pri 1

# Change a server to TACACS+ over TLS with certificate validation using a CA bundle.
config tacacs server change-transport-security 192.0.2.10 tls \
  --port 449 \
  --domain-name tacacs.example.com \
  --trust-anchor-ref /etc/sonic/credentials/tacacs-ca.pem

# Change a server to TACACS+ over TLS with certificate validation using a pinned server certificate.
config tacacs server change-transport-security 192.0.2.10 tls \
  --port 449 \
  --domain-name tacacs.example.com \
  --trust-anchor-ref /etc/sonic/credentials/tacacs-server.pem

# Change a server to TACACS+ over TLS without certificate validation. This is diagnostic only.
config tacacs server change-transport-security 192.0.2.10 tls \
  --port 449 \
  --domain-name tacacs.example.com \
  --certificate-verify disabled

# Change a server to TACACS+ over TLS 1.3 PSK. The domain name enables SNI when SNI is active. PSK-DHE uses approved default groups unless groups are supplied.
config tacacs server change-transport-security 192.0.2.10 psk \
  --port 449 \
  --domain-name tacacs.example.com \
  --psk-identity sonic-switch-01 \
  --psk-secret-ref /etc/sonic/credentials/tacacs-psk-01.key

config tacacs server modify 192.0.2.10 --single-connection enabled
show tacacs agent status
show tacacs agent counters
```

The destination transport-security argument tells the CLI which existing fields are no longer applicable. The operator supplies the target-mode inputs, including the target TCP port; the CLI clears non-target transport and credential fields and validates the final row before commit. For PSK, the command defaults to PSK-DHE with the SONiC-approved group list; operators may add `--psk-key-exchange-groups x25519,secp256r1` when they need to constrain the offered groups. The same pattern applies when moving from PSK to mTLS or from TLS back to `plain`: the CLI writes the target fields and removes incompatible fields in one committed server update. If the final CLI syntax includes separate credential objects, operators may stage those objects first, but the active server row still changes only from one valid TACACS+ server configuration to another.

Candidate stored fields and model concepts:

| Model concept | Purpose |
| --- | --- |
| `transport` | Plain TCP or TLS over TCP. |
| `tcp-port` | TCP port for the selected transport-security mode. |
| `domain-name` | Name used for certificate verification and SNI. |
| `sni-enabled` | Enable SNI. |
| `single-connection` | Enable persistent connection reuse. |
| `trust-anchor-ref` | Reference to CA bundle, trust bundle file, or credential profile. |
| `client-certificate-ref` | Reference to client certificate file or credential profile for mTLS. |
| `client-private-key-ref` | Reference to protected client key file or credential profile. |
| `psk-identity` | TLS PSK identity. |
| `psk-secret-ref` | Reference to protected TLS PSK symmetric key file or credential object. |
| `psk-key-exchange-groups` | Optional approved TLS group list for PSK-DHE; providing groups implies TLS 1.3 `psk_dhe_ke`. |
| `psk-key-exchange` | Optional interop override. The value `psk-only` maps to TLS 1.3 `psk_ke` and must not be combined with DHE groups. |

### 9.3 Config DB Enhancements

Existing TACACS+ CONFIG_DB entries remain valid. This HLD does not propose changing Redis to store TACACS+ configuration as a JSON document. The JSON below is the normal SONiC `config_db.json` representation of Redis-backed CONFIG_DB tables and hash fields. At runtime, these remain `FEATURE`, `TACPLUS`, and `TACPLUS_SERVER` rows.

The proposal is to add optional backward-compatible fields to the existing TACACS+ tables and to map those fields into the validated agent configuration before runtime use. Field names are draft names and require SONiC schema review.

The `FEATURE` scope fields in the example follow existing SONiC multi-ASIC service metadata. `has_global_scope` set to `True` and `has_per_asic_scope` set to `False` mean the central TACACS+ client agent is a single host-global service instance for the SONiC OS instance, not a per-ASIC service instance. These fields do not imply one agent for an entire modular chassis across multiple compute devices. A per-ASIC, chassis-wide, or DPU-specific service topology would require separate SONiC ownership and service-scope review, including confirmation that the target scope has the required local CONFIG_DB/Redis access and protected credential provisioning.

```json
{
  "FEATURE": {
    "tacacs-agent": {
      "state": "disabled",
      "auto_restart": "enabled",
      "has_global_scope": "True",
      "has_per_asic_scope": "False"
    }
  },
  "TACPLUS": {
    "global": {
      "auth_type": "pap",
      "timeout": "5",
      "passkey": "shared-secret",
      "src_intf": "Management0"
    }
  },
  "TACPLUS_SERVER": {
    "192.0.2.10": {
      "priority": "1",
      "tcp_port": "449",
      "timeout": "10",
      "transport": "tls",
      "domain_name": "tacacs.example.com",
      "sni_enabled": "true",
      "single_connection": "true",
      "psk_identity": "sonic-switch-01",
      "psk_secret_ref": "/etc/sonic/credentials/tacacs-psk-01.key",
      "psk_key_exchange_groups": "x25519,secp256r1"
    }
  }
}
```

The following rules apply:

- If `transport` is absent and no TLS-only fields are present, existing plain TCP/shared-secret behavior is used.
- If TLS fields are absent, existing configurations continue to load.
- If any TLS-only field is present, the row must explicitly select TLS and must include a target TCP port for the TLS mode.
- Stored ConfigDB rows are mapped into the validated agent configuration before runtime use.
- Raw private keys and raw PSK values shall not be stored directly in these rows; only ACMS-provisioned file paths, credential object names, or profile references shall be stored.
- Unknown extension fields shall not break existing TACACS+ behavior during migration.
- Configuration validation shall reject incomplete or ambiguous TLS credential settings. For example, an entry with `psk_identity` is incomplete without `psk_secret_ref`, and an entry with both PSK fields and mTLS client certificate fields is ambiguous.
- PSK servers shall default to TLS 1.3 `psk_dhe_ke` with a SONiC-approved default TLS group list when no PSK key exchange fields are present.
- `psk_key_exchange_groups` is valid only for TLS PSK server rows and implies TLS 1.3 `psk_dhe_ke`. The group list must be non-empty and limited to approved TLS supported groups.
- `psk_key_exchange` is valid only for TLS PSK server rows. The value `psk-only` requests TLS 1.3 `psk_ke` for interoperability and must not be combined with `psk_key_exchange_groups`.
- Configuration validation shall derive the active TLS credential mode from the populated credential fields. A separate stored `tls_credential_mode` flag is not required for the agent to decide how to connect.
- The stored `transport` value must agree with the populated credential fields. For example, PSK fields with `transport` absent or set to plain TCP are invalid.
- CLI commands that transition between transport-security modes shall name the destination mode, set the target port, clear fields from non-target transport and credential choices in software, and commit only a valid final server row. Direct ConfigDB edits are still validated by the central agent when it loads or hot-reloads configuration.

Candidate ConfigDB-to-agent mapping:

| Stored SONiC field | Model concept |
| --- | --- |
| `TACPLUS_SERVER` row key | `server` entry with name/address derived from the SONiC row. |
| `tcp_port` | `server.port`. |
| `priority` | SONiC server ordering, preserved through a SONiC extension to the RFC 9950-based model when needed. |
| `timeout` | Runtime server timeout policy. |
| `transport` | Operator/storage hint for plain TCP or TLS over TCP that must agree with the populated security fields. |
| `domain_name` and `sni_enabled` | `domain-name` and `sni-enabled`. |
| `trust_anchor_ref` | `server-authentication` credential reference, SONiC-approved truststore reference, or protected CA bundle path. |
| `client_certificate_ref` and `client_private_key_ref` | `client-identity` credential reference, SONiC-approved keystore reference, or protected certificate/key path. |
| `psk_identity` and `psk_secret_ref` | TLS PSK identity and protected symmetric key file or credential reference. |
| `psk_key_exchange_groups` | Approved TLS supported groups for PSK-DHE; presence implies TLS 1.3 `psk_dhe_ke`. |
| `psk_key_exchange` | Optional interoperability override. The value `psk-only` maps to TLS 1.3 `psk_ke`; absence maps to TLS 1.3 `psk_dhe_ke` with default approved groups unless `psk_key_exchange_groups` is present. |
| `single_connection` | Agent connection reuse policy associated with the server entry. |

The exact ACMS integration, directory names, and profile naming remain subject to SONiC review. The first phase prioritizes a reversible mapping that preserves current ConfigDB behavior.

### 9.4 Logs, Counters, and Show Commands

The implementation shall include operator-facing status and counters. Counter output shall expose the RFC 9950 TACACS+ statistics leaves per server. Candidate show output includes:

```text
show tacacs agent status
    Feature state: disabled|enabled
    Daemon state: running|stopped|failed
    Active server: 192.0.2.10
    Transport: tls
    TLS credential mode: certificate|mtls|psk
    Server certificate thumbprint (SHA-256): 3A:5E:...:91 (certificate/mTLS)
    Server certificate expires: 2027-05-25T18:30:00Z (certificate/mTLS)
    Client certificate thumbprint (SHA-256): A1:22:...:0F (mTLS)
    Client certificate expires: 2027-05-25T18:30:00Z (mTLS)
    TLS PSK identity: sonic-switch-01 (PSK)
    TLS PSK key exchange: DHE (psk_dhe_ke)
    TLS PSK DHE groups: x25519,secp256r1
    Failover state: preferred-active|failed-over|no-responsive-server

show tacacs agent counters
  Server: 192.0.2.10
  discontinuity-time
  connection-opens
  connection-closes
  connection-aborts
  connection-failures
  connection-timeouts
  messages-sent
  messages-received
  errors-received
  sessions
  cert-errors
```

The implementation may expose additional SONiC-local counters, such as UDS requests accepted, rejected, timed out, or retried, but those counters shall not replace the RFC 9950-aligned server statistics.

Sensitive fields shall be masked or omitted from all show output.

The server certificate thumbprint and expiry fields are shown when the active TLS mode validates a server certificate. The client certificate thumbprint and expiry fields are shown when mTLS is active. The PSK identity, effective key exchange policy, and DHE group selection fields are shown when TLS 1.3 PSK is active; the PSK value and PSK secret reference remain hidden or masked.

## 10. Warmboot and Fastboot Design Impact

This feature does not program the ASIC and does not require SAI state restore. Therefore, it is not expected to affect data plane warmboot or fastboot behavior.

When the feature is disabled, there shall be no daemon startup and no runtime memory growth from this feature.

When the feature is enabled, the central TACACS+ client agent starts as a host service after CONFIG_DB and network availability. It shall not block database service startup, platform initialization, or data plane restoration.

### 10.1 Warmboot and Fastboot Performance Impact

The feature shall be analyzed against the following boot impact points:

- The daemon reads CONFIG_DB and may open upstream TACACS+ connections after its service starts. This must not be in the boot critical path for switching data plane restoration.
- TLS handshakes can be delayed until the daemon starts or until the first TACACS+ request, depending on final service policy.
- The feature shall not add sleeps or long-running waits to existing SONiC boot scripts.
- The feature shall not require Jinja template rendering in the boot critical path when disabled.
- If enabled, the service may be delayed until management network readiness, subject to SONiC service ordering review.
- Warmboot and fastboot regression tests shall verify no unexpected data plane downtime is introduced.

## 11. Memory Consumption

When the feature is disabled by configuration, there shall be no running central TACACS+ client agent process. Installed binaries do not create runtime memory consumption.

When enabled, memory consumption comes from:

- One central TACACS+ client agent process.
- One upstream connection state machine per configured server, with only the active server normally holding an established connection.
- Bounded request and response buffers per local UDS request.
- Optional TLS session state and certificate material loaded by the daemon.

The implementation shall cap request sizes and prevent unbounded queue growth. Long-running tests shall verify that repeated configuration changes, server failover, and IPC requests do not cause unbounded memory growth.

## 12. Restrictions/Limitations

- The initial SONiC proposal is Alpha maturity and disabled by default.
- The first phase is additive and does not replace existing SONiC TACACS+ behavior.
- The selected TLS library must support every TLS credential choice, PSK key exchange policy, and configured PSK-DHE TLS group accepted by the configuration model.
- The current upstream SONiC TACACS+ schema does not contain all TLS certificate, PSK, or trust anchor fields. Schema work is required.
- Raw private keys and raw PSK material shall not be placed in plaintext CONFIG_DB fields.
- ConfigDB changes shall be applied through hot-reload with debounce. Invalid new configuration keeps the previous valid runtime state when one exists.
- Raw public key TLS server authentication is not supported in the first phase.
- This HLD does not improve shell command authorization coverage. That is covered by a separate HLD.
- The exact ACMS integration, directory paths, permissions, and rotation lifecycle for TLS key material, PSK material, and trust anchors require SONiC review.

## 13. Testing Requirements/Design

### 13.1 Unit Test Cases

The implementation shall include unit tests for the following items:

- Parsing existing `TACPLUS|global` and `TACPLUS_SERVER|*` rows.
- Mapping existing TACACS+ rows to runtime central agent configuration.
- Mapping backward-compatible SONiC TACACS+ rows into the validated agent configuration.
- Validating TACACS+ configuration, including credential references, priority ordering, transport-security mode, target port, and TLS credential choices.
- CLI validation rejects switching a server to TLS or changing its TLS credential shape when required fields for the target server shape are missing.
- CLI validation rejects direct or restored active server rows with redundant credential fields that would make the transport-security mode ambiguous.
- CLI validation allows destination-mode atomic transitions between plain, TLS server authentication, mTLS, and PSK without requiring operators to provide explicit clear modifiers, when the committed final server row maps to exactly one valid TACACS+ server configuration.
- Parsing TLS transport fields, domain name, SNI, PSK key exchange mode, PSK-DHE group lists, and single connection mode.
- Rejecting incomplete TLS credential configurations, including missing client certificate material or missing PSK material for the selected choice.
- Rejecting unsupported, empty, or unapproved PSK-DHE group lists and rejecting PSK-only configuration combined with DHE groups.
- Rejecting referenced credential files that are missing, unreadable, or have unsafe ownership or permissions.
- Masking sensitive fields in logs and show output helpers.
- Selecting preferred server and ordered failover behavior.
- Serializing reconnect attempts per upstream server.
- IPC error mapping and retriable flag behavior.
- CLI/YANG validation for backward-compatible configuration.

### 13.2 System Test Cases

The implementation shall include system tests for the following items:

- Existing TACACS+ shared-secret configuration continues to work with the central TACACS+ client agent disabled.
- The central TACACS+ client agent can be enabled and disabled through the SONiC feature mechanism.
- The agent reads TACACS+ server configuration from CONFIG_DB.
- The agent reports the active configuration source and validates the runtime configuration derived from stored ConfigDB rows.
- CLI attempts to switch a server to a TLS credential shape fail before commit when the effective server configuration is incomplete or ambiguous.
- CLI destination-mode transition between plain, TLS server authentication, mTLS, and PSK succeeds without explicit clear modifiers, without adding a duplicate TACACS+ server entry, without committing an intermediate invalid server row, and with the target port set for the selected mode.
- The agent connects to a TACACS+ server over TCP.
- The agent connects to a TACACS+ server over TLS with server certificate verification.
- The agent connects with mTLS using configured client certificate material.
- The agent connects to TLS servers using each configured TLS credential choice.
- The agent connects to TLS PSK servers using the default approved PSK-DHE groups, explicit PSK-DHE group lists, and explicit PSK-only interop mode when supported.
- Invalid certificate, wrong server name, or missing trust anchor causes connection failure.
- Multiple TACACS+ servers fail over in configured priority order.
- Preferred server probing returns traffic to the preferred server after recovery.
- Single connection mode reuses upstream connections for multiple requests.
- Dedicated connection mode opens separate connections for compatibility.
- CONFIG_DB changes are observed, debounced, validated, and logged.
- Changed upstream server sets are hot-reloaded without daemon restart, and invalid changes keep the previous valid runtime state when available.

### 13.3 Security Test Cases

The implementation shall include security tests for the following items:

- Private keys, PSK values, shared secrets, and passwords are not printed by show commands.
- Sensitive fields are not emitted in normal logs.
- ConfigDB contains only credential references or paths, not raw private key or raw PSK contents.
- IPC socket permissions prevent unauthorized local access.
- TLS certificate verification rejects expired, untrusted, and wrong-name certificates.
- Unsafe certificate verification disablement is visible in configuration and logs.

### 13.4 sonic-mgmt Test Plan

A sonic-mgmt test plan shall be prepared and reviewed before moving the feature beyond Alpha. The test plan shall cover:

- Configuration load and save behavior.
- Compatibility mapping between SONiC TACACS+ ConfigDB rows and the validated agent configuration.
- Feature enable and disable behavior.
- Plain TCP and TLS-over-TCP server connectivity across certificate-based server authentication, mTLS, and PSK credential choices.
- Failover and recovery.
- Backward compatibility with existing TACACS+ configuration.
- Hot-reload behavior for TACACS+ ConfigDB changes.
- Warmboot and fastboot regression.

### 13.5 Backward Compatibility and Regression Tests

Backward compatibility tests shall verify:

- Existing TACACS+ ConfigDB without new fields loads successfully.
- Existing CLI-generated configuration can be saved and restored.
- Disabling the central TACACS+ client agent restores existing TACACS+ behavior.
- Upgrading from a release without the central TACACS+ client agent does not enable the new feature unexpectedly.
- Downgrading with unknown TLS fields does not break the old TACACS+ path after unsupported fields are ignored or removed according to SONiC policy.
- Existing AAA sonic-mgmt tests continue to pass.

## 14. Open/Action Items

| Item | Owner | Status |
| --- | --- | --- |
| Decide whether SONiC consumes the Debian package from a submodule/source import built by SONiC CI or from an approved apt package source. | SONiC community | Open |
| Agree on ConfigDB field names for TLS transport, TLS credential choices, PSK key exchange and group selection, single connection mode, and TLS port defaults. | AAA and YANG reviewers | Open |
| Define the SONiC YANG extension used to preserve existing TACACS+ server priority ordering when mapping toward RFC 9950. | AAA and YANG reviewers | Open |
| Decide whether stored configuration remains table-shaped with TACACS+ model mapping or moves toward a more YANG-native representation in a later phase. | AAA, YANG, and ConfigDB reviewers | Open |
| Confirm ACMS/gNMI-style credential provisioning, directory paths, file permissions, and reference naming for TLS private keys, trust anchors, and PSK material. | Security and platform reviewers | Proposed |
| Define exact CLI syntax and show commands. | sonic-utilities reviewers | Open |
| Prepare sonic-mgmt test plan and identify testbed topology. | Test subgroup | Open |
| Prepare release notes maturity entry. | Feature owner | Open |

## 15. References

- RFC 8907, The TACACS+ Protocol.
- [RFC 9887, Terminal Access Controller Access-Control System Plus (TACACS+) over TLS 1.3](https://datatracker.ietf.org/doc/rfc9887/).
- [RFC 9950, A YANG Data Model for Terminal Access Controller Access-Control System Plus (TACACS+)](https://datatracker.ietf.org/doc/rfc9950/).
- SONiC HLD template: `doc/guidelines/hld_template.md`.
- SONiC feature quality definition: `doc/guidelines/SONiC feature quality definition.md`.
- SONiC TACACS+ improvement HLD: `doc/aaa/TACACS+ Design.md`.
- SONiC TACACS+ passkey encryption HLD: `doc/tacacs-passkey/TACACSPLUS_PASSKEY_ENCRYPTION.md`.
- SONiC LDAP HLD: `doc/aaa/ldap/hld_ldap.md`.
- SONiC gNSI HLD: `doc/mgmt/gnmi/gnsi.md`.
- SONiC gRPC client HLD: `doc/grpc_client/design_doc.md`.
- SONiC Management Framework HLD: `doc/mgmt/Management Framework.md`.
