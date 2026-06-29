# TACACS+ TLS with KubeSONiC Local Forwarding

## Table of Content

- [TACACS+ TLS with KubeSONiC Local Forwarding](#tacacs-tls-with-kubesonic-local-forwarding)
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
    - [6.2 Proposed KubeSONiC Architecture](#62-proposed-kubesonic-architecture)
    - [6.3 Component Responsibilities](#63-component-responsibilities)
    - [6.4 Repositories and Modules](#64-repositories-and-modules)
  - [7. High-Level Design](#7-high-level-design)
    - [7.1 Feature Type and Deployment Model](#71-feature-type-and-deployment-model)
    - [7.2 Existing Consumer Proxy Path](#72-existing-consumer-proxy-path)
    - [7.3 TACACS+ TLS Transport](#73-tacacs-tls-transport)
    - [7.4 TLS Credential Choices](#74-tls-credential-choices)
    - [7.5 Single Connection Model](#75-single-connection-model)
    - [7.6 Ordered Failover and Recovery](#76-ordered-failover-and-recovery)
    - [7.7 Native UDS Interface](#77-native-uds-interface)
    - [7.8 SONiC ConfigDB Integration](#78-sonic-configdb-integration)
    - [7.9 Secret and Certificate Material](#79-secret-and-certificate-material)
    - [7.10 Error Handling](#710-error-handling)
    - [7.11 Serviceability and Debug](#711-serviceability-and-debug)
    - [7.12 Container Packaging and Runtime Dependencies](#712-container-packaging-and-runtime-dependencies)
  - [8. SAI API](#8-sai-api)
  - [9. Configuration and Management](#9-configuration-and-management)
    - [9.1 Manifest](#91-manifest)
    - [9.2 CLI and Configuration Model Enhancements](#92-cli-and-configuration-model-enhancements)
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
| 0.2 | 2026-06-25 | Rodney Persky | Refocus on KubeSONiC-managed local forwarding, separate TLS ConfigDB tables, loopback compatibility, and native UDS integration surface. |

## 2. Scope

This document describes the high-level design for adding TACACS+ over TLS to SONiC through a KubeSONiC-managed local TACACS+ forwarding service. The goal is to improve management-plane TACACS+ transport security while minimizing changes to the SONiC root OS and existing AAA plugins.

The scope includes the following items:

- Support TACACS+ over TCP and TACACS+ over TLS 1.3, with TLS mode following [RFC 9887](https://datatracker.ietf.org/doc/rfc9887/).
- Support TACACS+ over TLS 1.3 using server certificate validation, mutual TLS, or TLS 1.3 pre-shared keys.
- Support a local loopback TACACS+ TCP listener for existing SONiC code that already uses native TACACS+ libraries. This proxy use case moves upstream transport to TLS without replacing PAM, shell, audit, accounting, or CLI integrations.
- Support a local UDS IPC surface for new SONiC code, or for components written in languages that have gRPC/protobuf support but do not have native TACACS+ libraries.
- Support a single connection model where the local forwarding service reuses an upstream TACACS+ connection for multiple TACACS+ sessions when supported by the server.
- Preserve a dedicated per-request connection mode for compatibility with existing TACACS+ deployments.
- Introduce a KubeSONiC-managed container per SONiC compute device or SONiC OS instance that owns upstream transport, TLS state, connection reuse, and failover.
- Read TLS-capable upstream TACACS+ server configuration from new SONiC CONFIG_DB tables that are not consumed by the existing SONiC TACACS+ components.
- Use the existing `TACPLUS|global` and `TACPLUS_SERVER|*` rows only for the compatibility path seen by existing SONiC TACACS+ consumers, including a loopback server entry followed by optional existing non-TLS fallback servers during migration.
- Make Unix domain socket IPC available through the local forwarding service, while adding SONiC component integrations only when a component requires the direct IPC contract.
- Define configuration, management, serviceability, testing, and approval requirements for this feature.

This document does not propose changes to authentication, command authorization, accounting coverage, or current root OS AAA plugins.

## 3. Definitions/Abbreviations

| Term | Meaning |
| --- | --- |
| AAA | Authentication, Authorization, and Accounting. |
| CONFIG_DB | SONiC Redis-backed configuration database, database index 4. |
| gRPC | Google Remote Procedure Call framework used here only for host-local IPC over UDS. |
| IPC | Inter-process communication. |
| KubeSONiC | SONiC deployment model where Kubernetes manages selected SONiC feature containers through manifests while SONiC keeps control of when a feature starts or stops. |
| Existing TACACS+ consumer | Existing SONiC host component that reads `TACPLUS` and `TACPLUS_SERVER` configuration and sends TACACS+ over TCP without understanding TACACS+ TLS fields. |
| Local forwarding service | KubeSONiC-managed service that accepts TACACS+ over a host-local loopback TCP listener and forwards requests to configured upstream TACACS+ servers over TCP or TLS. |
| Loopback TACACS+ server | Compatibility `TACPLUS_SERVER` entry, such as `127.0.0.1` or `::1`, used by existing SONiC TACACS+ consumers to reach the local forwarding service first. |
| mTLS | Mutual TLS, where both client and server present TLS certificates. |
| protobuf | Protocol Buffers schema language and encoding used for the local IPC contract. |
| PSK | Pre-shared key. In this document it means TLS 1.3 PSK unless otherwise specified. |
| SAI | Switch Abstraction Interface. |
| Single connection | TACACS+ operating model where one upstream transport connection carries multiple sessions identified by TACACS+ session ID. |
| TACACS+ | Terminal Access Controller Access-Control System Plus, as specified by RFC 8907. |
| TLS | Transport Layer Security. |
| Transport-security mode | The selected TACACS+ server connection mode over TCP: plain TCP/shared-secret, TLS server authentication, mTLS, or TLS PSK. |
| UDS | Unix domain socket. UDS is the native host-local IPC surface for integrations that use gRPC/protobuf instead of a native TACACS+ client library. |
| YANG | Data modeling language used for network configuration models. |

## 4. Overview

SONiC already supports TACACS+ for device administration workflows. Existing TACACS+ support is sufficient for current shared-secret deployments, but it does not provide a complete design for modern TACACS+ over TLS operation.

TLS introduces two design requirements:

1. TACACS+ clients need configuration references for the selected TLS identity and trust material, including trust anchors, client certificates, private keys, PSK identities, and protected secret references.
2. TACACS+ clients should avoid a full TCP and TLS handshake for every request because per-request TLS handshakes add latency and server load.

This HLD centralizes upstream TACACS+ transport in a KubeSONiC-managed local forwarding service. The service owns upstream TCP/TLS connection setup, TLS credential use, connection reuse, and ordered failover, while SONiC components consume the service through the host-local interface that matches their implementation needs.

The design supports two local consumption use cases:

1. Existing SONiC code with native TACACS+ libraries uses a loopback TACACS+ TCP proxy. These components continue to use the normal TACACS+ client path and do not need to understand TLS-specific configuration fields.
2. New SONiC code, or code written in languages without native TACACS+ libraries, can use a local UDS IPC contract when gRPC/protobuf support is available. The service can expose this UDS endpoint, and component integrations are added when a component requires the direct IPC API.

For the proxy use case, operators place the loopback listener first in the existing `TACPLUS_SERVER` priority list and can keep existing non-TLS servers later in the same list as migration fallback. The local forwarding service reads two upstream candidate sources: existing `TACPLUS_SERVER` rows after filtering out its own loopback compatibility row, and new `TACPLUS_SERVER_TLS` rows for TLS-capable upstream servers. Existing TACACS+ consumers still read only the existing compatibility rows and therefore do not discover TLS server rows or need to filter TLS and non-TLS entries.

The forwarding service accepts TACACS+ over the loopback listener, combines the filtered TCP candidates and TLS candidates by configured priority, and selects the first usable upstream server. That upstream connection can use TACACS+ over TCP or TACACS+ over TLS. This keeps deployment reversible: if the container is disabled, absent, or unhealthy, existing SONiC TACACS+ consumers can fall through to later non-TLS server entries according to existing TACACS+ failover behavior.

Native UDS-based integrations use the same local forwarding service but a different host-local interface. A component that opts into UDS can call the local IPC interface directly for authentication, authorization, and accounting operations. Components that do not opt in continue to use the loopback TACACS+ proxy, so moving upstream TACACS+ traffic to TLS does not require replacement of current SONiC PAM, shell, audit, accounting, or CLI integrations.

The TLS design treats server certificate validation, mutual TLS, and TLS PSK as TLS credential choices available through the same configuration and management model. A SONiC implementation of this feature must include the TLS library support needed for the credential choices, PSK key exchange policy, and PSK-DHE group configuration accepted by configuration.

The feature is disabled by default unless explicitly enabled and shall preserve existing TACACS+ operation when disabled. KubeSONiC deployment mechanics, sonic-mgmt test coverage, and community review are required parts of the accepted design.

## 5. Requirements

### 5.1 Functional Requirements

- The implementation shall support existing TACACS+ shared-secret operation for compatibility with current TACACS+ deployments.
- The implementation shall support TACACS+ over TLS 1.3 for upstream server communication.
- The implementation shall support TLS credential choices for server certificate verification using configured trust anchors, mutual TLS using client certificate material, and TLS 1.3 PSK using a PSK identity, protected secret reference, and PSK key exchange policy.
- The implementation shall include TLS library support for every TLS credential choice, PSK key exchange policy, and configured PSK-DHE group that the configuration accepts.
- The implementation shall validate the populated TLS credential choice and reject incomplete TLS identity or trust material.
- The local forwarding service shall run as a KubeSONiC-managed container when KubeSONiC is available for the target deployment.
- The proxy use case shall expose a host-local TACACS+ TCP listener on loopback for existing SONiC TACACS+ consumers.
- The native IPC use case shall expose a UDS endpoint for SONiC components that require a direct gRPC/protobuf API.
- Existing SONiC TACACS+ consumers shall not need to implement TLS, read TLS fields, or call UDS IPC when they use the proxy path.
- The compatibility `TACPLUS_SERVER` list shall allow a loopback entry as the first server and existing non-TLS servers as later fallback entries.
- The local forwarding service shall read upstream TLS-capable TACACS+ server configuration from new ConfigDB keys that are not consumed by existing SONiC TACACS+ components.
- The implementation shall support multiple upstream TACACS+ servers using the priority order configured across filtered TCP candidates and TLS candidates.
- The implementation shall prefer the first healthy server and fail over to later servers when the preferred server is not reachable.
- The implementation shall periodically probe the preferred server while failed over and return traffic to it when it recovers.
- The implementation shall support a single connection model where one service-owned upstream connection can carry multiple TACACS+ sessions.
- The implementation shall support a dedicated connection mode for deployments that require one upstream connection per request.
- The proxy path shall preserve current SONiC PAM, shell, audit, accounting, and CLI modules without requiring their replacement; this is a core requirement of the local forwarding proxy design.

### 5.2 Security Requirements

- TLS connections shall authenticate the upstream TACACS+ server according to the configured TLS credential choice.
- Certificate verification shall be disabled only when an explicitly unsafe diagnostic option is selected.
- The design shall not store raw TLS private keys or raw PSK material in plaintext CONFIG_DB fields.
- The feature shall define how certificates, trust anchors, private keys, and PSK material are referenced and protected on the device.
- The loopback TACACS+ listener shall bind only to a host-local address and shall not expose a network-reachable TACACS+ listener.
- The loopback TACACS+ listener shall support both unobfuscated local TACACS+ packets and obfuscated local TACACS+ packets from existing SONiC consumers. For obfuscated local packets, the local forwarding service shall deobfuscate using the loopback server configuration passkey, preserve the TACACS+ message data, and apply the selected upstream server obfuscation policy before sending the request upstream. Responses shall be decoded using the selected upstream policy and re-encoded for the local hop when the local client session uses obfuscation.
- Any native IPC endpoint shall be protected by Unix socket permissions on Linux.
- Unsafe TLS options, such as disabling certificate verification, shall be explicit in configuration and visible in logs and show output.
- Sensitive values such as shared secrets, private keys, PSK values, and user passwords shall not be logged or displayed.

### 5.3 Configuration and Management Requirements

- The feature shall be controlled by CONFIG_DB and disabled by default unless explicitly enabled.
- Existing `TACPLUS|global` and `TACPLUS_SERVER|*` configuration shall remain valid.
- Existing `TACPLUS|global` and `TACPLUS_SERVER|*` rows shall not be extended with TLS upstream server fields for the proxy path.
- New TLS-related upstream server fields shall be stored under new ConfigDB keys that existing SONiC TACACS+ components do not read.
- The local forwarding service shall validate stored upstream TACACS+ configuration against the TACACS+ model used by the implementation before runtime use.
- New stored CONFIG_DB fields should map cleanly into the TACACS+ YANG model where practical, but isolation from existing SONiC TACACS+ rows has priority for the compatibility path.
- CLI changes shall preserve save and restore compatibility with configurations from previous releases.
- CLI commands shall manage existing `TACPLUS` and `TACPLUS_SERVER` compatibility rows separately from new `TACPLUS_SERVER_TLS` rows; they shall not transform an existing TCP server row into a TLS server row or a TLS server row into a TCP server row.
- CLI commands that add or modify a `TACPLUS_SERVER_TLS` row shall validate the resulting TLS server configuration before committing the change.
- Priority changes shall control whether the local forwarding service selects a TCP or TLS upstream candidate first.
- Each active stored TLS server configuration shall map to one valid YANG security and credential choice. Redundant fields from another credential choice shall be rejected rather than ignored.
- YANG model changes shall describe TLS transport, single connection mode, and secret/certificate references, aligned with the TACACS+ YANG model in [RFC 9950](https://datatracker.ietf.org/doc/rfc9950/).
- YANG model changes shall preserve upstream TACACS+ server priority ordering, using a SONiC extension to RFC 9950 when needed.
- The management model shall allow operators to configure TCP and TLS upstream candidates independently, and for TLS to configure one credential choice: server certificate validation, mTLS, or PSK. For PSK, the CLI workflow shall default to PSK-DHE with approved TLS groups, allow optional group constraints, and allow explicit PSK-only interop mode.
- The management model shall allow operators to select persistent connection reuse or dedicated per-request connections.
- The management workflow shall configure the existing `TACPLUS_SERVER` compatibility list separately from the new upstream server list so existing consumers can use loopback first and non-TLS fallback servers later.

### 5.4 Scalability and Performance Requirements

- The local forwarding service shall avoid a new TCP or TLS handshake for every TACACS+ request when persistent single connection mode is enabled.
- The local forwarding service shall serialize reconnect attempts per upstream server so concurrent local clients do not create a connection storm.
- The local forwarding service shall debounce CONFIG_DB updates, re-read upstream TACACS+ configuration, validate the complete effective configuration, and hot-reload affected upstream server state without requiring a service restart.
- TLS and failover behavior shall not be in the switching data plane path.
- The feature shall not add SAI dependencies or data plane dependencies.

### 5.5 Backward Compatibility Requirements

- Existing TACACS+ authentication, authorization, accounting, and local fallback configuration shall continue to operate when the local forwarding service is disabled, absent, or not selected by TACACS+ server priority.
- Existing `TACPLUS|global` and `TACPLUS_SERVER|*` rows shall continue to map only to existing shared-secret TACACS+ behavior.
- Downgrading or disabling the feature shall not require existing SONiC TACACS+ consumers to parse or ignore TLS fields because upstream TLS configuration is stored in separate tables.
- Existing SONiC CLI commands shall continue to work unless explicitly changed and documented.
- Device administrators shall be able to disable the KubeSONiC-managed local forwarding service and return to the existing SONiC TACACS+ path.
- Configuration save and restore across upgrade and downgrade paths shall be documented and tested.

### 5.6 Serviceability Requirements

- The local forwarding service shall log upstream connection state changes, failover decisions, TLS validation failures, configuration parse errors, and local listener errors.
- The feature shall provide show commands or equivalent diagnostics for container health, local listener health, configured upstream server state, active failover target, and counters.
- The feature shall expose enough information for sonic-mgmt tests to determine whether TCP, TLS credential choices, PSK key exchange and group selection, failover, and single connection paths are active.

### 5.7 Exemptions and Not Supported Items

- This HLD does not propose any SAI API change.
- This HLD does not require switch ASIC or platform vendor API changes.
- This HLD does not remove the existing SONiC TACACS+ implementation.
- This HLD does not change command authorization coverage.
- This HLD does not introduce shell command interception or host session enforcement.
- This HLD does not require native UDS integration with PAM, shell, audit, accounting, or CLI components.
- Raw public key TLS server authentication is not supported by this design.

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

### 6.2 Proposed KubeSONiC Architecture

The proposed architecture adds a KubeSONiC-managed local forwarding service between local SONiC consumers and upstream TACACS+ servers. Existing consumers continue to read `TACPLUS|global` and `TACPLUS_SERVER|*`; the forwarding service reads a separate upstream configuration table.

```text
+----------------+        TCP to loopback        +----------------------+       TCP/TLS      +--------------+
| Existing PAM / | ----------------------------> | KubeSONiC-managed    | =================> | TACACS+      |
| AAA consumer   |                               | local forwarding svc | <================= | server       |
+-------+--------+                               +----------+-----------+                    +--------------+
        |                                                   |
        | reads existing compatibility rows                 | reads upstream rows
        v                                                   v
      +-------------------------+                    +-------------------------------+
      | TACPLUS and             |                    | TACPLUS_FORWARDER and         |
      | TACPLUS_SERVER          |                    | TACPLUS_SERVER_TLS            |
      | compatibility tables    |                    | tables in CONFIG_DB           |
      +-------------------------+                    +-------------------------------+
```

The compatibility `TACPLUS_SERVER` list places the loopback listener first. Existing non-TLS servers may remain later in the list so the current SONiC TACACS+ path can fall back during migration if the local listener is unavailable or if confirmed existing client behavior treats a local service error as a server failure.

The local forwarding service can serve multiple local consumers without each local consumer opening its own upstream TACACS+ connection. It also isolates the TLS upstream server configuration from existing SONiC components that cannot distinguish TLS and non-TLS server entries.

### 6.3 Component Responsibilities

| Component | Responsibility | Lifetime |
| --- | --- | --- |
| KubeSONiC-managed local forwarding service | Listens on loopback for TACACS+ from existing SONiC consumers, reads upstream TACACS+ configuration, opens upstream TCP/TLS connections, and performs ordered failover. | Feature container managed through KubeSONiC and SONiC feature control. |
| Existing SONiC TACACS+ consumer | Sends TACACS+ requests to the first reachable server in `TACPLUS_SERVER`, normally the loopback listener when using the proxy path. Examples include PAM, AAA, CLI, shell, audit, or accounting integrations as applicable. | Existing service or one-shot process. |
| Configuration model mapper | Parses and validates TACACS+ YANG or CONFIG_DB input and maps it into runtime upstream server configuration. | Library or service module. |
| SONiC CONFIG_DB adapter | Maps new SONiC ConfigDB upstream tables into the runtime configuration model and optionally reads existing compatibility rows for diagnostics. | Library or service module. |
| Diagnostic TACACS+ client | Sends test TACACS+ requests to the loopback listener, directly to an upstream server, or through a native IPC interface. | One-shot command. |
| Native client integration | Optional integration where selected SONiC consumers call a local UDS IPC contract instead of using the loopback TACACS+ compatibility path. | Service or module change. |

### 6.4 Repositories and Modules

The expected SONiC implementation requires changes in the following areas:

| Repository or area | Expected change |
| --- | --- |
| SONiC doc repository | This HLD and any related test plan documentation. |
| sonic-buildimage or KubeSONiC integration path | Provide the minimal feature metadata, service control, and container deployment integration required for a KubeSONiC-managed feature. Exact root OS changes should be kept small and reviewed for backport feasibility. |
| sonic-utilities | CLI changes for configuring the loopback compatibility entry, upstream TACACS+ TLS tables, and show commands, if accepted by review. |
| sonic-yang-models | YANG changes for upstream TLS transport fields, single connection mode, secret/certificate references, and priority-order preservation for the new upstream tables. |
| sonic-mgmt | Test plan and automated tests for KubeSONiC deployment, loopback compatibility, configuration, TLS, failover, and rollback. |
| Implementation repository or container image source | Source for the local forwarding service, ConfigDB mapping, tests, diagnostic tools, and container integration assets. The source can remain in a separate repository if SONiC consumes it through a reviewed container image, source import, submodule, or approved package source. |

## 7. High-Level Design

### 7.1 Feature Type and Deployment Model

The feature is an optional KubeSONiC-managed SONiC feature controlled by the SONiC `FEATURE` table, KubeSONiC deployment labels, and TACACS+ CONFIG_DB state. The runtime service is delivered as a container image managed through KubeSONiC. It is not a SAI feature and does not require changes to switch ASIC programming.

The service scope is one local forwarding service per SONiC compute device or SONiC OS instance. It is not a chassis-wide singleton across multiple compute devices and is not a per-ASIC service. The design assumes the container can access the local Redis-backed CONFIG_DB and credential provisioning mechanisms, such as ACMS or equivalent protected credential storage, through SONiC-approved mounts or APIs.

KubeSONiC is selected because it provides the feature-container boundary for the local forwarding service that owns upstream transport, TLS state, connection reuse, and failover. The root OS work should stay limited to the minimum feature metadata, CLI/schema integration, and host-loopback exposure required for the container to participate in existing SONiC TACACS+ workflows.

If a target deployment cannot run KubeSONiC-managed feature containers, that deployment requires a separate approval path. A built-in host service or Debian package fallback changes the deployment model and ownership boundary and is not the design target for this HLD.

### 7.2 Existing Consumer Proxy Path

The proxy use case uses a host-local TACACS+ TCP listener as the compatibility surface for existing SONiC TACACS+ consumers. Existing consumers continue to use the current `TACPLUS|global` and `TACPLUS_SERVER|*` configuration. Operators configure the loopback listener as the first TACACS+ server, with existing non-TLS servers retained later in the list when migration fallback is desired.

```text
Existing SONiC consumer
  -> TACACS+ over TCP to 127.0.0.1 or ::1
  -> KubeSONiC-managed local forwarding service
  -> TACACS+ over TCP or TACACS+ over TLS to configured upstream servers
```

The local listener accepts TACACS+ packets from existing consumers on loopback. Obfuscation handling follows the ConfigDB integration rules in this HLD. The proxy preserves the TACACS+ message data but may rewrite TACACS+ session IDs to avoid collisions between local client components, so it treats TACACS+ shared-secret obfuscation as hop-local: local-hop obfuscation uses the loopback server configuration passkey, and upstream-hop obfuscation uses the selected upstream server configuration.

The KubeSONiC deployment must make the listener reachable from the host network namespace at the configured loopback address and TCP port. A pod-local `127.0.0.1` listener is not sufficient because existing PAM, shell, audit, accounting, and CLI components run in the SONiC host context. The exact mechanism, such as host networking or an approved host-local port exposure pattern, requires KubeSONiC review.

When the local listener is unavailable, existing SONiC TACACS+ clients should be able to try later non-TLS servers in the current `TACPLUS_SERVER` priority list according to existing client failover behavior. The local forwarding service must avoid converting upstream transport outages into authentication denials when fallback is configured; it should surface local service failure in a form that the existing clients treat as a server failure. The exact failover trigger must be confirmed against existing SONiC TACACS+ client behavior and covered by sonic-mgmt tests.

### 7.3 TACACS+ TLS Transport

The local forwarding service uses TCP for all upstream TACACS+ server communication. This HLD uses transport-security mode to distinguish plain TACACS+ over TCP from TACACS+ over TLS 1.3 on TCP:

1. Plain TACACS+ over TCP using the [RFC 8907](https://datatracker.ietf.org/doc/rfc8907/) shared-secret obfuscation model.
2. TACACS+ over TLS 1.3 on TCP using the [RFC 9887](https://datatracker.ietf.org/doc/rfc9887/) profile. TLS can use server certificate validation, mTLS, or TLS 1.3 PSK.

When certificate-backed TLS is enabled, the local forwarding service validates the server certificate using configured trust anchors and the configured server name. SNI is independent of the selected TLS credential choice and shall be sent when enabled and when a server domain name is configured, including TLS PSK deployments where the server uses SNI for virtual hosting or PSK selection. A server entry from `TACPLUS_SERVER` uses plain TACACS+ over TCP. A server entry from `TACPLUS_SERVER_TLS` uses TACACS+ over TLS.

The TLS transport design shall include these configuration inputs:

| Input | Purpose |
| --- | --- |
| Server table | Select plain TCP from `TACPLUS_SERVER` or TLS over TCP from `TACPLUS_SERVER_TLS`. |
| `tcp_port` | Select the TCP port for the target transport-security mode. TLS examples in this HLD use port 449. |
| `cipher_suites` | Colon-separated TLS 1.3 cipher suite preference list. Values shall use RFC 8446 Appendix B.4 names such as `TLS_AES_128_GCM_SHA256`. The CLI may default this field, but stored `TACPLUS_SERVER_TLS` rows shall contain it. |
| `domain_name` | Server name for certificate verification when certificates are used and for SNI when enabled. |
| `sni_enabled` | Enable or disable SNI. |
| `trust_anchor_ref` | Reference to a trusted CA bundle or certificate object. |
| `certificate_verify` | Enable or disable certificate verification. Unsafe disablement is diagnostic only. |
| `single_connection` | Request persistent connection reuse when the server supports it. |
| `psk_key_exchange` | Optional interop override for TLS 1.3 PSK key exchange policy when PSK is active. |
| `psk_key_exchange_groups` | Optional colon-separated approved TLS group preference list for PSK-DHE; providing groups implies TLS 1.3 `psk_dhe_ke`. |

TLS supported group values shall use the `NamedGroup` labels from [RFC 8446](https://www.rfc-editor.org/info/rfc8446) verbatim, such as `secp256r1`, `secp384r1`, `secp521r1`, `x25519`, `x448`, `ffdhe2048`, `ffdhe3072`, `ffdhe4096`, `ffdhe6144`, and `ffdhe8192`. The `cipher_suites` value shall be a colon-separated preference list of cipher suite names from RFC 8446 Appendix B.4, such as `TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384`.

The existing shared-secret `passkey` remains valid for the local compatibility hop, for plain TCP upstream servers, and for deployments where the TACACS+ server still requires a TACACS+ shared secret inside the TLS-protected channel.

### 7.4 TLS Credential Choices

The local forwarding service derives the TLS credential choice from the upstream server configuration shape. The design shall use SONiC credential references or protected file paths for certificate, key, and PSK material rather than raw sensitive values in CONFIG_DB. The working assumption is that ACMS or another SONiC-approved credential provisioning flow places the required material on disk, and the upstream TACACS+ configuration stores references or paths to that protected material.

The configuration model shall make these modes explicit:

| Mode | Required material |
| --- | --- |
| TLS server authentication | Server address, optional domain name, trust anchor file or profile reference. |
| mTLS | TLS server authentication material plus client certificate reference and client private key reference. |
| TLS PSK | PSK identity, protected PSK symmetric key file or credential reference, and optional PSK-DHE group policy. |

Certificate material used for TLS server authentication, including configured trust anchors or pinned server certificates, shall be DER-encoded X.509. In mTLS mode, the configured client certificate shall also be DER-encoded X.509.

All TLS modes may also carry a TACACS+ `passkey` when required for interoperability with servers that still expect a TACACS+ shared secret inside the TLS-protected channel. This is not compliant with RFC 9887 TACACS+ over TLS behavior and should not be treated as additional protection beyond TLS.

The PSK key exchange policy is a PSK sub-mode, not a separate TLS credential choice. CLI-created PSK configuration shall default to PSK with ephemeral Diffie-Hellman key exchange, matching TLS 1.3 `psk_dhe_ke`, by writing a SONiC-approved default `psk_key_exchange_groups` preference list. Operators may constrain the offered DHE groups with a colon-separated `psk_key_exchange_groups` preference list or an equivalent CLI option such as `--psk-key-exchange-groups`; providing groups implies `psk_dhe_ke`. Group names use RFC 8446 `NamedGroup` labels. A stored PSK row without `psk_key_exchange_groups` uses PSK-only mode, matching TLS 1.3 `psk_ke`, and should be used only for interoperability with servers that require PSK-only TLS 1.3 handshakes.

The implementation shall reject incomplete or ambiguous TLS configurations. For example, a client certificate without a private key, a PSK identity without a PSK symmetric key reference, or an upstream server row containing both mTLS client identity fields and PSK identity fields shall fail validation.

### 7.5 Single Connection Model

In single connection mode, the local forwarding service reuses an upstream connection for multiple TACACS+ sessions. TACACS+ packets are routed by session ID so simultaneous local clients can share a connection without opening a new upstream TCP or TLS connection for every request.

```text
+----------+   loopback TACACS+   +------------------+      one TLS connection
| client A | -------------------> |                  | =======================>
+----------+                      | local forwarding |      TACACS+ server
+----------+   loopback TACACS+   | service          | <=======================
| client B | -------------------> |                  |      multiplexed by
+----------+                      +------------------+      session ID
```

Dedicated connection mode remains available. In dedicated mode, a request uses its own upstream connection. This mode is required for compatibility with servers or deployments that do not support persistent single connection operation.

### 7.6 Ordered Failover and Recovery

The local forwarding service maintains upstream server state. The preferred upstream server is the first healthy server in the priority order configured by the new upstream ConfigDB tables. When the service maps SONiC upstream rows into the RFC 9950-based model used internally, the implementation must preserve that SONiC priority order, using a SONiC YANG extension when the base RFC 9950 model does not carry the needed ordering field. If the preferred upstream server fails, the service tries the next upstream server. While using a backup server, the service periodically probes the preferred server and moves traffic back when it recovers.

The service shall serialize reconnect attempts for each upstream server. If multiple local requests arrive while a reconnect is in progress, one reconnect attempt is performed and the other requests wait for the result.

### 7.7 Native UDS Interface

Native UDS IPC is the direct host-local API for SONiC components that need a gRPC/protobuf interface instead of the loopback TACACS+ proxy. Existing SONiC TACACS+ consumers remain on the loopback TACACS+ compatibility path unless a component owner chooses to integrate with UDS, so TLS can be introduced without replacing PAM, shell, audit, accounting, or CLI TACACS+ integrations.

Selected local clients may communicate with the local forwarding service through gRPC over a Unix domain socket. The default Linux endpoint would be a protected path such as `/run/tacacs.sock` or a SONiC-approved equivalent. Network IPC between compute devices remains out of scope.

The IPC schema shall be defined with protobuf so clients can be written in the language most natural for each SONiC component. gRPC is used only as a host-local IPC mechanism in this design; the upstream TACACS+ server protocol remains TACACS+ over TCP or TACACS+ over TLS on TCP.

The candidate IPC service exposes unary request/response methods for TACACS+ authentication, accounting, and authorization operations. Each request carries the local user/session context and operation-specific fields, such as password material for login authentication, command accounting arguments, or authorization arg-value pairs. The service selects an upstream server, opens or reuses the upstream TACACS+ connection, applies failover, and returns either the TACACS+ server response or a structured service error with retry guidance.

The candidate IPC scope is limited as follows:

- Authentication is a password-based unary request. The service uses the configured SONiC TACACS+ authentication type, such as PAP or ASCII, and does not expose an arbitrary interactive challenge loop to local clients in the native IPC contract. CHAP, MS-CHAP, password-change flows, and TACACS+ FOLLOW handling remain out of scope unless a later HLD expands them.
- Accounting is a unary request for command accounting. The local client supplies the user/session context, command, and command arguments, and the service returns the upstream accounting result or a structured service error.
- Authorization is a unary request for command or service authorization. The local client supplies the user/session context, privilege level, and arg-value pairs, and the service returns the upstream authorization result, including any returned arg-value pairs, or a structured service error.

The candidate IPC contract has the following shape:

```text
service TacacsLocalService
  Authenticate(AuthenticationRequest) -> AuthenticationReply
  Accounting(AccountingRequest)       -> AccountingReply
  Authorization(AuthorizationRequest) -> AuthorizationReply

AuthenticationRequest
  user, port, remote_address, password, authen_service, privilege_level

AuthenticationReply
  result = AuthenticationResponse { server, status, server_message, data }
         | ServiceError { message, server, retriable }

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

The socket permissions shall restrict access to trusted local users or groups. Host-side consumers, such as SONiC AAA integration modules, CLI diagnostic tools, or test clients, could use this IPC surface so they do not need to implement upstream TACACS+ packet framing, TLS handling, single connection negotiation, or failover. When the local forwarding feature is disabled, existing SONiC TACACS+ paths continue to use the current implementation and do not depend on native IPC.

### 7.8 SONiC ConfigDB Integration

The proxy use case keeps existing TCP compatibility configuration, TLS server configuration, and forwarder-local configuration separate.

The design keeps three configuration views:

| View | Purpose |
| --- | --- |
| Existing TCP compatibility view | Existing `TACPLUS` and `TACPLUS_SERVER` rows used by existing SONiC TACACS+ consumers. During migration, this view normally contains a loopback server first and optional non-TLS fallback servers later. The forwarding service reads this view for TCP upstream candidates after filtering its own loopback row. |
| TLS server view | New `TACPLUS_SERVER_TLS` rows used only by the local forwarding service for upstream TLS server configuration, credential references, priority order, and connection setup. |
| Forwarder-local view | New `TACPLUS_FORWARDER` row used only by the local forwarding service for local listener and agent settings. |

Existing SONiC `TACPLUS|global` and `TACPLUS_SERVER|*` rows remain the TCP shared-secret configuration view for existing SONiC TACACS+ consumers. These rows shall not contain TLS upstream server fields. Operators add a loopback `TACPLUS_SERVER` row as the first server when they want existing consumers to use the local forwarding service first.

The local forwarding service reads server candidates from both configuration sources:

1. Existing `TACPLUS_SERVER|*` rows describe TACACS+ over TCP with shared-secret obfuscation only. The service shall filter out the loopback row assigned to itself before treating these rows as upstream candidates.
2. New `TACPLUS_SERVER_TLS|*` rows describe TACACS+ over TLS upstream servers, including certificate validation, mTLS, PSK, SNI, TLS port, single connection mode, and protected credential references.

Forwarder-local settings, such as local listener address and port, are stored in a separate table such as `TACPLUS_FORWARDER|global`. Existing SONiC TACACS+ consumers do not read `TACPLUS_SERVER_TLS` or `TACPLUS_FORWARDER` rows, so they do not need to filter TLS and non-TLS upstream servers.

The local forwarding service combines the filtered TCP server candidates and TLS server candidates using configured priority order. Operators can add a TLS server and promote it above an existing TCP server, or demote the TCP server, so the TLS server is selected first while the TCP server remains available as fallback.

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

The proxy migration view uses those same existing rows with a loopback entry for the local forwarding service, plus a TLS server row for the upstream TLS candidate:

```text
TACPLUS_SERVER|127.0.0.1
  priority    "1"
  tcp_port    "49"
  timeout     "3"
  passkey     "loopback-secret"

TACPLUS_SERVER|192.0.2.10
  priority    "100"
  tcp_port    "49"
  timeout     "10"
  passkey     "upstream-secret"

TACPLUS_SERVER_TLS|192.0.2.20
  priority    "1"
  tcp_port    "449"
  cipher_suites "TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384"
  timeout     "10"
  domain_name "tacacs.example.com"
  sni_enabled "true"
  single_connection "true"
  passkey     "upstream-secret"
  psk_identity "sonic-switch-01"
  psk_secret_ref "/etc/sonic/credentials/tacacs-psk-01.key"
  psk_key_exchange_groups "x25519:secp256r1"
```

The proxy does not exchange or synchronize TACACS+ shared-secret obfuscation keys between hops. It terminates TACACS+ obfuscation at the forwarding boundary and applies the local-hop and upstream-hop obfuscation policies independently. TACACS+ obfuscation depends on packet header fields, including the session ID, and the proxy may rewrite TACACS+ session IDs to avoid collisions among local client components. Therefore, preserving TACACS+ message data across a proxied session may require deobfuscating and reobfuscating packet bodies rather than forwarding an obfuscated body unchanged.

- If the packet received from the local TACACS+ client is obfuscated, the proxy deobfuscates it using the loopback compatibility server configuration passkey.
- If the packet received from the local TACACS+ client is unobfuscated, the proxy treats the local-hop TACACS+ message data as already cleartext.
- Before sending a request upstream, if the selected upstream server configuration enables TACACS+ shared-secret obfuscation, the proxy obfuscates the upstream packet using the selected upstream server configuration and the upstream session ID.
- Before sending a request upstream, if the selected upstream server configuration does not enable TACACS+ shared-secret obfuscation, the proxy sends the upstream packet unobfuscated.
- When receiving a response from an upstream server that used TACACS+ shared-secret obfuscation, the proxy deobfuscates the response using the selected upstream server configuration.
- When sending a response back to a local client session that used TACACS+ shared-secret obfuscation, the proxy obfuscates the local response using the loopback compatibility server configuration passkey and the local client session ID.
- When sending a response back to a local client session that did not use TACACS+ shared-secret obfuscation, the proxy sends the local response unobfuscated.

When the loopback compatibility row configures a `passkey`, that value is the local-hop TACACS+ obfuscation key for existing local clients that send obfuscated packets to the loopback listener. The loopback `passkey` does not need to match any upstream server `passkey`; each upstream candidate uses its own `passkey` only for the upstream hop when that hop requires TACACS+ shared-secret obfuscation.

The loopback TCP hop is locally sniffable with tools such as tcpdump. Operators choose between obfuscating the loopback hop with the loopback compatibility row `passkey`, which hides local packet contents on that hop, and leaving the loopback hop unobfuscated, which avoids maintaining a local-hop TACACS+ shared secret. This choice is independent of upstream obfuscation and TLS policy because the proxy applies obfuscation per hop. The unobfuscated loopback option keeps a similar practical security posture to current on-box TACACS+ behavior because the protection boundary remains the local device and the upstream connection policy.

The SONiC CLI is not required to expose the full TACACS+ YANG tree directly. CLI and management changes update the existing TCP compatibility rows, new TLS server rows, and forwarder-local row through stable SONiC commands. The local forwarding service validates and maps the combined upstream candidate set before use. This HLD does not propose replacing Redis-backed ConfigDB storage with RFC 7951 JSON or another YANG-backed datastore; RFC 7951 is used here only for the lexical style of values that map to YANG-modeled data.

The upstream model should follow `ietf-system-tacacs-plus` concepts used by the implementation configuration library, including server entries, `server-authentication`, `client-identity`, `client-credentials`, `server-credentials`, and credential references. SONiC-specific extensions are expected where the base RFC 9950 model does not describe SONiC behavior, such as upstream server priority ordering. The service preserves references for reporting and resolves them only when building runtime connection settings.

The local forwarding service reads CONFIG_DB at startup and observes relevant upstream key changes through Redis keyspace notifications. It debounces related changes, re-reads the complete effective upstream TACACS+ configuration, validates it, and hot-reloads affected upstream server state. If the new configuration is invalid, the service keeps the previous valid runtime state when one exists, logs the validation error, and reports the configuration failure in diagnostics.

### 7.9 Secret and Certificate Material

The first implementation should follow the existing SONiC credential pattern used by gNMI and gRPC clients: configuration stores references or paths, while private material is provisioned as protected files on disk. ACMS, gNSI Certz/Credentialz, or another SONiC-approved credential provisioning flow is expected to place trust bundles, client certificates, private keys, and TLS PSK symmetric key material in a root-owned credential location. Existing SONiC examples use locations such as `/etc/sonic/credentials/`, `/etc/sonic/telemetry/`, and service-specific certificate paths; the final TACACS+ directory or profile naming shall be reviewed with platform and security owners.

CONFIG_DB shall not contain raw private key or raw PSK contents. The upstream TACACS+ TLS server row shall contain only references for private key and PSK material that the local forwarding service resolves at runtime:

| Reference | Runtime material |
| --- | --- |
| `trust_anchor_ref` | DER-encoded X.509 trust anchor material, pinned server certificate material, trust bundle file, or credential profile used for server certificate validation. |
| `client_certificate_ref` | DER-encoded X.509 client certificate file or credential profile used for mTLS. |
| `client_private_key_ref` | Root-protected client private key file or credential profile used for mTLS. |
| `psk_secret_ref` | Root-protected file or credential object containing the TLS PSK symmetric key material. |

Referenced files shall be root-owned, writable only by the provisioning authority, and readable only by the local forwarding service or the least-privileged group required for operation. The service shall validate that referenced material exists and has acceptable permissions before using it. Missing files, unreadable files, unsafe permissions, or mismatched certificate/key pairs shall cause configuration validation or connection setup to fail.

Credential rotation should be compatible with ACMS or gNSI-style update semantics. A new credential may be staged outside the active upstream TACACS+ server row, validated by the provisioning flow, then referenced by an atomic TACACS+ configuration update. If a file path remains stable and ACMS replaces the file contents atomically, the service shall rebuild affected connections through the same hot-reload path used for ConfigDB changes.

The implementation shall prevent sensitive values from appearing in show command output, syslog, debug logs, crash dumps where practical, and generated configuration reports. File paths, credential object names, certificate thumbprints, certificate expiry timestamps, and TLS PSK identities may be shown when useful for troubleshooting, but raw private key material, PSK values, shared secrets, and user passwords shall always be masked or omitted.

### 7.10 Error Handling

The loopback compatibility path speaks TACACS+ to existing SONiC consumers, so it cannot depend on structured native service errors. The local forwarding service shall distinguish authentication results from local forwarding or upstream transport failures. Authentication failures returned by an upstream TACACS+ server shall be returned as TACACS+ authentication results. Local service failures, missing upstream availability, and upstream transport failures shall be surfaced in a way that existing clients treat as server failure when migration fallback is configured.

Native UDS clients may receive structured service errors. Errors that may succeed after reconnect or failover should be marked retriable. Errors caused by invalid configuration, missing TLS credential material, or failed TLS validation should be non-retriable until configuration changes.

Expected error behavior:

| Condition | Behavior |
| --- | --- |
| Preferred upstream TACACS+ server unreachable | Try next upstream server in priority order. |
| All upstream TACACS+ servers unreachable | Surface local service failure in a form that enables existing fallback when configured; return retriable service error to native IPC clients. |
| TLS certificate validation failure | Reject connection and log validation failure without exposing secrets. |
| Incomplete TLS credential configuration | Reject the new configuration and keep the previous valid state when available. |
| CONFIG_DB parse failure | Keep previous valid state when available, otherwise keep feature inactive. |
| Loopback listener unavailable | Existing SONiC TACACS+ consumers may try later existing `TACPLUS_SERVER` entries according to existing failover behavior. |
| Native IPC endpoint unavailable | Native clients receive a retriable local service error. |

### 7.11 Serviceability and Debug

The implementation shall provide logs and counters for operational troubleshooting. Counter names and semantics shall align at minimum with the RFC 9950 TACACS+ YANG statistics leaves for each configured server. Expected diagnostics include:

- Container startup, listener startup, and active configuration source.
- Current preferred TACACS+ server and failover state.
- Active TLS credential mode and non-secret identity details. Active TLS sessions shall report the negotiated TLS cipher suite. Certificate-backed TLS sessions shall report the validated server certificate SHA-256 thumbprint and certificate expiry timestamp in ISO 8601/RFC 3339 UTC format. mTLS sessions shall also report the configured client certificate SHA-256 thumbprint and expiry timestamp in the same format. TLS 1.3 PSK sessions shall report the configured PSK identity, effective PSK key exchange policy, and selected DHE group when DHE is active, not the PSK value.
- RFC 9950 per-server statistics: `connection-opens`, `connection-closes`, `connection-aborts`, `connection-failures`, `connection-timeouts`, `messages-sent`, `messages-received`, `errors-received`, `sessions`, and `cert-errors`.
- TLS handshake failures and certificate validation errors, mapped to the appropriate RFC-aligned counters and logs.
- Loopback request failures, native IPC request failures, and reconnect attempts.
- CONFIG_DB parse and validation failures.

Raw public key TLS server authentication is not supported by this design, so raw-public-key status and counters are not shown.

Show commands should present status without exposing sensitive values.

### 7.12 Container Packaging and Runtime Dependencies

The proposed SONiC deployment should follow the KubeSONiC feature container flow. The local forwarding service and related tools are delivered in a container image whose manifest declares the required runtime mounts, networking, environment, and feature labels. The SONiC image should contain only the minimal service metadata and management glue required for KubeSONiC to start, stop, and observe the feature.

The container image may be built from an approved source import, submodule, or external build pipeline and published to an approved registry. The KubeSONiC manifest controls which image version runs on eligible SONiC nodes. This allows service fixes to move through container qualification and manifest rollout without requiring every forwarding-service change to rebuild and validate the root SONiC OS image.

The container and management split should allow SONiC images or operators to enable only the desired components, such as the local forwarding service, diagnostic tools, operator CLI support, and native IPC client integrations.

The following packaging and runtime dependencies are expected:

| Dependency or deployment item | Purpose |
| --- | --- |
| Container image | Provides the local forwarding service binary, TLS library support, Redis client support, and supporting runtime dependencies. |
| KubeSONiC manifest | Declares image version, node selectors, feature labels, network exposure, resource limits, restart policy, and required mounts. |
| Host-loopback exposure | Makes the local TACACS+ listener reachable from existing SONiC host consumers at the configured loopback address and TCP port. |
| CONFIG_DB access | Allows the service to read and subscribe to the new upstream TACACS+ tables through a SONiC-approved Redis access pattern. |
| Credential mounts or APIs | Provide read access to trust anchors, client certificates, private keys, and PSK material without storing raw secrets in ConfigDB. |
| Diagnostic and operator tooling | Provides show commands, test commands, and logs either in the feature container or through SONiC utilities. |

## 8. SAI API

No SAI API changes are required for this feature.

This feature is a control-plane AAA and host-service feature. It does not add or modify ASIC_DB objects, does not require new SAI attributes, and does not require switch ASIC vendor implementation.

## 9. Configuration and Management

### 9.1 Manifest

This design proposes a KubeSONiC-managed feature container. A KubeSONiC manifest is required for this feature.

The manifest shall describe the local forwarding service image, node selector labels, feature enablement labels, restart policy, resource limits, ConfigDB access, credential mounts or APIs, logs, and the host-local listener exposure. The manifest shall make the listener reachable from the SONiC host network namespace only on the configured loopback address and TCP port.

The manifest shall not expose the local compatibility listener on the management interface or any data plane interface. If host networking is used, the service itself must still bind only to loopback. If KubeSONiC uses another approved host-local port exposure pattern, sonic-mgmt tests must verify that the listener is not network reachable.

### 9.2 CLI and Configuration Model Enhancements

CLI changes shall be reviewed with sonic-utilities maintainers. The exact command syntax is subject to review, but the following capabilities are required:

The CLI is the operator workflow. It should provide stable SONiC commands that update the existing TCP compatibility configuration, the new TLS server configuration, and the forwarder-local configuration without requiring operators to understand the full TACACS+ YANG tree. The local forwarding service validates the combined upstream candidate set before using it.

The existing `config tacacs` commands continue to manage `TACPLUS|global` and `TACPLUS_SERVER|*`. During migration, operators use those commands to put the loopback listener first and to keep existing non-TLS fallback servers later if desired. These rows remain plain TACACS+ TCP rows and shall not receive upstream TLS fields.

New TLS-specific commands manage `TACPLUS_SERVER_TLS|*` rows. These commands add, modify, and delete TLS server entries; they do not change existing `TACPLUS_SERVER|*` TCP entries into TLS entries. To move traffic to TLS, an operator adds a TLS server entry and assigns it a higher priority than the existing TCP server, or demotes the TCP server, so the local forwarding service selects the TLS server first while the TCP server remains available as fallback.

The stored TLS server row shall remain valid after every committed change. The CLI shall not leave an active `TACPLUS_SERVER_TLS` row containing fields from multiple TLS credential choices. For example, when a TLS server uses PSK, the row shall not also contain mTLS client certificate and key fields. When a TLS server uses mTLS, the row shall not also contain PSK identity, secret, or PSK key exchange fields. A TLS command must fail with a clear error if required target fields are missing, the target configuration is internally inconsistent, or the final row would be ambiguous.

The local forwarding service shall repeat validation when reading stored TCP and TLS server configuration so direct ConfigDB updates, config reload, or restored configuration cannot bypass the same checks.

- Enable or disable the local forwarding feature.
- Configure the existing `TACPLUS_SERVER` compatibility list with the loopback listener first and optional non-TLS fallback servers later.
- Configure the forwarder-local listener and agent settings in `TACPLUS_FORWARDER`.
- Add, modify, and delete TACACS+ over TLS server entries in `TACPLUS_SERVER_TLS`.
- Select certificate-based TLS server authentication, mTLS, or PSK for a TLS server by writing the corresponding valid TLS fields.
- Set the TLS TCP port for a TLS server.
- Configure the TLS 1.3 cipher suite preference list for a TLS server using RFC 8446 Appendix B.4 cipher suite names.
- Promote or demote TLS and TCP servers by priority so the local forwarding service selects the desired server first.
- Configure server domain name and SNI behavior.
- Configure references to trust anchors, client certificates, client private keys, PSK identity, and protected PSK symmetric key material.
- Configure single connection mode or dedicated connection mode.
- Display container health, loopback listener health, upstream connection state, failover state, and counters.

Candidate CLI examples:

```bash
config feature state tacacs-tls-forwarder enabled

# Existing SONiC TACACS+ consumers use loopback first.
config tacacs add 127.0.0.1 --port 49 --timeout 3 --key loopback-secret --type pap --pri 1

# Optional migration fallback through the existing non-TLS path.
config tacacs add 192.0.2.10 --port 49 --timeout 10 --key upstream-secret --type pap --pri 100

# Add a TACACS+ over TLS server with certificate validation using a CA bundle.
config tacacs tls add 192.0.2.20 certificate \
  --port 449 \
  --priority 1 \
  --key upstream-secret \
  --cipher-suites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384 \
  --domain-name tacacs.example.com \
  --trust-anchor-ref /etc/sonic/credentials/tacacs-ca.pem

# Modify a TACACS+ over TLS server to use a pinned server certificate.
config tacacs tls modify 192.0.2.20 certificate \
  --port 449 \
  --domain-name tacacs.example.com \
  --trust-anchor-ref /etc/sonic/credentials/tacacs-server.pem

# Configure TACACS+ over TLS without certificate validation. This is diagnostic only.
config tacacs tls modify 192.0.2.20 certificate \
  --port 449 \
  --domain-name tacacs.example.com \
  --certificate-verify disabled

# Add a TACACS+ over TLS 1.3 PSK server. The domain name enables SNI when SNI is active. PSK-DHE uses approved default groups unless groups are supplied.
config tacacs tls add 192.0.2.30 psk \
  --port 449 \
  --priority 2 \
  --key upstream-secret \
  --cipher-suites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384 \
  --domain-name tacacs.example.com \
  --psk-identity sonic-switch-01 \
  --psk-secret-ref /etc/sonic/credentials/tacacs-psk-01.key

# Promote TLS by priority and keep the existing TCP server as fallback.
config tacacs tls modify 192.0.2.20 --priority 1
config tacacs modify 192.0.2.10 --pri 100

config tacacs tls modify 192.0.2.20 --single-connection enabled
show tacacs tls-forwarder status
show tacacs tls-forwarder counters
```

The TLS command family writes only `TACPLUS_SERVER_TLS` rows. Existing `config tacacs` commands write only `TACPLUS` and `TACPLUS_SERVER` rows. Priority changes control which server the local forwarding service selects first; they do not convert a TCP server row into a TLS server row or a TLS server row into a TCP server row. CLI commands default `cipher_suites` to a strong RFC 8446 TLS 1.3 cipher suite preference list when the operator does not supply one. For PSK, the TLS command defaults to PSK-DHE with the SONiC-approved group preference list; operators may add `--psk-key-exchange-groups x25519:secp256r1` when they need to constrain the offered groups. Operators must explicitly provide `--psk-key-exchange psk-only` to request TLS 1.3 `psk_ke` for interoperability. If the final CLI syntax includes separate credential objects, operators may stage those objects first, but the active TLS server row still changes only from one valid TLS server configuration to another.

Candidate CLI, ConfigDB, and model mapping:

| CLI option or model concept | ConfigDB table or field | Purpose |
| --- | --- | --- |
| `--local-listen-address` | `TACPLUS_FORWARDER|global` / `local_listen_address` | Host-local loopback address used by existing SONiC TACACS+ consumers. |
| `--local-listen-port` | `TACPLUS_FORWARDER|global` / `local_listen_port` | TCP port used by the local loopback TACACS+ listener. |
| Server command family | `TACPLUS_SERVER` or `TACPLUS_SERVER_TLS` | Existing `config tacacs` commands manage TACACS+ over TCP/shared-secret rows; `config tacacs tls` commands manage TACACS+ over TLS rows. |
| `--port` | `tcp_port` | TCP port for the selected transport-security mode. |
| `--priority` or `--pri` | `priority` | Upstream server ordering used by the local forwarding service. |
| `--timeout` | `timeout` | Runtime server timeout policy. |
| `--cipher-suites` | `cipher_suites` | Colon-separated TLS 1.3 cipher suite preference list from RFC 8446 Appendix B.4, such as `TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384`. The CLI may default this field, but stored `TACPLUS_SERVER_TLS` rows shall contain it. |
| `--domain-name` | `domain_name` | Name used for certificate verification and SNI. |
| `--sni-enabled` | `sni_enabled` | Enable SNI. |
| `--single-connection` | `single_connection` | Enable persistent connection reuse. |
| `--key` | `passkey` | TACACS+ shared-secret value for the row being configured. On a loopback compatibility row, this is the local-hop obfuscation key for existing clients. On an upstream TCP or TLS row, this is the upstream-hop obfuscation key when required by the TACACS+ server. |
| `--trust-anchor-ref` | `trust_anchor_ref` | Reference to DER-encoded X.509 trust anchor material, pinned server certificate material, trust bundle file, or credential profile. |
| `--client-certificate-ref` | `client_certificate_ref` | Reference to DER-encoded X.509 client certificate file or credential profile for mTLS. |
| `--client-private-key-ref` | `client_private_key_ref` | Reference to protected client key file or credential profile. |
| `--psk-identity` | `psk_identity` | TLS PSK identity. |
| `--psk-secret-ref` | `psk_secret_ref` | Reference to protected TLS PSK symmetric key file or credential object. |
| `--psk-key-exchange-groups` | `psk_key_exchange_groups` | Optional colon-separated approved TLS group preference list for PSK-DHE; providing groups implies TLS 1.3 `psk_dhe_ke`. |
| `--psk-key-exchange` | `psk_key_exchange` | Optional CLI interop override. The value `psk-only` maps to TLS 1.3 `psk_ke`, must not be combined with DHE groups, and must be explicitly requested. |

### 9.3 Config DB Enhancements

Existing TACACS+ CONFIG_DB entries remain valid. This HLD does not propose changing Redis to store TACACS+ configuration as a JSON document. The JSON below is the normal SONiC `config_db.json` representation of Redis-backed CONFIG_DB tables and hash fields. New TLS values use RFC 7951 JSON encoding lexical style where those values map to YANG-modeled data, while ConfigDB table names and field names keep the existing SONiC TACACS+ naming style.

The proposal is to keep `TACPLUS` and `TACPLUS_SERVER` as the existing TCP shared-secret tables, add `TACPLUS_SERVER_TLS` for TLS upstream servers, and add `TACPLUS_FORWARDER` for local forwarding service settings. Field and table names are draft names and require SONiC schema review.

The `FEATURE` scope fields in the example follow existing SONiC multi-ASIC service metadata. `has_global_scope` set to `True` and `has_per_asic_scope` set to `False` mean the local forwarding service is a single host-global feature instance for the SONiC OS instance, not a per-ASIC service instance. These fields do not imply one forwarding service for an entire modular chassis across multiple compute devices. A per-ASIC, chassis-wide, or DPU-specific service topology would require separate SONiC ownership and service-scope review, including confirmation that the target scope has the required local CONFIG_DB/Redis access, loopback exposure, and protected credential provisioning.

```json
{
  "FEATURE": {
    "tacacs-tls-forwarder": {
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
    "127.0.0.1": {
      "priority": "1",
      "tcp_port": "49",
      "timeout": "3",
      "passkey": "loopback-secret"
    },
    "192.0.2.10": {
      "priority": "100",
      "tcp_port": "49",
      "timeout": "10",
      "passkey": "upstream-secret"
    }
  },
  "TACPLUS_FORWARDER": {
    "global": {
      "auth_type": "pap",
      "timeout": "5",
      "local_listen_address": "127.0.0.1",
      "local_listen_port": "49"
    }
  },
  "TACPLUS_SERVER_TLS": {
    "192.0.2.20": {
      "priority": "1",
      "tcp_port": "449",
      "cipher_suites": "TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384",
      "timeout": "10",
      "domain_name": "tacacs.example.com",
      "sni_enabled": "true",
      "single_connection": "true",
      "passkey": "upstream-secret",
      "psk_identity": "sonic-switch-01",
      "psk_secret_ref": "/etc/sonic/credentials/tacacs-psk-01.key",
      "psk_key_exchange_groups": "x25519:secp256r1"
    }
  }
}
```

The following rules apply:

- Existing `TACPLUS` and `TACPLUS_SERVER` rows remain valid TACACS+ TCP/shared-secret rows and shall not contain upstream TLS-only fields.
- Existing consumers read only the existing compatibility rows. The new `TACPLUS_SERVER_TLS` and `TACPLUS_FORWARDER` rows are used only by the local forwarding service and management tooling.
- The loopback compatibility row shall point to a host-local address and shall be the first server only when operators want existing consumers to use the forwarding service first.
- The local forwarding service shall filter out the loopback compatibility row assigned to itself before treating `TACPLUS_SERVER` rows as upstream TCP candidates.
- Optional non-TLS fallback servers may remain later in the existing `TACPLUS_SERVER` list during migration.
- The local listener address must be loopback or another SONiC-approved host-local endpoint.
- Upstream server rows shall not target the local listener address and port.
- `TACPLUS_SERVER` rows are upstream plain TCP/shared-secret candidates after loopback filtering.
- `TACPLUS_SERVER_TLS` rows are upstream TLS candidates and must include a target TCP port and `cipher_suites` for the TLS mode.
- Stored `TACPLUS_SERVER`, `TACPLUS_SERVER_TLS`, and `TACPLUS_FORWARDER` rows are mapped into the validated runtime configuration before use.
- The local forwarding service shall combine filtered TCP candidates and TLS candidates using configured priority order.
- `cipher_suites` shall be a colon-separated, non-empty preference list of RFC 8446 Appendix B.4 TLS 1.3 cipher suite names. CLI commands may default it to a strong value, but stored `TACPLUS_SERVER_TLS` rows shall contain the field.
- Raw private keys and raw PSK values shall not be stored directly in upstream rows; only ACMS-provisioned file paths, credential object names, or profile references shall be stored.
- `passkey` is accepted in any `TACPLUS_SERVER_TLS` credential mode only for interoperability with TACACS+ servers that still expect a TACACS+ shared secret inside the TLS-protected channel. This is not RFC 9887-compliant TACACS+ over TLS behavior.
- Configuration validation shall reject incomplete or ambiguous `TACPLUS_SERVER_TLS` credential settings. For example, an entry with `psk_identity` is incomplete without `psk_secret_ref`, and an entry with both PSK fields and mTLS client certificate fields is ambiguous.
- A stored TLS PSK row with `psk_key_exchange_groups` present uses TLS 1.3 `psk_dhe_ke`. A stored TLS PSK row without `psk_key_exchange_groups` uses TLS 1.3 `psk_ke` and does not offer DHE groups. CLI commands shall write a SONiC-approved default `psk_key_exchange_groups` value unless the operator explicitly requests PSK-only interop mode.
- `psk_key_exchange_groups` is valid only for TLS PSK server rows and implies TLS 1.3 `psk_dhe_ke`. The group list must be colon-separated, non-empty, ordered by preference, and limited to approved RFC 8446 `NamedGroup` labels.
- `psk_key_exchange` is valid only for TLS PSK server rows. The value `psk-only` requests TLS 1.3 `psk_ke` for interoperability, must not be combined with `psk_key_exchange_groups`, and must be explicitly requested.
- Configuration validation shall derive the active TLS credential mode from the populated credential fields. A separate stored `tls_credential_mode` flag is not required for the service to decide how to connect.
- CLI commands that add or modify TLS server rows shall set the target TLS fields and commit only a valid final `TACPLUS_SERVER_TLS` row. Direct ConfigDB edits are still validated by the local forwarding service when it loads or hot-reloads configuration.

Candidate ConfigDB-to-runtime mapping:

| Stored SONiC field | Model concept |
| --- | --- |
| `TACPLUS_SERVER` row key for loopback | Existing compatibility server entry consumed by existing SONiC TACACS+ clients. |
| `TACPLUS_SERVER` non-loopback row key | Upstream plain TCP/shared-secret server entry after loopback filtering. |
| `TACPLUS_FORWARDER` row | Global forwarding settings, including local listener address, local listener port, authentication type, and default timeout. |
| `TACPLUS_SERVER_TLS` row key | Upstream TLS server entry with name/address derived from the SONiC row. |
| `tcp_port` | `server.port`. |
| `cipher_suites` | Colon-separated TLS 1.3 cipher suite preference list from RFC 8446 Appendix B.4. |
| `priority` | Upstream server ordering, preserved through a SONiC extension to the RFC 9950-based model when needed. |
| `timeout` | Runtime server timeout policy. |
| `domain_name` and `sni_enabled` | `domain-name` and `sni-enabled`. |
| `trust_anchor_ref` | `server-authentication` credential reference, SONiC-approved truststore reference, or protected CA bundle path. |
| `client_certificate_ref` and `client_private_key_ref` | `client-identity` credential reference, SONiC-approved keystore reference, or protected certificate/key path. |
| `passkey` | TACACS+ shared-secret value for TACACS+ payload obfuscation on the row's hop. For the loopback compatibility row, it is the local-hop obfuscation key used with existing clients. For upstream TCP or TLS rows, it is the upstream-hop obfuscation key when required by the TACACS+ server. |
| `psk_identity` and `psk_secret_ref` | TLS PSK identity and protected symmetric key file or credential reference. |
| `psk_key_exchange_groups` | Colon-separated approved RFC 8446 `NamedGroup` preference list for PSK-DHE; presence implies TLS 1.3 `psk_dhe_ke`. |
| `psk_key_exchange` | Optional interoperability override. The value `psk-only` maps to TLS 1.3 `psk_ke`; stored rows without `psk_key_exchange_groups` also use `psk_ke`. CLI commands normally write default DHE groups unless PSK-only interop mode is explicitly requested. |
| `single_connection` | Service connection reuse policy associated with the upstream server entry. |

The exact ACMS integration, directory names, and profile naming remain subject to SONiC review. The design prioritizes an isolated upstream mapping that preserves current ConfigDB behavior.

### 9.4 Logs, Counters, and Show Commands

The implementation shall include operator-facing status and counters. Counter output shall expose the RFC 9950 TACACS+ statistics leaves per server. Candidate show output includes:

```text
show tacacs tls-forwarder status
  Feature state: disabled|enabled
  Container state: running|stopped|failed|pending
  Listener: 127.0.0.1:49
  Active upstream server: 192.0.2.20
  Transport: tls
  TLS negotiated cipher suite: TLS_AES_128_GCM_SHA256
  TLS credential mode: certificate|mtls|psk
  Server certificate thumbprint (SHA-256): 3A:5E:...:91 (certificate/mTLS)
  Server certificate expires: 2027-05-25T18:30:00Z (certificate/mTLS)
  Client certificate thumbprint (SHA-256): A1:22:...:0F (mTLS)
  Client certificate expires: 2027-05-25T18:30:00Z (mTLS)
  TLS PSK identity: sonic-switch-01 (PSK)
  TLS PSK key exchange: DHE (psk_dhe_ke)
  TLS PSK selected DHE group: x25519
  Failover state: preferred-active|failed-over|no-responsive-server

show tacacs tls-forwarder counters
  Upstream server: 192.0.2.20
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

The implementation may expose additional SONiC-local counters, such as loopback requests accepted, rejected, timed out, retried, or forwarded. For the proxy use case, SONiC-local counters should include loopback listener accepts, loopback listener rejects, local TACACS+ decode failures, upstream selection failures, and existing fallback-triggering local failures. UDS counters may be added when native IPC clients are implemented. Those counters shall not replace the RFC 9950-aligned server statistics.

Sensitive fields shall be masked or omitted from all show output.

The server certificate thumbprint and expiry fields are shown when the active TLS mode validates a server certificate. The client certificate thumbprint and expiry fields are shown when mTLS is active. The PSK identity, effective key exchange policy, and DHE group selection fields are shown when TLS 1.3 PSK is active; the PSK value and PSK secret reference remain hidden or masked.

## 10. Warmboot and Fastboot Design Impact

This feature does not program the ASIC and does not require SAI state restore. Therefore, it is not expected to affect data plane warmboot or fastboot behavior.

When the feature is disabled, there shall be no local forwarding container startup and no runtime memory growth from this feature.

When the feature is enabled, the KubeSONiC-managed local forwarding container starts after CONFIG_DB and network availability according to the approved feature dependency model. It shall not block database service startup, platform initialization, or data plane restoration.

### 10.1 Warmboot and Fastboot Performance Impact

The feature shall be analyzed against the following boot impact points:

- The local forwarding service reads CONFIG_DB and may open upstream TACACS+ connections after its container starts. This must not be in the boot critical path for switching data plane restoration.
- TLS handshakes can be delayed until the service starts or until the first TACACS+ request, depending on final service policy.
- The feature shall not add sleeps or long-running waits to existing SONiC boot scripts.
- The feature shall not require Jinja template rendering in the boot critical path when disabled.
- If enabled, the service may be delayed until management network readiness, subject to SONiC service ordering review.
- Warmboot and fastboot regression tests shall verify no unexpected data plane downtime is introduced.

## 11. Memory Consumption

When the feature is disabled by configuration, there shall be no running local forwarding service container. Installed feature metadata does not create runtime memory consumption.

When enabled, memory consumption comes from:

- One local forwarding service process in the feature container.
- One upstream connection state machine per configured server, with only the active server normally holding an established connection.
- Bounded request and response buffers per loopback TACACS+ request.
- Optional TLS session state and certificate material loaded by the service.

The implementation shall cap request sizes and prevent unbounded queue growth. Long-running tests shall verify that repeated configuration changes, upstream server failover, loopback requests, and native IPC requests do not cause unbounded memory growth.

## 12. Restrictions/Limitations

- The feature is disabled by default unless explicitly enabled.
- The feature is additive and does not replace existing SONiC TACACS+ behavior.
- The proxy use case depends on a KubeSONiC deployment path that can run the feature container and expose a host-local loopback listener.
- The selected TLS library must support every TLS credential choice, PSK key exchange policy, and configured PSK-DHE TLS group accepted by the configuration model.
- The current upstream SONiC TACACS+ schema does not contain all TLS certificate, PSK, or trust anchor fields. Schema work is required.
- TLS fields are stored in `TACPLUS_SERVER_TLS`, not in existing `TACPLUS_SERVER` rows.
- Raw private keys and raw PSK material shall not be placed in plaintext CONFIG_DB fields. TACACS+ `passkey` storage follows the existing `TACPLUS` and `TACPLUS_SERVER` behavior.
- ConfigDB changes shall be applied through hot-reload with debounce. Invalid new configuration keeps the previous valid runtime state when one exists.
- Raw public key TLS server authentication is not supported by this design.
- This HLD does not improve shell command authorization coverage. That is covered by a separate HLD.
- Native UDS integrations for PAM, shell, audit, accounting, and CLI consumers are optional component work; upstream TACACS+ TLS does not require those current modules to be replaced.
- The exact ACMS integration, directory paths, permissions, and rotation lifecycle for TLS key material, PSK material, and trust anchors require SONiC review.

## 13. Testing Requirements/Design

### 13.1 Unit Test Cases

The implementation shall include unit tests for the following items:

- Parsing existing `TACPLUS|global` and `TACPLUS_SERVER|*` rows for compatibility checks.
- Parsing new `TACPLUS_FORWARDER|global` and `TACPLUS_SERVER_TLS|*` rows.
- Validating loopback listener configuration, including host-local address, TCP port, and rejection of upstream self-targeting loops.
- Validating upstream TACACS+ configuration, including credential references, priority ordering across filtered TCP rows and TLS rows, target port, and TLS credential choices.
- CLI validation rejects adding or modifying a TLS server row when required fields for the target TLS credential shape are missing.
- CLI validation rejects direct or restored TLS server rows with redundant credential fields that would make the TLS credential choice ambiguous.
- CLI validation keeps TCP server rows and TLS server rows separate; priority changes can promote TLS above TCP without changing an existing TCP row into a TLS row.
- Parsing TLS transport fields, domain name, SNI, cipher suite preference lists, PSK key exchange mode, PSK-DHE group lists, and single connection mode.
- Rejecting empty or unsupported TLS cipher suite preference lists.
- Rejecting incomplete TLS credential configurations, including missing client certificate material or missing PSK material for the selected choice.
- Rejecting unsupported, empty, or unapproved PSK-DHE group lists and rejecting PSK-only configuration combined with DHE groups.
- Deobfuscating and reobfuscating proxied TACACS+ packets when loopback and upstream hops use different session IDs or different passkeys, while preserving TACACS+ message data.
- Rejecting referenced credential files that are missing, unreadable, or have unsafe ownership or permissions.
- Masking sensitive fields in logs and show output helpers.
- Selecting preferred upstream server and ordered failover behavior.
- Serializing reconnect attempts per upstream server.
- Mapping upstream transport failures into local TACACS+ listener behavior that can trigger existing fallback.
- Native IPC error mapping and retriable flag behavior.
- CLI/YANG validation for separated compatibility and upstream configuration.

### 13.2 System Test Cases

The implementation shall include system tests for the following items:

- Existing TACACS+ shared-secret configuration continues to work with the local forwarding feature disabled.
- The local forwarding feature can be enabled and disabled through the SONiC feature mechanism and KubeSONiC controls.
- KubeSONiC deploys the feature container only on eligible nodes and reports container state.
- The local listener is reachable from existing SONiC host TACACS+ consumers on loopback and is not reachable from management or data plane interfaces.
- Existing SONiC TACACS+ consumers use the loopback `TACPLUS_SERVER` row first and can use configured non-TLS fallback servers later in the existing list.
- The local forwarding service filters its own loopback row before using `TACPLUS_SERVER` entries as upstream TCP candidates.
- The local forwarding service reads upstream TACACS+ server configuration from CONFIG_DB.
- The local forwarding service reports the active configuration source and validates the runtime configuration derived from stored upstream ConfigDB rows.
- CLI attempts to add or modify a `TACPLUS_SERVER_TLS` row fail before commit when the effective TLS server configuration is incomplete or ambiguous.
- CLI TLS server add and modify commands commit only valid `TACPLUS_SERVER_TLS` rows and do not mutate existing `TACPLUS_SERVER` TCP rows.
- Priority changes can promote a TLS server above an existing TCP server or demote the TCP server so the local forwarding service selects TLS first while keeping TCP fallback available.
- The local forwarding service connects to an upstream TACACS+ server over TCP.
- The local forwarding service connects to an upstream TACACS+ server over TLS with server certificate verification.
- The local forwarding service connects with mTLS using configured client certificate material.
- The local forwarding service connects to TLS servers using each configured TLS credential choice.
- The local forwarding service connects to TLS PSK servers using the default approved PSK-DHE groups, explicit PSK-DHE group lists, and explicit PSK-only interop mode when supported.
- Invalid certificate, wrong server name, or missing trust anchor causes connection failure.
- Multiple upstream TACACS+ servers fail over in configured priority order.
- Preferred server probing returns traffic to the preferred server after recovery.
- Single connection mode reuses upstream connections for multiple requests.
- Dedicated connection mode opens separate connections for compatibility.
- CONFIG_DB changes are observed, debounced, validated, and logged.
- Changed upstream server sets are hot-reloaded without container restart, and invalid changes keep the previous valid runtime state when available.

### 13.3 Security Test Cases

The implementation shall include security tests for the following items:

- Private keys, PSK values, shared secrets, and passwords are not printed by show commands.
- Sensitive fields are not emitted in normal logs.
- ConfigDB contains only credential references or paths for private key and PSK material, not raw private key or raw PSK contents.
- The loopback listener does not bind to network-reachable interfaces.
- Native IPC socket permissions prevent unauthorized local access.
- TLS certificate verification rejects expired, untrusted, and wrong-name certificates.
- Unsafe certificate verification disablement is visible in configuration and logs.

### 13.4 sonic-mgmt Test Plan

A sonic-mgmt test plan shall be prepared and reviewed before broad enablement. The test plan shall cover:

- Configuration load and save behavior.
- Separation between existing compatibility rows and upstream forwarding rows.
- KubeSONiC feature enable, disable, deployment, rollback, and container health behavior.
- Loopback listener behavior and existing SONiC TACACS+ consumer compatibility.
- Plain TCP and TLS-over-TCP server connectivity across certificate-based server authentication, mTLS, and PSK credential choices.
- Failover and recovery.
- Backward compatibility with existing TACACS+ configuration.
- Existing non-TLS fallback behavior when the forwarding feature or all upstream servers are unavailable.
- Hot-reload behavior for upstream TACACS+ ConfigDB changes.
- Warmboot and fastboot regression.

### 13.5 Backward Compatibility and Regression Tests

Backward compatibility tests shall verify:

- Existing TACACS+ ConfigDB without new fields loads successfully.
- Existing CLI-generated configuration can be saved and restored.
- Disabling the local forwarding feature restores existing TACACS+ behavior.
- Upgrading from a release without the local forwarding feature does not enable the new feature unexpectedly.
- Downgrading with new upstream tables does not break the old TACACS+ path because existing consumers do not read those tables.
- Existing AAA sonic-mgmt tests continue to pass.

## 14. Open/Action Items

| Item | Owner | Status |
| --- | --- | --- |
| Confirm the KubeSONiC feature-container deployment path, host-loopback exposure mechanism, node labels, and rollback workflow for this service. | SONiC community and KubeSONiC owners | Open |
| Agree on ConfigDB table and field names for the new upstream TACACS+ configuration, including TLS transport, TLS credential choices, PSK key exchange and group selection, single connection mode, and TLS port defaults. | AAA and YANG reviewers | Open |
| Confirm existing SONiC TACACS+ client failover behavior when the loopback listener is unavailable or closes a request because all upstream servers are unavailable. | AAA and sonic-mgmt reviewers | Open |
| Define the SONiC YANG extension used to preserve upstream TACACS+ server priority ordering when mapping toward RFC 9950. | AAA and YANG reviewers | Open |
| Decide whether stored configuration remains table-shaped with TACACS+ model mapping or moves toward a more YANG-native representation in a separate HLD. | AAA, YANG, and ConfigDB reviewers | Open |
| Confirm ACMS/gNMI-style credential provisioning, directory paths, file permissions, and reference naming for TLS private keys, trust anchors, and PSK material. | Security and platform reviewers | Proposed |
| Define exact CLI syntax and show commands for loopback compatibility, upstream TLS configuration, and local forwarding diagnostics. | sonic-utilities reviewers | Open |
| Confirm which SONiC versions have enough KubeSONiC support to backport the feature without root OS TACACS+ plugin changes. | Release and platform owners | Open |
| Prepare sonic-mgmt test plan and identify testbed topology. | Test subgroup | Open |
| Prepare release notes and operator documentation. | Feature owner | Open |

## 15. References

- RFC 8907, The TACACS+ Protocol.
- [RFC 7951, JSON Encoding of Data Modeled with YANG](https://www.rfc-editor.org/info/rfc7951).
- [RFC 8446, The Transport Layer Security (TLS) Protocol Version 1.3](https://www.rfc-editor.org/info/rfc8446).
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
