# Redfish Certificate Provisioning Integration

## At a glance

What this design delivers, in one list. Each item has a full section below.

- **Automatic certificate consumption.** A staging helper (`stage-credentials.sh`) inside the redfish container reshapes the delivered files, whose paths come from CONFIG_DB (`REDFISH|certs`), into what bmcweb expects: a combined `server.pem`, a CA truststore with its `<hash>.0` symlink. bmcweb's code is untouched.
- **Automatic rotation.** A watcher picks up installs and rotations (inotify, plus a 60 second reconcile as a safety net) and restarts bmcweb, since bmcweb reads certificates only at startup. A cert/key pair guard ensures a mid-rotation mismatch is never staged. Requests in flight at the restart fail at the connection level; see "Applying a change" for the exact semantics.
- **mTLS enforcement, without local users.** With `client_auth` set to `cert`, `TLSStrict` requires clients to present a certificate signed by the staged CA and valid for client authentication. The certificate's common name is then checked against the trusted names configured in CONFIG_DB (`REDFISH|certs` field `client_crt_cname`), which accepts exact entries and wildcards such as `*.example.com`. There are no local users or passwords in the container: an accepted client is authorized as an administrator, and the common name is also what appears in sessions and logs.
- **Fail closed after first provisioning (secure mode).** A dedicated marker file, `/var/lib/bmcweb/provisioned`, is written on the first successful staging. Once it exists, every bmcweb start is gated: with no valid staged certificate, bmcweb does not start at all, instead of falling back to a self-signed cert. No CONFIG_DB attribute is involved, and the marker survives reboot and container recreation. Recovery is automatic when valid certs reappear.
- **Deletion behavior.** Deleting the source certificates does not tear down the running service (bmcweb keeps serving the last staged certificate), and it is not a way to revoke access: the running bmcweb keeps serving the already-loaded certificate and keeps trusting the same CA. To actually revoke, rotate the CA (clients whose certs were issued by the old CA then fail the mTLS handshake).
- **Observability.** The watcher publishes sync status to STATE_DB (`REDFISH_CERT_STATUS|global`: `in_sync`, `last_error`, fingerprints, served serial, plus `mtls_enforced` for the enforcement state) every cycle, and every decision is logged to syslog. A rotation that fails to land is visible, not silent; monitoring must watch `in_sync`.
- **Boot resilience preserved.** Before certificates are ever provisioned, the BMC still boots with bmcweb's self-signed certificate and the API is reachable.
- **Configured through CONFIG_DB.** The client authentication policy, the published host port, the delivered certificate paths, and the trusted client common names all come from the `REDFISH|config` and `REDFISH|certs` tables, in the same shape the other TLS-terminating services use. Every field has a default, so an unconfigured device still boots and can still be provisioned.

Delivery: one script in three supervisord roles (`--once` stage at container start, `--guard` gate every bmcweb start, `--watch` react to change), plus small supervisord.conf and Dockerfile changes in `dockers/docker-sonic-redfish/`.

## Problem Summary

bmcweb inside the docker redfish container serves the Redfish APIs over HTTPS. It needs a server certificate and private key for HTTPS, and (for mTLS) a CA certificate to verify client certificates.

Out of the box, bmcweb generates its own self-signed certificate so HTTPS comes up, but it is untrusted and mTLS is not enforced. Real, CA-signed certificates have to be provided to it.

In production, an external certificate provisioning agent (a separate host-side tool or container) installs the real certificates on the host under `/etc/sonic/credentials/` (not inside the redfish container), with different file names and layout than bmcweb expects.

The problem: bmcweb reads certificates from fixed container paths in a specific shape, only at startup, while the provisioning agent delivers them to a host directory in a different shape and only after boot. This document describes how we bridge that gap without changing bmcweb.

## Goal

Make bmcweb serve real, externally provisioned certificates from `/etc/sonic/credentials/` instead of a self-signed certificate, and do so without modifying bmcweb.

Concretely, the design must:

- Consume the provisioned certificates from the host directory and present them to bmcweb in the exact shape and location it already expects.
- Pick up certificate rotations automatically and reload bmcweb, since bmcweb reads certificates only at startup.
- Enforce mTLS once a CA is available.
- Preserve boot resilience: before certificates are provisioned, bmcweb must still come up (with its self-signed cert).
- In production, never fall back to self-signed once provisioned (fail-closed).

The rest of this document explains why this is not a "just point bmcweb at the new folder" change, and describes the solution.

## How SONiC runs bmcweb (containers and mounts)

bmcweb runs in a docker container called redfish. The container's mounts and port mapping are declared in `rules/docker-sonic-redfish.mk`:

```
-v /etc/sonic:/etc/sonic:ro              # delivered certs visible here, read-only
-v /var/lib/bmcweb:/var/lib/bmcweb:rw    # writable
-v /var/run/redis:/var/run/redis:rw      # redis unix socket
-p 0.0.0.0:<port>:18080                  # bmcweb listens on 18080; host port from
                                         # CONFIG_DB REDFISH|config:port (default 443)
```

What each mount means for this design:

- **`/etc/sonic:ro`**: the provisioning agent installs certs under `/etc/sonic`, so they are already visible inside the container wherever the configured paths point (the server pair and the CA may be in different directories). The mount is read-only, and the staged files live elsewhere regardless: the configured paths are the delivery location, and the reshaped copies bmcweb reads are kept separate from them.
- **`/var/lib/bmcweb:rw`**: the fingerprint stamp (`.staged-credentials.stamp`) and the provisioned marker (`provisioned`) live here. Unlike files in the container's writable layer, they survive container recreation, which the boot, restart, and fail-closed behavior relies on.
- **`/var/run/redis:rw`**: the container publishes certificate status to STATE_DB through this mounted redis socket.
- **`-p <port>:18080`**: client requests hit the configured host port (default `443`, the standard Redfish HTTPS port) while bmcweb internally binds `18080`. The host port is read from CONFIG_DB at container create time; see "Configuration" below.

The provisioned certificates are already readable inside the container, so no new mount is needed to see them. The reshaped files bmcweb reads are kept in separate, container-local locations rather than in the provisioning directory, and the container reaches STATE_DB through the mounted redis socket. The challenge is about file format, placement, and reload, not access.

### Configuration

The Redfish service is configured through CONFIG_DB, in the same shape as the other services that terminate TLS and authenticate clients by certificate (`RESTAPI|config` and `RESTAPI|certs`, `TELEMETRY|gnmi`):

```json
"REDFISH": {
    "config": {
        "client_auth": "cert",
        "port": "443"
    },
    "certs": {
        "server_crt": "/etc/sonic/redfish/redfishserver.cer",
        "server_key": "/etc/sonic/redfish/redfishserver.key",
        "ca_crt": "/etc/sonic/credentials/ROOT_CERTIFICATE.pem",
        "client_crt_cname": "bmcweb,*.example.com"
    }
}
```

| Field | Meaning | Default |
|---|---|---|
| `config:client_auth` | `cert` requires a verified client certificate (mTLS), `none` does not | `cert` |
| `config:port` | host port the Redfish API is published on | `443` |
| `certs:server_crt` | delivered server certificate | `/etc/sonic/redfish/redfishserver.cer` |
| `certs:server_key` | delivered server private key | `/etc/sonic/redfish/redfishserver.key` |
| `certs:ca_crt` | delivered CA certificate, used to verify client certificates | `/etc/sonic/credentials/ROOT_CERTIFICATE.pem` |
| `certs:client_crt_cname` | trusted client certificate common names, comma separated | unset, meaning any common name is accepted |

Every field has a default, and an unreadable or invalid value falls back to it, so a device with no Redfish configuration still boots, still serves, and can still be provisioned, and a configuration problem never blocks container creation.

**What the `certs` paths mean here.** restapi and telemetry pass their certificate paths to the daemon as arguments, so configuration tells the daemon where to read. bmcweb's paths are compile-time and it accepts no certificate arguments, which is the reason this design exists at all: for Redfish the configured paths name where the provisioning agent *delivers* the files, and staging reshapes them into the locations bmcweb reads. The configuration surface matches the sibling services; the extra hop is internal. The server pair and the CA may be delivered into different directories, as in the example above, so the watcher derives the directories it watches from the configured paths.

