# SONiC EOL and Deprecation Plan for 202611

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Why remove code](#5-why-remove-code)
- [6. Process](#6-process)
- [7. Candidates for 202611](#7-candidates-for-202611)
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
- [8. Config and management impact](#8-config-and-management-impact)
- [9. Warmboot/Fastboot impact](#9-warmbootfastboot-impact)
- [10. Testing](#10-testing)
- [11. Additional findings](#11-additional-findings)

### 1. Revision

| Rev | Date | Author | Change |
|-----|------|--------|--------|
| 0.1 | 2026-07-19 | Brad House (Nexthop) | First draft. Security WG. |
| 0.2 | 2026-07-24 | Brad House (Nexthop) | Added the Keep verdict. Moved bullseye to immediate removal and deprecated bookworm in its place. Folded Quagga into the GoBGP removal. |
| 0.3 | 2026-07-24 | Brad House (Nexthop) | Filled in the notification steps of the process, which are the mailing list, the working groups, the TSC for platform removals, and a second round before the branch date. |

### 2. Scope

This HLD does two things:

1. It sets up a repeatable, per-release process to deprecate and remove SONiC features.
2. It lists the features we propose to act on in 202611.

The work comes from the SONiC Security Working Group, whose goal is to shrink the attack surface. Less code means fewer packages, fewer CVEs, and less to build and test.

Releases ship twice a year, in November (`YYYY11`) and in May (`YYYY05`). The cycles referenced here are 202611 (November 2026), 202705 (May 2027), and 202711 (November 2027).

### 3. Definitions/Abbreviations

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

This HLD proposes a standing process to retire those features, along with the first batch to act on.

### 5. Why remove code

- The best fix for a CVE is to delete the code that carries it.
- Unmaintained code is a standing risk, because it rarely gets patched.
- Dead build wiring hides real problems and slows builds.
- Fewer features mean a smaller image, fewer scans to triage, and less CI.

### 6. Process

This section is the boilerplate for the deprecation cycle itself. It is meant to carry forward unchanged into the plan for each following release, so that only the candidate list in section 7 changes from one cycle to the next.

For each release:

1. **Propose.** File or update this HLD with candidates. Each candidate states what it is, what replaces it, the gap in what you lose, and a verdict.
2. **Pick a verdict.** There are three:
   - **Remove now:** dead, broken, or EOL with no real users. Delete it this cycle.
   - **Deprecate now, remove later:** still has possible users or needs migration work. Name a removal release.
   - **Keep:** the feature stays. Review turned up real usage, a dependency another feature relies on, or a gap that the proposed replacement does not cover.
3. **Review.** The community reviews it, and this HLD is scheduled at the weekly HLD review on Tuesdays. Component owners sign off. A feature is not removed without owner sign-off. Review can change a verdict in either direction, and moving a candidate to **Keep** is a normal outcome rather than a failure of the process. When that happens, record what the review turned up and why the feature stays, so that a later cycle does not have to rediscover it.
4. **Take platform removals to the TSC.** Platforms are special, because a platform is somebody's hardware and the people who own it are not always the people who read HLDs. Every platform removal is proposed to the TSC in addition to the steps above, and the TSC can reject it. Owner sign-off does not substitute for that, and the TSC decision is what settles a platform removal.
5. **Notify the mailing list.** After HLD review, send the proposal to `sonic-dev@lists.sonicfoundation.dev`. Not everyone with a stake attends HLD review, and the mailing list is how the rest of them find out while there is still time to object. Include the full candidate list, the verdict for each one, the named removal release, and a date by which responses are wanted.
6. **Notify the interested working groups.** Send each candidate to the working group that owns the area it touches, where one exists. A working group knows its own users, so it is the fastest way to turn "we think nobody runs this" into a real answer. Reach the routing group for routing stack and FRR changes, the telemetry group for telemetry changes, the management group for management interface changes, and the platform and hardware groups for platform removals. Sending the same item to more than one group is fine and is better than missing one.
7. **Notify again before the branch date.** Every notification above goes out a second time, no later than two months before the release branch is cut, and revised for whatever the first round turned up. Anyone who has since changed a verdict says so in that second round. This gives a user who missed the first notice a last chance to speak up while there is still time to revert a removal.
8. **Announce.** Deprecations go in the release notes.
9. **Remove** in the named release.

The goal of steps 4 through 7 is to over-communicate. It costs little to send the same proposal to one more list or one more group, and it costs a great deal to remove something that a user turns out to depend on. Nobody should learn that a feature is gone from the release notes, or from their build breaking.

A few rules of thumb guide the calls above:

- "Not built by default" and "not in CI" are hints, not proof. We check real use before calling anything dead.
- A forced bump, such as a libyang, base image, submodule pointer, or mass format change, does not count as maintenance.
- If a replacement has a gap, we name it so users can speak up.
- Silence is not consent on its own. It counts only after the notifications above have gone out twice and the second round has had time to draw a response.
- A removal that touches configuration is not finished until `db_migrator.py` cleans up what it leaves behind in CONFIG_DB. See section 8.

### 7. Candidates for 202611

Each candidate below stands on its own. It states what the feature is, why it should go, the paths to remove, and anything to watch out for.

Three of these are platform removals, which are 7.1.1 Barefoot, 7.1.3 standalone P4, and 7.1.4 Nephos. Those go to the TSC under step 4 of the process, separately from the rest of this list.

#### 7.1 Remove now

##### 7.1.1 Barefoot / Tofino platform

Intel has ended the Tofino line, and the platform is not in the CI build matrix (aspeed_arm64, broadcom, marvell-prestera, mellanox, nvidia_bluefield, vs, alpinevs, and vpp). Because nothing builds it, nothing tests it. The platform is roughly 7.7 MB across about 880 files, and it pulls in the Barefoot SAI, saithrift, the `docker-syncd-bfn` and `docker-saiserver-bfn` containers, and the ODM sub-platforms built on Tofino (Accton Wedge100BF, Arista 7170, Ingrasys, Netberg, and WNC).

**Remove:** `platform/barefoot/`; the Tofino `device/` folders (Accton Wedge100BF, Arista 7170, Ingrasys, Netberg, WNC); the `barefoot` job in `.azure-pipelines/azure-pipelines-build.yml`; the `barefoot` filter in `rules/docker-platform-monitor.mk`.

##### 7.1.2 DTEL (data-plane telemetry)

DTEL is SONiC's in-band data-plane telemetry. In practice it only ever ran on Barefoot Tofino, and that platform is EOL and is being removed in 7.1.1. With the only hardware that ran it gone, the DTEL code in the orchestration agent is dead. TAM, which was added in 202605, already covers the same need on current hardware.

**Remove:** `src/sonic-swss/orchagent/dtelorch.{cpp,h}`, the DTEL table set and initialization in `orchagent/orchdaemon.cpp`, and the DTEL handling in `orchagent/aclorch.{cpp,h}`; the DTEL CONFIG_DB tables and any `sonic-dtel` YANG model; `src/sonic-swss/tests/test_dtel.py`.

##### 7.1.3 Standalone P4 platform

This is the old bmv2 software behavioral model. It is a reference target rather than real hardware, and it has been dead since roughly 2022. Nothing in CI builds it. It is about 12 MB across 920 files, and it pulls in four stale external submodules. The only thing that references it outside `platform/p4/` is a Debian 8 era TODO in `rules/redis.mk`.

**Remove:** `platform/p4/` (which includes `docker-sonic-p4`, `sai-p4-bm`, `p4c-bm`, `tenjin`, and `p4-hlir`); the four P4 submodule entries in `.gitmodules` (`platform/p4/p4c-bm/p4c-bm`, `platform/p4/p4-hlir/p4-hlir`, `platform/p4/p4-hlir/p4-hlir-v1.1`, `platform/p4/SAI-P4-BM`); the stale TODO in `rules/redis.mk`.
**Keep:** `rules/p4lang.mk`. The p4lang toolchain it builds (bmv2, p4c, and PI) is a live dependency of DASH SAI, which ships in `sonic-vs.img.gz`, and of the PTF test containers.

##### 7.1.4 Nephos platform

The Nephos and MediaTek switch silicon vendor left the market around 2019. The platform is about 2.3 MB across 160 files. There is no `device/nephos` tree, there has been no genuine commit in years, and it is not in CI.

**Remove:** `platform/nephos/`; the `nephos` job in `.azure-pipelines/azure-pipelines-build.yml`.

##### 7.1.5 GoBGP and Quagga routing stacks

FRR is the only routing stack SONiC supports. `rules/config` already documents `frr` as the sole supported value of `SONIC_ROUTING_STACK`. Even so, both the build and the CLI still carry the machinery to elect GoBGP or Quagga instead, and that selectable-stack machinery is what this candidate removes.

GoBGP had its image build rules deleted back in 2021, so it has not been buildable as an image since then. Even so, every build still compiles a 2017 era Go GOBGP package that nothing installs. Quagga left even earlier. Its container and build rules are long gone, but the branches that would select it were never cleaned up, so the build glue, the CLI, and the sudoers policy still carry a Quagga path that cannot be reached. Removing both loses nothing, because FRR provides all of it. Once they are gone, every routing-stack conditional collapses to a single path, and `get_routing_stack()` has only one possible answer, so the runtime detection that shells out to `docker ps` can go with it.

The target here is stack selection rather than the word Quagga. FRR is itself a fork of Quagga, so Quagga-derived names legitimately survive in FRR-sourced code, including the whole of `src/sonic-frr/`, its `_QUAGGA_*` header guards, and the `fpm.h` that fpmsyncd carries. Those are upstream names and they stay.

Where a Quagga-named file turns out to be the live FRR implementation, rename it rather than delete it. `clear/bgp_quagga_v4.py` is the clear case, because the `frr` branch of `clear/main.py` imports it and there is no `clear/bgp_frr_v4.py`, which makes it the working implementation of `clear ip bgp` today.

**Remove (GoBGP):** `dockers/docker-fpm-gobgp/`, `src/gobgp/`, `rules/gobgp.mk`, and `rules/gobgp.dep`.
**Remove (stack selection in the build):** `rules/docker-fpm.mk` and `rules/docker-fpm.dep`, which exist only to elect a stack, so `DOCKER_FPM_FRR` can be referenced directly and the dead `DOCKER_FPM_GOBGP` and `DOCKER_FPM_QUAGGA` names go with them; the `else` branch that adds `$(GOBGP)` in `platform/vs/docker-sonic-vs.mk`; the `SONIC_ROUTING_STACK` conditionals in `slave.mk` and `files/build_templates/sonic_debian_extension.j2`, whose FRR blocks become unconditional; the commented-out `ROUTING_STACK` selection in `platform/p4/docker-sonic-p4.mk`, which goes with 7.1.3 in any case. Keep `SONIC_ROUTING_STACK = frr` in `rules/config` as a single-value knob, because downstream `rules/config.user` files may still set it.
**Remove (stack selection in the CLI):** in sonic-utilities, the `routing_stack == "quagga"` branches of `show/main.py` and `clear/main.py` along with `show/bgp_quagga_v4.py`, `show/bgp_quagga_v6.py`, and `clear/bgp_quagga_v6.py`; the non-frr `else` branches that carry the Quagga `bgp` and `zebra` groups in `debug/main.py` and `undebug/main.py`; the `/etc/quagga/bgpd.conf` branch of `show startupconfiguration bgp` and the matching `docker exec bgp cat /etc/quagga/bgpd.conf` entry in `files/image_config/sudoers/sudoers`; the cases that exercise the removed branches in `tests/show_test.py`, `tests/clear_test.py`, and `tests/debug_test.py`.
**Rename:** `src/sonic-utilities/clear/bgp_quagga_v4.py` to `clear/bgp_frr_v4.py`, and update the import in `clear/main.py`.

Comments that only mention Quagga in passing, such as the `docker-fpm.gz` line in `README.md`, the `## Quagga rules` header in `files/image_config/rsyslog/rsyslog.d/00-sonic.conf.j2`, and the "For quagga build" comments in the sonic-slave Dockerfiles, are worth correcting when the code around them is touched, but they are not the point of this candidate. The packages under that build comment, such as `libreadline-dev`, `libpam-dev`, and the texlive set, are FRR build dependencies now, so leave them alone.

##### 7.1.6 Python 2 packages

Both packages are gated behind `ENABLE_PY2_MODULES`, which is off for bullseye, bookworm, and trixie. As a result, neither is built on any current release, so both are dead weight. The py3 version of swsssdk is a separate matter, because it is still in use. It is out of scope here and is noted under Additional findings.

**Remove:** `rules/swsssdk-py2.mk`, `rules/swsssdk-py2.dep`, `rules/redis-dump-load-py2.mk`, and `rules/redis-dump-load-py2.dep`; the `SWSSSDK_PY2` dependency lines in `rules/sonic-py-common.mk` and `rules/swsssdk-py3.mk`.

##### 7.1.7 Kubernetes master

This runs a full Kubernetes control plane on the switch. That includes the apiserver, controller, scheduler, proxy, etcd 3.5.0, coredns 1.8.4, and the dashboard 2.7.0 web UI, along with cloud credential libraries used for backups. Every one of those versions is years past end of life, which makes this the single biggest reduction in CVE surface in this list. It is off by default and has no real CI coverage.

This applies to the master only. The worker feature (`INCLUDE_KUBERNETES`) is a separate feature and should stay. Someone hardened its cluster-join security before this working group existed, which points to a real user.

**Remove:** `files/image_config/kubernetes/` (`kubernetes_master_entrance.sh`, `kubernetes_master_entrance.service`, `kubernetes.list`); the `INCLUDE_KUBERNETES_MASTER` flag and the master version pins in `rules/config`; the master-only blocks in `files/build_templates/sonic_debian_extension.j2`; `sonic-kubernetes_master.yang`; the master build in `.azure-pipelines/azure-pipelines-build.yml`.
**Keep:** `INCLUDE_KUBERNETES` (the worker), `src/sonic-ctrmgrd*`, and the `ctrmgrd` wrapper, which runs for ordinary feature start and stop rather than only for k8s.

##### 7.1.8 docker-basic_router

This is a SAI demo and reference container. It is not wired into any build rule, it never ships in an image, and it is not in CI. Its last real change was in 2020, and nothing uses it.

**Remove:** `dockers/docker-basic_router/`.

##### 7.1.9 System Telemetry container

This container is off by default, and it is redundant. Both this container and the gnmi container run the same binary, `/usr/sbin/telemetry`, started by `telemetry.sh` and `gnmi-native.sh` respectively. There is no separate gNMI server. The `telemetry` binary is the server, and the name is only historical. Both containers read the same `TELEMETRY|gnmi` config, and the gnmi start script simply adds ZMQ and VRF options on top. There is therefore no functional gap, because Get, Set, Subscribe, and dial-out are identical in both.

**Remove:** `dockers/docker-sonic-telemetry/`, `rules/docker-telemetry.mk`, and `rules/docker-telemetry.dep`; the `INCLUDE_SYSTEM_TELEMETRY` flag in `rules/config`.
**Keep:** the `telemetry` binary, which is built by sonic-gnmi and run by the gnmi container.

##### 7.1.10 Broken FRR config modes

`docker_routing_config_mode` has four values. Both `separated` and `split` write per-daemon config files such as `bgpd.conf` and `zebra.conf`. FRR 10.5.4, which SONiC ships, dropped support for per-daemon config files, so both of these modes are broken today. Removing them is really just deleting dead code.

The supported path is `unified`, where the config comes from bgpcfgd and `config_db.json`, and that should become the default. Today `minigraph.py` hardcodes the default as `separated`, and init_cfg does not set it, so it resolves to `separated`. This change must flip that default to `unified`. The fourth mode, `split-unified`, still works and is handled under Deprecate.

**Change:** remove the `separated` and `split` branches in `dockers/docker-fpm-frr/docker_init.sh` and the per-daemon templates under `dockers/docker-fpm-frr/frr/{bgpd,zebra,staticd,sharpd}/`; flip the default in `src/sonic-config-engine/minigraph.py` from `separated` to `unified`.

##### 7.1.11 End-of-life Debian bases

Debian 8 (jessie), Debian 9 (stretch), Debian 10 (buster), and Debian 11 (bullseye) are all out of support. Bullseye leaves Debian LTS in August 2026, which is before 202611 ships, so it belongs with the rest rather than in a later cycle. The risk in every case is the same, which is that someone builds a new container on a base that no longer gets security updates.

jessie, stretch, and buster are pure leftovers, because nothing builds on them. Bullseye is different, because containers still build on it today, so those have to move first. Before deleting any base, confirm that nothing still builds a container on it. Debian 12 (bookworm) is still a live base and is handled under Deprecate.

**Remove (stretch):** `dockers/docker-base-stretch/`, `rules/docker-base-stretch.{mk,dep}`, `dockers/docker-config-engine-stretch/`, `rules/docker-config-engine-stretch.{mk,dep}`.
**Remove (buster):** `dockers/docker-base-buster/`, `rules/docker-base-buster.{mk,dep}`, `dockers/docker-config-engine-buster/`, `rules/docker-config-engine-buster.{mk,dep}`, `dockers/docker-swss-layer-buster/`, `rules/docker-swss-layer-buster.{mk,dep}`.
**Remove (jessie):** `sonic-slave-jessie/`, the `jessie` target in `Makefile`, and the jessie `SLAVE_DIR` branch in `Makefile.work`. jessie has no `docker-base-jessie`, so also check the jessie strings in the generic `dockers/docker-base/` (its armhf and arm64 sources and its `FROM ...:jessie` lines) before touching that container.
**Move first (bullseye):** seven containers still build on a bullseye base. Two of them, `docker-syncd-bfn` and `docker-saiserver-bfn`, go away with Barefoot in 7.1.1. The other five have to move to bookworm or trixie before bullseye can go, and they are `docker-syncd-centec` and `docker-saiserver-centec` under both `platform/centec/` and `platform/centec-arm64/`, plus `dockers/docker-sonic-sdk/`. The centec containers reach bullseye through `platform/template/docker-syncd-bullseye.mk`, so pointing their `docker-syncd-centec.mk` at the bookworm or trixie template covers four of the five.
**Remove (bullseye):** `dockers/docker-base-bullseye/`, `rules/docker-base-bullseye.{mk,dep}`, `dockers/docker-config-engine-bullseye/`, `rules/docker-config-engine-bullseye.{mk,dep}`, `dockers/docker-swss-layer-bullseye/`, `rules/docker-swss-layer-bullseye.{mk,dep}`, `platform/template/docker-syncd-bullseye.mk`, and `sonic-slave-bullseye/`; the `bullseye` target and the `NOBULLSEYE` and `BUILD_BULLSEYE` handling in `Makefile`, the bullseye `SLAVE_DIR` branch in `Makefile.work`, the `sonic-slave-bullseye` entry in `Makefile.cache`, and in `slave.mk` the `BULLSEYE_DEBS_PATH` and `BULLSEYE_FILES_PATH` variables, the `bullseye` target, and the `BLDENV` tests that name it; the `BLDENV == bullseye` conditionals in `rules/grpc.mk`, `rules/protobuf.mk`, `rules/sonic-dash-api.mk`, and `rules/sonic-fips.mk`.

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

### 8. Config and management impact

Removing a feature drops its `FEATURE` table entries, its build flags, and any YANG models tied to it, such as `sonic-kubernetes_master.yang`. Users who never enabled these features see no CLI change.

Removing the code is only half of it, because a device that upgrades keeps whatever it already had in CONFIG_DB. Every removal that touches configuration therefore has to update `sonic-utilities/scripts/db_migrator.py`, and that update is part of the removal rather than a follow-up. Without it, an upgraded device carries dead `FEATURE` rows and orphaned tables forever, a table that outlives its YANG model can fail config validation, and a setting whose supported values have narrowed can leave the device pointing at a value that no longer exists.

The shape of the change is the same each time. Add a new `version_<branch>_<build>` method chained onto the current tail of the version chain, bump `CURRENT_VERSION` to it, which is `version_202605_01` today, and drop the state that is going away with `delete_table` or with entry deletion. What this batch needs:

- `DEVICE_METADATA|localhost|docker_routing_config_mode`. A device holding `separated` or `split` has to be migrated to `unified`, because 7.1.10 deletes the code behind both. This is the case that matters most, since skipping it leaves a device configured for a routing mode that no longer exists rather than merely carrying dead config.
- The `KUBERNETES_MASTER` table, which goes with 7.1.7, along with its YANG model.
- The DTEL tables, which go with 7.1.2.
- `FEATURE|telemetry`, which goes with 7.1.9. `FEATURE|gnmi` stays, and the two must not be confused, because the surviving container is the gnmi one.
- `FEATURE|restapi`, when the REST API is removed in 202711 under 7.2.3, which lands in that release's migrator rather than this one.

The FRR change removes `separated` and `split` from `docker_routing_config_mode` and makes `unified` the default. The platform removals do not affect other platforms.

Collapsing the routing stack to FRR alone does not change any command an operator runs, because the FRR branch of every affected command already provides the same CLI. `clear ip bgp` keeps working through the renamed `clear/bgp_frr_v4.py`. The one visible difference is `show startupconfiguration bgp`, which loses its `/etc/quagga/bgpd.conf` branch and reads only `/etc/frr/bgpd.conf`.

### 9. Warmboot/Fastboot impact

There is no warmboot or fastboot impact. Every candidate is off by default, already dead, or specific to hardware that is being removed. None of this touches the warmboot or fastboot path on supported platforms.

### 10. Testing

- Each supported CI platform still builds after the removals.
- The removed packages no longer appear in the SBOM or the CVE scan, confirmed by an image diff.
- The default FRR path (`unified`) comes up and programs routes.
- A `config_db.json` from the previous release migrates cleanly, with no leftover tables for removed features and no config validation errors against the reduced YANG model set.
- A device configured for `separated` or `split` comes up in `unified` after upgrade, rather than pointing at a mode whose code is gone.
- Every remaining container builds with nothing pointing at a deleted base, and the centec and sonic-sdk containers build on their new base.
- `show ip bgp` and `clear ip bgp` still work after the routing-stack collapse and the `clear/bgp_frr_v4.py` rename.

### 11. Additional findings

These are real, but they are out of scope here, because removing them needs code porting that this HLD does not cover. They are listed so they are tracked.

- **swsssdk-py3.** This is the old Python Redis SDK. `swsscommon` replaces it, but code still imports `swsssdk` at runtime, including `sonic-utilities/scripts/dualtor_neighbor_check.py`, `sonic-py-common`, and the vpp container. It cannot be deprecated until those are ported to `swsscommon`.
