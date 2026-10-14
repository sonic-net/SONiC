# Automated Dependency Hygiene #

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Installation scope](#71-installation-scope)
  - [7.2 Native managers](#72-native-managers)
  - [7.3 Hand-pinned versions](#73-hand-pinned-versions)
  - [7.4 Pull request grouping](#74-pull-request-grouping)
  - [7.5 Branch policy](#75-branch-policy)
  - [7.6 Approval and merge](#76-approval-and-merge)
  - [7.7 Reviewers](#77-reviewers)
  - [7.8 Existing automation](#78-existing-automation)
  - [7.9 Rollout](#79-rollout)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
  - [9.4 Renovate configuration](#94-renovate-configuration)
  - [9.5 Setup steps](#95-setup-steps)
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
| 0.2 | 2026-10-14 | Brad House (Nexthop) | Restructured as a design and implementation plan. Review corrections. |

### 2. Scope

[Renovate](https://docs.renovatebot.com/) runs across the `sonic-net` GitHub organization and updates third party dependencies.

In scope:

- Dependencies declared in a checked-in manifest: `go.mod`, `Cargo.toml`, `requirements.txt`, `setup.py`, GitHub Actions workflows, Dockerfiles.
- Versions SONiC pins by hand in its own build scripts, such as Docker and the OpenTelemetry Collector.
- Which updates open a pull request, how those pull requests are grouped, and which ones merge without a person.

Out of scope:

| Item | Reason |
|------|--------|
| The Linux kernel | Each bump needs a config refresh and out-of-tree module rebuilds on every platform |
| Stock Debian packages | The nightly version freeze pipeline moves them. See [7.8](#78-existing-automation) |
| Debian packages SONiC rebuilds from pinned sources | Re-pinning a git commit or a FIPS build is a judgment call. SBOM-driven triage covers them |
| Locally patched components | A version bump conflicts with the patch series |
| Removing unused dependencies | Owned by the [202611 EOL and deprecation plan](../eol-planning/202611-eol-and-deprecation.md) |

The design changes no runtime code.

### 3. Definitions/Abbreviations

| Term | Meaning |
|------|---------|
| Renovate | An open source bot that reads dependency files, finds newer versions, and opens pull requests |
| Manifest | A file that names a dependency and its version, such as `go.mod` |
| Manager | The part of Renovate that reads one manifest format |
| Custom manager | A regular expression that tells Renovate where a version sits in a file it does not otherwise read |
| Datasource | Where Renovate looks up the newest version of a dependency |
| Automerge | Merging a pull request without a person |
| Security update | An update that fixes a published vulnerability, as classified by GitHub advisories or OSV |
| Merge robot | `azure-pipelines/automation-pr-scan.yml` in `sonic-pipelines`, which merges labeled bot pull requests |
| SBOM | Software Bill of Materials, the list of everything in a build |
| WG | Working group |

### 4. Overview

Most third party versions in SONiC move only when another change forces them. Renovate opens a pull request when upstream publishes a release, and the existing test suite decides whether it is safe.

Each source of third party code has one owner:

| Source | Where the version is set | Kept current by |
|--------|--------------------------|-----------------|
| Go, Rust and Python modules | `go.mod`, `Cargo.toml`, `requirements.txt`, `setup.py` | Renovate, native managers |
| GitHub Actions and Dockerfile base images | Workflow files, Dockerfiles | Renovate, native managers |
| Versions pinned by hand | `build_debian.sh`, Dockerfile templates, `rules/*.mk` | Renovate, custom managers |
| Stock Debian packages | The Debian snapshot and `files/build/versions*` | Version freeze pipeline |
| Submodule commits | `sonic-buildimage` submodule pointers | Submodule update pipeline |
| Debian packages SONiC rebuilds | `rules/*.mk`, `src/` | SBOM-driven triage |
| The Linux kernel | `sonic-linux-kernel` | People |

Hand-pinned versions sit in no file Renovate reads by default. Each one has a custom manager (R9).

### 5. Requirements

| # | Requirement |
|---|-------------|
| R1 | Renovate is authorized across the `sonic-net` organization, with one configuration file per repository |
| R2 | A security update opens a pull request without anyone asking |
| R3 | A security update that is not a major version bump, and that passes every check, merges without a person |
| R4 | A major version bump never merges without a person, including a security update |
| R5 | Release branches receive security updates, and patch and minor updates to hand-pinned versions. Nothing else |
| R6 | Development branches receive every update. `master` is the development branch |
| R7 | One pull request per ecosystem per update type |
| R8 | One pull request per dependency for a major version bump |
| R9 | Every hand-pinned version has a custom manager |
| R10 | Reviewers are assigned automatically: the Security Working Group, plus the release branch owner on a release branch |
| R11 | The reproducible build version files keep working |

R1 to R10 do not apply to the exclusions in [section 2](#2-scope).

### 6. Architecture Design

Nothing changes in the SONiC image, its containers, or anything that runs on a switch. The change is to the development workflow:

```
upstream release ──▶ Renovate ──▶ pull request ──▶ checks ──┬─▶ automerge label, all checks pass ──▶ merge robot merges
                                                            └─▶ otherwise ──▶ reviewer
```

Renovate runs as the hosted GitHub App. Nothing is installed on build machines. Each repository controls its behavior through a `renovate.json` at its root.

### 7. High-Level Design

#### 7.1 Installation scope

| Repository | Renovate configuration |
|------------|------------------------|
| `sonic-buildimage` | Yes |
| Submodules owned by `sonic-net` | Yes |
| Third party submodules (FRR, scapy, supervisor, vendor platform repositories) | No. Their dependencies arrive through the pinned submodule commit |

The app is authorized on the whole organization. A repository without a `renovate.json` is ignored.

#### 7.2 Native managers

| Manager | Reads | Enabled |
|---------|-------|---------|
| `gomod` | `go.mod` | Yes |
| `cargo` | `Cargo.toml` | Yes |
| `github-actions` | `.github/workflows/*.yml` | Yes |
| `dockerfile` | `Dockerfile` | Yes |
| `pip_requirements`, `setup-py` | `requirements.txt`, `setup.py` | No, until the pip constraint seam is resolved. See [7.8](#78-existing-automation) |
| `git-submodules` | `.gitmodules` | No. The submodule update pipeline owns submodule pointers |

#### 7.3 Hand-pinned versions

A version a person pins in a build script has a custom manager entry beside it.

| Variable | File | Datasource | Merge |
|----------|------|------------|-------|
| `DOCKER_VERSION` (`docker-ce`) | `build_debian.sh` | `deb`, `download.docker.com` | Reviewer |
| `CONTAINERD_IO_VERSION` (`containerd.io`) | `build_debian.sh` | `deb`, `download.docker.com` | Reviewer |
| `OTEL_VERSION` | `dockers/docker-sonic-otel/Dockerfile.j2` | `github-releases` | Reviewer |
| Rust toolchain | `sonic-slave-trixie/Dockerfile.j2` | `github-releases` | Reviewer |
| `FIPS_GOLANG_VERSION` | `rules/sonic-fips.mk` | `golang-version` | Dashboard only |

**Docker and containerd.** Each package has its own entry, because each is a separate package in the apt repository. The pin omits the distribution suffix, and the build appends `~$IMAGE_DISTRO`. The apt index carries the suffix, so `extractVersionTemplate` strips it before comparison and before the new value is written:

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/^build_debian\\.sh$/"],
      "matchStrings": ["DOCKER_VERSION=(?<currentValue>\\S+?)~\\$IMAGE_DISTRO"],
      "depNameTemplate": "docker-ce",
      "datasourceTemplate": "deb",
      "registryUrlTemplate": "https://download.docker.com/linux/debian?suite=trixie&components=stable&binaryArch=amd64",
      "extractVersionTemplate": "^(?<version>.+)~trixie$"
    },
    {
      "customType": "regex",
      "managerFilePatterns": ["/^build_debian\\.sh$/"],
      "matchStrings": ["CONTAINERD_IO_VERSION=(?<currentValue>\\S+?)~\\$IMAGE_DISTRO"],
      "depNameTemplate": "containerd.io",
      "datasourceTemplate": "deb",
      "registryUrlTemplate": "https://download.docker.com/linux/debian?suite=trixie&components=stable&binaryArch=amd64",
      "extractVersionTemplate": "^(?<version>.+)~trixie$"
    }
  ]
}
```

The `suite` parameter and the stripped suffix both name the image distribution, and change together when it does.

**OpenTelemetry Collector.** The built-in `dockerfile` manager does not read a `.j2` file and has no datasource for a bare `ARG`:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^dockers/docker-sonic-otel/Dockerfile\\.j2$/"],
  "matchStrings": ["ARG OTEL_VERSION=(?<currentValue>\\S+)"],
  "depNameTemplate": "open-telemetry/opentelemetry-collector-releases",
  "datasourceTemplate": "github-releases",
  "extractVersionTemplate": "^v(?<version>.*)$"
}
```

**Rust toolchain.** The `rustup` invocation carries a plain version string:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^sonic-slave-trixie/Dockerfile\\.j2$/"],
  "matchStrings": ["--default-toolchain (?<currentValue>\\d+\\.\\d+\\.\\d+)"],
  "depNameTemplate": "rust-lang/rust",
  "datasourceTemplate": "github-releases"
}
```

**FIPS Go toolchain.** `FIPS_GOLANG_VERSION` names a FIPS package SONiC publishes to its own mirror, which exists only after SONiC builds it. Renovate lists the upstream Go release on the Dependency Dashboard and opens a pull request only when someone approves it there:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^rules/sonic-fips\\.mk$/"],
  "matchStrings": ["FIPS_GOLANG_VERSION = (?<currentValue>\\d+\\.\\d+\\.\\d+)"],
  "depNameTemplate": "go",
  "datasourceTemplate": "golang-version"
}
```

```json
{
  "matchManagers": ["custom.regex"],
  "matchDatasources": ["golang-version"],
  "dependencyDashboardApproval": true
}
```

#### 7.4 Pull request grouping

| Base branch | Update type | Grouping |
|-------------|-------------|----------|
| Any | Security | One pull request per ecosystem |
| `master` | Patch | One pull request per ecosystem |
| `master` | Minor | One pull request per ecosystem |
| `master` | Major | One pull request per dependency |

A major bump is the update most likely to break, and an isolated failure names its cause.

`prConcurrentLimit` and `prHourlyLimit` bound the volume of ordinary updates. Security updates ignore both. `vulnerabilityAlerts.prConcurrentLimit` bounds them separately. The first run clears the accumulated backlog and is the largest.

#### 7.5 Branch policy

`202611` is the first release branch in scope. Older release branches carry no Renovate rules.

| Update | `master` | Release branch |
|--------|----------|----------------|
| Security, patch or minor | `automerge` label | `automerge` label |
| Security, major | Reviewer | Reviewer |
| Hand-pinned version, patch or minor | Reviewer | Reviewer |
| Hand-pinned version, major | Reviewer | Not opened |
| Any other patch or minor | Grouped, reviewer | Not opened |
| Any other major | One per dependency, reviewer | Not opened |

**Security classification.** Renovate classifies a security update from GitHub vulnerability alerts and OSV, both keyed by ecosystem:

| Lane | Datasource | Classified as security |
|------|------------|------------------------|
| `gomod`, `cargo`, `pip` | Ecosystem registry | Yes |
| Docker, containerd | `deb` | No |
| OpenTelemetry Collector, Rust | `github-releases` | No |
| FIPS Go | `golang-version` | No |

A custom manager has no advisory feed behind it. A release branch therefore enables hand-pinned updates by name, and a reviewer decides whether each one is needed.

**The `automerge` label.** Renovate applies the `vulnerabilityAlerts` object to every security update with precedence over all package rules. That object sets only the `security` label. A package rule adds `automerge` to security updates that are patch or minor:

```json
{
  "vulnerabilityAlerts": { "enabled": true, "labels": ["security"] },
  "packageRules": [
    {
      "description": "Security updates below a major version merge unattended",
      "matchJsonata": ["isVulnerabilityAlert = true"],
      "matchUpdateTypes": ["patch", "minor"],
      "addLabels": ["automerge"]
    }
  ]
}
```

A security update that needs a major version opens with the `security` label alone and waits for a reviewer.

#### 7.6 Approval and merge

Renovate cannot approve its own pull requests. The existing merge robot merges them.

| | |
|---|---|
| `renovate.json` | Applies the `automerge` label as set out in [7.5](#75-branch-policy). Renovate's own `automerge` setting stays off |
| Merge robot | Lists Renovate pull requests carrying the `automerge` label, evaluates their checks, merges the ones that pass with `gh pr merge --admin`, and escalates the ones that fail to the release branch owner |
| Branch protection | `--admin` bypasses the review requirement. GitHub still enforces every required status check |

Which pull requests merge is decided in `renovate.json`, by the label. Whether a labeled pull request merges is decided by the required checks and by the robot.

Robot check evaluation is a prerequisite for the `automerge` label. Before any Renovate pull request carries the label, the robot merges only when every check it reads has completed successfully:

| Case | Required behavior |
|------|-------------------|
| A check still in progress | Not merged |
| A check that timed out, needs action, or failed to start | Not merged |
| A commit status (legacy status context) in failure or error | Not merged |
| An empty check list | Not merged |
| A check named `vulnerability scan` | Evaluated |
| A check named `OPTIONAL` | Skipped |

Until that lands, Renovate opens every pull request without the `automerge` label.

`EasyCLA` is a required check, and a pull request from the Renovate bot clears it the same way one from `mssonicbld` does.

Alternatives considered:

| Option | Not chosen because |
|--------|--------------------|
| [`renovate-approve`](https://github.com/apps/renovate-approve) app | Adds a second app and an admin setting on every repository. It is the path back if the robot proves unsuitable |
| Ruleset bypass for Renovate | Applies to every Renovate pull request, and cannot be limited to security updates |
| `automergeType: branch` | Commits without a pull request, which leaves no review record on a release branch |

#### 7.7 Reviewers

Renovate assigns reviewers from an explicit list. `CODEOWNERS` is not used, because most paths Renovate edits fall through to a single catch-all owner.

```json
{
  "reviewers": ["team:sonic-security-wg"]
}
```

| Rule | Reason |
|------|--------|
| The reviewer is the `@sonic-net/sonic-security-wg` team | One place to edit when membership changes |
| The team holds the public Working Group membership | It is a new team, created for this |
| `sonic-private-security-group` is never a reviewer | It handles embargoed vulnerabilities. These pull requests are public |
| A release branch adds its owner through `additionalReviewers` | The owner is listed in `azure-pipelines/release-owners_github_account.json` in `sonic-pipelines`, which the merge robot also reads |

Renovate sets reviewers when it opens a pull request and does not revisit them.

#### 7.8 Existing automation

Three pipelines already keep parts of the tree current, all acting as `mssonicbld`. Renovate is added beside them.

| Pipeline | Owns | Where it lives |
|----------|------|----------------|
| Version freeze | What the build resolves: `apt` and `pip` versions per platform, architecture and container, and the Debian snapshot timestamp | `sonic-buildimage`, `.azure-pipelines/azure-pipelines-UpgrateVersion.yml` |
| Submodule update | Which commit of each submodule `sonic-buildimage` builds | `sonic-pipelines`, `azure-pipelines/submodule-update.yml` |
| Merge robot | Merging labeled bot pull requests | `sonic-pipelines`, `azure-pipelines/automation-pr-scan.yml` |
| Renovate | What manifests declare, and hand-pinned versions | Each repository's `renovate.json` |

**The pip seam.** The pip build hook in `src/sonic-build-hooks/scripts/buildinfo_base.sh` passes the frozen `versions-py3` file to every `pip install` as a constraint file. It releases a package from the constraint only when an exact version appears on the command line, and it does not read `-r requirements.txt`. A Renovate bump to a `requirements.txt` therefore conflicts with the frozen constraint until the next freeze.

| Resolution | Effect |
|------------|--------|
| Exclude `pip_requirements` and `setup-py` | Python stays with the freeze pipeline. Chosen for the first phases |
| Teach the build hook to read requirements files | Removes the seam |
| Order the Renovate pull request behind a re-freeze | Keeps both, with a dependency between them |

#### 7.9 Rollout

| Phase | Work |
|-------|------|
| 1 | Docker, containerd and OpenTelemetry custom managers in `sonic-buildimage`, on `master` |
| 2 | Native managers on `master` in `sonic-buildimage` and the owned repositories holding `go.mod` or `Cargo.toml` |
| 3 | Rust and FIPS Go custom managers |
| 4 | Remaining owned repositories, and the `202611` branch |
| 5 | The `automerge` label on security updates, once the robot check evaluation in [7.6](#76-approval-and-merge) has landed and the earlier phases have run under review for one release cycle |
| 6 | A resolution for the pip seam |

### 8. SAI API

No change.

### 9. Configuration and management

#### 9.1 Manifest

Not applicable. This is not a SONiC Application Extension.

#### 9.2 CLI/YANG model Enhancements

No change.

#### 9.3 Config DB Enhancements

No change.

#### 9.4 Renovate configuration

Shared settings live in one preset at `renovate/default.json` in `sonic-net/sonic-pipelines`, beside the merge robot and the submodule updater. Each repository extends it:

```json
{
  "extends": ["local>sonic-net/sonic-pipelines//renovate/default"]
}
```

Repository-specific settings, such as custom managers, sit beside the `extends` line. The double slash selects a file in a subdirectory.

The preset:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "baseBranchPatterns": ["master", "202611"],
  "reviewers": ["team:sonic-security-wg"],
  "dependencyDashboard": true,
  "osvVulnerabilityAlerts": true,
  "separateMajorMinor": true,
  "separateMinorPatch": true,
  "enabledManagers": ["gomod", "cargo", "github-actions", "dockerfile", "custom.regex"],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"]
  },
  "packageRules": [
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
    },
    {
      "description": "Release branches take security updates only",
      "matchBaseBranches": ["202611"],
      "matchPackageNames": ["*"],
      "enabled": false
    },
    {
      "description": "Release branches also take patch and minor updates to hand-pinned versions",
      "matchBaseBranches": ["202611"],
      "matchManagers": ["custom.regex"],
      "matchUpdateTypes": ["patch", "minor"],
      "enabled": true
    },
    {
      "description": "Release branch owner reviews release branch pull requests",
      "matchBaseBranches": ["202611"],
      "additionalReviewers": ["<202611 release owner>"]
    },
    {
      "description": "Security updates below a major version merge unattended",
      "matchJsonata": ["isVulnerabilityAlert = true"],
      "matchUpdateTypes": ["patch", "minor"],
      "addLabels": ["automerge"]
    },
    {
      "description": "FIPS Go is published by SONiC; open only on dashboard approval",
      "matchManagers": ["custom.regex"],
      "matchDatasources": ["golang-version"],
      "dependencyDashboardApproval": true
    }
  ]
}
```

The `automerge` rule is added in rollout phase 5 and is absent before it.

#### 9.5 Setup steps

| Step | Who | Work |
|------|-----|------|
| 1 | Organization administrator | At <https://github.com/apps/renovate>, select **Configure**, choose `sonic-net`, grant access to all repositories, and grant read access to Dependabot alerts |
| 2 | Organization administrator, Security WG | Create the `sonic-security-wg` team with the public Working Group membership |
| 3 | SONiC Foundation EasyCLA administrators | Give the Renovate bot the same EasyCLA treatment as `mssonicbld` |
| 4 | `sonic-pipelines` maintainers | In `automation-pr-scan.yml`, add the Renovate bot to the author filter, add every Renovate repository to the `repos` parameter, and fix the check evaluation in [7.6](#76-approval-and-merge) |
| 5 | `sonic-pipelines` maintainers | Add `renovate/default.json` |
| 6 | Each repository's owners | Add a `renovate.json` extending the preset |

Renovate does nothing in a repository until step 6. Dependabot alerts must also be enabled on each repository for GitHub vulnerability alerts to reach Renovate.

| Action | Effect |
|--------|--------|
| Remove the `automerge` rule from the preset | Nothing merges unattended |
| Remove a repository's `renovate.json` | Renovate ignores that repository |
| Uninstall the app | Renovate stops everywhere |

### 10. Warmboot and Fastboot Design Impact

No direct impact. Renovate changes no code that runs at boot. A dependency bump passes the same warmboot and fastboot tests as any other pull request.

| Question | Answer |
|----------|--------|
| Added to the boot critical chain | Nothing |
| New CPU work on the boot path | None |
| Third party updates | Each is gated by the same pipeline as any other pull request |
| New service or container | None |

### 11. Memory Consumption

No change. Nothing is added to the image.

### 12. Restrictions/Limitations

| Limitation | Effect |
|------------|--------|
| Hand-pinned versions are never classified as security updates | No advisory feed sits behind a custom manager. They are enabled by name and merged by a reviewer. See [7.5](#75-branch-policy) |
| The merge robot bypasses the review requirement | Required status checks are still enforced by GitHub. Other checks are enforced by the robot. See [7.6](#76-approval-and-merge) |
| The FIPS Go pin depends on a SONiC FIPS build | Renovate lists the upstream release on the dashboard. The bump lands after SONiC publishes the package |
| Renovate reads only what a manifest declares | Versions resolved at build time belong to the version freeze pipeline |
| npm lockfiles inside Debian's Go and Ruby packages are not reached | They are part of Debian's packages and are not SONiC dependencies |
| Findings with no published fix are not addressed | Nothing can update to a fix that does not exist. Shipping less is the [EOL plan](../eol-planning/202611-eol-and-deprecation.md)'s remit |
| SONiC's Debian rebuilds are not covered | SBOM-driven triage covers them |
| A bump can conflict with a local patch | Locally patched components are out of scope |
| Python is excluded | See the pip seam in [7.8](#78-existing-automation) |

### 13. Testing Requirements/Design

#### 13.1 Unit Test cases

Renovate ships no code into SONiC. The configuration is tested:

| Test | Method |
|------|--------|
| Configuration is valid | `npx --yes --package renovate -- renovate-config-validator` in CI on every change to a `renovate.json` or the preset |
| Custom managers match the right lines | A Renovate run against a fork finds `DOCKER_VERSION`, `CONTAINERD_IO_VERSION`, `OTEL_VERSION`, `FIPS_GOLANG_VERSION` and the `rustup` toolchain, and nothing else |
| Custom managers write the right value | In that run, each pushed branch's diff keeps the `~$IMAGE_DISTRO` suffix, `containerd.io` tracks its own package, and the new version exists in the apt index |
| Release branch rules hold | A run against `202611` proposes security updates and hand-pinned patch and minor updates only |
| Grouping is correct | A run against `master` proposes one pull request per ecosystem per update type, and majors one per dependency |
| A major security update is not labeled `automerge` | A run against a fork pinned to a vulnerable version whose fix needs a major bump opens a pull request with the `security` label alone |

#### 13.2 System Test cases

Every Renovate pull request runs the existing SONiC pipeline. No new test infrastructure is required.

| Test | Method |
|------|--------|
| A bumped image builds | `Azure.sonic-buildimage` on the pull request |
| A bumped image works | The existing regression suite |
| Warm and fast reboot are unaffected | The existing warmboot and fastboot tests |
| Fixable findings go down | An SBOM scan of each release branch build, compared run to run |

The scan and the comparison:

```bash
make ENABLE_SBOM=y target/sonic-broadcom.bin
python3 scripts/sbom_vuln_scan.py --vex vex/ target/sonic-broadcom.bin.cdx.json
python3 scripts/sbom_vuln_diff.py <previous>.vuln.json target/sonic-broadcom.bin.vuln.json
```

### 14. Open/Action items

Owners come from `CODEOWNERS` where a repository has one, and from the organization or Foundation for an account or policy setting. `sonic-pipelines` has no `CODEOWNERS`, so its items go to its maintainers. A suggested owner has not agreed to the work.

| # | Item | Touches | Suggested owner |
|---|------|---------|-----------------|
| 1 | Authorize the Renovate app on the `sonic-net` organization | Organization settings | Organization administrators |
| 2 | Create the `sonic-security-wg` team | Organization settings | Organization administrators, Security WG |
| 3 | Give the Renovate bot the EasyCLA treatment `mssonicbld` has | EasyCLA configuration | SONiC Foundation EasyCLA administrators |
| 4 | Fix the merge robot check evaluation in [7.6](#76-approval-and-merge). Prerequisite for the `automerge` label | `sonic-pipelines` | `sonic-pipelines` maintainers, Security WG |
| 5 | Add the Renovate bot to the merge robot author filter, and each Renovate repository to its `repos` parameter | `sonic-pipelines` | `sonic-pipelines` maintainers |
| 6 | Add the shared preset at `renovate/default.json` | `sonic-pipelines` | `sonic-pipelines` maintainers |
| 7 | Add a `202611` entry to `release-owners_github_account.json` | `sonic-pipelines` | 202611 release manager |
| 8 | Choose a resolution for the pip seam | `src/sonic-build-hooks/` | `@sonic-net/sonic-build` |
| 9 | Confirm the FIPS Go release cadence, so the toolchain pin has something to track | `src/sonic-fips/`, `rules/sonic-fips.mk` | `@sonic-net/sonic-build` |
| 10 | Stand up SBOM-driven triage for the Debian packages SONiC rebuilds | — | Security WG |
| 11 | Confirm the release branch policy in [7.5](#75-branch-policy) | `renovate.json` | Security WG |