**When a change takes effect.** The watcher re-reads `client_auth` and the `certs` paths on every wake, so a change is picked up within one watch interval, and a change that alters what bmcweb must load bounces bmcweb. `client_crt_cname` is consulted on every request, so adding or removing a trusted name takes effect immediately. `port` is different, because docker applies port mappings only when a container is created: the generated container start script resolves it immediately before `docker create`, and a change takes effect on the next redfish service restart, which recreates the container. On start the script compares the running container's published port against CONFIG_DB and recreates on mismatch, the same pattern the start script already uses for HWSKU changes. bmcweb's internal port (18080) is compile-time and does not change; only the published host side is configurable.

The recreate wipes the container's writable layer, which the certificate flow already tolerates: the oneshot re-stages before bmcweb's first start and the provisioned marker on the host mount is unaffected, so a port change on a provisioned unit comes back serving the CA-signed certificate with mTLS enforced and no self-signed window. One operational note: clients, monitoring, and tests assume 443 by default, so a non-default port must be communicated to every consumer of the API.

## How bmcweb handles certificates

### What bmcweb does on startup

At startup, bmcweb looks for `/etc/ssl/certs/https/server.pem`. If that file is missing or invalid, it creates the parent directory if needed and generates its own temporary self-signed certificate, so HTTPS still comes up out of the box.

For client verification it tells OpenSSL to trust any CA found in `/etc/ssl/certs/authority`. OpenSSL scans that folder by hash lookup: the CA file alone is not enough, there must be a symlink next to it whose name is a hash of the CA certificate's subject (for example `a1b2c3d4.0`) pointing to the CA file.

Three behaviours to remember:

- **Self-signed fallback**: if no real certificate is present, bmcweb generates its own. The BMC always boots with working HTTPS. The integration must preserve this behaviour for the bootstrap phase, and deliberately override it in secure mode (covered later).
- **Read-once at startup**: certificates are loaded into bmcweb's in-memory SSL context only during startup. bmcweb does not watch the files for changes, so picking up a new certificate always requires restarting bmcweb.
- **mTLS is off by default**: even with a CA staged, bmcweb does not require client certificates unless `TLSStrict` is enabled in its persistent state file `/bmcweb_persistent_data.json` (covered in its own section).

### The exact shape bmcweb expects

Putting the above together, provisioning bmcweb with a real certificate means producing all of the following, and then restarting bmcweb:

| Item | Location (inside the container) | Shape |
|---|---|---|
| Server certificate + private key | `/etc/ssl/certs/https/server.pem` | One combined PEM file, cert and key concatenated |
| CA certificate | `/etc/ssl/certs/authority/CA-cert.pem` | PEM file |
| CA hash symlink | `/etc/ssl/certs/authority/<hash>.0` | Symlink to the CA file, name derived from its content |
| mTLS enforcement | `/bmcweb_persistent_data.json` | `TLSStrict: true` (write only while bmcweb is stopped) |

This table is the contract the staging logic has to fulfil. Everything the solution does is reshaping the provisioned files into exactly these four items.

## The problem, stated precisely

What the provisioning agent delivers and what bmcweb expects do not line up. The agent installs three files on the host, at the paths configured in `REDFISH|certs` (defaults shown):

| Configured path | Content | Default |
|---|---|---|
| `server_crt` | server certificate | `/etc/sonic/redfish/redfishserver.cer` |
| `server_key` | server private key | `/etc/sonic/redfish/redfishserver.key` |
| `ca_crt` | CA certificate | `/etc/sonic/credentials/ROOT_CERTIFICATE.pem` |

On rotation, the provisioning agent writes new versioned files and atomically repoints these stable names (they are symlinks) to the new versions.

Comparing this against the contract table above, there are three mismatches:

1. **Two files vs one.** the provisioning agent delivers the server certificate and key as separate files; bmcweb wants them concatenated into a single `server.pem`.
2. **Different location.** The agent writes to the configured delivery paths; bmcweb reads from its compile-time `/etc/ssl/certs/` paths inside the container.
3. **Missing hash symlink.** bmcweb's truststore needs a `<hash>.0` symlink next to the CA, and the hash depends on the CA certificate itself, so it cannot be precomputed at image build time.

And two timing constraints:

1. **certificates arrive late.** The switch boots and the redfish container starts before the provisioning agent is installed and writes the real certs. At boot, `/etc/sonic/credentials/` may be empty, and bmcweb must still come up (with its self-signed cert).
2. **bmcweb reads certs only at startup.** Whenever the certificates first appear or later rotate, something must notice and restart bmcweb, or it keeps serving the old (or self-signed) certificate indefinitely.

One non-goal worth stating: `/etc/sonic/credentials/` is the provisioning directory and stays untouched. The solution never writes into it; the reshaped files are produced in the container-local locations bmcweb reads.

## Why the obvious shortcuts don't work

**Shortcut 1: create a symlink at image build time, `server.pem -> /etc/sonic/credentials/...`**

A symlink points at one file, but bmcweb needs the certificate and key concatenated into one file. A symlink cannot merge two files. On top of that, at boot the target may not exist yet (certificates arrive late), leaving a dangling link, and bmcweb would try to write its self-signed fallback through it into the provisioning directory.

**Shortcut 2: symlink the CA file straight into the truststore folder**

The truststore only works with a `<hash>.0` symlink whose name is derived from the CA certificate itself, so it cannot be created at build time (the CA does not exist yet). It can only be produced after the CA arrives, which already requires a runtime component; at that point copying the CA and creating the hash link next to it is the same amount of work, without aliasing into the provisioning directory.

**Shortcut 3: change bmcweb's compiled-in paths to /etc/sonic/credentials**

