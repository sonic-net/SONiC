# s6-overlay container supervision for SONiC (opt-in build option)

## Table of Contents

- [Revision](#revision)
- [Scope](#scope)
- [Definitions / Abbreviations](#definitions--abbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
  - [Build option](#build-option)
  - [Conversion of supervisord configuration](#conversion-of-supervisord-configuration)
  - [Event protocol compatibility](#event-protocol-compatibility)
  - [Stopping the container on a critical-process exit](#stopping-the-container-on-a-critical-process-exit)
  - [supervisorctl compatibility](#supervisorctl-compatibility)
  - [Containers that cannot run s6](#containers-that-cannot-run-s6)
  - [Logging](#logging)
  - [Host-side integration](#host-side-integration)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions / Limitations](#restrictions--limitations)
- [Testing Requirements / Design](#testing-requirements--design)
- [Open / Action items](#open--action-items)

## Revision

| Rev | Date       | Author                  | Change Description |
|-----|------------|-------------------------|--------------------|
| 0.1 | 2026-10-01 | Kostiantyn Buravchenko  | Initial draft      |

## Scope

This document describes an **opt-in** build option for sonic-buildimage,
`DOCKER_PROCESS_MANAGER=s6`, which runs
[s6-overlay](https://github.com/just-containers/s6-overlay) instead of
supervisord as the init (PID 1) and process supervisor inside the SONiC
dockers. The default (`DOCKER_PROCESS_MANAGER=supervisord`) is the
current behaviour and is unchanged.

## Definitions / Abbreviations

| Term        | Meaning |
|-------------|---------|
| supervisord | Python process-control system; today the PID 1 of every SONiC container |
| s6          | skarnet.org small supervision suite (s6-svscan, s6-supervise, s6-svc, s6-svstat) |
| s6-rc       | Service manager on top of s6: longruns, oneshots, dependencies, bundles |
| s6-overlay  | Container-oriented packaging of s6 + s6-rc with an `/init` entrypoint |
| longrun     | A supervised, restartable daemon service |
| oneshot     | A run-to-completion task; dependents start only after it finished |
| proc-exit-listener | The SONiC supervisor event listener that stops a container when a critical process exits unexpectedly |

## Overview

Every SONiC container currently boots a full Python interpreter
(supervisord) as PID 1 whose only job is to start and watch a handful of
processes. Dependency-ordered startup is provided by a third-party
plugin (`supervisord-dependent-startup`), and critical-process handling
is implemented by an event listener that signals supervisord to bring
the whole container down.

s6-overlay is a purpose-built container init: a few small C binaries
providing a supervision tree and a real service manager with native
support for dependencies, oneshots and supervised logging. Replacing
supervisord with s6 reduces the per-container memory footprint and
startup time, and gives startup ordering first-class semantics.

The key design decision: **the per-container supervisord configuration
remains the single source of truth.** No `supervisord.conf` or
`critical_processes` file changes. In s6 mode, a converter translates
the supervisord program definitions into an s6-rc service tree at
container start, and thin wrappers keep the external interfaces
(`supervisord` entrypoint, `supervisorctl`, the supervisor event
protocol consumed by the proc-exit-listener) unchanged. The two modes
can therefore coexist indefinitely, and a container works identically
from the point of view of the host, system-health and the feature
auto-restart machinery.

## Requirements

1. Opt-in build option; with the option unset the build output is
   byte-identical to today.
2. No changes to per-container supervisord configuration files.
3. Critical-process handling (feature auto-restart) works unmodified:
   an unexpected critical-process exit stops the container.
4. `dependent_startup_wait_for` ordering is honoured, including the
   `:exited` (run-to-completion) contract.
5. `supervisorctl status/start/stop/restart/signal` keep working for
   external callers (system-health, CLI, tests).
6. Containers that cannot run s6 (`--pid=host`) transparently fall back
   to supervisord within the same image.
7. All process output is delivered to syslog, as today.

## Architecture Design

No change to the SONiC system architecture: the set of containers, their
systemd services and the host-side `docker_image_ctl` lifecycle remain
the same. The change is confined to what runs as PID 1 *inside* a
container.

```
 supervisord mode (default)              s6 mode (DOCKER_PROCESS_MANAGER=s6)

 docker start                            docker start
   └─ supervisord (PID 1, Python)          └─ supervisord wrapper (bash)
        ├─ rsyslogd                             ├─ create_s6_config.py:
        ├─ start.sh ─ dependent-startup         │    /etc/supervisor/conf.d/*.conf
        ├─ daemon A                             │      -> /etc/s6-overlay/s6-rc.d/...
        ├─ daemon B                             └─ exec /init (s6-svscan, PID 1)
        └─ proc-exit-listener                        ├─ s6-supervise rsyslogd
             (event protocol on stdin)               ├─ s6-rc oneshot start.sh
                                                     ├─ s6-supervise daemon A ──┐ events
                                                     ├─ s6-supervise daemon B ──┤ (FIFO)
                                                     └─ s6-supervise proc-exit-listener <┘
```

## High-Level Design

### Build option

`rules/config`:

```
# DOCKER_PROCESS_MANAGER - process manager (container init) used inside the SONiC dockers
#   supervisord - supervisord runs as PID 1 of every container (default)
#   s6          - s6-overlay runs as PID 1 (experimental, opt-in)
DOCKER_PROCESS_MANAGER ?= supervisord
```

The value is validated and exported by `slave.mk`, passed into the slave
build by `Makefile.work`, and included in the docker-base cache
dependency flags so flipping the option rebuilds the base image. In s6
mode, `docker-base-trixie` additionally installs the s6-overlay noarch
and per-arch tarballs and the wrappers described below. All runtime
containers on master derive from the trixie base, so the option covers
all of them; legacy bases are untouched.

### Conversion of supervisord configuration

`create_s6_config.py` runs once at container start (from the supervisord
wrapper, before `exec /init`) and translates
`/etc/supervisor/conf.d/*.conf` into `/etc/s6-overlay/s6-rc.d/`:

| supervisord                                        | s6-rc |
|----------------------------------------------------|-------|
| `[program:x]`                                      | longrun service `x` with a `run` script |
| program `x` that others wait for with `x:exited`   | **oneshot** whose `up` runs the command to completion |
| `dependent_startup_wait_for=y:running`             | `dependencies.d/y` |
| `autorestart=false` (non-critical)                 | `finish` script holds the service down (`s6-svc -D`) |
| critical process (from `critical_processes`)       | restarted by s6-supervise |
| `[eventlistener:supervisor-proc-exit-listener]`    | longrun reading the event FIFO (see below) |

The generated listener run script exports `S6_SUPERVISED=1` before executing the listener. The listener binaries use this explicit gate (combined with an init-is-s6-svscan check for the container-stop path) to enable their s6-specific behaviour; without the variable they follow the stock supervisord code path unchanged.
| stdout/stderr to syslog                            | s6-log pipeline into `logger` |

The oneshot translation is essential for correctness: s6-rc considers a
longrun "up" the moment the process is spawned, while the supervisord
`:exited` contract means "ran to completion". Config-rendering `start.sh`
tasks must be oneshots or their dependents race the configuration files
they render.

### Event protocol compatibility

The existing proc-exit-listener consumes the supervisor event protocol
on stdin. In s6 mode the generated `run`/`finish` scripts synthesize the
same wire format:

* a service's `run` script writes `PROCESS_STATE_RUNNING` for the
  service to a FIFO (`/var/run/event_listener/input`) before exec-ing
  the daemon;
* its `finish` script writes `PROCESS_STATE_EXITED` with the `expected:`
  flag derived from the exit code;
* the listener service runs with stdin redirected from that FIFO (held
  open read-write so writers never block and the reader never sees EOF).

The listener binary itself is unchanged and shared between both modes
(the compiled Rust `supervisor-proc-exit-listener-rs` is preferred, the
Python one is the fallback).

Unlike supervisord's ack-driven protocol (one event in flight per READY
handshake), the FIFO delivers bursts. The listener must therefore drain
all buffered events before returning to its edge-triggered poller;
otherwise an `EXITED` event behind a startup burst is acted on late or
never.

### Stopping the container on a critical-process exit

Under supervisord the listener signals `getppid()` - supervisord is both
its parent and PID 1, so the container stops. Under s6 the listener's
parent is the s6 supervisor of the listener itself; signalling it merely
respawns the listener while the container keeps running, and the
critical process would be restarted in place without its dependants
(e.g. orchagent against a live syncd, defeating the feature-level
auto-restart contract).

In s6 mode the container must be stopped through PID 1 (s6-svscan).
Both listeners choose the target at runtime: PID 1 if `/proc/1/comm` is
`s6-svscan`, else `getppid()`. The `/proc/1/comm` check (rather than an
unconditional PID 1) keeps `--pid=host` containers safe, where PID 1 is
the host init.

### supervisorctl compatibility

A bash `supervisorctl` wrapper maps the used subset onto s6 tools:

| supervisorctl        | s6 |
|----------------------|----|
| `status [svc]`       | `s6-svstat -o up,pid,updownfor,updownsince` (formatted like supervisorctl) |
| `start/stop [svc]`   | `s6-svc -u/-d` (or `s6-rc -u/-d` for all) |
| `restart svc`        | stop + start |
| `signal SIG svc`     | `s6-svc -a/-b/-q/...` |

### Containers that cannot run s6

s6-overlay requires being PID 1. Containers started with `--pid=host`
share the host PID namespace, so the wrapper detects `$$ != 1` and execs
the real supervisord instead; the supervisorctl wrapper likewise falls
back when `/run/s6-rc` does not exist. Both process managers are
installed in the image, so the fallback needs no build-time knowledge of
which containers use `--pid=host`.

### Logging

Service stdout/stderr flow through an s6-log pipeline into `logger` (to
syslog, as today). Output that escapes the service tree lands in
s6-overlay's uncaught log (`/run/uncaught-logs/current`), which rsyslog
picks up via an `imfile` input shipped with the base image.

### Host-side integration

`docker_image_ctl.j2` waits for the database/chassisdb containers with
`pgrep -x supervisord` before pinging redis. Under s6 no supervisord
process exists; the rendered script (build-time jinja, zero diff in
supervisord mode) waits on the redis PING alone.

## SAI API

Not applicable.

## Configuration and management

None at runtime: the process manager is a build-time image property.
There is no CONFIG_DB schema, CLI or YANG change. `supervisorctl`
remains the management interface inside containers in both modes.

## Warmboot and Fastboot Design Impact

The container lifecycle (systemd service -> docker_image_ctl ->
container init) is unchanged, and the proc-exit-listener semantics are
preserved, so no warm/fast boot flow changes by design. Warm-boot
regression runs on an s6 image are part of the test plan before the
option can be considered for broader default use.

## Restrictions / Limitations

* Experimental, opt-in; default images are bit-identical with the
  option off.
* Implemented for the trixie docker base only (all runtime containers on
  current master).
* Containers relying on supervisord `priority=` implicit ordering may
  need explicit `dependent_startup_wait_for` declarations to behave
  identically under s6 (identified so far: docker-fpm-frr benefits from
  an explicit fpmsyncd-before-zebra ordering; to be submitted as
  container-level follow-ups).
* `supervisorctl` wrapper implements the subset used by SONiC
  (status/start/stop/restart/signal), not the full supervisorctl UI.
* s6-overlay tarballs are fetched from GitHub releases at docker-base
  build time; mirroring through the versions framework is an open item.

## Testing Requirements / Design

Unit tests (run in PR CI):

* proc-exit-listener (Python and Rust): `supervisor_pid()` selection
  (s6-svscan -> PID 1, otherwise parent), burst-drain regression test.
* `create_s6_config.py` conversion of representative supervisord
  configurations (longrun, oneshot, dependencies, autorestart variants).

System tests on an s6-built image:

* every feature container reaches a running state with s6-svscan as
  PID 1; `supervisorctl status` reports all services;
* critical-process kill (orchagent, syncd, bgpd) stops the container and
  feature auto-restart restores it with correct dependant ordering;
* `config reload`, `reboot`, warm-reboot and fast-reboot regressions;
* system-health reports the same process states as a supervisord image;
* `--pid=host` containers run with the supervisord fallback.

## Open / Action items

* Mirror the s6-overlay artifacts through the SONiC versions framework.
* Decide whether sonic-mgmt needs an s6 image in a CI lane while the
  option matures.
* Container-level `dependent_startup_wait_for` follow-ups (docker-fpm-frr).
