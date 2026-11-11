# Live-Addon Framework and Build Design

This document describes the proposed SONiC-owned framework, image build, and
runtime implementation in `sonic-buildimage`. The
[vendor integration specification](./design_vendor_spec.md)
is the authoritative definition of vendor inputs, options, and restrictions.
Release and rollout orchestration are outside the image build.

| Revision | Date | Description |
|---|---|---|
| 0.1 | 2026-11-09 | Initial community proposal |

## 1. Executive Summary

Live-addon is a proposed container framework for running vendor- or
platform-specific diagnostic programs on SONiC switches. It provides a consistent
way to build, validate, package, supervise, and health-check those programs while
keeping the production image and runtime policy under SONiC community ownership.

The framework separates diagnostic functionality from container infrastructure.
Vendors define their diagnostic programs and semantic health checks; the SONiC
live-addon design defines how those inputs are incorporated into an image and
managed at runtime. The proposed model is:

- The SONiC community owns the final Dockerfile and image policy.
- The vendor supplies source code or prebuilt binary artifacts, a deterministic
  script to build or copy the artifact, and declarative installation metadata.
  Binary-only integrations do not require disclosure of proprietary source code.
- The vendor supplies an explicit set of platform-specific Supervisor program
  fragments.
- The SONiC framework supplies the main Supervisor configuration and fixed
  entrypoint.
- The vendor supplies startup, liveness, and readiness health commands. A
  vendor may use the same executable for all three checks.
- The SONiC framework supplies the on-demand HTTP health server and Kubernetes
  probe integration.
- When a live-addon build is explicitly requested, SONiC Make rules default to
  a checked-in example through the local source path, without external vendor
  inputs. Vendor integrations are explicitly selected and may be contributed
  through normal upstream PRs.

The vendor may maintain its own Dockerfile for independent
development and testing, but that Dockerfile should not define the production
image published by the SONiC build pipeline.

---

## 2. Scope and Terminology

### 2.1 Scope

This proposal covers image construction and runtime support for vendor- or
platform-specific diagnostics: source acquisition, artifact validation and
installation, process supervision, health interfaces, and image metadata.
The implementation target is `sonic-buildimage`.

Live-addon-specific files, profiles, and commands in these documents describe
the proposed implementation layout, not files already available upstream.
Repository-relative build paths refer to `sonic-buildimage`, not this
documentation repository. Vendor-specific examples illustrate the contract;
they do not establish a dependency on a particular vendor or claim that its
integration already implements the proposal.

Live-addon is an optional diagnostic and troubleshooting mechanism, not an
always-on part of normal SONiC operation. The operator responsible for a SONiC
deployment decides whether to build or select an addon image and when, where,
and for how long to deploy it, based on the issue being investigated. Live-addon
images are built only when explicitly requested and are not included in normal
SONiC installer images by default. Building an image does not install or enable
the addon. Deployment and release orchestration remain separate operator
responsibilities.

