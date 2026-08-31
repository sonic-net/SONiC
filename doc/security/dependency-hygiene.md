# Automated Dependency Hygiene #

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
  - [4.1 Where the findings come from](#41-where-the-findings-come-from)
  - [4.2 What automation can reach](#42-what-automation-can-reach)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Where Renovate runs](#71-where-renovate-runs)
  - [7.2 What Renovate reads](#72-what-renovate-reads)
  - [7.3 Custom managers for SONiC's own pins](#73-custom-managers-for-sonics-own-pins)
  - [7.4 One pull request per ecosystem per update type](#74-one-pull-request-per-ecosystem-per-update-type)
  - [7.5 Branch policy](#75-branch-policy)
  - [7.6 Approval and merge](#76-approval-and-merge)
  - [7.7 Reviewers](#77-reviewers)
  - [7.8 Relationship to the nightly version freeze](#78-relationship-to-the-nightly-version-freeze)
  - [7.9 Rollout](#79-rollout)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
  - [9.4 Renovate configuration](#94-renovate-configuration)
  - [9.5 Steps for organization administrators](#95-steps-for-organization-administrators)
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
| 0.1 | 2026-08-31 | Brad House (Nexthop) | First draft. Security WG. |

### 2. Scope

This document proposes running [Renovate](https://docs.renovatebot.com/) across the `sonic-net` GitHub organization to update third party dependencies automatically.

In scope:

- Dependencies declared in a file someone wrote and checked in: `go.mod`, `Cargo.toml`, `requirements.txt`, `setup.py`, GitHub Actions workflows, Dockerfiles.
- Version numbers SONiC pins by hand in its own build scripts, such as the Docker and OpenTelemetry Collector versions.
- The rules for which updates open a pull request, how those pull requests are grouped, and which ones merge without a person.

Out of scope:

| Item | Reason |
|------|--------|
| The Linux kernel | Highest risk change in the tree. Needs config refresh and out-of-tree module rebuilds on every platform. Stays a human process. |
| Debian packages | Debian ships the fixes. The nightly version freeze pipeline already sweeps them forward. See [7.8](#78-relationship-to-the-nightly-version-freeze). |
| Locally patched components | A version bump fights the patch series. Handled by hand. |
| Removing unused dependencies | Belongs to the [202611 EOL and deprecation plan](../eol-planning/202611-eol-and-deprecation.md). |

This document changes no runtime code. It changes how updates arrive.

### 3. Definitions/Abbreviations

| Term | Meaning |
|------|---------|
| Renovate | An open source bot that reads dependency files, finds newer versions, and opens pull requests. |
| Manifest | A file that names a dependency and its version, such as `go.mod`. |
| Lockfile | A file recording the exact versions a build resolved, such as `go.sum`. |
| Manager | The part of Renovate that understands one manifest format. |
| Custom manager | A user-supplied pattern that teaches Renovate to read a version number out of a file it does not otherwise understand. |
| Datasource | Where Renovate looks up the newest version of something. |
| Automerge | Merging a pull request without a person clicking merge. |
| Security update | An update that fixes a known published vulnerability. |
| CVE | A published vulnerability identifier. |
| SBOM | Software Bill of Materials, the list of everything in a build. |
| Finding | One CVE against one package in one build. |
| WG | Working group. |

### 4. Overview

SONiC ships thousands of third party components. Nobody updates most of them on purpose. They move when something else forces them to move.

The numbers below come from the CycloneDX SBOM of a `sonic-broadcom` image built 2026-08-30, scanned with `grype`. Method is in [13.2](#132-system-test-cases).

#### 4.1 Where the findings come from

Absolute finding counts are deliberately withheld until the work below has landed. Everything here is expressed as a share, which is what the argument rests on anyway.

Where the findings sit:

| Source | Share of all findings | In scope |
|--------|----------------------:|----------|
| Linux kernel and packages built from it | ~71% | No |
| Debian packages | ~18% | No |
| Go, Rust, Python, npm components | ~10% | Yes |

Nearly all of the in-scope findings have a published fix available. The rest of this section is about that in-scope tenth.

#### 4.2 What automation can reach

Every fixable in-scope finding was traced back to the file that would have to change. Grouped by that file:

| Fixed by changing | Share of in-scope findings | Actions |
|-------------------|---------------------------:|---------|
| `DOCKER_VERSION` and `CONTAINERD_IO_VERSION` in `build_debian.sh` | ~29% | 2 version strings |
| SONiC's own `go.mod` files | ~29% | 59 bumps |
| The Go toolchains pinned for the build slaves | ~15% | 3 toolchains |
| `ARG OTEL_VERSION` in `dockers/docker-sonic-otel/Dockerfile.j2` | ~14% | 1 version string |
| `requirements.txt` and `setup.py` | ~4% | 14 bumps |
| `Cargo.toml` files | ~2% | 13 bumps |
| **Reachable by automation** | **~92%** | |
| npm lockfiles vendored inside Debian's Go and Ruby packages | ~8% | Not ours |

Three results drive this proposal:

1. **Three version strings account for more than four in ten in-scope findings**, and a disproportionate share of the most severe ones. They sit in a shell script and a Dockerfile template, and today a person edits them by hand, rarely. This is the single largest win and it needs custom managers.
2. **The build slaves carry three Go toolchains**, worth about one in seven in-scope findings. Nobody decided that. It is what happens without this workflow. See [7.3](#73-custom-managers-for-sonics-own-pins).
3. **The rest is ordinary dependency drift.** 59 Go bumps, 13 Rust, 14 Python. Routine work no one is doing.

Only the npm findings are out of reach, about one in twelve. They are lockfiles buried inside Debian's own Go and Ruby packages, and are not SONiC dependencies in any useful sense. There is no tracked `package.json` in the tree.

### 5. Requirements

| # | Requirement |
|---|-------------|
| R1 | Renovate is authorized across the `sonic-net` organization, with one configuration file per repository. |
| R2 | Security updates open a pull request without anyone asking. |
| R3 | A security pull request that passes the test suite merges without a person. |
| R4 | Release branches receive security updates only. No feature, bugfix, or major version bumps. |
| R5 | Development branches receive all updates, including major versions. Today `master` is the only development branch. |
| R6 | One pull request per ecosystem per update type. Not one per dependency. |
| R7 | Major version bumps get their own pull request, one dependency at a time. |
| R8 | Version numbers SONiC pins by hand are updated by the same automation. |
| R9 | Reviewers are assigned automatically. |
| R10 | The existing reproducible build version files keep working. |

Exemptions: the kernel (R1–R9 do not apply), Debian packages, and locally patched components.

### 6. Architecture Design

No change to the SONiC image, its containers, or anything that runs on a switch.

The change is in the development workflow:

```
  Today
    upstream release ──▶ (nobody notices) ──▶ CVE scan finds it months later ──▶ manual PR

  Proposed
    upstream release ──▶ Renovate ──▶ grouped PR ──▶ SONiC test suite ──┬─▶ pass: merge
                                                                        └─▶ fail: human
```

Renovate runs as a hosted GitHub App. Nothing is installed on build machines. Each repository controls its own behaviour through a `renovate.json` at its root.

### 7. High-Level Design

#### 7.1 Where Renovate runs

Renovate is installed per repository, not per directory. `sonic-buildimage` has 52 submodules, and each one is a separate GitHub repository with its own dependency files.

| | Count |
|---|---:|
| Submodules in `sonic-buildimage` | 52 |
| Owned by `sonic-net` | 32 |
| Third party (FRR, scapy, supervisor, vendor platform repos) | 20 |
| Repositories with a Renovate config today | 0 |

- Authorize the Renovate app on the whole `sonic-net` organization.
- Add a `renovate.json` to `sonic-buildimage` and to each of the 32 owned submodules.
- Third party submodules get nothing. We do not control them. Their dependencies arrive through whatever version of the submodule we pin.

#### 7.2 What Renovate reads

Files present in `sonic-buildimage` and its submodules today:

| Manager | Files | Direct dependencies |
|---------|------:|--------------------:|
| `gomod` | 10 | 151 |
| `cargo` | 34 | 338 |
| `pip_requirements` | 7 | 12 |
| `setup-py` | 28 | not counted |
| `github-actions` | 77 | 165 |
| `dockerfile` | 155 | base images |
| `npm` | 0 | — |

There is no tracked `package.json` anywhere in the tree. npm needs no configuration.

#### 7.3 Custom managers for SONiC's own pins

Three version numbers fix more than four in ten in-scope findings. None sit in a file Renovate understands by default.

**Docker and containerd** — `build_debian.sh` lines 39-40:

```bash
DOCKER_VERSION=5:28.5.2-1~debian.13~$IMAGE_DISTRO
CONTAINERD_IO_VERSION=1.7.28-2~debian.13~$IMAGE_DISTRO
```

These come from `download.docker.com`, not from Debian. Debian will never move them for us.

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/^build_debian\\.sh$/"],
      "matchStrings": [
        "DOCKER_VERSION=(?<currentValue>\\S+?)~\\$IMAGE_DISTRO",
        "CONTAINERD_IO_VERSION=(?<currentValue>\\S+?)~\\$IMAGE_DISTRO"
      ],
      "depNameTemplate": "docker-ce",
      "datasourceTemplate": "deb",
      "registryUrlTemplate": "https://download.docker.com/linux/debian?suite=trixie&components=stable&binaryArch=amd64"
    }
  ]
}
```

**OpenTelemetry Collector** — `dockers/docker-sonic-otel/Dockerfile.j2` line 32:

```dockerfile
ARG OTEL_VERSION=0.144.0
```

This is a Dockerfile, but with a `.j2` suffix, so Renovate skips it. Point the built-in Dockerfile manager at the template and give it a datasource:

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/^dockers/docker-sonic-otel/Dockerfile\\.j2$/"],
      "matchStrings": ["ARG OTEL_VERSION=(?<currentValue>\\S+)"],
      "depNameTemplate": "open-telemetry/opentelemetry-collector-releases",
      "datasourceTemplate": "github-releases",
      "extractVersionTemplate": "^v(?<version>.*)$"
    }
  ]
}
```

**Build toolchains.** Go and Rust do not come from Debian. SONiC pins both by hand:

| Toolchain | Pinned at | Share of in-scope findings |
|-----------|-----------|---------------------------:|
| Go 1.24, trixie slave, Debian `golang-go` | `sonic-slave-trixie/Dockerfile.j2:577,589` | ~7% |
| Go 1.19, bookworm slave, FIPS build | `rules/sonic-fips.mk:22` | ~5% |
| Go 1.26, trixie slave, FIPS build | `rules/sonic-fips.mk:11` | ~3% |
| Rust 1.86.0 | `sonic-slave-trixie/Dockerfile.j2:798` | none today |

Three Go toolchains is not a decision anyone made:

- **Go 1.19** belongs to the bookworm slave and disappears when bookworm does. The [202611 EOL plan](../eol-planning/202611-eol-and-deprecation.md) already proposes deprecating the bookworm base.
- **Go 1.24 and 1.26 are both installed in the trixie slave** — Debian's `golang-go` alongside the FIPS build. The older of the two carries the larger share of findings. That redundancy should be removed whether or not Renovate lands.

Rust is a plain version string and needs only a pattern:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^sonic-slave-trixie/Dockerfile\\.j2$/"],
  "matchStrings": ["--default-toolchain (?<currentValue>\\d+\\.\\d+\\.\\d+)"],
  "depNameTemplate": "rust-lang/rust",
  "datasourceTemplate": "github-releases"
}
```

Go needs one caveat. `FIPS_GOLANG_VERSION` points at a FIPS patched package SONiC publishes to its own mirror, so the bump cannot land until that package exists. Renovate can still watch upstream Go and open a pull request reporting how far behind we are. Treat the Go toolchain as a notification, not an automerge candidate.

Each new hand-pinned version added to the tree should come with a custom manager entry. That is the rule this document asks for: **if a person pins it, the bot maintains it.**

#### 7.4 One pull request per ecosystem per update type

Not one pull request per dependency. Grouping keeps the count manageable and keeps related changes testable together.

| Base branch | Update type | Grouping |
|-------------|-------------|----------|
| Any | Security | One PR per ecosystem |
| `master` | Patch | One PR per ecosystem |
| `master` | Minor | One PR per ecosystem |
| `master` | Major | One PR per dependency |

Major bumps are isolated because they are the ones that break. When a grouped PR fails, nobody knows which dependency did it. When an isolated major fails, everybody does.

Expected volume at steady state is a handful of pull requests per week per repository. The initial sweep will be larger and will shrink as the backlog clears.

#### 7.5 Branch policy

`202611` is the first release branch in scope. Older branches are left alone.

**Release branches — security only.** Disable everything, then let vulnerability handling re-enable what matters:

```json
{
  "baseBranchPatterns": ["202611"],
  "packageRules": [
    { "matchPackageNames": ["*"], "enabled": false }
  ],
  "vulnerabilityAlerts": { "enabled": true },
  "osvVulnerabilityAlerts": true
}
```

**Development branches — everything.** `master` today.

```json
{
  "baseBranchPatterns": ["master"],
  "separateMajorMinor": true,
  "separateMinorPatch": true,
  "packageRules": [
    { "matchUpdateTypes": ["patch"], "groupName": "{{manager}} patch updates" },
    { "matchUpdateTypes": ["minor"], "groupName": "{{manager}} minor updates" },
    { "matchUpdateTypes": ["major"], "groupName": null }
  ]
}
```

What counts as a security update is decided by GitHub's vulnerability alerts and by the OSV database. Both cover Go, Rust, Python, and npm, which is the whole of the in-scope set. Debian and the kernel are excluded from this document, so nothing in scope depends on a source Renovate cannot see.

#### 7.6 Approval and merge

Renovate cannot approve its own pull requests. Something must supply the approval.

| Option | How | Trade-off |
|--------|-----|-----------|
| Ruleset bypass | Add Renovate to the list of actors that skip required reviews | Simple. Applies to every Renovate PR. Cannot be limited to security updates. |
| **`renovate-approve` app** | Approves only PRs Renovate already marked for automerge | **Recommended.** Scope is set in `renovate.json`, so "security only on release branches" is enforced in config. Review requirements stay intact for everyone else. |
| `automergeType: branch` | No PR at all; commits straight to the branch when tests pass | Quietest. No audit trail. Poor fit for a release branch. |
| Bot account plus approval workflow | A machine account approves via GitHub Actions | Most control, most to maintain, standing credential in org secrets. |

The recommendation is the [`renovate-approve` app](https://github.com/apps/renovate-approve). It is the only option where the decision about what merges unattended lives in the same file that defines what a security update is.

Two prerequisites for the organization administrators:

1. **`allow_auto_merge` is currently `false` on `sonic-buildimage`.** It must be enabled per repository.
2. **`EasyCLA` is a required status check on `master`.** A bot author has to clear it. The existing `mssonicbld` version upgrade bot already opens pull requests against these branches, so this has been solved before in this organization and that solution should be reused.

Required checks on `master` today are `EasyCLA`, `Azure.sonic-buildimage`, and `Semgrep`. All three must pass before an automerge fires. The SONiC test suite is thorough, so a green run on a dependency bump is strong evidence the bump is good. That is the basis for merging without a person.

#### 7.7 Reviewers

Automatic reviewer assignment needs `CODEOWNERS`, and coverage is thin:

| Repository | CODEOWNERS |
|------------|-----------|
| `sonic-buildimage` | Yes, 59 rules |
| `sonic-swss` | Yes, 14 rules |
| 3 other submodules | Present but nearly empty |
| Remaining 48 submodules | None |

In `sonic-buildimage` itself, most paths Renovate touches are not covered by a specific rule. `build_debian.sh` and the `src/*/Cargo.toml` trees fall through to the catch-all `* @lguohan`, which would route a large share of the first wave to one person.

Either write explicit `reviewers` lists into each `renovate.json`, or extend `CODEOWNERS` first. This is a prerequisite of the rollout, not a detail to discover after the pull requests start arriving.

#### 7.8 Relationship to the nightly version freeze

`.azure-pipelines/azure-pipelines-UpgrateVersion.yml` already automates part of this. It runs nightly, builds 9 platforms with version pinning switched off so `apt` and `pip` resolve whatever is current, runs `make freeze` to record what was actually installed, and opens a pull request as `mssonicbld`.

**It stays.** It does something Renovate cannot do:

| | Nightly freeze | Renovate |
|---|---|---|
| Works from | What a build actually resolved | What a manifest declares |
| Covers transitive packages | Yes | No |
| Per platform, per architecture, per container | Yes | No |
| Pins the Debian snapshot timestamp | Yes | No |
| Reads `go.mod`, `Cargo.toml`, `package.json` | No | Yes |

The dividing line: **the pipeline owns what the build resolves. Renovate owns what a manifest declares.** They do not overlap, with one exception.

**The pip seam.** The `pip` build hook (`src/sonic-build-hooks/scripts/buildinfo_base.sh`, lines 327-350) passes the frozen `versions-py3` file to every `pip install` as a constraint file. It removes a package from that constraint only when an exact version appears on the pip command line. It never reads `-r requirements.txt`. So if Renovate bumps a pin inside a `requirements.txt`, the frozen constraint still names the old version, and the build either fails on a conflict or quietly installs the old one until the next nightly freeze.

Three ways to resolve it:

1. Leave Python to the nightly pipeline. Exclude `pip` and `setup-py` from Renovate. Costs 14 bumps, and removes the seam entirely.
2. Teach the build hook to read requirements files.
3. Order the Renovate pull request behind a re-freeze.

Option 1 is the cheapest and is what this document proposes for the first phase. Python is a small share of the reachable findings.

#### 7.9 Rollout

| Phase | Work | Share addressed |
|-------|------|----------------:|
| 1 | Custom managers for Docker, containerd, and OpenTelemetry in `sonic-buildimage` | ~43% |
| 2 | Remove the duplicate Go toolchain from the trixie slave, then add toolchain custom managers | ~15% |
| 3 | Native managers on `master` in `sonic-buildimage` and the 6 repositories holding `go.mod` and `Cargo.toml` | ~31% |
| 4 | Enable automerge for security updates once the earlier phases have run manually for one cycle | — |
| 5 | Extend to the remaining owned repositories and to the `202611` branch | — |
| 6 | Resolve the pip seam | ~4% |

Automerge is deliberately last. The first cycles should be watched by a person, so the failure modes are understood before the bot is trusted to merge on its own.

### 8. SAI API

No change. This feature does not touch SAI.

### 9. Configuration and management

#### 9.1 Manifest

Not applicable. This is not a SONiC Application Extension.

#### 9.2 CLI/YANG model Enhancements

No change. No CLI, no YANG models, no command reference updates.

#### 9.3 Config DB Enhancements

No change. Nothing is written to `CONFIG_DB` or any other database.

#### 9.4 Renovate configuration

Configuration lives in `renovate.json` at the root of each repository. A worked example for `sonic-buildimage`:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "baseBranchPatterns": ["master", "202611"],
  "dependencyDashboard": true,
  "osvVulnerabilityAlerts": true,
  "separateMajorMinor": true,
  "separateMinorPatch": true,
  "enabledManagers": ["gomod", "cargo", "github-actions", "dockerfile", "custom.regex"],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"],
    "automerge": true
  },
  "packageRules": [
    {
      "description": "Release branches take security updates only",
      "matchBaseBranches": ["202611"],
      "matchPackageNames": ["*"],
      "enabled": false
    },
    {
      "description": "Group patch and minor updates per ecosystem on master",
      "matchBaseBranches": ["master"],
      "matchUpdateTypes": ["patch", "minor"],
      "groupName": "{{manager}} {{updateType}} updates"
    },
    {
      "description": "Major updates get their own pull request",
      "matchBaseBranches": ["master"],
      "matchUpdateTypes": ["major"],
      "groupName": null
    }
  ]
}
```

Shared settings should live in a preset in the `sonic-net/.github` repository so that 33 files do not drift apart:

```json
{
  "extends": ["local>sonic-net/.github:renovate-config"]
}
```

#### 9.5 Steps for organization administrators

Nothing here requires a server, a build machine, or a stored credential. It is all GitHub settings. Five steps, in order.

**Step 1 — Let Renovate see the repositories.**

- Go to <https://github.com/apps/renovate> and select **Configure**.
- Choose the **sonic-net** organization.
- Grant access to all repositories.

Renovate does nothing until a repository contains a `renovate.json`. Granting access org-wide is safe; each repository still opts in by adding that file.

**Step 2 — Turn on auto-merge in each repository.**

This is off today in `sonic-buildimage`, and nothing merges automatically until it is on.

- In the repository: **Settings → General → Pull Requests**.
- Tick **Allow auto-merge**.

Repeat for every repository in scope. This only permits auto-merge; it does not make anything merge on its own.

**Step 3 — Let approvals happen without a person.**

GitHub does not let Renovate approve its own pull requests, so a second app supplies the approval.

- Install <https://github.com/apps/renovate-approve> on the same organization.
- If a repository requires two approving reviews, also install `renovate-approve-2`.

This app only approves pull requests that Renovate has already marked for automatic merging. Which ones those are is decided in `renovate.json`, not here. Everything else still needs a human review as it does today.

**Step 4 — Let the bot pass the CLA check.**

`EasyCLA` is a required check on these branches, and a pull request from a bot has to clear it or it can never merge.

The `mssonicbld` bot already opens pull requests against these same branches for nightly version upgrades, so this has been solved before in this organization. Find how that bot is handled in the Linux Foundation EasyCLA configuration and apply the same treatment to the Renovate bot.

**Step 5 — Check the branch rules.**

For each branch in scope, `master` and `202611`:

- Confirm which checks are required. Today on `master` they are `EasyCLA`, `Azure.sonic-buildimage`, and `Semgrep`. All of them must pass before anything merges automatically. That is the intended behaviour and should not be relaxed.
- Confirm whether approving reviews are required. This cannot be read without administrator access, so someone with those rights has to check it. If reviews are required, step 3 is what satisfies them.
- Do **not** add Renovate to any bypass list. The design deliberately routes approval through step 3 instead, because that is the only place where "security updates only on release branches" can actually be enforced.

**What to expect afterwards.**

- A burst of pull requests on `master` the first week, as a backlog of never-applied updates clears. It shrinks quickly.
- Only security updates on `202611`. Never a feature or major version bump.
- Anything that fails the test suite stays open as a normal pull request for a person to look at. Nothing broken merges itself.

**How to stop it.** Remove the `renovate.json` from a repository, or uninstall the app from the organization. There is no other state to unwind.

### 10. Warmboot and Fastboot Design Impact

No direct impact. Renovate changes no code that runs during boot.

Indirectly, any dependency bump could affect boot time, the same as any other pull request. This is covered by the existing test suite, which every Renovate pull request must pass before merging. No dependency bump is exempt from that gate.

Against the specific questions in the template:

- Nothing is added to the boot critical chain.
- No new CPU work is added to the boot path.
- Third party bumps are the point of the feature, and each one is measured by the existing pipeline like any other change.
- No new service or container is introduced, so there is nothing to delay.

### 11. Memory Consumption

No change. Nothing is added to the image.

### 12. Restrictions/Limitations

| Limitation | Effect |
|------------|--------|
| About one in twelve fixable findings is unreachable | npm lockfiles inside Debian's Go and Ruby packages. Not SONiC dependencies. |
| The Go toolchain bump depends on a FIPS build | Renovate reports the lag; it cannot merge the bump until the FIPS package exists. See [7.3](#73-custom-managers-for-sonics-own-pins). |
| Renovate only sees what is in a manifest | Anything resolved at build time is invisible to it. That is the nightly pipeline's job. |
| A bump can conflict with a local patch | Locally patched components are out of scope for this document. |
| `CODEOWNERS` coverage is thin | Automatic reviewer assignment will not work well until this is fixed. See [7.7](#77-reviewers). |
| The pip constraint seam | See [7.8](#78-relationship-to-the-nightly-version-freeze). Python is excluded in phase 1. |
| The `git-submodules` manager is beta | Automatic bumping of the 52 submodule pointers is not proposed here. Submodule pointers stay manual. |
| Renovate cannot tell why a submodule pointer moved | Even if enabled later, a pointer bump cannot be classified as a security update, so it could not be automerged on a release branch. |

### 13. Testing Requirements/Design

#### 13.1 Unit Test cases

Renovate ships no code into SONiC, so there is nothing to unit test in the usual sense. The configuration itself is validated:

| Test | Method |
|------|--------|
| Configuration is valid | `npx --yes --package renovate -- renovate-config-validator` in CI on every change to a `renovate.json` |
| Custom managers match the right lines | Renovate dry run against a branch; confirm it finds `DOCKER_VERSION`, `CONTAINERD_IO_VERSION`, and `OTEL_VERSION` and no others |
| Release branch rules hold | Dry run against `202611`; confirm only security updates are proposed |
| Grouping is correct | Dry run against `master`; confirm one PR per ecosystem per update type, and majors ungrouped |

#### 13.2 System Test cases

Every Renovate pull request runs the existing SONiC pipeline. No new test infrastructure is required. That is the whole basis for merging without a person.

| Test | Method |
|------|--------|
| A bumped image builds | `Azure.sonic-buildimage` on the pull request |
| A bumped image works | The existing regression suite, unchanged |
| Warm and fast reboot are unaffected | Existing warmboot and fastboot tests, unchanged |
| Findings actually go down | Re-run the SBOM scan after each merged batch and compare |

The last one is how this proposal is measured. The baseline in [section 4](#4-overview) was produced with:

```bash
make ENABLE_SBOM=y target/sonic-broadcom.bin
python3 scripts/sbom_vuln_scan.py --vex vex/ target/sonic-broadcom.bin.cdx.json
```

Drift between two scans is reported by `scripts/sbom_vuln_diff.py`. A scheduled scan comparing each release branch against its previous run turns this document's claim into a number anybody can check.

### 14. Open/Action items

| # | Item | Owner |
|---|------|-------|
| 1 | Authorize the Renovate app on the `sonic-net` organization | Org admins |
| 2 | Enable `allow_auto_merge` on the repositories in scope | Org admins |
| 3 | Install `renovate-approve` and confirm it satisfies branch protection | Org admins |
| 4 | Confirm how `mssonicbld` clears `EasyCLA`, and reuse it for Renovate | Build WG |
| 5 | Decide whether `CODEOWNERS` is extended or explicit reviewer lists are used | Component owners |
| 6 | Confirm whether required reviews are configured on the branches in scope. The branch protection API does not expose this without admin rights | Org admins |
| 7 | Choose a resolution for the pip constraint seam | Build WG |
| 8 | Remove the duplicate Go toolchain from the trixie slave. Debian `golang-go` and the FIPS build are both installed | Build WG |
| 9 | Confirm the FIPS Go release cadence, so the toolchain pin has something to track | Build WG |
