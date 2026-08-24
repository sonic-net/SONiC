# SONiC EOL and Deprecation Plan for 202611

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Remove now](#71-remove-now)
    - [7.1.1 Barefoot / Tofino platform](#711-barefoot--tofino-platform)
    - [7.1.2 DTEL (data-plane telemetry)](#712-dtel-data-plane-telemetry)
    - [7.1.3 Standalone P4 platform](#713-standalone-p4-platform)
    - [7.1.4 Nephos platform](#714-nephos-platform)
    - [7.1.5 GoBGP and Quagga routing stacks](#715-gobgp-and-quagga-routing-stacks)
    - [7.1.6 Python 2 packages](#716-python-2-packages)
    - [7.1.7 Kubernetes master](#717-kubernetes-master)
    - [7.1.8 docker-basic_router](#718-docker-basic_router)
    - [7.1.9 System Telemetry container](#719-system-telemetry-container)
    - [7.1.10 Broken FRR config modes](#7110-broken-frr-config-modes)
    - [7.1.11 End-of-life Debian bases](#7111-end-of-life-debian-bases)
  - [7.2 Deprecate now, remove later](#72-deprecate-now-remove-later)
    - [7.2.1 Bookworm base containers](#721-bookworm-base-containers)
    - [7.2.2 FRR split-unified config mode](#722-frr-split-unified-config-mode)
    - [7.2.3 REST API](#723-rest-api)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit Test cases](#131-unit-test-cases)
  - [13.2 System Test cases](#132-system-test-cases)
- [14. Open/Action items](#14-openaction-items)

### 1. Revision

| Rev | Date | Author | Change |
|-----|------|--------|--------|
| 0.1 | 2026-07-19 | Brad House (Nexthop) | First draft. Security WG. |
| 0.2 | 2026-07-24 | Brad House (Nexthop) | Added the Keep verdict. Moved bullseye to immediate removal and deprecated bookworm in its place. Folded Quagga into the GoBGP removal. |
| 0.3 | 2026-07-24 | Brad House (Nexthop) | Filled in the notification steps of the process, which are the mailing list, the working groups, the TSC for platform removals, and a second round before the branch date. |
| 0.4 | 2026-08-24 | Brad House (Nexthop) | Moved the standing process, the verdicts, and the rules of thumb into the TSC policy document, so that this HLD covers only the 202611 candidates. Restructured to the HLD template. |

### 2. Scope

This HLD is the 202611 release plan for feature deprecation and removal. It lists the features proposed for a verdict in this cycle, states what each one is, why it should go, and the exact paths that go with it.

The process this plan follows is not defined here. It lives in [the SONiC Feature Deprecation and Removal Policy](../../tsc/eol-deprecation/sonic_eol_deprecation_policy.md), which is release independent and covers the verdicts, the review and notification steps, the rules of thumb behind the calls, and what a release plan has to contain. This document is one instance of that policy. A later release files its own plan beside this one and does not restate the process.

The work comes from the SONiC Security Working Group, whose goal is to shrink the attack surface. Less code means fewer packages, fewer CVEs, and less to build and test.

Releases ship twice a year, in November (`YYYY11`) and in May (`YYYY05`). The cycles referenced here are 202611 (November 2026), 202705 (May 2027), and 202711 (November 2027).

This document is documentation only. It removes nothing by itself. Each removal lands as its own pull request after review and component owner sign-off.

### 3. Definitions/Abbreviations

The verdicts used below, which are **Remove now**, **Deprecate now, remove later**, and **Keep**, are defined in [the policy](../../tsc/eol-deprecation/sonic_eol_deprecation_policy.md#3-verdicts).

| Term | Meaning |
|------|---------|
| Deprecate | Mark a feature as going away. It still ships, but it warns of removal. |
| Remove | Delete the code and its build wiring. |
| SBOM | Software Bill of Materials. |
| DTEL | Data-plane telemetry (in-band / INT). |
| TAM | Telemetry and Monitoring (added in 202605). |
| EOL | End of life. |
| CI | The community build/test gate. |
| TSC | Technical Steering Committee. |
| WG | Working group. |

### 4. Overview

SONiC still ships features that few or no one runs. Some of them are dead. Some broke when a dependency moved on. Some were tied to hardware that no longer exists. Each one still adds packages to the image, findings to every CVE scan, and jobs to CI.

This HLD proposes the first batch to act on. Fourteen candidates are listed. Eleven are proposed for removal in 202611, and three are proposed for deprecation now with a named removal release, which is 202705 for two of them and 202711 for the REST API.

### 5. Requirements

- Every candidate carries a verdict, the evidence behind it, and the exact paths it covers, as required by [section 6 of the policy](../../tsc/eol-deprecation/sonic_eol_deprecation_policy.md#6-what-a-release-plan-contains).
- No feature is removed without component owner sign-off.
- The three platform removals, which are 7.1.1 Barefoot, 7.1.3 standalone P4, and 7.1.4 Nephos, go to the TSC in addition to HLD review. The TSC decision is what settles them.
- A user who never enabled any of these features sees no functional change and no CLI change.
- Every removal that touches configuration is accompanied by a `db_migrator.py` update, so that a device that upgrades does not carry dead config or point at a value that no longer exists. See section 9.3.
- Each supported CI platform still builds after the removals, and no remaining container points at a deleted base.

Out of scope for this plan:

- The removals themselves. This document is documentation only, and each removal is a separate pull request.
- The standing process, which is the policy document.
- Anything under section 14, which needs code porting this plan does not cover.

### 6. Architecture Design

There is no change to the SONiC architecture. Every candidate below removes a component, a build rule, or a platform, and nothing is added. None of these features is a SONiC Application Extension, so the Application Extension infrastructure is not involved.

Two candidates narrow an existing choice rather than deleting a leaf:

- 7.1.10 collapses `docker_routing_config_mode` from four values to `unified` and `split-unified`, and makes `unified` the default. The supported path is unchanged, because `unified` already works today and the two removed modes are broken with the FRR version SONiC ships.
- 7.1.5 collapses the routing stack to FRR alone. `rules/config` already documents `frr` as the sole supported value of `SONIC_ROUTING_STACK`, and neither alternative has been buildable for years, so this deletes unreachable branches rather than changing which stack runs.

### 7. High-Level Design

These are built-in SONiC features rather than Application Extensions. The repositories that change are `sonic-buildimage` for the platforms, containers, build rules, and pipeline jobs, `sonic-swss` for the DTEL orchestration agent code, `sonic-utilities` for `db_migrator.py` and the routing CLI, and `sonic-restapi`, which is removed outright in 202711. No new module or interface is introduced, and no sequence diagram applies, because nothing new runs.

Each candidate below stands on its own. It states what the feature is, why it should go, the paths to remove, and anything to watch out for.

Three of these are platform removals, which are 7.1.1 Barefoot, 7.1.3 standalone P4, and 7.1.4 Nephos. Those go to the TSC under step 4 of the policy, separately from the rest of this list.

#### 7.1 Remove now

##### 7.1.1 Barefoot / Tofino platform

Intel has ended the Tofino line, and the platform is not in the CI build matrix (aspeed_arm64, broadcom, marvell-prestera, mellanox, nvidia_bluefield, vs, alpinevs, and vpp). Because nothing builds it, nothing tests it. The platform is roughly 7.7 MB across about 880 files, and it pulls in the Barefoot SAI, saithrift, the `docker-syncd-bfn` and `docker-saiserver-bfn` containers, and the ODM sub-platforms built on Tofino (Accton Wedge100BF, Arista 7170, Ingrasys, Netberg, and WNC).

**Remove:** `platform/barefoot/`; the Tofino `device/` folders (Accton Wedge100BF, Arista 7170, Ingrasys, Netberg, WNC); the `barefoot` job in `.azure-pipelines/azure-pipelines-build.yml`; the `barefoot` filter in `rules/docker-platform-monitor.mk`.

##### 7.1.2 DTEL (data-plane telemetry)

DTEL is SONiC's in-band data-plane telemetry. In practice it only ever ran on Barefoot Tofino, and that platform is EOL and is being removed in 7.1.1. With the only hardware that ran it gone, the DTEL code in the orchestration agent is dead. TAM, which was added in 202605, already covers the same need on current hardware.

**Remove:** `src/sonic-swss/orchagent/dtelorch.{cpp,h}`, the DTEL table set and initialization in `orchagent/orchdaemon.cpp`, and the DTEL handling in `orchagent/aclorch.{cpp,h}`; the DTEL CONFIG_DB tables and any `sonic-dtel` YANG model; `src/sonic-swss/tests/test_dtel.py`.

##### 7.1.3 Standalone P4 platform

This is the old bmv2 software behavioral model. It is a reference target rather than real hardware, and it has been dead since roughly 2022. Nothing in CI builds it. It is about 12 MB across 920 files, and it pulls in four stale external submodules. The only thing that references it outside `platform/p4/` is a Debian 8 era TODO in `rules/redis.mk`.

**Remove:** `platform/p4/` (which includes `docker-sonic-p4`, `sai-p4-bm`, `p4c-bm`, `tenjin`, and `p4-hlir`); the four P4 submodule entries in `.gitmodules` (`platform/p4/p4c-bm/p4c-bm`, `platform/p4/p4-hlir/p4-hlir`, `platform/p4/p4-hlir/p4-hlir-v1.1`, `platform/p4/SAI-P4-BM`); the stale TODO in `rules/redis.mk`. **Keep:** `rules/p4lang.mk`. The p4lang toolchain it builds (bmv2, p4c, and PI) is a live dependency of DASH SAI, which ships in `sonic-vs.img.gz`, and of the PTF test containers.

##### 7.1.4 Nephos platform

The Nephos and MediaTek switch silicon vendor left the market around 2019. The platform is about 2.3 MB across 160 files. There is no `device/nephos` tree, there has been no genuine commit in years, and it is not in CI.

**Remove:** `platform/nephos/`; the `nephos` job in `.azure-pipelines/azure-pipelines-build.yml`.

##### 7.1.5 GoBGP and Quagga routing stacks

FRR is the only routing stack SONiC supports. `rules/config` already documents `frr` as the sole supported value of `SONIC_ROUTING_STACK`. Even so, both the build and the CLI still carry the machinery to elect GoBGP or Quagga instead, and that selectable-stack machinery is what this candidate removes.

GoBGP had its image build rules deleted back in 2021, so it has not been buildable as an image since then. Even so, every build still compiles a 2017 era Go GOBGP package that nothing installs. Quagga left even earlier. Its container and build rules are long gone, but the branches that would select it were never cleaned up, so the build glue, the CLI, and the sudoers policy still carry a Quagga path that cannot be reached. Removing both loses nothing, because FRR provides all of it. Once they are gone, every routing-stack conditional collapses to a single path, and `get_routing_stack()` has only one possible answer, so the runtime detection that shells out to `docker ps` can go with it.

The target here is stack selection rather than the word Quagga. FRR is itself a fork of Quagga, so Quagga-derived names legitimately survive in FRR-sourced code, including the whole of `src/sonic-frr/`, its `_QUAGGA_*` header guards, and the `fpm.h` that fpmsyncd carries. Those are upstream names and they stay.

Where a Quagga-named file turns out to be the live FRR implementation, rename it rather than delete it. `clear/bgp_quagga_v4.py` is the clear case, because the `frr` branch of `clear/main.py` imports it and there is no `clear/bgp_frr_v4.py`, which makes it the working implementation of `clear ip bgp` today.

**Remove (GoBGP):** `dockers/docker-fpm-gobgp/`, `src/gobgp/`, `rules/gobgp.mk`, and `rules/gobgp.dep`. **Remove (stack selection in the build):** `rules/docker-fpm.mk` and `rules/docker-fpm.dep`, which exist only to elect a stack, so `DOCKER_FPM_FRR` can be referenced directly and the dead `DOCKER_FPM_GOBGP` and `DOCKER_FPM_QUAGGA` names go with them; the `else` branch that adds `$(GOBGP)` in `platform/vs/docker-sonic-vs.mk`; the `SONIC_ROUTING_STACK` conditionals in `slave.mk` and `files/build_templates/sonic_debian_extension.j2`, whose FRR blocks become unconditional; the commented-out `ROUTING_STACK` selection in `platform/p4/docker-sonic-p4.mk`, which goes with 7.1.3 in any case. Keep `SONIC_ROUTING_STACK = frr` in `rules/config` as a single-value knob, because downstream `rules/config.user` files may still set it. **Remove (stack selection in the CLI):** in sonic-utilities, the `routing_stack == "quagga"` branches of `show/main.py` and `clear/main.py` along with `show/bgp_quagga_v4.py`, `show/bgp_quagga_v6.py`, and `clear/bgp_quagga_v6.py`; the non-frr `else` branches that carry the Quagga `bgp` and `zebra` groups in `debug/main.py` and `undebug/main.py`; the `/etc/quagga/bgpd.conf` branch of `show startupconfiguration bgp` and the matching `docker exec bgp cat /etc/quagga/bgpd.conf` entry in `files/image_config/sudoers/sudoers`; the cases that exercise the removed branches in `tests/show_test.py`, `tests/clear_test.py`, and `tests/debug_test.py`. **Rename:** `src/sonic-utilities/clear/bgp_quagga_v4.py` to `clear/bgp_frr_v4.py`, and update the import in `clear/main.py`.

Comments that only mention Quagga in passing, such as the `docker-fpm.gz` line in `README.md`, the `## Quagga rules` header in `files/image_config/rsyslog/rsyslog.d/00-sonic.conf.j2`, and the "For quagga build" comments in the sonic-slave Dockerfiles, are worth correcting when the code around them is touched, but they are not the point of this candidate. The packages under that build comment, such as `libreadline-dev`, `libpam-dev`, and the texlive set, are FRR build dependencies now, so leave them alone.

##### 7.1.6 Python 2 packages

Both packages are gated behind `ENABLE_PY2_MODULES`, which is off for bullseye, bookworm, and trixie. As a result, neither is built on any current release, so both are dead weight. The py3 version of swsssdk is a separate matter, because it is still in use. It is out of scope here and is noted under Additional findings.

**Remove:** `rules/swsssdk-py2.mk`, `rules/swsssdk-py2.dep`, `rules/redis-dump-load-py2.mk`, and `rules/redis-dump-load-py2.dep`; the `SWSSSDK_PY2` dependency lines in `rules/sonic-py-common.mk` and `rules/swsssdk-py3.mk`.

##### 7.1.7 Kubernetes master

This runs a full Kubernetes control plane on the switch. That includes the apiserver, controller, scheduler, proxy, etcd 3.5.0, coredns 1.8.4, and the dashboard 2.7.0 web UI, along with cloud credential libraries used for backups. Every one of those versions is years past end of life, which makes this the single biggest reduction in CVE surface in this list. It is off by default and has no real CI coverage.

This applies to the master only. The worker feature (`INCLUDE_KUBERNETES`) is a separate feature and should stay. Someone hardened its cluster-join security before this working group existed, which points to a real user.

**Remove:** `files/image_config/kubernetes/` (`kubernetes_master_entrance.sh`, `kubernetes_master_entrance.service`, `kubernetes.list`); the `INCLUDE_KUBERNETES_MASTER` flag and the master version pins in `rules/config`; the master-only blocks in `files/build_templates/sonic_debian_extension.j2`; `sonic-kubernetes_master.yang`; the master build in `.azure-pipelines/azure-pipelines-build.yml`. **Keep:** `INCLUDE_KUBERNETES` (the worker), `src/sonic-ctrmgrd*`, and the `ctrmgrd` wrapper, which runs for ordinary feature start and stop rather than only for k8s.

##### 7.1.8 docker-basic_router

This is a SAI demo and reference container. It is not wired into any build rule, it never ships in an image, and it is not in CI. Its last real change was in 2020, and nothing uses it.

**Remove:** `dockers/docker-basic_router/`.

##### 7.1.9 System Telemetry container

This container is off by default, and it is redundant. Both this container and the gnmi container run the same binary, `/usr/sbin/telemetry`, started by `telemetry.sh` and `gnmi-native.sh` respectively. There is no separate gNMI server. The `telemetry` binary is the server, and the name is only historical. Both containers read the same `TELEMETRY|gnmi` config, and the gnmi start script simply adds ZMQ and VRF options on top. There is therefore no functional gap, because Get, Set, Subscribe, and dial-out are identical in both.

**Remove:** `dockers/docker-sonic-telemetry/`, `rules/docker-telemetry.mk`, and `rules/docker-telemetry.dep`; the `INCLUDE_SYSTEM_TELEMETRY` flag in `rules/config`. **Keep:** the `telemetry` binary, which is built by sonic-gnmi and run by the gnmi container.

##### 7.1.10 Broken FRR config modes

`docker_routing_config_mode` has four values. Both `separated` and `split` write per-daemon config files such as `bgpd.conf` and `zebra.conf`. FRR 10.5.4, which SONiC ships, dropped support for per-daemon config files, so both of these modes are broken today. Removing them is really just deleting dead code.

The supported path is `unified`, where the config comes from bgpcfgd and `config_db.json`, and that should become the default. Today `minigraph.py` hardcodes the default as `separated`, and init_cfg does not set it, so it resolves to `separated`. This change must flip that default to `unified`. The fourth mode, `split-unified`, still works and is handled under Deprecate.

**Change:** remove the `separated` and `split` branches in `dockers/docker-fpm-frr/docker_init.sh` and the per-daemon templates under `dockers/docker-fpm-frr/frr/{bgpd,zebra,staticd,sharpd}/`; flip the default in `src/sonic-config-engine/minigraph.py` from `separated` to `unified`.

##### 7.1.11 End-of-life Debian bases

Debian 8 (jessie), Debian 9 (stretch), Debian 10 (buster), and Debian 11 (bullseye) are all out of support. Bullseye leaves Debian LTS in August 2026, which is before 202611 ships, so it belongs with the rest rather than in a later cycle. The risk in every case is the same, which is that someone builds a new container on a base that no longer gets security updates.

jessie, stretch, and buster are pure leftovers, because nothing builds on them. Bullseye is different, because containers still build on it today, so those have to move first. Before deleting any base, confirm that nothing still builds a container on it. Debian 12 (bookworm) is still a live base and is handled under Deprecate.

**Remove (stretch):** `dockers/docker-base-stretch/`, `rules/docker-base-stretch.{mk,dep}`, `dockers/docker-config-engine-stretch/`, `rules/docker-config-engine-stretch.{mk,dep}`. **Remove (buster):** `dockers/docker-base-buster/`, `rules/docker-base-buster.{mk,dep}`, `dockers/docker-config-engine-buster/`, `rules/docker-config-engine-buster.{mk,dep}`, `dockers/docker-swss-layer-buster/`, `rules/docker-swss-layer-buster.{mk,dep}`. **Remove (jessie):** `sonic-slave-jessie/`, the `jessie` target in `Makefile`, and the jessie `SLAVE_DIR` branch in `Makefile.work`. jessie has no `docker-base-jessie`, so also check the jessie strings in the generic `dockers/docker-base/` (its armhf and arm64 sources and its `FROM ...:jessie` lines) before touching that container. **Move first (bullseye):** seven containers still build on a bullseye base. Two of them, `docker-syncd-bfn` and `docker-saiserver-bfn`, go away with Barefoot in 7.1.1. The other five have to move to bookworm or trixie before bullseye can go, and they are `docker-syncd-centec` and `docker-saiserver-centec` under both `platform/centec/` and `platform/centec-arm64/`, plus `dockers/docker-sonic-sdk/`. The centec containers reach bullseye through `platform/template/docker-syncd-bullseye.mk`, so pointing their `docker-syncd-centec.mk` at the bookworm or trixie template covers four of the five. **Remove (bullseye):** `dockers/docker-base-bullseye/`, `rules/docker-base-bullseye.{mk,dep}`, `dockers/docker-config-engine-bullseye/`, `rules/docker-config-engine-bullseye.{mk,dep}`, `dockers/docker-swss-layer-bullseye/`, `rules/docker-swss-layer-bullseye.{mk,dep}`, `platform/template/docker-syncd-bullseye.mk`, and `sonic-slave-bullseye/`; the `bullseye` target and the `NOBULLSEYE` and `BUILD_BULLSEYE` handling in `Makefile`, the bullseye `SLAVE_DIR` branch in `Makefile.work`, the `sonic-slave-bullseye` entry in `Makefile.cache`, and in `slave.mk` the `BULLSEYE_DEBS_PATH` and `BULLSEYE_FILES_PATH` variables, the `bullseye` target, and the `BLDENV` tests that name it; the `BLDENV == bullseye` conditionals in `rules/grpc.mk`, `rules/protobuf.mk`, `rules/sonic-dash-api.mk`, and `rules/sonic-fips.mk`.

#### 7.2 Deprecate now, remove later

##### 7.2.1 Bookworm base containers

This should be removed in 202705. Bookworm is Debian 12. Its regular security support ends in 2026, which leaves LTS only, and trixie is the current base. It is still a live base, so it deserves a cycle of notice rather than immediate removal. Three syncd containers build on it, which are `docker-syncd-pensando`, `docker-syncd-vs` under `platform/alpinevs/`, and `docker-syncd-vs` under `platform/nokia-vs/`, and the last two reach it through `platform/template/docker-syncd-bookworm.mk`. Move those to trixie first, and then remove the base.

**Remove (202705):** `dockers/docker-base-bookworm/`, `rules/docker-base-bookworm.{mk,dep}`, `dockers/docker-config-engine-bookworm/`, `rules/docker-config-engine-bookworm.{mk,dep}`, `dockers/docker-swss-layer-bookworm/`, `rules/docker-swss-layer-bookworm.{mk,dep}`, `platform/template/docker-syncd-bookworm.mk`, and `sonic-slave-bookworm/`; the `bookworm` target and the `NOBOOKWORM` and `BUILD_BOOKWORM` handling in `Makefile`, and the bookworm `SLAVE_DIR` branch in `Makefile.work`.

##### 7.2.2 FRR split-unified config mode

This should be removed in 202705. It is the manual routing mode, where the operator writes `frr.conf` by hand. It has a real problem. The bgp container runs supervisord rather than systemd, so FRR cannot hot-reload, and any change to `frr.conf` forces a full FRR restart that drops BGP sessions. That makes it impractical for production, so it is doubtful anyone serious runs it. The plan is to consolidate on `unified`, which uses bgpcfgd and `config_db.json`. Before removing it, confirm that bgpcfgd and `config_db.json` cover the FRR features operators actually need.

**Change (202705):** remove the `split-unified` branch in `dockers/docker-fpm-frr/docker_init.sh`.

##### 7.2.3 REST API

This should be removed in 202711. It is off by default. Its own spec calls it the "SONiC REST API for Baremetal Scenarios." It is an imperative agent for baremetal VNET, VXLAN, and VLAN config over HTTPS, not a general REST interface. gNMI is the intended replacement, but it does not cover two things. The first is bulk route programming with per-route partial success (HTTP 207). The second is route expiry, which is timed route aging. Because of that gap, this candidate gets the longest runway. Before removing it, confirm that no control plane still drives it. The mgmt-framework REST server is a different thing and stays.

**Remove (202711):** `dockers/docker-sonic-restapi/`, `src/sonic-restapi/` and its `.gitmodules` entry, `rules/docker-restapi.{mk,dep}`, and `rules/restapi.{mk,dep}`; the `INCLUDE_RESTAPI` flag in `rules/config`; the `restapi` feature in `files/build_templates/init_cfg.json.j2`.
### 8. SAI API

There is no change to the SAI API. Nothing here adds, removes, or modifies a SAI API or object, and silicon vendors have nothing to implement for this plan.

Two candidates touch SAI adjacent code without changing the interface. 7.1.1 removes the Barefoot SAI implementation and saithrift wiring for a platform that is EOL, which is a vendor implementation rather than the API. 7.1.2 removes the orchestration agent code that calls the SAI DTEL APIs, which leaves those APIs in SAI itself untouched and simply stops SONiC from calling them.

### 9. Configuration and management

Removing a feature drops its `FEATURE` table entries, its build flags, and any YANG models tied to it. Users who never enabled these features see no CLI change.

#### 9.1 Manifest

Not applicable. None of these features is a SONiC Application Extension, so there is no manifest.

#### 9.2 CLI/YANG model Enhancements

No command is added, and no command changes its syntax. The changes are deletions and one default.

YANG models removed with their features:

- `sonic-kubernetes_master.yang`, with 7.1.7.
- The `sonic-dtel` model and the DTEL CONFIG_DB tables, with 7.1.2.

CLI effects:

- Collapsing the routing stack to FRR in 7.1.5 does not change any command an operator runs, because the FRR branch of every affected command already provides the same CLI. `clear ip bgp` keeps working through the renamed `clear/bgp_frr_v4.py`. The one visible difference is `show startupconfiguration bgp`, which loses its `/etc/quagga/bgpd.conf` branch and reads only `/etc/frr/bgpd.conf`.
- `docker_routing_config_mode` accepts fewer values after 7.1.10, which is a narrowing of an existing setting rather than a CLI change.

`sonic-utilities/doc/Command-Reference.md` carries more Quagga material than the code does, and it is updated in the same pull request as 7.1.5. That means the whole `## Quagga BGP Show Commands` section and its entry in the table of contents, the `Versions <= 201811 using Quagga routing stack` variants and the links to them under the BGP show commands, and the `## Routing Stack` section, which still tells the reader that SONiC is agnostic of the routing stack and that Quagga is a choice. The `show startupconfiguration bgp` entry loses its Quagga path with the code. Nothing in the reference describes the other candidates, because the Kubernetes commands documented there belong to the worker feature, which stays.

#### 9.3 Config DB Enhancements

Removing the code is only half of it, because a device that upgrades keeps whatever it already had in CONFIG_DB. Every removal that touches configuration therefore has to update `sonic-utilities/scripts/db_migrator.py`, and that update is part of the removal rather than a follow-up. Without it, an upgraded device carries dead `FEATURE` rows and orphaned tables forever, a table that outlives its YANG model can fail config validation, and a setting whose supported values have narrowed can leave the device pointing at a value that no longer exists.

The shape of the change is the same each time. Add a new `version_<branch>_<build>` method chained onto the current tail of the version chain, bump `CURRENT_VERSION` to it, which is `version_202605_01` today, and drop the state that is going away with `delete_table` or with entry deletion. What this batch needs:

- `DEVICE_METADATA|localhost|docker_routing_config_mode`. A device holding `separated` or `split` has to be migrated to `unified`, because 7.1.10 deletes the code behind both. This is the case that matters most, since skipping it leaves a device configured for a routing mode that no longer exists rather than merely carrying dead config.
- The `KUBERNETES_MASTER` table, which goes with 7.1.7, along with its YANG model.
- The DTEL tables, which go with 7.1.2.
- `FEATURE|telemetry`, which goes with 7.1.9. `FEATURE|gnmi` stays, and the two must not be confused, because the surviving container is the gnmi one.
- `FEATURE|restapi`, when the REST API is removed in 202711 under 7.2.3, which lands in that release's migrator rather than this one.

The default for `docker_routing_config_mode` also changes. Today `src/sonic-config-engine/minigraph.py` hardcodes `separated` and init_cfg does not set it, so a device with no explicit value resolves to `separated`. 7.1.10 flips that default to `unified`.

### 10. Warmboot and Fastboot Design Impact

There is no warmboot or fastboot impact. Every candidate is off by default, already dead, or specific to hardware that is being removed. None of this touches the warmboot or fastboot path on supported platforms.

The one candidate that touches a path a supported device runs is 7.1.10, and it changes which FRR config mode is selected at container start rather than anything in the warmboot or fastboot sequence. A device already running `unified`, which is the supported mode, sees no change at all.

#### Warmboot and Fastboot Performance Impact

There is no degradation, and the direction of every change is downward.

- No stall, sleep, or IO operation is added to the boot critical chain. Code is deleted from it, not added.
- No CPU heavy processing is added. 7.1.10 removes three of the four branches in `docker_init.sh` and the per-daemon Jinja templates behind them, which is strictly less template rendering at bgp container start.
- No third party dependency is bumped for a device that ships today. The base image moves in 7.1.11 and 7.2.1 change which Debian base a container is built from, and the containers involved are the centec syncd and saiserver containers and `docker-sonic-sdk`. Those are build time changes, and the platforms that own them validate boot time as part of the move.
- Nothing here needs to be delayed, because nothing here starts.

### 11. Memory Consumption

No memory is added. Every candidate is a removal, so runtime memory either drops or is unchanged, and image size drops.

The features that carried a running process are off by default today, so a device that never enabled them frees nothing at runtime and simply stops carrying the code. A device that did enable the System Telemetry container (7.1.9) or the Kubernetes master (7.1.7) frees whatever those processes used, and in the telemetry case the same functionality continues in the gnmi container, which is already running the same binary.

### 12. Restrictions/Limitations

- Bullseye cannot be removed until five containers move off it, which are the centec syncd and saiserver containers under `platform/centec/` and `platform/centec-arm64/`, and `dockers/docker-sonic-sdk/`. That move is a prerequisite of 7.1.11 rather than part of it, and it depends on the platform owners.
- The same applies to bookworm in 7.2.1, where three syncd containers have to move to trixie first.
- gNMI does not fully replace the REST API. It does not cover bulk route programming with per-route partial success (HTTP 207), and it does not cover route expiry. That gap is why 7.2.3 gets the longest runway, and it is not closed by this plan.
- Removing a feature that is off by default is not proof that nobody runs it. The notification steps in the policy exist for that reason, and a verdict can move to **Keep** at any point before the removal lands.

### 13. Testing Requirements/Design

Each removal is tested in the pull request that performs it, rather than here. The requirements below apply to that pull request and to the release as a whole.

#### 13.1 Unit Test cases

- `db_migrator` unit tests cover each table and field this batch drops, including a device that starts on `separated` and one that starts on `split`, and both end on `unified`.
- The `sonic-config-engine` tests cover the new `unified` default in `minigraph.py`, with and without an explicit `docker_routing_config_mode`.
- The `sonic-swss` test suite still passes with `tests/test_dtel.py` and the DTEL orchestration agent code removed.
- YANG model tests pass with the removed models absent, and no remaining model references them.

#### 13.2 System Test cases

- Each supported CI platform still builds after the removals.
- The removed packages no longer appear in the SBOM or the CVE scan, confirmed by an image diff.
- The default FRR path (`unified`) comes up and programs routes.
- A `config_db.json` from the previous release migrates cleanly, with no leftover tables for removed features and no config validation errors against the reduced YANG model set.
- A device configured for `separated` or `split` comes up in `unified` after upgrade, rather than pointing at a mode whose code is gone.
- Every remaining container builds with nothing pointing at a deleted base, and the centec and sonic-sdk containers build on their new base.
- `show ip bgp` and `clear ip bgp` still work after the routing-stack collapse and the `clear/bgp_frr_v4.py` rename.
- gNMI still serves Get, Set, Subscribe, and dial-out after the System Telemetry container is removed.

### 14. Open/Action items

- Component owner sign-off is outstanding for every candidate. No removal lands without it.
- The three platform removals need a TSC decision, which is step 4 of the policy.
- The five bullseye containers and the three bookworm containers need an owner to move them to a newer base, as described in section 12.
- **swsssdk-py3.** This is the old Python Redis SDK. `swsscommon` replaces it, but code still imports `swsssdk` at runtime, including `sonic-utilities/scripts/dualtor_neighbor_check.py`, `sonic-py-common`, and the vpp container. It cannot be deprecated until those are ported to `swsscommon`, so it is not a candidate in this plan. It is recorded here so that a later cycle picks it up.