An operator-enabled live-addon deployment must recover after both cold and warm
system reboots on its qualified SONiC releases and platforms. Restarting services
does not imply uninterrupted execution or automatic resumption of an in-progress
diagnostic session. Vendor restart-safety, session-continuity, and qualification
requirements are defined in
[vendor specification section 9](./design_vendor_spec.md#9-submission-and-qualification).

### 2.2 Terminology

| Term | Meaning |
|---|---|
| Live-addon | The proposed container framework for vendor- or platform-specific diagnostics |
| Framework | SONiC-owned build, validation, installation, supervision, and health infrastructure |
| Vendor | Provider of diagnostic source or prebuilt binaries and declarative integration inputs |
| Platform profile | `platform/<platform>.ini`, selecting one integration independently of SONiC's ASIC/build `PLATFORM` |
| Artifact bundle | A source-built or prebuilt vendor package or archive, validated before installation |
| Supervisor | Process supervisor that runs as container PID 1 and manages the declared programs |
| SBOM | Software Bill of Materials identifying the image's installed software |

---

## 3. Design Goals

The proposed integration should:

1. Keep the final production Dockerfile under SONiC community control.
2. Keep vendor integration simple.
3. Allow the vendor to control how its binaries are started without allowing
   it to replace the container's main Supervisor configuration.
4. Provide a common health interface for Kubernetes probes.
5. Support repository-local and external integration inputs, including
   proprietary binary-only packages, through one platform configuration.
6. Pin external input revisions and verify every artifact bundle.
7. Preserve a clear path for vendor-specific dependencies and initialization.
8. Build through normal SONiC Make targets, without a pipeline preparation
   step or a separate Python build orchestrator.
9. Support a public, vendor-free default and optional reviewed vendor
   integrations without requiring private repositories or credentials.

### Non-goals

- Hosting general-purpose vendor applications unrelated to diagnostics.
- SONiC maintainers do not need to understand the internal implementation of
  every vendor process.
- SONiC maintainers do not need to rewrite the vendor's development Dockerfile.

---

## 4. Recommended Ownership Boundary

| Concern | SONiC framework | Vendor |
|---|---:|---:|
| Final production Dockerfile | Yes | No |
| Base image | Yes | No |
| OS package installation policy | Yes | Declares requirements |
| Artifact preparation | Runs and validates | Supplies source or prebuilt binaries |
| Artifact installation implementation | Owns and executes | Declares format and destination |
| Main `/etc/supervisor/supervisord.conf` | Yes | No |
| Supervisor program fragments | Validates and installs | Produces and declares |
| Container `ENTRYPOINT` | Yes | No |
| Program startup details | No | Yes |
| Generic on-demand health server | Yes | No |
| Semantic health check | Executes and reports | Defines |
| Kubernetes probes | Yes | Provides health semantics |
| Feature Manager manifest | Defines schema, validates, and generates label | Declares platform values |

This boundary lets the vendor retain control over its executable lifecycle
while the SONiC framework retains control over the container lifecycle.
The vendor-facing deliverables are defined in
[vendor specification section 2](./design_vendor_spec.md#2-integration-inputs-and-platform-configuration).

---

## 5. Source, Artifact Build, and Installation

The proposed framework has one platform model. Every platform, including the
default example, is described by `platform/<platform>.ini` and follows the same
artifact, validation, Supervisor, health, and image-generation path. Whether
the source is stored in this repository or an external repository affects only
how the framework resolves the source root.

`[source]` locates integration inputs, not necessarily program source code.
The artifact script may compile supplied source or simply copy a prebuilt binary
bundle into the clean output directory. Both use the same controlled build
environment, validation, and installation path; proprietary program source need
not be provided.

The profile schema and complete example are defined in
[vendor specification section 2](./design_vendor_spec.md#2-integration-inputs-and-platform-configuration).
Source selection, artifact production, and payload restrictions are defined in
[section 3](./design_vendor_spec.md#3-source-selection),
[section 4](./design_vendor_spec.md#4-artifact-build-script), and
[section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions).
The framework implements those requirements rather than maintaining a second
input contract.

### 5.1 Source resolution and common build path

1. Read and validate the selected profile before running source-provided code.
2. Resolve a repository-local source path without a Git checkout, or fetch the
   external repository and record the concrete commit selected by its revision.
3. Invoke the declared artifact preparation script, whether build or copy, in
   the controlled environment described below, passing the framework's absolute
   output directory.
4. Validate the resulting bundle and declared runtime configuration.
5. Prepare the approved image inputs and install the validated bundle through
   the shared SONiC-owned Dockerfile.

Source acquisition is separate from artifact building. Private-source
credentials remain in acquisition, outside the artifact build environment and
final Docker context. After acquisition, local and external source use identical
build prerequisites. Neither source tree is copied directly into the image.

The artifact-build prerequisite recreates its isolated output directory before
every invocation, then evaluates the artifact glob there. This prevents stale
output from a previous build from being collected. Missing or invalid profiles
and inputs fail explicitly rather than falling back to the example image.

The default example uses the same path; see section 9.2. Source location does
not select a different Dockerfile or runtime-generation mechanism.

### 5.2 Build script isolation

The artifact build script must use documented, version-pinned build dependencies
and produce the declared artifact in the framework-provided output directory.
Network access may be used for documented dependency downloads. The script must
not modify unrelated CI resources, access unrelated credentials, or require
host-control privileges.

### 5.3 Validation and layer-safe installation

The framework checks the vendor bundle's format, files, package metadata, and
required dependencies against the rules in
[vendor specification section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions).
It uses the appropriate checks and installation tools for the actual format:
Debian package tools, `tar`, or `unzip`. If the bundle's actual format does not
match the format declared by the vendor, the build fails.

Before building the image, the framework can check the package metadata and
files without installing the package or running vendor code. For Debian
packages, some checks also need to know which packages are already installed
and what the package manager would change. The framework runs these checks in
a SONiC-controlled build stage that uses the approved base image:

1. Identify all required packages, including their dependencies, using the
   approved repository snapshot whose contents cannot change.
2. Fix the exact version and target architecture of every package. Record its
   repository and content hash in the build record (provenance) and software
   bill of materials (SBOM).
3. Simulate the full installation before making changes. Reject any package
   changes forbidden by the
   [restricted Debian profile](./design_vendor_spec.md#52-restricted-debian-profile).
4. Install only after the package metadata, files, and simulated installation
   pass these checks. Use the same fixed package versions and architectures,
   with `--no-install-recommends`. Do not let the package manager choose a new,
   unchecked dependency set or install an unchecked bundle with
   `apt-get install -y ./vendor.deb`.

The framework places the checked bundle at a framework-reserved location in
the files supplied to Docker for the build (the Docker build context). This is
where the build reads the bundle, not where its files will be installed.

The generated Dockerfile must not use `COPY` or `ADD` to put the bundle into
the image. Docker saves filesystem changes in layers; deleting the bundle in
a later step would not remove its contents from the earlier layer.

Instead, a BuildKit read-only bind mount lets the installation `RUN` step read
the bundle from the build context without storing the bundle itself in an
image layer:

```dockerfile
RUN --mount=type=bind,source=vendor-artifacts/vendor-bundle.tar.gz,target=/tmp/vendor-bundle.tar.gz,readonly \
    mkdir -p /opt/cisco/live-addon && \
    tar -xzf /tmp/vendor-bundle.tar.gz \
        -C /opt/cisco/live-addon \
        --strip-components=1
```

The framework generates the bundle's source filename and installation command
from the checked artifact metadata. The installed files remain in the image,
but the package or archive itself does not.

For Debian, the generated package-manager commands install the checked local
package and the fixed dependency set. For TAR and ZIP, the generated commands
extract files using the checked installation root and archive options. They
never run an installer included in the archive. The vendor specification's
installation restrictions apply to every format.

Installation and package-manager cache cleanup must happen in the same `RUN`
step. A package-manager or extraction error fails the image build. This approach
requires BuildKit; the SONiC organization build already uses `docker buildx build`.

The final Docker build context contains only the newly built artifact, explicitly
declared and checked Supervisor configuration fragments, generated health
configuration, and approved framework files. These framework files include the
repository snapshot inputs and records of fixed package versions. Do not include
the entire vendor source tree. Any failed validation, content-integrity check,
artifact build, or installation stops the build.

---

## 6. Supervisor Runtime Design

### 6.1 Main configuration ownership

The SONiC community should maintain the main Supervisor configuration as a
framework file in the source repository:

```text
dockers/docker-live-addon/framework/supervisord.conf
```

The generated Dockerfile copies that file to:

```text
/etc/supervisor/supervisord.conf
```

The framework must not depend on the distribution package's default
configuration because its daemon and logging defaults are not the live-addon
container contract. The SONiC-owned configuration should contain:

```ini
[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0
pidfile=/var/run/supervisord.pid
user=root

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[include]
files=/etc/supervisor/conf.d/*.conf
```

`nodaemon=true` keeps Supervisor running as the container's PID 1 instead of
forking into the background. Docker and Kubernetes track the lifetime and exit
status of PID 1 and send container termination signals to it. If Supervisor
daemonizes and its original PID 1 exits, the container is considered stopped
and its remaining processes are terminated. Foreground operation inside the
container does not make the Kubernetes workload interactive or prevent it
from running detached from an operator's terminal.

With `nodaemon=true`, Supervisor already writes its activity log to stdout.
`logfile=/dev/null` avoids duplicating those messages in the container log,
and `logfile_maxbytes=0` disables rotation. Vendor program logging follows
[vendor specification section 6](./design_vendor_spec.md#6-supervisor-program-fragments).

The production image should always use the fixed SONiC-owned entrypoint:

```dockerfile
ENTRYPOINT ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
```

The `-n` option enforces the same foreground invariant at the process
invocation boundary. Either `-n` or `nodaemon=true` is sufficient by itself;
using both keeps the repository configuration independently correct and
protects the container lifecycle if one setting is accidentally changed.

The Unix socket remains available for local debugging with `supervisorctl`.
For example, an operator may enter the running container with `docker exec` or
`kubectl exec` and run `supervisorctl status`; that interactive process is
separate from Supervisor's standard-output stream. No Supervisor TCP control
interface is exposed.

### 6.2 Fragment validation and installation

The framework validates the complete declared fragment set against
[vendor specification section 6](./design_vendor_spec.md#6-supervisor-program-fragments),
then copies only those files to `/etc/supervisor/conf.d/<basename>`. It must
validate names and group references across the set, not just each file in
isolation. The artifact cannot populate that directory or replace the main
configuration.

An explicitly empty list is accepted for profiles with no resident addon
programs. The framework health-server program is still installed independently.
The complete main configuration and copied fragment set must pass
`supervisord` configuration parsing during the image build.

### 6.3 Container lifecycle boundary

The fixed entrypoint starts Supervisor identically for every platform. Vendor
startup details remain inside the validated fragments rather than being
duplicated in framework build rules.

This provides a stable platform boundary:

```text
Kubernetes
    -> SONiC-owned ENTRYPOINT
        -> SONiC-owned main supervisord.conf
            -> validated vendor <platform>-*.conf fragments
                -> vendor binaries
```

---

## 7. Kubernetes Health Probe Design

### 7.1 Health cannot be inferred generically

There is no reliable universal test that can determine whether an arbitrary
vendor binary is semantically healthy. A running process may still be
deadlocked, disconnected from a required dependency, or unable to perform its
function.

The framework therefore defines how checks are invoked and interpreted, while
the vendor provides the platform-specific startup, liveness, and readiness
executables.

### 7.2 On-demand checks

Kubernetes already decides when to request health checks. The health server
runs the vendor checks when requested, avoiding a separate background monitor
and saved results that could be out of date.

### 7.3 On-demand health architecture

The SONiC framework should provide one common process:

| Component | File | Responsibility |
|---|---|---|
| Health HTTP server | `framework/health_server.py` | Invoke the command mapped to the requested endpoint and return its current result |

```text
Kubernetes kubelet
       |
       | GET /health/startup, /health/live, or /health/ready
       v
framework/health_server.py
       |
       | invokes the corresponding command with a strict timeout
       v
Vendor startup, liveness, or readiness executable
       |
       v
HTTP 200 or HTTP 503
```

When a health endpoint is called, the server runs the corresponding vendor
health-check command and returns its result. Results are not cached for later
checks. Calls that arrive while the same check is still running share its result.

The default example supplies small read-only health-check commands through
the same contract. The health server invokes them on demand: successful checks
produce HTTP 200 and failures produce HTTP 503. Missing health commands remain
a build error for every profile.

The server should start independently of the vendor processes. If Kubernetes
probes the container before the server is listening, the connection failure is
a failed probe and Kubernetes retries according to the probe configuration. If
the server is listening but the vendor is not initialized, the startup command
returns non-zero and the server returns HTTP 503.

The initial deployment contract requires `hostNetwork: true`. The health
server must listen only on `127.0.0.1:50200`, and every Kubernetes HTTP probe
must explicitly set `host: 127.0.0.1` and `port: 50200`. Because a
host-networked Pod shares the SONiC node's network namespace, the health server
and the host kubelet use the same loopback interface.

The proposed deployment reserves port `50200` for this health server.
Qualification must verify that no other host-network service on
the node uses that address and port. Binding the server to `0.0.0.0` is not
permitted because it would expose unauthenticated endpoints that execute vendor
commands through every applicable switch interface. The bind address and port
are framework-owned values and are not vendor-configurable.

### 7.4 Runtime health configuration

During the image build, the framework reads and validates the `[health]`
settings in `platform/<platform>.ini`. It uses these settings to generate
`/etc/live-addon/health.ini` in the image, in the format expected by the health
server. The health server uses this file to run the configured checks.

The command syntax, meaning, timeout, and diagnostic limits are defined in
[vendor specification section 7](./design_vendor_spec.md#7-health-commands).

### 7.5 Request execution rules

The server maps endpoints directly:

| Endpoint | Command |
|---|---|
| `/health/startup` | `startup-command` |
| `/health/live` | `liveness-command` |
| `/health/ready` | `readiness-command` |

For every request, the server should:

1. Validate the endpoint and select its configured command.
2. Start the command without a shell in a new process group.
3. Capture size-limited standard output and error.
4. Wait up to `command-timeout-seconds`.
5. On timeout, terminate the process group, wait a short grace period, and
   force-kill any remaining processes.
6. Return HTTP 200 only for exit code `0`; otherwise return HTTP 503.
7. Log the endpoint, duration, exit code or timeout, and bounded diagnostics.

Checks are independent. The server does not require startup state to decide
whether a liveness or readiness command may run. Kubernetes provides the normal
ordering by withholding liveness and readiness probes until the startup probe
succeeds.

Vendor health commands may be closed-source binaries whose execution time and
resource use cannot be assumed. The framework therefore permits at most one
active invocation of each check type. Concurrent requests for the same
endpoint must use single-flight coalescing: the first request starts the
command, and later requests wait for that in-flight command and receive the
same result. They must not start another vendor process or fail solely because
another caller reached the endpoint first.

Different check types may run concurrently. The Python server should use
`ThreadingHTTPServer` and maintain synchronized in-flight state for each
endpoint. When a command completes, the server must publish its result, wake
all waiting requests, and clear the in-flight state before writing any HTTP
response. A slow or disconnected client must not prevent a later request from
starting the next command. Client disconnection must not cancel an invocation
that still has other waiting callers.

Waiting requests must not outlive the configured command timeout. The
`command-timeout-seconds` value must leave sufficient margin below the
Kubernetes probe `timeoutSeconds` for a waiting kubelet request to receive the
shared HTTP response.

### 7.6 Kubernetes probe semantics

The kubelet is the Kubernetes agent running on each node. For live-addon, it
sends HTTP requests to the health endpoints; the health server runs the
corresponding vendor commands.

Kubernetes uses the results as follows:

| Probe | Action when the configured failure threshold is reached |
|---|---|
| `startupProbe` | Restart the container if initialization has not completed within the allowed startup window |
| `livenessProbe` | Restart the container |
| `readinessProbe` | Mark the Pod not ready, without restarting the container |

The deployment owner supplies the Kubernetes deployment YAML and configures
how often probes run, their timeouts, and their failure thresholds. Use the
endpoint addresses described in section 7.3 and the timeout margin in section 7.5.

Allow enough time for vendor initialization and required SONiC services to
become ready before the startup probe's failure threshold is reached. This
does not control the order in which other containers start.

### 7.7 Supervisor integration

The SONiC framework should add only the generic health server independently of
the vendor fragments:

```ini
[program:live-addon-health-server]
command=/usr/bin/health_server.py --config /etc/live-addon/health.ini --bind 127.0.0.1 --port 50200
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

If the health server exits unexpectedly, Supervisor restarts it. Probe
connection failures during that interval are treated as health failures by
Kubernetes.

---

## 8. SONiC Feature Manager Image Manifest

A manifest is a JSON description of the addon image. It records the addon name
and release version, whether it runs as a host or ASIC service, the SONiC
services listed in `after`, and whether it requires a privileged container.
SONiC stores this JSON in an image label named `com.azure.sonic.manifest`.
A label is information attached to the Docker image; Feature Manager reads
it from the host without running the addon container.

The vendor supplies these values in the platform profile's `[manifest]`
section. [Vendor specification section 8](./design_vendor_spec.md#8-feature-manager-metadata)
defines the required settings and valid values. The framework checks them
before building the image and fails the build if they are invalid or a required
value is missing.

The vendor sets `package-name` in `[manifest]` in the selected
`platform/<platform>.ini` file. For example,
`package-name=live-addon-cisco-8000` names the addon and its container; it is
not the filename of the vendor's Debian package. See the
[platform profile example](./design_vendor_spec.md#2-integration-inputs-and-platform-configuration).

The framework reads that INI file and creates `live-addon.vars`, a build-time
file containing Make variable assignments for the addon name, release version
and other image settings. Make reads this generated file before using those
settings to build the image. The vendor does not supply `live-addon.vars`.

SONiC's existing `generate_manifest` routine creates most of the manifest from
these Make settings, including the package name, release version, `after`
service list and container privilege requirement.

For the two service flags, the proposed framework supplies
`dockers/docker-live-addon/manifest.part.json.j2`. This is a SONiC-owned
Jinja template; `.j2` identifies the template format. "Part" means it produces
only part of the final manifest, not a second complete manifest. The framework
passes the validated `host-service` and `asic-service` values from the INI
file to this template. For the vendor profile example, it produces:

```json
{
  "service": {
    "host-service": true,
    "asic-service": false
  }
}
```

The build renders this template to `manifest.part.json` and merges its two values
into the full `manifest.json`. This ensures the final service flags match the
vendor's declarations. The existing
[manifest-generation routine](https://github.com/sonic-net/sonic-buildimage/blob/master/rules/functions#L212-L241)
supports this partial-file merge.

SONiC's regular image build then stores the completed JSON in the
`com.azure.sonic.manifest` image label.

For example, the generated manifest contains:

```json
{
  "version": "1.0.0",
  "package": {
    "name": "live-addon-cisco-8000",
    "version": "202411.1.0.15"
  },
  "service": {
    "host-service": true,
    "asic-service": false,
    "after": ["syncd"]
  },
  "container": {
    "privileged": true
  }
}
```

There are two different versions in this JSON. The top-level `version`
(`1.0.0`) identifies the manifest format. The nested `package.version`
(`202411.1.0.15` in this example) identifies the addon release.
Qualification checks that select supported addon versions must read
`package.version`, not the Docker image tag, and must fail if the release
version is missing.

The checked-in example profile uses its own package name and release version.
It sets `host-service=false`, `asic-service=false`, and `privileged=false`,
and leaves `after` empty. It therefore does not register a working vendor
service.

To read the addon release version without starting the container:

```bash
sudo docker image inspect <image:tag> \
  --format '{{ index .Config.Labels "com.azure.sonic.manifest" }}' \
  | jq -r '.package.version'
```

The manifest only describes the image. It does not install Feature Manager
inside the container or grant Kubernetes privileges. The deployment owner must
configure the deployment to match the service and privilege values declared
in the manifest.

---

## 9. Proposed Build Flow

### 9.1 Native image recipe

Add `rules/docker-live-addon.mk` to register `docker-live-addon.gz` in
`SONIC_DOCKER_IMAGES` and the supported builder-release list, such as
`SONIC_BOOKWORM_DOCKERS`. Use the SONiC-owned
`dockers/docker-live-addon/Dockerfile.j2` with the existing image build recipe
in `slave.mk`.

The live-addon Make rule must run the preparation steps before building the
image: obtain the selected inputs, build or copy the vendor artifact, validate
the inputs and artifact, and prepare the files needed by the Docker build.
Make tracks these steps as prerequisites of the image target. Small Python
helpers can perform validation; Make remains responsible for running the build.

Keep live-addon out of the default installer image lists and default
`EXTRA_DOCKER_TARGETS`. Build it only when someone requests the live-addon
target or selects it in a diagnostic build job.

### 9.2 Checked-in example default and optional vendor selection

For an explicitly requested live-addon build, `LIVE_ADDON_PLATFORM` defaults to
`example`, selecting `platform/example.ini`
with `[source] path=dockers/docker-live-addon/platform/example`. This path is
relative to the `sonic-buildimage` repository root. The sample source provides
a deterministic artifact build script and small health-check commands, using
the same build, validation and installation flow as vendor integrations. Its
payload is confined to the approved sample root `/opt/example/live-addon`.
The following are proposed commands after the normal SONiC build setup:

```bash
# Build the checked-in sample; no vendor checkout or private credentials
make target/docker-live-addon.gz

# Explicitly select a reviewed vendor integration
make LIVE_ADDON_PLATFORM=cisco-8000 target/docker-live-addon.gz
```

`LIVE_ADDON_PLATFORM` selects the addon profile; it does not replace SONiC's
`PLATFORM` ASIC/build configuration. Forward the selection through the
host-to-builder Make invocation; vendor CI jobs must set it explicitly when
removing the old preparation step. An unknown profile or unsupported
release/architecture fails explicitly.

The default image contains the approved OS dependencies, main Supervisor
configuration, fixed entrypoint, framework health server, sample health-check
payload and example manifest. The sample explicitly declares `[supervisor]`
with an empty `conf-files` value: only the framework health server runs under
Supervisor, and sample checks execute only when requested. It needs no
privileged operation, host PID namespace or host-filesystem mounts. Public CI
must build this example without external vendor inputs. It is not automatically
installed or deployed and does not claim to implement a real vendor service.

Vendor contributions follow
[vendor specification section 9](./design_vendor_spec.md#9-submission-and-qualification).
The Make dependency graph activates integration-specific prerequisites only for
the selected profile. Repository-local and external source retain the same
contract; private integrations cannot become public-build prerequisites.

### 9.3 Dependency and cache handling

```text
make target/docker-live-addon.gz [LIVE_ADDON_PLATFORM=<platform>]
              |
              v
Make resolves and validates the selected profile
              |
              +--> example/local vendor: resolve the checked-in source path
              |
              +--> external vendor: fetch the declared repo and pinned ref
              |
              +--> build or copy the selected artifact in a controlled environment
              +--> validate one bundle and declared runtime configuration
              +--> stage approved snapshot sources, locks and metadata
              |
              v
Shared regular-image recipe renders Dockerfile.j2, generates the manifest,
injects hooks in place, builds Dockerfile and saves the image
              |
              v
target/docker-live-addon.gz + version records + final SBOM
```

Declare configuration, source revision, artifact build inputs, validators,
framework files, snapshot sources and locks as dependencies and cache inputs.
Prebuilt bundle content digests are cache inputs too: changing a binary bundle
must invalidate artifact and image outputs even if its path and profile are
unchanged.
Changing profiles, including switching back to `example`, must invalidate both
the output archive and SONiC's image cache. Isolate staged inputs by profile,
release and architecture, and prevent concurrent builds from modifying the
same context. A missing generated output must be rebuilt; a stale stamp or
`live-addon.vars` must not hide missing files or retain another vendor's data.
Generate included Make metadata through a declared makefile-remaking rule
before its values are consumed, with correctly escaped, validated data.

Approved SONiC-built OS packages may use the regular image dependency
variables. Vendor bundles must still pass the validation and restricted
installation flow in section 5.3, enforcing
[vendor specification section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions);
do not pass them to an unrestricted generic package-install macro merely
because they are Debian packages.

### 9.4 Base image, version controls and SBOM

SONiC maintainers select a Debian base image by approved digest; using SONiC's
build machinery does not require inheriting from `docker-base-bookworm` or
another larger SONiC runtime image. The prepared Dockerfile must copy the
approved snapshot-source configuration before its first `RUN`, so the injected
hooks have usable sources. Live-addon must prepare these sources explicitly
rather than rely on automatic source generation for other SONiC image names.

Enable SONiC version controls with `SONIC_VERSION_CONTROL_COMPONENTS=all` and
`MIRROR_SNAPSHOT=y`, using reviewed snapshot timestamps and image-specific
locks under `files/build/versions/dockers/docker-live-addon/`. Select the lock
set for the profile (including `example`), Debian release, and architecture, and
keep prepared inputs separate between builds. Missing approved digests,
snapshots, or required locks must fail the build; warnings or unconstrained
fallback resolution do not satisfy this contract.

Enable shared SBOM collection with `ENABLE_SBOM=y` and explicitly generate and
verify the final SBOM for the published live-addon image, including vendor
payloads and dependencies. Enabling collection alone is not sufficient.
Shared hooks do not replace section 5.3's validation against the vendor
specification; their package operations and cleanup must also preserve the
validated package set and layer-content requirements.

The shared template installs the validated bundle for every profile, including
the example. Fragment-copy steps run only when fragments are declared. The
generated Dockerfile should:

1. Start from a SONiC-approved, digest-pinned Debian base image.
2. Install SONiC-approved OS dependencies from the selected snapshot at
   their locked versions.
3. Mount the validated bundle read-only for the installation `RUN`
   instruction using BuildKit.
4. Run the framework-generated package installation or archive extraction
   without copying the bundle into an image layer.
5. Remove package-manager caches and temporary installation output in the same
   `RUN` instruction.
6. Copy each declared vendor Supervisor fragment to
   `/etc/supervisor/conf.d/<basename>`.
7. Install the generic on-demand health server.
8. Add required SONiC image labels, leaving `com.azure.sonic.manifest`
   to the shared recipe as described in section 8.
9. Copy the repository-owned framework `supervisord.conf` to
   `/etc/supervisor/supervisord.conf`.
10. Use the fixed SONiC-owned foreground entrypoint.

---

## 10. Future Enhancements

### 10.1 Cgroup-based vendor process containment

The initial health server terminates a timed-out command by signalling its
process group. A descendant that deliberately creates a new session or process
group can escape that cleanup and remain running after the check completes.

A future implementation may execute each vendor health command in a dedicated
Linux cgroup. This would allow the framework to terminate all processes from
one invocation regardless of process-group changes and, where appropriate,
apply limits for process count, CPU, and memory. This enhancement requires a
safely delegated cgroup hierarchy and coordination with Kubernetes and the
container runtime, so it is independent of single-flight request coalescing
and is not required for the initial health-server implementation.

The initial process-group cleanup relies on the foreground/no-detached-process
restriction in [vendor specification section 7](./design_vendor_spec.md#7-health-commands).

---

## 11. Framework Validation and Acceptance Criteria

The implementation must satisfy the following acceptance criteria:

The example and vendor profiles share the artifact and health contract;
addon-program lifecycle criteria apply to declared addon programs.
Contract validation tests use the [vendor specification](./design_vendor_spec.md)
as their source of expected acceptance and rejection rules.

1. Every platform is configured by `platform/<platform>.ini`;
   `platform/example.ini` selects the checked-in default through `[source] path`.
2. Repository-local and external source use the same build path after source
   resolution.
3. Every profile uses the same framework-owned Dockerfile and runtime
   configuration generation.
4. Every live-addon image is built from a SONiC-owned Dockerfile.
5. The vendor Dockerfile is not used by the production pipeline.
6. The repository-owned framework `supervisord.conf` is installed as
   `/etc/supervisor/supervisord.conf` and enables foreground operation,
   container-stream logging without rotation, the local Supervisor control
   socket, and inclusion of `/etc/supervisor/conf.d/*.conf`.
7. The image entrypoint explicitly starts that main configuration with
   Supervisor foreground mode enabled, leaving Supervisor as container PID 1.
8. Every declared vendor fragment is copied to
   `/etc/supervisor/conf.d/<basename>`, and no undeclared vendor fragment is
   copied.
9. Fragment validation rejects inputs that violate
   [vendor specification section 6](./design_vendor_spec.md#6-supervisor-program-fragments).
10. Selected vendor binaries start successfully under Supervisor.
11. `SIGTERM` reaches the process group and shutdown completes within the
   Kubernetes grace period.
12. For a selected vendor, the startup endpoint returns failure until vendor
    initialization completes.
13. Successful startup, liveness, and readiness commands produce HTTP 200 on
    their corresponding endpoints.
14. Concurrent requests for the same endpoint start one vendor command and
    receive its shared result. Non-zero exit, timeout, spawn failure, or
    internal execution error produces HTTP 503 for all requests sharing that
    invocation.
15. Kubernetes startup and liveness probe failures cause the expected restart
    behavior.
16. Every image build records the selected profile, framework revision,
    resolved external commit or local parent repository commit, artifact
    format, artifact digest, and version.
17. The published image has a generated and verified SBOM covering
    installed payloads and dependencies, together with the expected image labels.
    Its `com.azure.sonic.manifest` value matches the validated `[manifest]`
    configuration, and `package.name` matches the container name in
    `live-addon.vars`. The inspected `package.version` matches the declared
    `package-version`.
18. Artifact preparation, including copy-only scripts, follows the invocation
    and isolation contract in
    [vendor specification section 4](./design_vendor_spec.md#4-artifact-build-script)
    and fail explicitly on errors.
19. Artifact collection rejects missing or ambiguous output from the newly
    created output directory.
20. Artifact validation rejects bundles that violate
    [vendor specification section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions).
21. Missing or invalid declarative installation metadata fails before installation.
22. The generated Dockerfile does not use `COPY` or `ADD` for the vendor
    artifact; installation uses a BuildKit read-only bind mount.
23. The artifact bundle, package-manager caches, and temporary installation
    output are absent from the final image and its committed layers.
24. The health server listens only on `127.0.0.1:50200`, the deployment uses
    `hostNetwork: true`, and every Kubernetes HTTP probe explicitly targets
    that loopback address and port.
25. Payload validation enforces
    [vendor specification section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions)
    for every format, including unowned destinations and link escapes. Debian
    simulation and installation use the same locked dependency set and reject
    transactions forbidden by the restricted Debian profile.
26. The image uses SONiC's regular-image recipe with shared build hooks enabled,
    not `# SKIP_HOOK`. The build verifies and records the approved base digest,
    snapshot selection, and profile/release/architecture lock set; missing or
    mismatched inputs fail the build.
27. After normal SONiC setup, `make target/docker-live-addon.gz` builds the
    checked-in example through its local source path and normal artifact build,
    without external vendor inputs, private credentials, or a separate build
    orchestrator. The explicitly empty fragment list is accepted; only Supervisor
    and the framework health server remain running. Sample health checks produce HTTP
    200 on success and HTTP 503 on failure. The example requires no privileged
    operation, host PID namespace or host-filesystem mounts and is not
    automatically installed, enabled or deployed. Normal SONiC installer builds
    do not build or include live-addon unless explicitly selected.
28. Explicit vendor selection uses the same Make target without a pipeline
    preparation step. Invalid selections fail rather than silently producing
    the default image. Switching between two vendors and back to `example`
    rebuilds the correct context, manifest and image without stale outputs or
    cross-profile cache reuse.
29. A binary-only integration produces a validated image from a prebuilt bundle
    and copy script without requiring proprietary program source. Replacing
    that bundle invalidates the artifact and image caches.
30. With an enabled deployment, cold/warm reboot and relevant service-restart
    qualification verifies diagnostic recovery and readiness, preserved forwarding
    during warm recovery, and any declared session-continuity behavior, following
    [vendor specification section 9](./design_vendor_spec.md#9-submission-and-qualification).

---

## 12. Recommendation

Adopt the vendor artifact build and installation contract managed by the SONiC
build framework as the target architecture. The SONiC community should own the
complete production Dockerfile, fixed Supervisor entrypoint, generic health
implementation, and Kubernetes probe behavior.

Use a regular SONiC image recipe with Make-owned prerequisites, a checked-in
example built through the local source path by default, and opt-in vendor
contributions through upstream PRs. Keep focused validation helpers, not a
separate build orchestrator.

Keep the [vendor integration specification](./design_vendor_spec.md) as the
single definition of vendor deliverables and restrictions; this document
defines how the framework enforces and implements that contract.

This is a small and explicit integration contract. It avoids requiring
SONiC maintainers to know the vendor's internal startup sequence while ensuring
that the SONiC build and deployment framework remains in control of the image
it builds, signs, publishes, and deploys.

---

## 13. References

- [Live-Addon Vendor Integration Specification](./design_vendor_spec.md)
- [SONiC buildimage repository](https://github.com/sonic-net/sonic-buildimage):
  shared image recipes, build hooks, and manifest generation.
- [Kubernetes startup, liveness, and readiness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/):
  deployment-side probe behavior.
- [Supervisor configuration](https://supervisord.org/configuration.html):
  process supervision and configuration semantics.