This means patching and rebuilding bmcweb, which the design explicitly avoids, and it still solves almost nothing: the two-files-vs-one mismatch remains (bmcweb's loader reads a single combined PEM), the hash symlink still cannot live in the provisioning directory, the self-signed fallback would try to write into it, and bmcweb still reads certificates only at startup, so rotation still needs an external watcher and restart. A deeper bmcweb change (separate cert/key paths, a single CA file, or hot reload) is possible in principle, but it means carrying a permanent patch on bmcweb's TLS code, and it would only remove the file-reshaping steps; the rotation detection, restart, and secure-mode logic are needed either way.

The common thread: every shortcut runs into at least one of the three mismatches or the two timing constraints. The fixes have to happen at runtime, inside the container, after the files arrive, which is exactly what the staging helper does.

## The solution

Add a small credential-staging helper to the redfish container: a single script, `stage-credentials.sh`, that copies and reshapes the provisioned files into the exact files bmcweb already expects, and restarts bmcweb whenever they appear or change. bmcweb itself is unchanged: it keeps reading the same locations it always has. We are just filling those locations automatically.


### One script, three modes

The same script runs as three supervisord programs, each in a different mode. Splitting the roles keeps each one simple and lets supervisord manage their lifecycles independently.

| supervisord program | Mode | Role | Lifecycle |
|---|---|---|---|
| `stage-credentials` | `--once` | Stage whatever is already present at container start, before bmcweb runs | oneshot, exits |
| `bmcweb` | `--guard` | Gate bmcweb's startup: self-heal the staged files if needed, fail closed once provisioned, then `exec bmcweb` | wraps bmcweb itself |
| `credentials-watcher` | `--watch` | Watch for installs and rotations; re-stage and bounce bmcweb on change | long-running daemon |

**`--once` (stage on start).** Runs before bmcweb in the supervisord dependency order. If provisioned certs are already present (for example, the container restarted after the provisioning agent was provisioned), they are staged so bmcweb starts directly with the real certificate, no self-signed phase and no extra restart. If the folder is empty it is a no-op, and bmcweb falls back to its self-signed certificate. Boot is never blocked.

**`--guard` (gate bmcweb).** bmcweb's supervisord entry does not launch bmcweb directly; it launches the script in guard mode, which does two things and then `exec`s bmcweb (so bmcweb replaces the script in the same process, and supervisord supervises bmcweb as usual). First, self-heal: if the staged certificate is missing or invalid but valid source certs exist, it re-stages them, covering any window a restart could slip through. Second, fail closed: if the unit has been provisioned before (the `/var/lib/bmcweb/provisioned` marker exists) and no valid staged certificate exists, it refuses to start bmcweb entirely (details in the Secure mode section). Since every bmcweb start goes through the guard, these checks hold no matter who restarts bmcweb or when.

**`--watch` (react to change).** The long-running watcher. It waits for filesystem events on the source directory and re-stages + bounces bmcweb when the certificates first appear or are rotated. It also wakes periodically to reconcile even without an event, and publishes the sync status to STATE_DB on every cycle (details in the Change detection and Observability sections).

### supervisord ordering

The programs start in dependency order via `dependent_startup`:

```
rsyslogd
  -> sonic-dbus-bridge
  -> stage-credentials (--once, runs and exits)
       -> bmcweb (--guard, waits for stage-credentials to finish)
       -> credentials-watcher (--watch)
```

`stage-credentials` must finish before bmcweb starts, so that a box that already has provisioned certs comes up with the real certificate on the very first bmcweb start. The watcher also waits for it, so the two never stage concurrently at boot.

## What staging does

Staging is the `stage_certs` step of the script. It runs on the first install and on every rotation, and produces the contract items from the table above:

1. Concatenate the configured `server_crt` + `server_key` into `server.pem`, written to a temporary file and moved into place, so bmcweb can never observe a half-written file.
2. Copy the configured `ca_crt` to `/etc/ssl/certs/authority/CA-cert.pem`.
3. Compute the CA's subject hash with `openssl x509 -hash` and create the `<hash>.0` symlink next to it.

Staging only runs when the input is complete and consistent. The readiness check (`certs_ready`) requires:

- All three source files exist (a partial upload stages nothing).
- The server certificate and the CA certificate both parse as X.509.
- The certificate and the private key actually belong together: the public key is derived independently from each, and staging proceeds only if the two are identical. This works for both RSA and EC keys, and it is what protects the mid-rotation window (see the Pair guard section).

### The fingerprint stamp

After a successful stage, the script records a combined sha256 fingerprint of the three source files in `/var/lib/bmcweb/.staged-credentials.stamp`. The stamp answers one question: which source set was last applied. On every wake, the watcher compares the current source fingerprint against the stamp and re-stages only when they differ (or when the staged output itself is broken). This makes the whole pipeline idempotent: repeated events for the same content cause no redundant bmcweb restarts.

Two properties matter:

- **The stamp advances only on success.** If staging fails, the stamp is left unchanged, so the next reconcile retries. Writing the stamp unconditionally would mark new certs as "applied" even when `server.pem` was never rewritten, and every later reconcile would short-circuit.
- **The stamp lives on the host mount** (`/var/lib/bmcweb`), so it survives container recreation. Even if it were lost, correctness is preserved (the staged-output check would trigger a re-stage); the stamp only avoids unnecessary bounces.

### Applying a change: stop, write, start

bmcweb reads certificates and its persistent config only at startup, so applying a change means restarting it. The watcher does this as stop, stage, start (`apply_and_bounce`) rather than a plain restart, because bmcweb persists its auth config back to `/bmcweb_persistent_data.json` while running; writing that file while bmcweb is up risks bmcweb clobbering the change when it next persists. bmcweb is always started again afterwards, even if staging failed, so a failed stage never leaves the service down.

**Impact on in-flight requests.** bmcweb does not drain connections on shutdown, so a request in flight at the instant of the stop has its connection closed without a response; the client observes a transport error (connection reset), never an HTTP error status such as 500, because no bmcweb exists to produce one. Whether the operation took effect depends on how far processing got: a request whose response was already delivered completed normally, and one that never reached bmcweb did nothing, but a mutating request (for example a POST) caught mid-processing may have been applied without its response being delivered. This ambiguity is inherent to any dropped connection (a network failure mid-request has exactly the same property, and this design does not add a new failure mode) and the standard REST discipline applies: the client may simply reissue idempotent requests, while for non-idempotent actions it should confirm the outcome by reading the resource state before reissuing. Nothing retries on the client's behalf. During the window between stop and start, new connections are refused; the window is a few file operations plus bmcweb's startup, typically a couple of seconds, occurring once per rotation and identical to any bmcweb restart. Established token sessions survive the restart, because a rotation does not rewrite the persistent auth config; mTLS clients carry no session state at all (their identity is re-derived from the client certificate on each connection), so for them the restart costs only the TCP reconnect.

## Turning mTLS on (TLSStrict)

Staging the certificates makes mTLS possible but does not by itself make bmcweb request or require a client certificate. Enforcement is controlled by bmcweb's persistent state file `/bmcweb_persistent_data.json`, and enabling it (`enable_mtls`) is a required part of first-time provisioning.

The keys that matter in its `auth_config` block:

| Key | Value | Effect |
|---|---|---|
| `TLS` | `true` | allow client-certificate authentication |
| `TLSStrict` | `true` | require a verified client certificate (verify_peer + fail_if_no_peer_cert) |
| `MTLSCommonNameParseMode` | `2` | take the client cert's CommonName as the session identity |

With these set, a client must present a certificate signed by the staged CA and valid for client authentication (clientAuth EKU). The CN is extracted as the session identity: it is what appears in sessions and logs, and it is what common name validation checks. `TLSStrict` is written only when `client_auth` is `cert`; with `none` it is left disabled and client certificates are not required.

**Common name validation.** A certificate that the CA issued proves authenticity, but not that this particular client is meant to manage this BMC. The trusted common names are configured in CONFIG_DB, `REDFISH|certs` field `client_crt_cname`, as a comma separated list:

- An entry without a wildcard matches exactly: `bmcweb` accepts only the common name `bmcweb`.
- An entry of the form `*.example.com` matches any name ending in the remaining suffix, so it accepts `one.example.com` and `two.one.example.com`, but not `example.com` itself and not `example.com.edu`. A wildcard may only appear at the start of an entry. This is the same matching the SONiC REST API server performs for its client certificates.
- When the list is unset or empty, any common name from a certificate the staged CA issued is accepted. Configuring the list is what turns common name enforcement on, so a device is usable before the list has been pushed and no deployment ordering problem is created.

The list is consulted on every request, so adding or removing a trusted name takes effect immediately, with no restart and no bmcweb bounce. A client whose common name matches nothing is rejected even though its certificate is trusted.

**No local users.** The redfish container ships with no local user accounts and no passwords. bmcweb resolves an authenticated identity's privileges through the `xyz.openbmc_project.User.Manager` D-Bus interface, and on SONiC that service performs the common name validation above and answers with administrator privileges (`priv-admin`) for an accepted identity, instead of consulting a local user database. Access is therefore decided by two independent checks, both outside bmcweb: the CA signature on the client certificate, and the configured common name. Before first provisioning only the unauthenticated service root (`/redfish/v1`) responds, since no credential of any kind exists on the unit; password-based authentication is not possible in any phase. Revoking access is done by rotating the CA, or by removing a name from the trusted list; disabling the service entirely is done through the redfish feature state, not through user management.

Why enforcement is coupled to the CA being present: bmcweb deliberately defaults `TLSStrict` to false because "root certificates will not be provisioned at startup" (comment in the source). That is exactly our lifecycle: at boot there is no CA, and requiring a client certificate then would lock everyone out. So `enable_mtls` runs right after the CA is staged.

Written once; it persists. `TLSStrict` survives restarts in the persistent data file, so the file is rewritten only when the configured policy differs from what is already there. On a rotation the policy is unchanged, so the file is left alone and saved sessions are not reset. Changing `client_auth` does rewrite it, and takes effect on the next bmcweb start, which the watcher performs. The file is only ever written while bmcweb is stopped, per the stop/write/start rule above.

## Secure mode (fail closed)

The features so far preserve bmcweb's self-signed fallback: useful during bootstrap, but wrong for a provisioned production unit, where falling back to an untrusted, non-mTLS certificate on a cert problem would be a silent security downgrade. Secure mode closes that door.

**The marker.** Secure mode is not a configuration flag: it is the state a unit enters permanently at its first successful provisioning, recorded by a dedicated marker file, `/var/lib/bmcweb/provisioned`. The file is self-describing: it contains the timestamp of first provisioning and a note that its presence permanently disables the self-signed fallback and that it must not be deleted except to deliberately return the BMC to the unprovisioned factory state. Once the marker exists, bmcweb must never serve a self-signed certificate; if no valid provisioned certificate is staged, bmcweb does not run at all (fail closed).

**Enforced at every start.** Because bmcweb's supervisord entry runs the script's guard mode, every single bmcweb start passes the gate:

1. If the staged certificate is missing or invalid but valid source certs exist, re-stage them (self-heal), so an otherwise healthy unit never fails the gate spuriously.
2. If the provisioned marker exists and there is still no valid staged certificate, log the refusal and exit without starting bmcweb. supervisord will retry and eventually mark bmcweb FATAL; the endpoint stays down.

A "valid staged certificate" (`staged_ok`) means: `server.pem` exists, parses, and is not self-signed (issuer differs from subject), the CA truststore with its hash symlink is in place, and, when `client_auth` is `cert`, `TLSStrict` is enabled. Checked on the destination only, so the gate holds even if the source directory is momentarily unavailable.

**One-way by construction.** The marker is written only on successful staging and is never removed by anything in the container, so enforcement engages automatically at first provisioning, with no manual step and no window where a provisioned unit still allows fallback, and nothing in the container ever turns it off. The marker must outlive the certificates it guards, which is why it lives on the host mount: a container recreate wipes the staged files and the persistent data, but not the marker, and without it bmcweb could not distinguish "never provisioned" (self-signed is correct) from "provisioned, then wiped" (must fail closed): the two states look identical on inspection.

**Recovery is automatic and driven by the watcher.** supervisord's own retries give up after a few failed starts (FATAL state). The watcher is what brings bmcweb back: when valid certificates (re)appear, its reconcile stages them and issues a start. A start from FATAL is allowed (FATAL only ends supervisord's automatic retries, not explicit starts), the guard re-runs, now passes, and bmcweb comes up. So a unit that failed closed recovers by itself the moment a valid certificate is provisioned, no operator action needed.

