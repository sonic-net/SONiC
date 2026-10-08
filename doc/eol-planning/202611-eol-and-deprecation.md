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
    - [7.1.1 Nephos platform](#711-nephos-platform)
    - [7.1.2 Barefoot / Tofino platform](#712-barefoot--tofino-platform)
    - [7.1.3 DTEL (data-plane telemetry)](#713-dtel-data-plane-telemetry)
    - [7.1.4 Standalone P4 platform](#714-standalone-p4-platform)
    - [7.1.5 GoBGP and Quagga routing stacks](#715-gobgp-and-quagga-routing-stacks)
    - [7.1.6 Python 2 packages](#716-python-2-packages)
    - [7.1.7 Kubernetes master](#717-kubernetes-master)
    - [7.1.8 docker-basic_router](#718-docker-basic_router)
    - [7.1.9 System Telemetry container](#719-system-telemetry-container)
    - [7.1.10 End-of-life Debian bases](#7110-end-of-life-debian-bases)
  - [7.2 Deprecate now, remove later](#72-deprecate-now-remove-later)
    - [7.2.1 Bookworm base containers](#721-bookworm-base-containers)
    - [7.2.2 FRR split and split-unified config modes](#722-frr-split-and-split-unified-config-modes)
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
| 0.4 | 2026-08-24 | Brad House (Nexthop) | Moved the standing process, the verdicts, and the rules of thumb into the TSC policy document, and restructured this plan to the HLD template. Led the remove-now list with Nephos so that the platform removals read together. Dropped the FRR config mode candidate, whose premise did not survive a check against the FRR source, and widened 7.2.2 to cover `split` as well as `split-unified` in its place. Spelled out in 7.2.3 that RESTCONF is not affected, and compared both candidate replacements against what the REST API actually writes. Re-derived every candidate against the tree: corrected the Barefoot device folders, the bookworm container list, the DTEL replacement and YANG claims, and the CI statements for Barefoot and Nephos. Turned the file enumerations into lists. |

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

This HLD proposes the first batch to act on. Thirteen candidates are listed. Ten are proposed for removal in 202611, and three are proposed for deprecation now with a named removal release, which is 202705 for two of them and 202711 for the REST API.

### 5. Requirements

- Every candidate carries a verdict, the evidence behind it, and the exact paths it covers, as required by [section 6 of the policy](../../tsc/eol-deprecation/sonic_eol_deprecation_policy.md#6-what-a-release-plan-contains).
- No feature is removed without component owner sign-off.
- The three platform removals, which are 7.1.1 Nephos, 7.1.2 Barefoot, and 7.1.4 standalone P4, go to the TSC in addition to HLD review. The TSC decision is what settles them.
- A user who never enabled any of these features sees no functional change and no CLI change.
- Every removal that touches configuration is accompanied by a `db_migrator.py` update, so that a device that upgrades does not carry dead config or point at a value that no longer exists. See section 9.3.
- Each supported CI platform still builds after the removals, and no remaining container points at a deleted base.

Out of scope for this plan:

- The removals themselves. This document is documentation only, and each removal is a separate pull request.
- The standing process, which is the policy document.
- Anything under section 14, which needs code porting this plan does not cover.

### 6. Architecture Design

There is no change to the SONiC architecture. Every candidate below removes a component, a build rule, or a platform, and nothing is added. None of these features is a SONiC Application Extension, so the Application Extension infrastructure is not involved.

One candidate narrows an existing choice rather than deleting a leaf:

- 7.1.5 collapses the routing stack to FRR alone. `rules/config` already documents `frr` as the sole supported value of `SONIC_ROUTING_STACK`, and neither alternative has been buildable for years, so this deletes unreachable branches rather than changing which stack runs.

### 7. High-Level Design

These are built-in SONiC features rather than Application Extensions. The repositories that change are `sonic-buildimage` for the platforms, containers, build rules, and pipeline jobs, `sonic-swss` for the DTEL orchestration agent code, `sonic-utilities` for `db_migrator.py` and the routing CLI, and `sonic-restapi`, which is removed outright in 202711. No new module or interface is introduced, and no sequence diagram applies, because nothing new runs.

Each candidate below stands on its own. It states what the feature is, why it should go, the paths to remove, and anything to watch out for.

Three of these are platform removals, which are 7.1.1 Nephos, 7.1.2 Barefoot, and 7.1.4 standalone P4. Those go to the TSC under step 4 of the policy, separately from the rest of this list.

#### 7.1 Remove now

##### 7.1.1 Nephos platform

The Nephos and MediaTek switch silicon vendor left the market around 2019. The platform is about 2.3 MB across 166 files, and there is no `device/nephos` tree at all, so no shipping device selects it.

Nothing builds it, so nothing tests it. There is a `nephos` entry in the default `jobGroups` of `.azure-pipelines/azure-pipelines-build.yml`, but no pipeline instantiates it, so the entry is itself dead wiring. See 7.1.2 for how that is determined, since Barefoot is in the same position.

Every commit touching `platform/nephos/` for years has been a tree-wide sweep rather than work on the platform, the most recent being build-cache dependency tracking in August 2026, and before that the supervisor exit listener, per-ASIC warmboot, and mirror URL changes.

**Remove:**

- `platform/nephos/`
- the `nephos` job group in `.azure-pipelines/azure-pipelines-build.yml`

##### 7.1.2 Barefoot / Tofino platform

Intel has ended the Tofino line. The platform is roughly 7.8 MB across 880 files, and it pulls in the Barefoot SAI, saithrift, the `docker-syncd-bfn` and `docker-saiserver-bfn` containers, and the ODM sub-platforms built on Tofino.

Nothing builds it, so nothing tests it, and this is worth stating precisely because there is a `barefoot` entry in the default `jobGroups` of `.azure-pipelines/azure-pipelines-build.yml` that makes it look otherwise. Nothing instantiates that entry. The pull request gate in `azure-pipelines.yml` passes its own job groups, which are vs, vpp, alpinevs, broadcom, mellanox, marvell-prestera on arm64 and armhf, nvidia-bluefield, and aspeed-arm64. Official builds go through `.azure-pipelines/official-build.yml`, which passes `jobFilters: none`, and `azure-pipelines-job-groups.yml` then emits a group only when the pipeline definition name ends with that group's name. The definitions that exist are the ones the badges in `README.md` point at, which are broadcom, mellanox, marvell-teralynx, and marvell-prestera on armhf and arm64. There is no `Azure.sonic-buildimage.official.barefoot`, and none of the release branches has one either.

The same reasoning covers `nephos` in 7.1.1, and the dead job group entries go with each platform.

The device folders are listed individually below rather than by vendor, because most of these vendors also ship non-Tofino platforms. The list is every folder whose `platform_asic` file reads `barefoot`, which is fourteen of them today, and it is worth re-deriving that way at removal time rather than trusting this list.

**Remove:**

- `platform/barefoot/`
- the whole `device/barefoot/` tree, which is `x86_64-accton_as9516_32d-r0`, `x86_64-accton_as9516bf_32d-r0`, `x86_64-accton_wedge100bf_32x-r0`, and `x86_64-accton_wedge100bf_65x-r0`
- `device/accton/x86_64-accton_wedge100bf_32qs-r0`
- `device/arista/x86_64-arista_7170_32c`, `x86_64-arista_7170_32cd`, `x86_64-arista_7170_64c`, and `x86_64-arista_7170b_64c`
- `device/ingrasys/x86_64-ingrasys_s9280_64x-r0`, which is the only Tofino platform Ingrasys ships. The rest of `device/ingrasys/` stays.
- `device/netberg/x86_64-netberg_aurora_610-r0`, `x86_64-netberg_aurora_710-r0`, and `x86_64-netberg_aurora_750-r0`
- `device/wnc/x86_64-wnc_osw1800-r0`
- the `barefoot` job group in `.azure-pipelines/azure-pipelines-build.yml`
- the `barefoot` filter in `rules/docker-platform-monitor.mk`

##### 7.1.3 DTEL (data-plane telemetry)

DTEL is SONiC's in-band data-plane telemetry. In practice it only ever ran on Barefoot Tofino, and that platform is EOL and is being removed in 7.1.2. With the only hardware that ran it gone, the DTEL code in the orchestration agent is dead, and that is the whole of the argument for removing it.

TAM is the intended successor for in-band telemetry and drop monitoring, and its HLD is in review as sonic-net/SONiC#2094, alongside #2344 and #2379 in the same area. None of it has merged, so nothing in the tree covers DTEL's function today. This candidate does not wait on TAM, because the case here is that the hardware is gone rather than that a replacement has arrived.

**Remove:**

- `src/sonic-swss/orchagent/dtelorch.{cpp,h}`
- the DTEL table set and its initialization in `src/sonic-swss/orchagent/orchdaemon.cpp`
- the DTEL handling in `src/sonic-swss/orchagent/aclorch.{cpp,h}`
- the DTEL CONFIG_DB tables. There is no `sonic-dtel` YANG model in the tree, so nothing to remove there.
- `src/sonic-swss/tests/test_dtel.py`

##### 7.1.4 Standalone P4 platform

This is the old bmv2 software behavioral model. It is a reference target rather than real hardware, and it has been dead since roughly 2022. Nothing in CI builds it. It is about 12 MB across 920 files, and it pulls in four stale external submodules. The only thing that references it outside `platform/p4/` is a Debian 8 era TODO in `rules/redis.mk`.

**Remove:**

- `platform/p4/`, which includes `docker-sonic-p4`, `sai-p4-bm`, `p4c-bm`, `tenjin`, and `p4-hlir`
- the four P4 submodule entries in `.gitmodules`, which are `platform/p4/p4c-bm/p4c-bm`, `platform/p4/p4-hlir/p4-hlir`, `platform/p4/p4-hlir/p4-hlir-v1.1`, and `platform/p4/SAI-P4-BM`
- the jessie-era TODO in `rules/redis.mk`, which is the only reference to this platform outside `platform/p4/`

**Keep:**

- `rules/p4lang.mk`. The p4lang toolchain it builds, which is bmv2, p4c, and PI, is a live dependency of DASH SAI through `rules/dash-sai.mk`, and of `platform/vs/docker-ptf.mk` and `platform/vs/docker-ptf-sai.mk`.

##### 7.1.5 GoBGP and Quagga routing stacks

FRR is the only routing stack SONiC supports. `rules/config` already documents `frr` as the sole supported value of `SONIC_ROUTING_STACK`. Even so, both the build and the CLI still carry the machinery to elect GoBGP or Quagga instead, and that selectable-stack machinery is what this candidate removes.

GoBGP had its image build rules deleted back in 2021, so it has not been buildable as an image since then. Even so, every build still compiles a 2017 era Go GOBGP package that nothing installs. Quagga left even earlier. Its container and build rules are long gone, but the branches that would select it were never cleaned up, so the build glue, the CLI, and the sudoers policy still carry a Quagga path that cannot be reached. Removing both loses nothing, because FRR provides all of it. Once they are gone, every routing-stack conditional collapses to a single path, and `get_routing_stack()` has only one possible answer, so the runtime detection that shells out to `docker ps` can go with it.

The target here is stack selection rather than the word Quagga. FRR is itself a fork of Quagga, so Quagga-derived names legitimately survive in FRR-sourced code, including the whole of `src/sonic-frr/`, its `_QUAGGA_*` header guards, and the `fpm.h` that fpmsyncd carries. Those are upstream names and they stay.

Where a Quagga-named file turns out to be the live FRR implementation, rename it rather than delete it. `clear/bgp_quagga_v4.py` is the clear case, because the `frr` branch of `clear/main.py` imports it and there is no `clear/bgp_frr_v4.py`, which makes it the working implementation of `clear ip bgp` today.

**Remove (GoBGP):**

- `dockers/docker-fpm-gobgp/`, `src/gobgp/`, `rules/gobgp.mk`, and `rules/gobgp.dep`

**Remove (stack selection in the build):**

- `rules/docker-fpm.mk` and `rules/docker-fpm.dep`, which exist only to elect a stack. `DOCKER_FPM_FRR` can be referenced directly, and the dead `DOCKER_FPM_GOBGP` and `DOCKER_FPM_QUAGGA` names go with them.
- the `else` branch that adds `$(GOBGP)` in `platform/vs/docker-sonic-vs.mk`
- the `SONIC_ROUTING_STACK` conditionals in `slave.mk` and `files/build_templates/sonic_debian_extension.j2`, whose FRR blocks become unconditional
- the commented-out `ROUTING_STACK` selection in `platform/p4/docker-sonic-p4.mk`, which goes with 7.1.4 in any case

**Remove (stack selection in the CLI), all in sonic-utilities:**

- the `routing_stack == "quagga"` branches of `show/main.py` and `clear/main.py`
- `show/bgp_quagga_v4.py`, `show/bgp_quagga_v6.py`, and `clear/bgp_quagga_v6.py`
- the non-frr `else` branches carrying the Quagga `bgp` and `zebra` groups in `debug/main.py` and `undebug/main.py`
- the `/etc/quagga/bgpd.conf` branch of `show startupconfiguration bgp`, and the matching `docker exec bgp cat /etc/quagga/bgpd.conf` entry in `files/image_config/sudoers/sudoers`
- the cases exercising the removed branches in `tests/show_test.py`, `tests/clear_test.py`, and `tests/debug_test.py`

**Rename:**

- `src/sonic-utilities/clear/bgp_quagga_v4.py` to `clear/bgp_frr_v4.py`, updating the import in `clear/main.py`

**Keep:**

- `SONIC_ROUTING_STACK = frr` in `rules/config` as a single-value knob, because downstream `rules/config.user` files may still set it

Comments that only mention Quagga in passing, such as the `docker-fpm.gz` line in `README.md`, the `## Quagga rules` header in `files/image_config/rsyslog/rsyslog.d/00-sonic.conf.j2`, and the "For quagga build" comments in the sonic-slave Dockerfiles, are worth correcting when the code around them is touched, but they are not the point of this candidate. The packages under that build comment, such as `libreadline-dev`, `libpam-dev`, and the texlive set, are FRR build dependencies now, so leave them alone.

##### 7.1.6 Python 2 packages

Both packages are gated behind `ENABLE_PY2_MODULES`, which is off for bullseye, bookworm, and trixie. As a result, neither is built on any current release, so both are dead weight. The py3 version of swsssdk is a separate matter, because it is still in use. It is out of scope here and is noted under Additional findings.

**Remove:**

- `rules/swsssdk-py2.mk` and `rules/swsssdk-py2.dep`
- `rules/redis-dump-load-py2.mk` and `rules/redis-dump-load-py2.dep`
- the `SWSSSDK_PY2` dependency lines in `rules/sonic-py-common.mk` and `rules/swsssdk-py3.mk`

##### 7.1.7 Kubernetes master

This runs a full Kubernetes control plane on the switch. That includes the apiserver, controller, scheduler, proxy, etcd 3.5.0, coredns 1.8.4, and the dashboard 2.7.0 web UI, along with cloud credential libraries used for backups. Every one of those versions is years past end of life, which makes this the single biggest reduction in CVE surface in this list. It is off by default and has no real CI coverage.

This applies to the master only. The worker feature (`INCLUDE_KUBERNETES`) is a separate feature and should stay. Someone hardened its cluster-join security before this working group existed, which points to a real user.

**Remove:**

- `files/image_config/kubernetes/`, which is `kubernetes_master_entrance.sh`, `kubernetes_master_entrance.service`, and `kubernetes.list`
- the `INCLUDE_KUBERNETES_MASTER` flag in `rules/config`, and the `MASTER_*` version pins beside it, which are `MASTER_KUBERNETES_VERSION`, `MASTER_KUBERNETES_CONTAINER_IMAGE_VERSION`, `MASTER_PAUSE_VERSION`, `MASTER_COREDNS_VERSION`, `MASTER_ETCD_VERSION`, `MASTER_CRI_DOCKERD`, `MASTER_UI_METRIC_VERSION`, and `MASTER_UI_DASH_VERSION`
- the `include_kubernetes_master` blocks in `files/build_templates/sonic_debian_extension.j2`
- `src/sonic-yang-models/yang-models/sonic-kubernetes_master.yang`
- the `K8S_MASTER_CHANGED` master image build in `.azure-pipelines/azure-pipelines-build.yml`

**Keep:**

- `INCLUDE_KUBERNETES`, which is the worker and a separate feature
- `src/sonic-ctrmgrd*` and the `ctrmgrd` wrapper, which runs for ordinary feature start and stop rather than only for k8s

##### 7.1.8 docker-basic_router

This is a SAI demo and reference container. It is not wired into any build rule, it never ships in an image, and it is not in CI. Its last real change was in 2020, and nothing uses it.

**Remove:**

- `dockers/docker-basic_router/`

##### 7.1.9 System Telemetry container

This container is off by default, and it is redundant. Both this container and the gnmi container run the same binary, `/usr/sbin/telemetry`, started by `telemetry.sh` and `gnmi-native.sh` respectively. There is no separate gNMI server. The `telemetry` binary is the server, and the name is only historical. Both containers read the same `TELEMETRY|gnmi` config, and the gnmi start script simply adds ZMQ and VRF options on top. There is therefore no functional gap, because Get, Set, Subscribe, and dial-out are identical in both.

**Remove:**

- `dockers/docker-sonic-telemetry/`
- `rules/docker-telemetry.mk` and `rules/docker-telemetry.dep`
- the `INCLUDE_SYSTEM_TELEMETRY` flag in `rules/config`

**Keep:**

- the `telemetry` binary, which is built by sonic-gnmi and run by the gnmi container through `gnmi-native.sh`

##### 7.1.10 End-of-life Debian bases

Debian 8 (jessie), Debian 9 (stretch), Debian 10 (buster), and Debian 11 (bullseye) are all out of support. Bullseye leaves Debian LTS in August 2026, which is before 202611 ships, so it belongs with the rest rather than in a later cycle. The risk in every case is the same, which is that someone builds a new container on a base that no longer gets security updates.

jessie, stretch, and buster are pure leftovers, because nothing builds on them. Bullseye is different, because containers still build on it today, so those have to move first. Before deleting any base, confirm that nothing still builds a container on it. Debian 12 (bookworm) is still a live base and is handled under Deprecate.

**Remove (stretch):**

- `dockers/docker-base-stretch/` and `rules/docker-base-stretch.{mk,dep}`
- `dockers/docker-config-engine-stretch/` and `rules/docker-config-engine-stretch.{mk,dep}`

**Remove (buster):**

- `dockers/docker-base-buster/` and `rules/docker-base-buster.{mk,dep}`
- `dockers/docker-config-engine-buster/` and `rules/docker-config-engine-buster.{mk,dep}`
- `dockers/docker-swss-layer-buster/` and `rules/docker-swss-layer-buster.{mk,dep}`

**Remove (jessie):**

- `sonic-slave-jessie/`
- the `jessie` target in `Makefile`, and the jessie `SLAVE_DIR` branch in `Makefile.work`
- jessie has no `docker-base-jessie`, so check the jessie strings in the generic `dockers/docker-base/` first, meaning its armhf and arm64 sources and its `FROM ...:jessie` lines, before touching that container

**Move first (bullseye).** Seven containers still build on a bullseye base. Two of them, `docker-syncd-bfn` and `docker-saiserver-bfn`, go away with Barefoot in 7.1.2. The other five have to move to bookworm or trixie before bullseye can go:

- `docker-syncd-centec` and `docker-saiserver-centec` under `platform/centec/`
- `docker-syncd-centec` and `docker-saiserver-centec` under `platform/centec-arm64/`
- `dockers/docker-sonic-sdk/`

The centec containers reach bullseye through `platform/template/docker-syncd-bullseye.mk`, so pointing their `docker-syncd-centec.mk` at the bookworm or trixie template covers four of the five.

**Remove (bullseye):**

- `dockers/docker-base-bullseye/` and `rules/docker-base-bullseye.{mk,dep}`
- `dockers/docker-config-engine-bullseye/` and `rules/docker-config-engine-bullseye.{mk,dep}`
- `dockers/docker-swss-layer-bullseye/` and `rules/docker-swss-layer-bullseye.{mk,dep}`
- `platform/template/docker-syncd-bullseye.mk` and `sonic-slave-bullseye/`
- in `Makefile`, the `bullseye` target and the `NOBULLSEYE` and `BUILD_BULLSEYE` handling
- the bullseye `SLAVE_DIR` branch in `Makefile.work`, and the `sonic-slave-bullseye` entry in `Makefile.cache`
- in `slave.mk`, the `BULLSEYE_DEBS_PATH` and `BULLSEYE_FILES_PATH` variables, the `bullseye` target, and the `BLDENV` tests that name it
- the `BLDENV == bullseye` conditionals in `rules/grpc.mk`, `rules/protobuf.mk`, `rules/sonic-dash-api.mk`, and `rules/sonic-fips.mk`

#### 7.2 Deprecate now, remove later

##### 7.2.1 Bookworm base containers

This should be removed in 202705. Bookworm is Debian 12. Its regular security support ends in 2026, which leaves LTS only, and trixie is the current base. It is a live base with more on it than bullseye has, so it deserves a cycle of notice rather than immediate removal.

Five containers build on bookworm today, and all five move to trixie before the base can go:

- `platform/vs/docker-sonic-vs`, which takes `docker-swss-layer-bookworm` directly. This is the virtual switch image the community tests with, so it is the one to move first and the one most likely to surface problems.
- `platform/cisco/docker-syncd-cisco` and `platform/cisco/docker-gbsyncd-cisco`, both `FROM docker-config-engine-bookworm`
- `platform/alpinevs/docker-syncd-vs` and `platform/nokia-vs/docker-syncd-vs`, which reach it through `platform/template/docker-syncd-bookworm.mk`

`docker-syncd-pensando` is not among them, despite what an earlier draft of this plan said. It is already on trixie, through `platform/template/docker-syncd-trixie.mk`.

**Remove (202705):**

- `dockers/docker-base-bookworm/` and `rules/docker-base-bookworm.{mk,dep}`
- `dockers/docker-config-engine-bookworm/` and `rules/docker-config-engine-bookworm.{mk,dep}`
- `dockers/docker-swss-layer-bookworm/` and `rules/docker-swss-layer-bookworm.{mk,dep}`
- `platform/template/docker-syncd-bookworm.mk` and `sonic-slave-bookworm/`
- in `Makefile`, the `bookworm` target and the `NOBOOKWORM` and `BUILD_BOOKWORM` handling
- the bookworm `SLAVE_DIR` branch in `Makefile.work`

##### 7.2.2 FRR split and split-unified config modes

Both should be removed in 202705. These are the two manual routing modes, where SONiC renders no FRR config at all and the operator writes it by hand, as per-daemon files under `split` and as a single `frr.conf` under `split-unified`. The other two values of `docker_routing_config_mode`, which are `separated` and `unified`, generate the config from CONFIG_DB and are not touched by this candidate.

They share a real problem. The bgp container runs supervisord rather than systemd, so FRR cannot hot-reload, and any change to the hand-written config forces a full FRR restart that drops BGP sessions. That makes both impractical for production, so it is doubtful anyone serious runs either. `split` has a second problem of its own, which is that FRR no longer writes per-daemon files. Since the move to `mgmtd`, `write memory` updates only the integrated config, and FRR's own documentation calls per-daemon files a transition mechanism to be removed once a user has moved off them. An operator running `split` therefore cannot save the running config back to the files they manage.

Neither mode is as separate from CONFIG_DB as its description suggests. supervisord starts bgpcfgd in every mode, because nothing in the container consults `docker_routing_config_mode` to decide, so a box in a split mode still has bgpcfgd pushing whatever BGP state CONFIG_DB holds. It is a no-op in practice only because such a box has no BGP tables filled in.

Before removing them, name where an operator who manages their own FRR config is expected to go. `unified` is the intended destination, but it is not a drop-in one today. Its bgpcfgd template renders no `fpm address` line, and zebra's `dplane_fpm_sonic` module does not connect without one, so that gap is closed first.

**Change (202705):**

- remove the `split` and `split-unified` branches in `dockers/docker-fpm-frr/docker_init.sh`, along with the `write_default_zebra_config` helper, which has no other caller
- drop `split-unified` from the `vtysh_b` condition in `dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.common.j2`
- narrow the `docker_routing_config_mode` pattern in `src/sonic-yang-models/yang-models/sonic-device_metadata.yang` from `separated|unified|split|split-unified` to `separated|unified`, and drop the two descriptions above it

##### 7.2.3 REST API

This should be removed in 202711. It is off by default in `rules/config`, though that is not the whole picture: the pull request pipeline sets `INCLUDE_RESTAPI: y` for the broadcom and marvell-prestera-armhf job groups, so community builds for those platforms do carry it, and `init_cfg.json.j2` has a broadcom-specific enable path on top. Its own spec calls it the "SONiC REST API for Baremetal Scenarios." It is an imperative agent for baremetal VNET, VXLAN, and VLAN config over HTTPS, not a general REST interface. gNMI is the intended replacement, but it does not cover two things. The first is bulk route programming with per-route partial success (HTTP 207). The second is route expiry, which is timed route aging. Because of that gap, this candidate gets the longest runway. Before removing it, confirm that no control plane still drives it.

This candidate is `sonic-restapi` and nothing else. **RESTCONF is not affected and is not going away.** The two are separate servers in separate repositories, and the names are close enough that it is worth being explicit about which is which.

`sonic-restapi` is a hand-written imperative API. Its routes are `/v1/config/interface/vlan/{vlan_id}`, `/v1/config/tunnel/encap/vxlan/{vnid}`, `/v1/config/vrouter/{vnet_name}/routes` and the like, defined in `src/sonic-restapi/sonic_api.yaml` and served by `src/sonic-restapi/go-server-server/`. It is off by default and it is what this candidate removes. There is no RESTCONF anywhere in that repository.

RESTCONF is implemented in the management framework, in `src/sonic-mgmt-framework/rest/server/restconf.go`, which serves `/restconf/data/`, `/restconf/operations/`, `yang-library-version` and the `ietf-restconf-monitoring` capabilities over `application/yang-data+json`. It is YANG driven through `src/sonic-mgmt-common/`, it listens on 443 rather than 8081, and it ships enabled by default, because `INCLUDE_MGMT_FRAMEWORK = y` in `rules/config`.

RESTCONF is kept, but it is not a replacement for this API either, and it is worth saying so before anyone assumes it is. The management framework serves openconfig-acl, openconfig-interfaces with if-ethernet and if-ip, openconfig-lldp, openconfig-platform, openconfig-sampling-sflow, openconfig-system, the gnsi models, and sonic-acl, sonic-interface, sonic-port and sonic-show-techsupport, backed by translib apps for ACL, LLDP, platform and system in `src/sonic-mgmt-common/translib/`. None of the tables this API writes is modelled there, and those are `VNET`, `VXLAN_TUNNEL`, `VNET_ROUTE_TUNNEL`, `VLAN`, `VLAN_MEMBER`, `VLAN_INTERFACE`, `NEIGH`, and `STATIC_ROUTE`. Reaching them through RESTCONF would mean writing new YANG models and new translib apps, which is more work than the removal itself.

gNMI reaches them without new models, because its Set writes CONFIG_DB rows directly rather than through a per-table model, in `MixedDbClient.Set` in `src/sonic-gnmi/sonic_data_client/mixed_db_client.go`. That is why gNMI, and not RESTCONF, is named as the replacement above.

Neither closes the two gaps. The bulk route PATCH returns `http.StatusMultiStatus` per element in `src/sonic-restapi/go-server-server/go/default.go`, and route expiry is a server-side timer backed by the `STATIC_ROUTE_EXPIRY_TIME` table, reached through `/v1/config/vrf/route_expiry`. RESTCONF has no per-item partial success, because the management framework does not implement YANG Patch, and it has no notion of an expiring entry. Whoever drives this API today needs an answer for both before it goes.

**Keep,** none of which this candidate touches:

- `src/sonic-mgmt-framework/` and `src/sonic-mgmt-common/`
- `dockers/docker-sonic-mgmt-framework/`
- `rules/docker-sonic-mgmt-framework.{mk,dep}`, `rules/sonic-mgmt-framework.{mk,dep}`, and `rules/sonic-mgmt-common.{mk,dep}`
- the `INCLUDE_MGMT_FRAMEWORK` flag in `rules/config`, which is `y`
- the `mgmt-framework` feature in `files/build_templates/init_cfg.json.j2`

**Remove (202711):**

- `dockers/docker-sonic-restapi/`
- `src/sonic-restapi/` and its `.gitmodules` entry
- `rules/docker-restapi.{mk,dep}` and `rules/restapi.{mk,dep}`
- the `INCLUDE_RESTAPI` flag in `rules/config`
- the `restapi` feature in `files/build_templates/init_cfg.json.j2`
- the `INCLUDE_RESTAPI: y` overrides in the broadcom and marvell-prestera-armhf job groups in `azure-pipelines.yml`

### 8. SAI API

There is no change to the SAI API. Nothing here adds, removes, or modifies a SAI API or object, and silicon vendors have nothing to implement for this plan.

Two candidates touch SAI adjacent code without changing the interface. 7.1.2 removes the Barefoot SAI implementation and saithrift wiring for a platform that is EOL, which is a vendor implementation rather than the API. 7.1.3 removes the orchestration agent code that calls the SAI DTEL APIs, which leaves those APIs in SAI itself untouched and simply stops SONiC from calling them.

### 9. Configuration and management

Removing a feature drops its `FEATURE` table entries, its build flags, and any YANG models tied to it. Users who never enabled these features see no CLI change.

#### 9.1 Manifest

Not applicable. None of these features is a SONiC Application Extension, so there is no manifest.

#### 9.2 CLI/YANG model Enhancements

No command is added, and no command changes its syntax. The changes are deletions and one default.

YANG models removed with their features:

- `src/sonic-yang-models/yang-models/sonic-kubernetes_master.yang`, with 7.1.7. This is the only YANG model this batch removes.
- DTEL, with 7.1.3, drops CONFIG_DB tables but no model, because it never had one.

CLI effects:

- Collapsing the routing stack to FRR in 7.1.5 does not change any command an operator runs, because the FRR branch of every affected command already provides the same CLI. `clear ip bgp` keeps working through the renamed `clear/bgp_frr_v4.py`. The one visible difference is `show startupconfiguration bgp`, which loses its `/etc/quagga/bgpd.conf` branch and reads only `/etc/frr/bgpd.conf`.

`sonic-utilities/doc/Command-Reference.md` carries more Quagga material than the code does, and it is updated in the same pull request as 7.1.5. That means the whole `## Quagga BGP Show Commands` section and its entry in the table of contents, the `Versions <= 201811 using Quagga routing stack` variants and the links to them under the BGP show commands, and the `## Routing Stack` section, which still tells the reader that SONiC is agnostic of the routing stack and that Quagga is a choice. The `show startupconfiguration bgp` entry loses its Quagga path with the code. Nothing in the reference describes the other candidates, because the Kubernetes commands documented there belong to the worker feature, which stays.

#### 9.3 Config DB Enhancements

Removing the code is only half of it, because a device that upgrades keeps whatever it already had in CONFIG_DB. Every removal that touches configuration therefore has to update `sonic-utilities/scripts/db_migrator.py`, and that update is part of the removal rather than a follow-up. Without it, an upgraded device carries dead `FEATURE` rows and orphaned tables forever, and a table that outlives its YANG model can fail config validation.

The shape of the change is the same each time. Add a new `version_<branch>_<build>` method chained onto the current tail of the version chain, bump `CURRENT_VERSION` to it, which is `version_202605_01` today, and drop the state that is going away with `delete_table` or with entry deletion. What this batch needs:

- The `KUBERNETES_MASTER` table, which goes with 7.1.7, along with its YANG model.
- The DTEL tables, which go with 7.1.3.
- `FEATURE|telemetry`, which goes with 7.1.9. `FEATURE|gnmi` stays, and the two must not be confused, because the surviving container is the gnmi one.
- `FEATURE|restapi`, when the REST API is removed in 202711 under 7.2.3, which lands in that release's migrator rather than this one.
- `DEVICE_METADATA|localhost|docker_routing_config_mode`, when the split modes are removed in 202705 under 7.2.2. A device holding `split` or `split-unified` is migrated to a value that still exists, and this lands in that release's migrator rather than this one.

### 10. Warmboot and Fastboot Design Impact

There is no warmboot or fastboot impact. Every candidate is off by default, already dead, or specific to hardware that is being removed. None of this touches the warmboot or fastboot path on supported platforms.

#### Warmboot and Fastboot Performance Impact

There is no degradation, and the direction of every change is downward.

- No stall, sleep, or IO operation is added to the boot critical chain. Code is deleted from it, not added.
- No CPU heavy processing is added. Nothing here renders a template, starts a process, or does work of any kind in the boot path that was not already there.
- No third party dependency is bumped for a device that ships today. The base image moves in 7.1.10 and 7.2.1 change which Debian base a container is built from, and the containers involved are the centec syncd and saiserver containers and `docker-sonic-sdk`. Those are build time changes, and the platforms that own them validate boot time as part of the move.
- Nothing here needs to be delayed, because nothing here starts.

### 11. Memory Consumption

No memory is added. Every candidate is a removal, so runtime memory either drops or is unchanged, and image size drops.

The features that carried a running process are off by default today, so a device that never enabled them frees nothing at runtime and simply stops carrying the code. A device that did enable the System Telemetry container (7.1.9) or the Kubernetes master (7.1.7) frees whatever those processes used, and in the telemetry case the same functionality continues in the gnmi container, which is already running the same binary.

### 12. Restrictions/Limitations

- Bullseye cannot be removed until five containers move off it, which are the centec syncd and saiserver containers under `platform/centec/` and `platform/centec-arm64/`, and `dockers/docker-sonic-sdk/`. That move is a prerequisite of 7.1.10 rather than part of it, and it depends on the platform owners.
- The same applies to bookworm in 7.2.1, where three syncd containers have to move to trixie first.
- gNMI does not fully replace the REST API. It does not cover bulk route programming with per-route partial success (HTTP 207), and it does not cover route expiry. That gap is why 7.2.3 gets the longest runway, and it is not closed by this plan.
- Removing a feature that is off by default is not proof that nobody runs it. The notification steps in the policy exist for that reason, and a verdict can move to **Keep** at any point before the removal lands.

### 13. Testing Requirements/Design

Each removal is tested in the pull request that performs it, rather than here. The requirements below apply to that pull request and to the release as a whole.

#### 13.1 Unit Test cases

- `db_migrator` unit tests cover each table and field this batch drops, starting from a `config_db.json` that still carries them.
- The `sonic-swss` test suite still passes with `tests/test_dtel.py` and the DTEL orchestration agent code removed.
- YANG model tests pass with the removed models absent, and no remaining model references them.

#### 13.2 System Test cases

- Each supported CI platform still builds after the removals.
- The removed packages no longer appear in the SBOM or the CVE scan, confirmed by an image diff.
- BGP comes up and programs routes after the routing-stack collapse in 7.1.5, in whichever `docker_routing_config_mode` the device already runs.
- A `config_db.json` from the previous release migrates cleanly, with no leftover tables for removed features and no config validation errors against the reduced YANG model set.
- Every remaining container builds with nothing pointing at a deleted base, and the centec and sonic-sdk containers build on their new base.
- `show ip bgp` and `clear ip bgp` still work after the routing-stack collapse and the `clear/bgp_frr_v4.py` rename.
- gNMI still serves Get, Set, Subscribe, and dial-out after the System Telemetry container is removed.

### 14. Open/Action items

- Component owner sign-off is outstanding for every candidate. No removal lands without it.
- The three platform removals need a TSC decision, which is step 4 of the policy.
- The five bullseye containers and the three bookworm containers need an owner to move them to a newer base, as described in section 12.
- **FRR config modes were considered and dropped.** An earlier draft proposed removing the `separated` and `split` values of `docker_routing_config_mode` as dead code, on the grounds that FRR 10.5 had dropped per-daemon config files. That is not what happened. FRR still reads per-daemon files, and since FRR 9.0 `mgmtd` reads them on behalf of the daemons that moved to it, which are zebra, staticd, ripd, and ripngd. `separated` is the default that `minigraph.py` sets and it works. The candidate is recorded here so that a later cycle does not repeat the mistake. What survived the check is 7.2.2, which deprecates the two modes where SONiC generates no config at all, and which carries the prerequisite for any later consolidation on `unified`.
- **swsssdk-py3.** This is the old Python Redis SDK. `swsscommon` replaces it, but code still imports `swsssdk` at runtime, including `sonic-utilities/scripts/dualtor_neighbor_check.py`, `sonic-py-common`, and the vpp container. It cannot be deprecated until those are ported to `swsscommon`, so it is not a candidate in this plan. It is recorded here so that a later cycle picks it up.