**Why a file, not CONFIG_DB or STATE_DB.** The marker must survive everything short of a re-image with no external help. STATE_DB is cleared on reboot. An unsaved CONFIG_DB entry is also lost on reboot, and persisting it automatically would require `config save` from inside a container, which saves the entire running configuration as a side effect. A file on the host-mounted `/var/lib/bmcweb` has none of these problems. A dedicated, self-describing file is used rather than overloading the fingerprint stamp, so an operator inspecting the directory understands its purpose, and understands the consequences before ever deleting it.

## Change detection and reconciliation

The watcher must notice two kinds of change: first install and rotation. It combines an event-driven fast path with a periodic safety net.

**Fast path: inotify.** The watcher blocks on `inotifywait`, watching the directories that hold the configured delivery paths (deduplicated, since the server pair and the CA may live in different directories) for create, modify, move, close-write, and delete events. A change wakes it immediately; measured on hardware, a rotation is picked up and served within a few seconds. A short settle delay after each event batch lets a multi-file drop (three files copied one after another) be handled as one change instead of three.

**Safety net: periodic reconcile.** inotify has gaps: it does not queue events for a process that is not running (a change made while the watcher was restarting is lost), a watch follows inodes so an atomic directory replace can end it, and events for host-side writes crossing the bind mount are not guaranteed on every platform. So the wait also has a timeout (60 seconds, configurable via `BMCWEB_WATCH_INTERVAL`), and the loop reconciles at the top of every wake, before blocking again:

```
re-stage if:  certs_ready
              AND ( source fingerprint != stamp   OR   staged output is broken )
```

Each reconcile pass is a cheap fingerprint compare, and it is idempotent: nothing happens unless there is a real discrepancy. The consequence is a hard upper bound: any change lands within one watch interval, events or no events.

**Reconcile before block.** The reconcile runs first on every wake, including the watcher's own startup. So if the watcher crashed and supervisord restarted it (autorestart is on), any change that happened while it was down is applied within seconds, without waiting for a future event.

## Pair guard (mid-rotation consistency)

When the provisioning agent rotates, it writes new versioned files and repoints the stable `server.crt` and `server.key` symlinks. Each repoint is atomic, but they are two separate operations, so there is a brief window where the certificate points at the new version while the key still points at the old one. Staged naively, that mismatched pair would make bmcweb's TLS context fail to build, breaking HTTPS.

The pair check inside `certs_ready` prevents this: staging proceeds only when the public key derived from the certificate equals the public key derived from the private key. During the mismatch window the check reports not-ready, the pass is skipped, and the next event or reconcile sees the consistent pair and applies it. bmcweb is never handed a cert and key that do not match, and it keeps serving the previous valid pair in the meantime.

The same guard also covers the pathological case where a rotation is left half-done (only one of the two files ever updated): nothing is staged, bmcweb keeps serving the old valid certificate, and the condition is reported as out-of-sync in STATE_DB until the other half arrives.

## Deletion

**Source files deleted (`/etc/sonic/credentials`).** Deletion is not treated as revocation:

- bmcweb keeps running and keeps serving the last staged certificate (still valid, CA-signed). Deleting source files does not degrade the security of the running service.
- The condition is immediately visible: STATE_DB reports `in_sync false` with a "credentials not ready" reason.
- If bmcweb restarts while the source is gone, the guard decides: the staged certificate is still present and valid, so bmcweb starts normally even on a provisioned unit. Only if the staged certificate is also gone does the unit fail closed.

Revocation is done by rotating the CA (clients trusting the old CA stop being accepted), not by deleting files.

## Observability

A rotation that silently fails to land is a security flaw: the endpoint keeps answering with the old certificate and nobody notices. The design makes cert state observable in two places.

**STATE_DB status.** On every cycle the watcher publishes to STATE_DB key `REDFISH_CERT_STATUS|global`:

| Field | Meaning |
|---|---|
| `source_fingerprint` | sha256 over the current source trio |
| `applied_fingerprint` | the stamp: last successfully applied trio |
| `served_serial` | serial number of the certificate currently in `server.pem` |
| `in_sync` | `true` when the source is ready, matches what was applied, and the staged output is valid |
| `mtls_enforced` | `true` when `TLSStrict` is enabled and a valid CA-signed certificate is staged, i.e. every connection requires a client certificate |
| `last_update` | timestamp of the last publish (also proves the watcher is alive) |
| `last_error` | precise reason when out of sync |

`in_sync` is the single field monitoring should watch. `last_error` distinguishes the causes: source not ready (missing files, unparseable cert, or cert/key mismatch), source changed but not applied (staging pending or failing), or staged output missing/tampered/self-signed. `mtls_enforced` publishes the enforcement state: `true` means the mTLS enforcement configuration is in effect, so client-certificate authentication is required on every connection. mTLS handshakes themselves are per-connection events, so "handshake complete" has no steady-state value; `mtls_enforced` is the publishable fact that every handshake now requires and verifies a client certificate. A persistent `mtls_enforced false` is actionable in both phases: on a never-provisioned unit it means provisioning has not completed, and on a provisioned unit it means the certificate material was lost and the unit is failing closed; the guard refusal in syslog and the provisioned marker on the host distinguish the two during triage.

Read it with:

```
sonic-db-cli STATE_DB hgetall 'REDFISH_CERT_STATUS|global'
```

**Syslog.** Every decision the script takes (staged, skipped and why, mTLS enabled, guard refusal, staging failure) is logged via `logger` and lands in the host syslog, giving a time-ordered trail of what happened when. STATE_DB gives current state at a glance; syslog gives the history.

## Walkthrough

**Boot, before certificates are provisioned.** `/etc/sonic/credentials` is empty. The oneshot finds nothing and exits. The guard finds no staged cert and no source; the provisioned marker does not exist (never provisioned), so bmcweb starts and self-signs. The unauthenticated service root (`/redfish/v1`) answers over HTTPS with the self-signed cert; authenticated endpoints return 401, since the container has no local accounts and no CA is staged, so no authentication method can succeed. STATE_DB shows `in_sync false`, "credentials not ready".

**Certificates are provisioned.** The watcher wakes (event, or within one interval), sees a ready trio with no stamp, and applies: stop bmcweb, stage the four contract items, enable TLSStrict, write the stamp and the provisioned marker, start bmcweb. bmcweb comes up serving the CA-signed certificate and requires client certificates; any client presenting a certificate issued by the staged CA is authorized as an administrator. From this moment the unit is production-secured and fail-closed. STATE_DB flips to `in_sync true`.

**Certificate rotation.** New versioned files are written and the stable symlinks repointed. If the watcher looks mid-rotation, the pair guard skips the pass. On the consistent pair, the fingerprint differs from the stamp, so it re-stages and bounces bmcweb. TLSStrict is already on, so the persistent config is untouched and sessions survive. The served serial changes; STATE_DB returns to `in_sync true` with the new fingerprints.

**Container restarts (certificates already provisioned).** The oneshot stages before bmcweb's first start (or finds everything already matching and does nothing), so bmcweb comes up directly with the real certificate. No self-signed phase.

**bmcweb alone restarts.** Every start passes the guard: staged cert valid, gate passes, bmcweb `exec`s. If the staged files are absent (for example after a container recreate), the guard re-stages from source first. On a provisioned unit with no valid cert available anywhere, the start is refused.

**Provisioned unit, certificates lost.** If both the source and the staged certificate are gone and bmcweb restarts, the guard refuses to start it (the provisioned marker still exists): fail closed, endpoint down, rather than silently serving self-signed. supervisord retries then goes FATAL. The moment certificates are re-provisioned, the watcher stages and starts bmcweb again automatically.

## Behavior matrix

| Situation | Behavior | Visible as |
|---|---|---|
| Boot, no certs ever | bmcweb up, self-signed, no mTLS | `in_sync false`, "not ready" |
| First install | staged + mTLS on + stamp and provisioned marker written, bmcweb bounced | `in_sync true` |
| Rotation (both files) | re-staged, bmcweb bounced, sessions preserved | `in_sync true`, new serial |
| Mid-rotation window | pass skipped, old cert keeps serving | transient `in_sync false`, mismatch reason |
| Half rotation left permanent | nothing staged, old cert keeps serving | persistent `in_sync false`, mismatch reason |
| Partial upload (missing file) | nothing staged | `in_sync false`, "not ready" |
| Corrupt source cert | nothing staged | `in_sync false`, "not ready" |
| Source deleted | bmcweb keeps serving last staged cert | `in_sync false`, "not ready" |
| Source deleted + bmcweb restart | guard: staged cert still valid, starts normally | unchanged |
| Provisioned (marker present) + no valid cert anywhere + restart | bmcweb refuses to start (fail closed) | bmcweb FATAL, guard refusal in syslog |
| Valid certs reappear after fail-closed | watcher stages and starts bmcweb automatically | `in_sync true`, bmcweb RUNNING |
| Watcher down during a change | reconcile applies it on watcher restart | applied within seconds of restart |
| No events crossing the bind mount | periodic reconcile applies within one interval | applied within 60s |

## Reboot and re-image behavior

What persists where:

| State | Location | Survives bmcweb restart | Survives container recreate | Survives reboot |
|---|---|---|---|---|
| provisioned source certs | host `/etc/sonic/credentials` | yes | yes | yes |
| Staged certs, TLSStrict | container writable layer | yes | no | yes (container is restarted, not recreated) |
| Fingerprint stamp | host `/var/lib/bmcweb` | yes | yes | yes |
| Provisioned marker | host `/var/lib/bmcweb` | yes | yes | yes |

**Reboot.** The provisioned marker and the stamp live on the host filesystem, so they survive reboot as-is. The staged certificates in the container's writable layer also survive a reboot (the container is restarted, not recreated), so a provisioned unit returns to the same secured state: with source certs present the oneshot re-stages before bmcweb starts, with the source lost the guard still passes on the surviving staged copies, and if the staged copies are also gone the unit fails closed rather than self-signing.

**Container recreate (writable layer wiped).** Staged certs and TLSStrict are gone, but the source and the stamp survive. The oneshot re-stages everything from source before bmcweb starts. Back to secured state with no self-signed phase.

**Re-image.** A fresh image starts from the bootstrap state: no certs, no marker, bmcweb self-signs, and the cycle begins again when certificates are provisioned. On an image upgrade the marker and stamp are per-image state and start absent; whether `/etc/sonic/credentials` content carries across depends on how the provisioning agent manages its files during upgrades. If it does carry over, the first boot of the new image stages it immediately and re-creates the stamp and marker before bmcweb starts (same as "container restarts, already provisioned"), so there is no self-signed window.


## Conclusion

The provisioned certificates are already visible inside the redfish container, but in the wrong shape, in a different location, and they arrive after boot; bmcweb reads a single combined PEM and a hashed CA folder, only at startup, and enforces mTLS only when TLSStrict is set. The solution is one script in three supervisord roles: stage on start, guard every bmcweb start, and watch for change. It reshapes the delivered files, whose paths and client authentication policy come from CONFIG_DB, into exactly what bmcweb expects, applies mTLS enforcement with common name validation, fails closed after first provisioning (recorded by a dedicated marker file on the host mount) so a production unit never falls back to self-signed, detects installs and rotations through inotify with a periodic reconcile as a hard upper bound, refuses mismatched cert/key pairs, and publishes its sync state to STATE_DB and syslog so a rotation that fails to land is visible instead of silent. bmcweb's code is untouched, and boot without certificates still works.

## Test coverage (sonic-mgmt)

### Test environment and common fixtures

No provisioning agent is involved in these tests. All certificates are generated by the test itself and installed into `/etc/sonic/credentials` on the BMC, following the provisioning layout: versioned files plus stable symlinks (`server.crt`, `server.key`, `server_ca.crt`).

**Reused from existing sonic-mgmt code:**

- `tests/common/cert_utils.py` (`TlsCertificateGenerator`): generates CA, server, and client certificates. Used with `client_cn="bmcweb"`, matching the common name the tests configure in `client_crt_cname`, and the BMC's Redfish endpoint IP/hostname as the server SAN, so verified TLS connections succeed. Configurable validity/backdating covers the expired-certificate cases.
- `tests/redfish/redfish_client.py` (`RedfishClient`) and the `bmc_ip` / `bmc_creds` / `redfish_client` fixtures from `tests/redfish/conftest.py`.
- `wait_until` from `tests/common/utilities.py` for all polling.

**Extensions needed:**

- `RedfishClient` mTLS support: options for `--cacert`, `--cert`, `--key`, and verified (non `-k`) connections.
- Rotation helper: generate a new server cert/key signed by the same CA (reuse the CA key/cert across `TlsCertificateGenerator` calls, or a thin wrapper). The CA must not be regenerated on rotation.
- Negative-input helpers: client cert from a different (untrusted) CA, expired client cert, client cert without a CN, client cert whose CN is not in the trusted list, corrupt PEM files.

**New fixtures needed:**

- BMC shell access: run commands on the BMC host over SSH (write to `/etc/sonic/credentials`, `docker exec redfish ...`, `redis-cli` against CONFIG_DB/STATE_DB).
- Cert install helper: place generated files into `/etc/sonic/credentials` with the versioned-file + stable-symlink layout; supports partial installs for negative cases.
- Poll helpers: wait-until on STATE_DB `REDFISH_CERT_STATUS|global` fields (`in_sync`, fingerprints, `last_update`) and on the served certificate serial.
- Teardown (critical, the provisioned state is one-way by design): remove test certs from `/etc/sonic/credentials`, delete the provisioned marker `/var/lib/bmcweb/provisioned` and the stamp `/var/lib/bmcweb/.staged-credentials.stamp`, remove staged files and `/bmcweb_persistent_data.json` inside the container (or recreate the redfish container), returning the BMC to the bootstrap state for other test modules.

**Test independence:** every test case is self-contained and order-independent. Each case brings the DUT to the state its steps require (via setup/fixtures) and restores state on teardown, so no case relies on another having run first. Where a section lists a precondition (for example "a valid trio is staged"), that state is established by the case's own setup, not inherited from a previous case. A shared install fixture provides the common "v1 staged, in_sync" starting point; cases that need a different starting point (bootstrap, mismatched pair) set it up themselves.

**Ordering note:** the bootstrap cases (Section 1) require a device with no certificate staged. Each such case declares this as a precondition and is skipped when the DUT is already provisioned; because every case is independent, section order does not affect correctness.

### Section 1: Bootstrap (no provisioned certificates, self-signed)

**Test Case #1: bmcweb comes up self-signed when no credentials are provisioned**

**Precondition (skip if not met):**

- This case requires the bootstrap state: `/etc/sonic/credentials` contains no `server.crt`, `server.key`, or `server_ca.crt`, and the provisioned marker `/var/lib/bmcweb/provisioned` does not exist. If either is present, the DUT is provisioned; skip this case with a clear reason rather than resetting the device.

**Steps:**

1. Confirm the bootstrap precondition above (skip otherwise).
2. Restart the redfish container and poll until bmcweb reaches RUNNING under supervisord.

**Verification:**

1. The served certificate is self-signed: issuer equals subject.
2. GET `/redfish/v1` succeeds without any authentication, but only with certificate verification disabled (`curl -k`); with verification enabled the request fails, since the certificate chains to no CA.
3. A privileged API (for example GET `/redfish/v1/UpdateService/FirmwareInventory`) returns 401: without credentials, and also with any username/password (the container has no local accounts, so password authentication cannot succeed in any phase). Only the unauthenticated discovery endpoints respond before provisioning.
4. mTLS is not enforced: no client certificate is requested during the TLS handshake.
5. STATE_DB `REDFISH_CERT_STATUS|global` reports `in_sync false` with `last_error` indicating credentials not ready, and `mtls_enforced` is `false`.
6. The `stage-credentials` oneshot is EXITED with code 0 and `credentials-watcher` is RUNNING under supervisord.

### Section 2: First install and staged artifacts

**Test Case #1: Watcher stages certs on first install and secures the unit**

**Precondition (skip if not met):**

- Bootstrap state: no certs in `/etc/sonic/credentials`, no provisioned marker at `/var/lib/bmcweb/provisioned`, bmcweb serving its self-signed certificate.

**Steps:**

1. Confirm the bootstrap precondition (skip otherwise): STATE_DB `REDFISH_CERT_STATUS|global` reports `in_sync false` with a "credentials not ready" reason, and the provisioned marker does not exist.
2. Generate a valid trio with the test cert generator: a CA, and a server cert/key whose SAN matches the BMC's Redfish endpoint (IP/hostname).
3. Install `server.crt`, `server.key`, and `server_ca.crt` into `/etc/sonic/credentials` in the versioned-file + stable-symlink layout.
4. Poll (2s interval, 90s timeout) until STATE_DB reports `in_sync true`.

**Verification:**

1. The served certificate matches the installed server cert (same serial) and is no longer self-signed (issuer differs from subject).
2. `/etc/ssl/certs/https/server.pem` inside the container is well formed and contains exactly the installed server cert and key (the certificate's public key matches the key).
3. `CA-cert.pem` is present in `/etc/ssl/certs/authority` and a valid `<hash>.0` symlink points to it.
4. The fingerprint stamp `/var/lib/bmcweb/.staged-credentials.stamp` is written and equals the fingerprint of the installed trio.
5. `TLSStrict: true` is set in `/bmcweb_persistent_data.json`.
6. No CONFIG_DB entry is created; the marker `/var/lib/bmcweb/provisioned` now exists, marking the unit as provisioned (fail closed from now on), automatically and with no manual step, and its content records the provisioning timestamp and the do-not-delete warning.
7. STATE_DB `REDFISH_CERT_STATUS|global`: `in_sync true`, `last_error` empty, `source_fingerprint` equals `applied_fingerprint`, `served_serial` equals the installed server cert's serial, and `mtls_enforced` is `true`.

### Section 3: mTLS enforcement

Preconditions for this section: a valid trio is staged and `in_sync true` (the end state of Section 2). Each case uses a client cert signed by the same CA, with CN `bmcweb`, accepted either because no trusted list is configured or because `client_crt_cname` includes it, unless stated otherwise.

**Test Case #1: Valid client certificate is accepted and server identity verifies**

**Steps:**

1. With certs staged, send GET `/redfish/v1` presenting the CA, the client cert (CN `bmcweb`), and the client key, with server verification enabled (no `-k`) and no username/password.
2. Address the endpoint by the name/IP present in the server cert SAN.

**Verification:**

1. The response is HTTP 200.
2. Server identity verifies: the connection succeeds without `-k`, proving the server cert chains to the installed CA and the SAN matches the address used.
3. No basic-auth credentials were supplied, confirming authentication was via client certificate.

**Test Case #2: Requests without a valid client certificate are rejected**

**Steps:**

1. Send a request presenting the CA but no client certificate.
2. Send a request presenting a client cert signed by a different, untrusted CA (with the correct CN `bmcweb`).
3. Send a request presenting an expired client cert (signed by the trusted CA, CN `bmcweb`, validity window in the past).

**Verification:**

1. Case 1 is rejected at the TLS layer with a certificate-required failure (no HTTP response body).
2. Case 2 is rejected: chain verification fails because the client cert does not chain to the staged CA.
3. Case 3 is rejected: the expired certificate fails validation.
4. In all three cases no Redfish resource is returned, confirming TLSStrict is enforced rather than falling back to unauthenticated or basic access.

### Section 4: Client certificate common name validation

Preconditions for this section: a valid trio is staged and `in_sync true`. This section covers authorization, which is common name based and involves no local user database. `REDFISH|certs` `client_crt_cname` is set per case and cleared on teardown.

**Test Case #1: Configured exact common names are enforced**

**Steps:**

1. Set `client_crt_cname` to `bmcweb`.
2. Send GET `/redfish/v1` and a privileged GET (for example `/redfish/v1/UpdateService/FirmwareInventory`) with a client cert signed by the trusted CA whose CN is `bmcweb`, server verification enabled, no password.
3. Repeat with a client cert from the same CA whose CN is `ghost`.

**Verification:**

1. The `bmcweb` requests succeed with HTTP 200, including the privileged endpoint, confirming an accepted identity is authorized as administrator with no local account involved.
2. The `ghost` request is rejected even though the certificate is trusted and its chain is valid, confirming the common name, not merely CA trust, is the deciding factor.
3. The only difference between the two requests is the certificate common name.

**Test Case #2: Wildcard entries match by suffix only**

**Steps:**

1. Set `client_crt_cname` to `*.example.com`.
2. Send a request with each of these client certs from the trusted CA: CN `one.example.com`, CN `two.one.example.com`, CN `example.com`, CN `example.com.edu`.

**Verification:**

1. `one.example.com` and `two.one.example.com` are accepted.
2. `example.com` and `example.com.edu` are rejected: a wildcard matches names ending in the suffix, not the bare domain and not a longer unrelated domain.
3. The same matching rules as the SONiC REST API server are observed.

**Test Case #3: An unset list accepts any common name**

**Steps:**

1. Remove `client_crt_cname` from CONFIG_DB.
2. Send a request with a client cert from the trusted CA with an arbitrary CN.

**Verification:**

1. The request succeeds: with no list configured, any common name from a certificate the staged CA issued is accepted, so a device is usable before the list is pushed.
2. A client cert from a different CA is still rejected, confirming CA trust is always required.

**Test Case #4: A common name change takes effect without a restart**

**Steps:**

1. Set `client_crt_cname` to `bmcweb` and confirm a `ghost` cert is rejected.
2. Change `client_crt_cname` to `bmcweb,ghost` without restarting anything.
3. Immediately repeat the `ghost` request.

**Verification:**

1. The `ghost` request now succeeds, with no bmcweb restart and no container restart, confirming the list is consulted per request.
2. Removing `ghost` again makes the request fail immediately.

**Test Case #5: A trusted client cert without a common name is rejected**

**Steps:**

1. Generate a client cert signed by the same trusted CA, with a valid chain, but with an empty subject CN.
2. Send GET `/redfish/v1` presenting the CA and this client cert, with server verification enabled.

**Verification:**

1. The request is not authorized: bmcweb cannot form a session identity without a CN (`MTLSCommonNameParseMode 2` extracts the CN as the session identity), so the request falls through to the other authentication methods and fails with 401.
2. Password-based access remains impossible: no combination of username and password without a client certificate reaches any endpoint, since TLSStrict rejects the handshake first.

### Section 5: Certificate rotation

Preconditions for this section: a valid trio (call it v1) is staged and `in_sync true`, with mTLS working. Rotation reuses the existing CA; the CA is not regenerated, so client certs continue to chain to it.

**Test Case #1: Rotation is served and existing configuration is preserved**

**Steps:**

1. Record the current served serial and the fingerprint stamp.
2. Generate a new server cert/key (v2) signed by the same CA, with the same SAN.
3. Install v2 by writing the new versioned files and atomically repointing both `server.crt` and `server.key`.
4. Poll until STATE_DB `served_serial` changes to v2's serial and `in_sync true`.

**Verification:**

1. The served certificate is now v2 (new serial) and still chains to the same CA.
2. An mTLS request with the original client cert (unchanged, same CA) still succeeds with HTTP 200.
3. `TLSStrict` is still `true`.
4. The fingerprint stamp advanced to the v2 trio, and `source_fingerprint` equals `applied_fingerprint`.
5. The provisioned marker still exists and the stamp advanced to the new trio (the unit remains provisioned; rotation never clears the marker).

**Test Case #2: Rotating the CA is staged and the new truststore takes effect**

**Steps:**

1. With v1 staged, generate a new CA and a server cert/key signed by the new CA, plus a client cert signed by the new CA.
2. Install the new `server_ca.crt`, `server.crt`, and `server.key` together (repoint all three).
3. Poll until STATE_DB reports `in_sync true` with the new fingerprints.

**Verification:**

1. `CA-cert.pem` in the container is the new CA and a new `<hash>.0` symlink (matching the new CA's hash) points to it; the old hash symlink is gone or no longer resolves to a trusted CA.
2. An mTLS request with a client cert signed by the new CA succeeds with HTTP 200.
3. An mTLS request with the old client cert (signed by the previous CA) is now rejected, confirming CA rotation is the revocation mechanism.

### Section 6: Pair guard (mid-rotation consistency)

Preconditions for this section: a valid trio (v1) is staged and `in_sync true`, with mTLS working.

**Test Case #1: A mismatched cert and key pair is never staged**

**Steps:**

1. Record the current served serial.
2. Generate a new server cert/key (v2) signed by the same CA.
3. Repoint only `server.crt` to v2, leaving `server.key` pointed at v1, creating a mismatched pair (this simulates the transient mid-rotation window, held open deliberately).
4. Wait at least one full watch interval so at least one reconcile pass has run against the mismatched state.

**Verification:**

1. Nothing was staged: the served serial is unchanged (still v1), `server.pem` in the container is unchanged, and bmcweb was not bounced.
2. An mTLS request with the client cert still succeeds with HTTP 200, because bmcweb keeps serving the consistent v1 pair.
3. STATE_DB reports `in_sync false` with `last_error` indicating a cert/key mismatch (credentials not ready).

**Test Case #2: Completing a rotation after a mismatch stages the consistent pair**

**Steps:**

1. Set up: from a valid v1 staged state, generate v2 signed by the same CA and repoint only `server.crt` to v2, establishing the mismatched pair. Confirm STATE_DB is `in_sync false` with the mismatch reason.
2. Repoint `server.key` to v2 as well, so both now point at v2.
3. Poll until STATE_DB `served_serial` changes to v2 and `in_sync true`.

**Verification:**

1. The served certificate is now v2, confirming the guard released once the pair became consistent.
2. An mTLS request with the client cert succeeds with HTTP 200.
3. STATE_DB `in_sync true`, `last_error` empty, and the fingerprint stamp equals the v2 trio.

**Test Case #3: A permanently half-completed rotation keeps serving the old cert**

**Steps:**

1. From a valid v1 staged state, repoint only `server.crt` to v2 and never repoint `server.key`.
2. Wait several watch intervals.

**Verification:**

1. Across the whole period the served serial stays v1 and bmcweb is never bounced (no flapping).
2. STATE_DB stays `in_sync false` with the mismatch reason for the entire duration, and `last_update` keeps advancing (the watcher is alive and repeatedly declining to stage, not stuck).
3. mTLS requests keep succeeding on the v1 pair throughout, confirming a half-rotation is a liveness problem for the new cert, never an availability problem for the running service.

### Section 7: Watcher resilience and reconcile

Preconditions for this section: a valid trio (v1) is staged and `in_sync true`.

Note: the periodic reconcile (the watch-interval timeout) shares the same reconcile logic exercised by Test Case #1. It cannot be isolated deterministically on a platform where inotify delivers source events, so it is not given a separate case; Test Case #1 validates that a source change is applied by the reconcile path with no live inotify event.

**Test Case #1: Watcher reconciles a change made while it was down**

**Steps:**

1. Stop the watcher: `supervisorctl stop credentials-watcher`.
2. While it is down, rotate to v2: generate v2 signed by the same CA, write the versioned files, and repoint both symlinks.
3. Confirm no inotify event can have been acted on (the watcher process is not running).
4. Start the watcher: `supervisorctl start credentials-watcher`, and poll until STATE_DB `served_serial` changes to v2 and `in_sync true`.

**Verification:**

1. supervisord shows `credentials-watcher` RUNNING after the start.
2. The served certificate is v2, staged by the startup reconcile (the change occurred with no event delivered to a live watcher), confirming reconcile-on-startup applies changes missed during downtime.
3. STATE_DB `in_sync true` and the fingerprint stamp equals the v2 trio.

**Test Case #2: A non-content change does not bounce bmcweb**

**Steps:**

1. With v1 staged and `in_sync true`, record the current bmcweb start time (or PID) and the served serial.
2. Trigger a filesystem event in `/etc/sonic/credentials` that does not change certificate content: for example rewrite the same versioned files with identical bytes, or `touch` them.
3. Wait at least one watch interval.

**Verification:**

1. The fingerprint is unchanged (identical content), so no staging occurs.
2. bmcweb was not bounced: its start time / PID is unchanged and the served serial is unchanged.
3. STATE_DB remains `in_sync true` throughout, confirming idempotency (events for unchanged content cause no restart).

### Section 8: Boot and restart behavior

Preconditions for this section: a valid trio (v1) is staged and `in_sync true` (except where a case sets up its own state).

**Test Case #1: Container recreate with certs present comes up staged, no self-signed phase**

**Steps:**

1. With v1 staged, recreate the redfish container so the writable layer is wiped: `systemctl stop redfish`, `docker rm -f redfish`, `systemctl start redfish`.
2. Poll until bmcweb reaches RUNNING and STATE_DB reports `in_sync true`.

**Verification:**

1. The `stage-credentials` oneshot ran and reached EXITED (code 0) before bmcweb started (staging happened ahead of the first bmcweb start).
2. bmcweb's first served certificate is the v1 provisioned cert, not self-signed: at no point during startup was a self-signed cert served (the served serial is v1 from the first successful HTTPS response).
3. mTLS is enforced immediately (a request without a client cert is rejected; a valid client cert returns HTTP 200).
4. The provisioned marker survived the recreate (it lives on the host mount), so the unit remains provisioned and fail closed.

**Test Case #2: A bmcweb-only restart retains mTLS and does not re-run the oneshot**

**Steps:**

1. With v1 staged, record the `stage-credentials` oneshot's start time and the served serial.
2. Restart only bmcweb: `docker exec redfish supervisorctl restart bmcweb`.
3. Poll until bmcweb is RUNNING again.

**Verification:**

1. bmcweb returns serving the same v1 cert with mTLS still enforced, reusing the already-staged files.
2. The `stage-credentials` oneshot did not re-run (its start time is unchanged): it is a separate program triggered only at container/supervisord start, not by a bmcweb restart.
3. STATE_DB remains `in_sync true`.

**Test Case #3: Reboot on a provisioned unit returns to the secured state**

**Steps:**

1. With v1 staged and source certs present in `/etc/sonic/credentials`, reboot the DUT.
2. After boot, poll until the redfish container is up and STATE_DB reports `in_sync true`.

**Verification:**

1. bmcweb comes up serving the v1 provisioned cert with mTLS enforced, with no self-signed phase, because the oneshot re-stages from the surviving source certs before bmcweb starts.
2. The provisioned marker exists after boot (it lives on the host filesystem and survives reboot directly).
3. The fingerprint stamp (on the host mount) survived the reboot and matches the v1 trio.

### Section 9: Robustness and negative input

Preconditions for this section: a valid trio (v1) is staged and `in_sync true`, so each case can confirm the bad input does not disturb the already-served cert.

**Test Case #1: A partial upload (missing file) is not staged**

**Steps:**

1. Record the currently served serial (v1).
2. Install only `server.crt` (a new v2 cert), leaving `server.key` and `server_ca.crt` absent or unchanged such that the trio is incomplete relative to the new cert.
3. Wait at least one watch interval.

**Verification:**

1. Nothing new is staged: the served serial is unchanged (still v1), and bmcweb is not bounced.
2. STATE_DB reports `in_sync false` with `last_error` indicating credentials not ready (missing files).

**Test Case #2: A corrupt server certificate is not staged**

**Steps:**

1. Record the currently served serial (v1).
2. Replace `server.crt` with a file that is not valid PEM/X.509 (corrupt bytes), keeping the other files present.
3. Wait at least one watch interval.

**Verification:**

1. The certificate parse fails, so nothing is staged and the served serial is unchanged (still v1).
2. STATE_DB reports `in_sync false` with a credentials-not-ready reason.

**Test Case #3: A corrupt CA certificate is not staged and does not cause flapping**

**Steps:**

1. Record the currently served serial (v1) and bmcweb's start time.
2. Replace `server_ca.crt` with a file that is not valid PEM/X.509, keeping `server.crt` and `server.key` valid.
3. Wait several watch intervals.

**Verification:**

1. Nothing is staged: served serial unchanged, `server.pem` unchanged.
2. bmcweb is not bounced even once (start time unchanged) across the whole period: the readiness check rejects the corrupt CA before staging, so there is no stage-fail/retry restart loop.
3. STATE_DB stays `in_sync false` with a credentials-not-ready reason, `last_update` still advancing.

**Test Case #4: A mismatched pair as the first install leaves the unit in bootstrap**

The pair guard on a provisioned unit is covered by Section 6; this case covers the one variant Section 6 cannot: the very first install.

**Steps:**

1. Start from the bootstrap state (no marker, bmcweb self-signed).
2. As the first install, deliver a `server.crt` and `server.key` that are individually valid but do not form a pair (cert from one keypair, key from another), with a valid `server_ca.crt`.
3. Wait at least one watch interval.

**Verification:**

1. Nothing is staged and no provisioned marker is written: the unit remains unprovisioned and bmcweb keeps serving its self-signed certificate.
2. STATE_DB reports `in_sync false` with a cert/key mismatch reason.
3. Replacing the key with the matching one completes the first install normally (marker written, mTLS enforced).

**Test Case #5: Deleting the source does not tear down the running service**

**Steps:**

1. With v1 staged and mTLS working, delete `server.crt`, `server.key`, and `server_ca.crt` from `/etc/sonic/credentials`.
2. Wait at least one watch interval.

**Verification:**

1. `credentials-watcher` stays RUNNING and bmcweb keeps serving the v1 cert (served serial unchanged); an mTLS request still succeeds with HTTP 200.
2. STATE_DB reports `in_sync false` with a credentials-not-ready reason.
3. Deletion is not treated as revocation: the running service is unaffected, and the staged cert is still served until a restart or a real rotation.


### Section 10: Secure mode (fail closed)

Preconditions for this section: the unit is provisioned, i.e. the marker `/var/lib/bmcweb/provisioned` exists (established by a prior successful install, which the case's setup performs).

**Test Case #1: Guard refuses to start bmcweb when no valid cert is available**

**Steps:**

1. Set up: install v1 so the provisioned marker is written and mTLS works.
2. Remove the source trio from `/etc/sonic/credentials`, and inside the container remove the staged `server.pem` (so neither a valid source nor a valid staged cert exists), then restart bmcweb: `docker exec redfish supervisorctl restart bmcweb`.
3. Wait for supervisord to finish its start attempts.

**Verification:**

1. bmcweb does not reach RUNNING; it ends in BACKOFF/FATAL after supervisord's retries.
2. The guard logged the fail-closed refusal (unit provisioned, no valid staged cert).
3. The HTTPS endpoint is not reachable: an unauthenticated `curl -k` GET `/redfish/v1` fails at the connection level (no listener), not with a self-signed TLS handshake, confirming a provisioned unit strictly prevents the self-signed fallback that the bootstrap state allows.
4. STATE_DB reports `in_sync false`.

**Test Case #2: Recovery is automatic when valid certs reappear**

**Steps:**

1. Set up the fail-closed condition as in TC #1 (bmcweb in FATAL, marker present).
2. Reinstall a valid trio (v2) into `/etc/sonic/credentials`.
3. Poll until STATE_DB reports `in_sync true` and bmcweb is RUNNING, without issuing any manual bmcweb start.

**Verification:**

1. The credentials-watcher stages the new certs and starts bmcweb (recovery is watcher-driven; supervisord's own retries had already been exhausted).
2. bmcweb serves the v2 provisioned cert with mTLS enforced.
3. STATE_DB `in_sync true`, confirming the unit self-recovers from fail-closed with no operator action.

**Test Case #3: Guard self-heals a damaged staged cert at start when source is valid**

**Steps:**

1. Set up: install v1 (unit provisioned). Inside the container, delete the staged `server.pem` but leave the source trio present.
2. Restart bmcweb: `docker exec redfish supervisorctl restart bmcweb`.
3. Poll until bmcweb is RUNNING.

**Verification:**

1. bmcweb comes up serving the v1 provisioned cert: the guard re-staged from the valid source before starting, so the missing staged cert did not trigger fail-closed.
2. mTLS is enforced (valid client cert returns HTTP 200; no client cert is rejected).
3. STATE_DB `in_sync true`.

### Section 11: Observability

Preconditions for this section: ability to read STATE_DB `REDFISH_CERT_STATUS|global` on the DUT. Individual cases set up the specific state they assert.

**Test Case #1: STATE_DB fields are correct in the in-sync state**

**Steps:**

1. Install a valid trio (v1) and poll until `in_sync true`.

**Verification:**

1. `source_fingerprint` equals `applied_fingerprint`.
2. `served_serial` equals the serial of the served certificate (fetched independently from the HTTPS endpoint).
3. `in_sync` is `true` and `last_error` is empty.
4. `mtls_enforced` is `true` (and a client-certificate request during the TLS handshake confirms enforcement independently).

**Test Case #2: last_error distinguishes the out-of-sync causes**

**Steps:**

1. Drive the DUT through each out-of-sync condition and read `last_error` after each: (a) missing file (partial upload), (b) cert/key mismatch, (c) source deleted after a successful install.

**Verification:**

1. Each condition yields a correct `last_error` reason: a credentials-not-ready reason for (a), (b), and (c).
2. `in_sync` is `false` in every out-of-sync condition.

**Test Case #3: last_update proves watcher liveness**

**Steps:**

1. With the watcher RUNNING, read `last_update` twice, at least one watch interval apart.
2. Stop the watcher (`supervisorctl stop credentials-watcher`), wait more than one interval, and read `last_update` again.

**Verification:**

1. While the watcher is running, `last_update` advances between the two reads.
2. After the watcher is stopped, `last_update` stops advancing (stale), giving monitoring a signal that the watcher itself is down independent of cert state.


### Section 12: CONFIG_DB configuration

Preconditions for this section: a valid trio is staged and `in_sync true` (so the recreate path is exercised on a provisioned unit). Teardown restores the defaults: remove the `REDFISH|config` and `REDFISH|certs` entries from CONFIG_DB and restart the redfish service.

**Test Case #1: Default port is 443 with no configuration**

**Steps:**

1. Confirm `REDFISH|config` has no `port` field (or the table is absent) in CONFIG_DB.
2. Read the published port of the running container (`docker port redfish 18080`).

**Verification:**

1. The published host port is 443, and the mTLS request from Section 3 succeeds against `https://<bmc>` with no explicit port.

**Test Case #2: A configured port is applied by a service restart and the certificate flow survives the recreate**

**Steps:**

1. Set the port: `sonic-db-cli CONFIG_DB hset "REDFISH|config" port 8443`.
2. Restart the redfish service and wait for bmcweb to reach RUNNING.
3. Record the container creation time before and after the restart.

**Verification:**

1. The container was recreated (creation time changed), and the published host port is 8443.
2. The mTLS request succeeds on `https://<bmc>:8443` and the connection to 443 is refused.
3. The served certificate is still the provisioned CA-signed certificate with mTLS enforced (the oneshot re-staged from source during the recreate; no self-signed window), and STATE_DB reports `in_sync true` with `mtls_enforced true`.

**Test Case #3: An invalid port value falls back to the default**

**Steps:**

1. Set an invalid value: `sonic-db-cli CONFIG_DB hset "REDFISH|config" port notaport`, restart the redfish service.

**Verification:**

1. The container is created successfully and publishes port 443 (the invalid value is ignored), and the API serves normally: configuration problems never block container creation.

**Test Case #4: Certificates are consumed from the configured paths**

**Steps:**

1. Set `REDFISH|certs` `server_crt`, `server_key` and `ca_crt` to a non-default location, for example under `/etc/sonic/redfish-test/`, with the server pair and the CA in different directories.
2. Deliver a valid trio to those paths and wait for the watcher to react.

**Verification:**

1. The certificates are staged and served from the configured paths, confirming the delivery location is configuration driven and that two different directories are watched.
2. Delivering to the previous (now unconfigured) location has no effect.

**Test Case #5: client_auth none disables client certificate enforcement**

**Steps:**

1. Set `REDFISH|config` `client_auth` to `none` and wait for the watcher to apply it.
2. Send GET `/redfish/v1` with the CA but no client certificate.
3. Set `client_auth` back to `cert` and wait for the watcher to apply it.

**Verification:**

1. With `none`, `TLSStrict` is false in `/bmcweb_persistent_data.json`, the request without a client certificate completes the TLS handshake, and STATE_DB reports `mtls_enforced false`.
2. bmcweb still serves the provisioned CA-signed certificate; the server side is unaffected by the client authentication policy.
3. With `cert` restored, `TLSStrict` is true again, a request without a client certificate is rejected at the handshake, and `mtls_enforced` returns to `true`.

**Test Case #6: Defaults apply when the tables are absent**

**Steps:**

1. Remove the `REDFISH|config` and `REDFISH|certs` entries entirely and restart the redfish container.

**Verification:**

1. The container is created and bmcweb starts: a device with no Redfish configuration is still functional.
2. The default paths are used for staging and the default port 443 is published, confirming no configuration is required for a working device.
