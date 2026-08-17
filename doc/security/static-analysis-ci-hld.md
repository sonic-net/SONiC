# Static Analysis CI Gates for SONiC Repositories #

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
  - [4.1 Current state](#41-current-state)
  - [4.2 Why this matters — measured evidence](#42-why-this-matters--measured-evidence)
    - [4.2.1 The existing CodeQL and Semgrep workflows are not gates](#421-the-existing-codeql-and-semgrep-workflows-are-not-gates)
  - [4.3 Design summary](#43-design-summary)
- [5. Requirements](#5-requirements)
  - [5.1 Functional requirements](#51-functional-requirements)
  - [5.2 Non-functional requirements](#52-non-functional-requirements)
  - [5.3 Exemptions](#53-exemptions)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Is it a built-in SONiC feature or an Application Extension?](#71-is-it-a-built-in-sonic-feature-or-an-application-extension)
  - [7.2 The `sonic-net/sonic-ci` repository](#72-the-sonic-netsonic-ci-repository)
  - [7.3 The severity manifest](#73-the-severity-manifest)
    - [7.3.1 Gate scope: repo-wide versus regression-only](#731-gate-scope-repo-wide-versus-regression-only)
  - [7.4 Per-language design](#74-per-language-design)
    - [7.4.1 Python — `ruff` + `pyright`](#741-python--ruff--pyright)
    - [7.4.2 C/C++ — `clang-tidy`](#742-cc--clang-tidy)
    - [7.4.3 Rust — `clippy`](#743-rust--clippy)
    - [7.4.4 Go — `golangci-lint`](#744-go--golangci-lint)
    - [7.4.5 Shell — `shellcheck`](#745-shell--shellcheck)
  - [7.5 Suppressions (R7)](#75-suppressions-r7)
  - [7.6 Build dependency](#76-build-dependency)
    - [7.6.1 Moving the remaining pipelines to trixie](#761-moving-the-remaining-pipelines-to-trixie)
  - [7.7 Rollout plan](#77-rollout-plan)
  - [7.8 Items explicitly not changed](#78-items-explicitly-not-changed)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1. Manifest](#91-manifest)
  - [9.2. CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3. Config DB Enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
  - [Warmboot and Fastboot Performance Impact](#warmboot-and-fastboot-performance-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1. Unit Test cases](#131-unit-test-cases)
  - [13.2. System Test cases](#132-system-test-cases)
  - [13.3. Regression testing](#133-regression-testing)
- [14. Open/Action items](#14-openaction-items)
- [Appendix A: Measured baseline](#appendix-a-measured-baseline)
- [Appendix B: Python 2 files proposed for removal](#appendix-b-python-2-files-proposed-for-removal)
- [Appendix C: Repository coverage](#appendix-c-repository-coverage)

### 1. Revision

| Rev | Date       | Author     | Change Description |
|-----|------------|------------|--------------------|
| 0.1 | 2026-08-17 | Brad House | Initial version    |

### 2. Scope

SONiC has no working merge gate for code defects. Every language in the tree is analyzed
either not at all or by something that reports and is ignored, so code a standard analyzer
would reject merges routinely.

This document proposes one: analyzers wired into the build pipelines each repository
already runs, blocking a merge when a pull request introduces a defect. How that is built
is covered in Sections 6 and 7.

**In scope.** Python, C/C++, Rust, Go and shell, in the repositories the SONiC community
owns, on the `master` branch.

**Out of scope.** Code the community cannot change — vendor-hosted platform submodules and
vendored upstream projects such as FRR and scapy. Release branches, which are not
backported to. And anything that requires running the code rather than reading it, such as
sanitizers and coverage, which SONiC already handles separately. Exact repository lists are
in [Appendix C](#appendix-c-repository-coverage).

This document sits under `doc/security/` because a gate on code defects is a security
control: memory-safety findings, the `bandit`-derived Python rules, and Rust's correctness
lints all arrive through it, and security-specific rules can later be added in one place
rather than repository by repository.

### 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| **ruff** | A fast Python linter (Rust implementation) covering pyflakes, pycodestyle, bugbear, bandit and others |
| **pyright** | A Python static type checker (Microsoft) |
| **Clang Static Analyzer** | Traces execution paths through code to find null dereferences, leaks, and uninitialized memory. Runs as `clang-tidy`'s `clang-analyzer-*` checks |
| **clang-tidy** | The C/C++ analyzer used here. Runs both the Clang Static Analyzer and pattern-matching checks |
| **bear** | Builds that record by watching an ordinary `make` run |
| **clippy** | The Rust lint tool, distributed with the Rust toolchain |
| **golangci-lint** | A Go lint aggregator wrapping `go vet`, `staticcheck`, `errcheck`, and others |
| **Compilation database** | `compile_commands.json` — a record of the exact compiler command used for each source file, so an analyzer sees the same defines and include paths the real build did |
| **Gating rule** | Breaking it fails the pipeline and blocks the merge |
| **Advisory rule** | Breaking it is reported in the pipeline output but does not block the merge |

### 4. Overview

#### 4.1 Current state

The SONiC tree spans 52 populated submodules plus a large body of code held directly in
`sonic-buildimage`. Merge gating is performed by per-repository Azure DevOps pipelines
(`azure-pipelines.yml`), which run inside the `sonic-slave-<debian_version>` container
images that the build already depends on. A small number of repositories additionally
carry GitHub Actions workflows for CodeQL and Semgrep.

Static analysis coverage today is close to zero:

| Repository | Static analysis present |
|------------|-------------------------|
| `sonic-utilities` | A `Pretest` stage runs `pre-commit`, whose only hook is `flake8 --diff` with `--max-line-length=120`. The stage is declared `continueOnError: true`, so **it does not block a merge.** |
| `sonic-gnmi` | The `Makefile` default target depends on a `gofmt -l` check. This is a real gate, but only enforces *formatting* — no `go vet`, no `staticcheck`. |
| ~19 repositories | GitHub Actions CodeQL and Semgrep. Both are guarded by `if: github.repository_owner == 'sonic-net'` and therefore do nothing in any fork, neither is a required check, and in practice neither functions as a gate. Measured evidence in [Section 4.2.1](#421-the-existing-codeql-and-semgrep-workflows-are-not-gates). |
| Everything else | None. |

Concretely, this means:

- **C/C++** (~1,700 files across `sonic-swss`, `sonic-sairedis`, `sonic-swss-common`,
  `linkmgrd`, `sonic-bmp`, `sonic-stp`, `dhcprelay`, `dhcpmon` and others) has no
  static analyzer of any kind.
- **Rust** (`sonic-swss`, `sonic-swss-common`, `sonic-host-services`, `sonic-dash-ha`)
  never runs `clippy`. All four workspaces carry an identical copy-pasted
  `[workspace.lints.rust]` block with four `warn`-level lints, no `[workspace.lints.clippy]`
  section, and no `--deny warnings`, so even those four lints cannot fail a build.
- **Go** (~440 files across `sonic-gnmi`, `sonic-mgmt-common`, `sonic-restapi`,
  `sonic-mgmt-framework`) runs no `go vet`, no `staticcheck`, and no lint aggregator.
- **Python** — by far the largest surface, at 3,277 files inside `sonic-buildimage`
  alone plus ~1,500 across the submodules — is gated only by a non-blocking,
  diff-scoped `flake8` in a single repository.

#### 4.2 Why this matters — measured evidence

The analysis below was produced by running `ruff 0.16.3` over the in-scope tree.
Full numbers are in [Appendix A](#appendix-a-measured-baseline).

**122 files in the tree are still Python 2 and cannot be parsed by any Python 3 tool.**
56 of those are tracked directly in `sonic-buildimage` under `device/` and `platform/`
and are packaged into shipping images; the remaining 66 are inside excluded
vendor/third-party submodules. Example, from
`device/ragile/x86_64-ragile_ra-b6510-32c-r0/fantlv.py:204`:

```python
        except Exception as e:
            print e
```

**Pyflakes reports 445 `undefined-name` (F821) findings** outside those files. Sampling
shows these are not false positives — they are latent `NameError` crashes, and they
cluster in exactly the error-handling paths that only execute once something has
already gone wrong:

```
platform/pensando/.../fru_tlvinfo_decoder.py:269   F821 Undefined name `raw_input`
platform/pddf/i2c/utils/pddfparse.py:2449          F821 Undefined name `unicode`
platform/pddf/.../pddf_chassis.py:296              F821 Undefined name `syslog`
platform/pddf/.../pddf_eeprom.py:99                F821 Undefined name `TlvInfoDecoder`
platform/pddf/.../sonic_platform_ref/sfp.py:5      F821 Undefined name `e`
```

`raw_input` and `unicode` are Python 2 builtins that do not exist in Python 3. `syslog`
and `TlvInfoDecoder` are simply never imported. Each of these is a guaranteed crash the
moment the line is reached, in platform code that runs on shipping hardware.

These defects are cheap to find. A full `ruff` pass over all 3,277 Python files in
`sonic-buildimage` completes in **0.29 seconds**.

##### 4.2.1 The existing CodeQL and Semgrep workflows are not gates

It is reasonable to ask whether SONiC already has this capability, given that ~19
repositories carry CodeQL and Semgrep workflows. Measured against
`sonic-net/sonic-buildimage` on 2026-08-17, they do not.

**Semgrep is permanently failing and is ignored.** The workflow runs on both `push` and
`pull_request`. Of the **last 100 `push` runs, 100 failed** — every one. A representative
failing run reports:

```
 • Findings: 338 (338 blocking)
 • Rules run: 1077
 • Targets scanned: 15993
   Has findings for blocking rules so exiting with code 1
```

Master has carried 338 blocking Semgrep findings continuously. Pull requests pass only
because `semgrep ci` diff-scopes against a baseline on PR events, so pre-existing findings
are invisible there. The full-tree result is produced on every push to master, is red every
time, and blocks nothing because the code has already merged.

**CodeQL is configured for quality, not security, and reports to a dashboard nobody
gates on.** Its config requests the `security-and-quality` and `security-extended` query
suites. `sonic-buildimage` currently has **more than 3,100 open code-scanning alerts**. Of
the first 3,000 sampled, **50 carry a `security` tag and 2,950 do not** — they are
correctness and maintainability findings such as `py/mixed-returns`
(severity `note`, tags `correctness, quality, reliability`). By severity, a 100-alert
sample was 86 `note`, 7 `warning`, 7 `error`.

CodeQL is also configured `language: [ 'python' ]` in every repository that has it,
including the C/C++ repositories. `sonic-swss` and `sonic-sairedis` carry a CodeQL
workflow that analyzes none of their ~1,150 C/C++ files.

Two conclusions follow, and both shape this design. First, "SONiC already runs static
analysis" is not an accurate description of the status quo — it runs two reporters that
nothing acts on. Second, an analyzer that produces findings without gating produces a
backlog and nothing else; 3,100 alerts and 338 blocking findings are what that looks like
after several years. The gate, not the analyzer, is the part that is missing.

#### 4.3 Design summary

1. Create `sonic-net/sonic-ci` as the single home for CI templates, analyzer
   configuration, and the rule severity manifest.
2. Each in-scope repository adds a ~10-line reference to that repository. All tool
   versions, rule selections, and gate/advisory decisions live centrally; rolling out a
   change to the entire fleet is a tag bump.
3. Analysis for compiled languages runs as additional **steps inside the existing build
   job**, reusing the already-provisioned dependencies and build tree. Analysis for
   Python and shell runs as a small standalone `Pretest` stage on the cheap
   `sonic-ubuntu-1c` pool, because it needs no build at all.
4. A small, high-confidence rule set blocks merges from day one, everywhere in the
   repository. A much larger set blocks only defects a pull request *introduces*,
   measured against the target branch — which is what makes a 35,862-finding backlog
   survivable without a cleanup nobody would do. Everything else is reported only.
5. The 56 Python 2 files still in the tree are proposed for removal.

### 5. Requirements

#### 5.1 Functional requirements

| ID | Requirement |
|----|-------------|
| R1 | Static analysis MUST run automatically on every pull request to an in-scope repository. |
| R2 | A defined subset of findings MUST block the merge; the pipeline MUST fail. |
| R3 | Findings outside that subset MUST be reported without blocking, and MUST be visible in the pipeline result. |
| R3a | A rule MUST be enforceable against defects a pull request introduces while its pre-existing occurrences are only reported. "Introduced" MUST be determined by comparing findings against the target branch, not by checking which lines the pull request touched. |
| R4 | The set of tools, their versions, their rule selections, and the gate/advisory split MUST be defined in exactly one place and consumed by all repositories. |
| R5 | The per-repository change required to adopt the capability MUST be small enough to review at a glance and MUST NOT need to be edited to change rules or tool versions. |
| R6 | A developer MUST be able to reproduce a CI finding locally with a single documented command. |
| R7 | The gate MUST support per-repository and per-path suppression, with suppressions checked into the repository and reviewable. |
| R8 | Analysis MUST cover Python, C/C++, Rust, Go, and shell. |

#### 5.2 Non-functional requirements

| ID | Requirement |
|----|-------------|
| R9 | Analysis MUST NOT require provisioning new build agents or a new CI system. |
| R10 | For compiled languages, analysis MUST NOT introduce a second full compilation of the source tree. |
| R11 | Added wall-clock time MUST be bounded and reported per language; the target is < 10% of existing job duration for interpreted languages and < 40% for C/C++. |
| R12 | Analyzers MUST be available in, or installable into, the existing `sonic-slave-trixie` image. Preference is given to tools already present. |
| R13 | Adoption MUST be incremental. A repository that has not yet adopted MUST be unaffected. |
| R14 | The design MUST function in downstream forks. It MUST NOT depend on `github.repository_owner == 'sonic-net'` guards or on organization-specific secrets. |

#### 5.3 Exemptions

- Vendor-hosted platform submodules and vendored upstream projects are excluded; the
  exact list and the reasoning are in [Appendix C](#appendix-c-repository-coverage).
- No requirement is placed on retroactively achieving a clean tree. Existing findings
  outside the hard-gate set are tracked, not blocked on.

### 6. Architecture Design

There is no change to the SONiC runtime architecture. Nothing described here is
compiled into, packaged into, or executed on a switch. This design affects only the
build and CI infrastructure.

Two pieces of build infrastructure change:

1. **The `sonic-slave-trixie` container image** gains five analyzer packages. Most of what
   is needed — `clang`, `shellcheck`, `nodejs`, Go, and Rust — is already there
   ([Section 7.6](#76-build-dependency)).
2. **Each repository's Azure pipeline** gains either a small standalone stage or a few
   extra steps in the build job it already runs. Both come from templates held in the new
   `sonic-ci` repository, so the repository itself carries almost no configuration.

```
              ┌──────────────────────────────────────────────┐
              │   sonic-net/sonic-ci   (new, see 7.2)        │
              │   templates · tool configs · severity.yml    │
              └───────────────────┬──────────────────────────┘
                                  │  referenced by tag
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
   ┌──────▼─────────┐    ┌────────▼────────┐    ┌─────────▼──────┐
   │ sonic-utilities│    │   sonic-swss    │    │   sonic-gnmi   │
   │                │    │                 │    │                │
   │ separate stage │    │ steps inside    │    │ steps inside   │
   │ (no build      │    │ the existing    │    │ the existing   │
   │  needed)       │    │ build job       │    │ build job      │
   └────────────────┘    └─────────────────┘    └────────────────┘
```

This cross-repository template mechanism is not new to SONiC. `sonic-swss-common`,
`sonic-sairedis`, and `sonic-utilities` already declare `resources: repositories:`
entries pointing at each other in order to share build templates. This design applies
the same, already-proven pattern to a repository whose sole purpose is to be shared.

### 7. High-Level Design

#### 7.1 Is it a built-in SONiC feature or an Application Extension?

Neither. This is build/CI infrastructure. No manifest, no container, no package.

#### 7.2 The `sonic-net/sonic-ci` repository

A new repository under `sonic-net`:

```
sonic-ci/
├── azure/
│   ├── python-pretest.yml      # standalone stage: ruff + pyright
│   ├── shell-pretest.yml       # standalone stage: shellcheck
│   ├── cpp-steps.yml           # steps injected into an existing build job
│   ├── rust-steps.yml          # steps injected into an existing build job
│   └── go-steps.yml            # steps injected into an existing build job
├── config/
│   ├── ruff.toml
│   ├── pyrightconfig.json
│   ├── clang-tidy.yml          # copied to .clang-tidy at run time
│   ├── clippy-lints.toml       # canonical [workspace.lints.*] block
│   └── golangci.yml            # copied to .golangci.yml at run time
├── bin/
│   └── sonic-analyze           # single entry point, used by CI and by developers
├── severity.yml                # THE gate/advisory manifest
├── tool-versions.yml           # pinned analyzer versions
└── docs/
    ├── adopting.md
    ├── suppressions.md
    └── local-usage.md
```

**Consumption.** A repository adopts the capability by adding a `resources` block and
one template reference. For a Python repository:

```yaml
resources:
  repositories:
  - repository: sonic-ci
    type: github
    name: sonic-net/sonic-ci
    endpoint: sonic-net
    ref: refs/tags/v1.0.0

stages:
- stage: StaticAnalysis
  jobs:
  - template: azure/python-pretest.yml@sonic-ci
    parameters:
      profile: default
```

For a repository with a compiled build, the steps template is spliced into the
existing job instead:

```yaml
  steps:
  - checkout: self
    clean: true
    submodules: true
  # ... existing dependency installation, artifact downloads ...
  - template: azure/rust-steps.yml@sonic-ci
  - template: azure/cpp-steps.yml@sonic-ci
    parameters:
      make_target: all
  # ... existing build and test steps ...
```

Everything arrives by bumping that tag — new rules, tool upgrades, a rule moving from
advisory to blocking. Each is one reviewable commit in the consuming repository, and
reverting is the same operation. The repository's own diff stays at about ten lines and
never needs editing again (R5).

#### 7.3 The severity manifest

One file decides what blocks a merge and what is merely reported, for every repository and
every language:

```yaml
# Three scopes (see 7.3.1):
#   gate      - fails on any occurrence, repo-wide
#   gate-new  - fails only on findings absent from the target-branch baseline
#   advisory  - reported, never fails
version: 1

python:
  tool: ruff
  gate:
    # pyflakes — near-certain defects
    - F821   # undefined name
    - F811   # redefinition of unused name
    - F502, F506, F507        # broken %-format strings
    - F522, F524              # broken .format() calls
    - F601, F602              # duplicate dict keys
    - F632   # `is` comparison with a literal
    - F702, F706, F707        # misplaced continue / return / except
    - E9     # syntax and IO errors
    # flake8-bugbear — high-confidence bug patterns
    - B002   # unary prefix increment (a Python no-op that looks like C)
    - B006   # mutable argument default
    - B012   # break/continue/return inside finally
    - B017   # assertRaises(Exception)
    - B023   # function definition does not bind loop variable
  gate-new:                 # vs. target-branch baseline
    - E        # pycodestyle
    - W        # pycodestyle warnings, incl. W605 invalid escape sequence
    - B        # remaining flake8-bugbear
    - SIM      # flake8-simplify
    - UP       # pyupgrade
    - I        # import sorting
  advisory: all

python_types:
  tool: pyright
  mode: standard          # see 7.4.1
  gate:
    - reportUndefinedVariable
    - reportMissingImports
    - reportSelfClsParameterName
    - reportAssertAlwaysTrue
  advisory: all

cpp:
  tool: clang-tidy
  gate:
    # Clang Static Analyzer — path-sensitive, near-certain defects
    - clang-analyzer-core.*            # null deref, division by zero, uninitialized
    - clang-analyzer-unix.Malloc       # leaks, double free, use-after-free
    - clang-analyzer-cplusplus.*       # new/delete mismatch, self-assignment
    # AST patterns that are wrong on sight
    - bugprone-use-after-move
    - bugprone-sizeof-expression
    - bugprone-assignment-in-if-condition
    - bugprone-suspicious-memset-usage
    - bugprone-integer-division
    - bugprone-string-integer-assignment
  gate-new:               # vs. target-branch baseline
    - bugprone-*          # remaining bugprone checks
    - performance-*
    - cert-*
  advisory: all           # everything else enabled in config/clang-tidy.yml

rust:
  tool: clippy
  gate: deny-warnings     # see 7.4.3
  advisory: []

go:
  tool: golangci-lint
  gate:
    - govet
    - staticcheck
    - errcheck
    - ineffassign
  gate-new:               # baseline-differenced by sonic-analyze, not golangci's native mode
    - gosimple
    - unused
    - revive
  advisory: all

shell:
  tool: shellcheck
  gate: [error]
  gate-new: [warning]
  advisory: [info, style]
```

Promoting a rule is a one-line change here plus a tag bump. Whether to promote is a
community decision, informed by the advisory data the pipelines will have been publishing.

##### 7.3.1 Gate scope: repo-wide versus regression-only

`severity.yml` assigns each rule one of three scopes:

| Scope | Behaviour | Purpose |
|---|---|---|
| `gate` | Fails on **any** occurrence, anywhere in the repository | The small, high-confidence set whose backlog Phase 2 clears |
| `gate-new` | Fails only on findings **absent from the target branch's baseline** | Large rule sets whose existing backlog will never be cleared |
| `advisory` | Reported and published; never fails | Everything else |

`gate-new` is what makes the measured backlog tractable. `sonic-buildimage` carries 35,862
`ruff` findings under the full rule set — a number no one will clear. Enforcing those rules
against a baseline means the tree stops getting worse immediately, at zero migration cost.

**Why baseline differencing rather than changed-line filtering.**

The obvious implementation is to filter findings against the lines a PR touched. It is
wrong, and measurably so: for path-sensitive checks the reported line is the *symptom*,
while the change that caused it is elsewhere. The following was run against `clang-tidy`
18 with `clang-analyzer-core.*`:

```c
 4    char *p = NULL;
 5    if (n > 0) p = malloc(n);
 6    if (!p) return NULL;          // PR changes this line to `if (n > 1000)`
 7    strcpy(p, "hi");              // unchanged, byte-identical
```

`git diff` reports **line 6** as the only change. The analyzer's verdict goes from no
findings to:

```
after.c:7:5: warning: Null pointer passed to 1st parameter expecting 'nonnull'
             [clang-analyzer-core.NonNullParamChecker]
```

The finding lands on **line 7**, which the PR did not touch. A changed-line filter
suppresses it, and a newly-introduced null dereference merges with a green gate. The same
class of miss applies to `ruff` `F401` when the last use of an import is deleted, and to
`pyright` when a signature change in one file breaks a call site in another.

Comparing *finding sets* rather than *locations* has no such blind spot: the finding is
absent from the baseline and present at HEAD, so it is new regardless of where it is
reported.

**Fingerprinting.**

Findings must survive line-number shifts, or every insertion above a finding makes
everything below it look new. Each finding is keyed as:

```
(repo-relative path, ruleId, sha1(stripped source line), nth-occurrence-of-that-key)
```

**The fingerprint must be computed at analysis time**, against the tree as it was
analyzed. It cannot be reconstructed later from stored line numbers, because those
line numbers no longer address the same source. `sonic-analyze` therefore emits
fingerprints alongside findings, and the baseline artifact stores fingerprints, not
locations.

Validated on a file with four pre-existing findings: inserting 20 lines above them and
introducing one genuine new defect yields exactly **one** new fingerprint, with the four
pre-existing findings correctly matched despite every line number having shifted.

**Obtaining the baseline.**

The baseline is the finding set of the PR's target branch, published as a pipeline
artifact by that branch's own build. Pull requests download it rather than recomputing it,
so **a PR costs one analysis run, not two** — the target-branch analysis has already
happened on merge. This reuses the `DownloadPipelineArtifact@2` /
`runVersion: latestFromBranch` mechanism that every SONiC pipeline already uses to fetch
`libswsscommon`, `sairedis`, and `libnl` artifacts; no new infrastructure is introduced.

Tooling note: only `golangci-lint` offers a native equivalent
(`issues.new-from-merge-base`). It is **not** used, because it is blame-based and shares
the changed-line blind spot above. All languages go through the same `sonic-analyze`
baseline comparison, which also keeps the behaviour uniform and centrally defined. Every
analyzer emits structured output sufficient to fingerprint from:

| Tool | Structured output | Notes |
|---|---|---|
| `ruff` | `--output-format sarif` or `json` | SARIF carries no `partialFingerprints`; fingerprints are computed by `sonic-analyze` |
| `pyright` | `--outputjson` | `range.start.line` is **0-based**, unlike every other tool |
| `clang-tidy` | `run-clang-tidy -export-fixes` | note chains retained for multi-location findings |
| `clippy` | `--message-format=json` | `spans[].line_start` |
| `golangci-lint` | `--out-format json` | native `new-from-*` deliberately unused |
| `shellcheck` | `--format=json` | `line`, `endLine` |

**Known behaviours of this approach.**

- **Editing a line that carried a pre-existing finding re-reports it as new.** The line
  hash changes, so the match is lost. This is treated as correct: a PR that touches the
  line takes ownership of the finding on it.
- **Baseline drift.** The baseline comes from the tip of the target branch, not the PR's
  merge-base, so a finding introduced by an unrelated commit can surface in the next PR to
  run. The alternative — analysing the merge-base per PR — costs a second full run. Drift
  is accepted; the mis-attributed finding is real and still needs fixing.
- **File renames** invalidate every fingerprint in the renamed file. `sonic-analyze`
  applies `git diff -M` rename detection to remap paths before comparing.
- **No baseline** (first adoption, or a new branch) is treated as an empty gate: findings
  are recorded to establish the baseline and nothing fails.
- **Fixed findings** — present in baseline, absent at HEAD — are reported as an
  improvement count. They do not affect the gate result.

#### 7.4 Per-language design

##### 7.4.1 Python — `ruff` + `pyright`

`ruff` is a single binary replacing `flake8`, `isort`, `pyupgrade`, `pycodestyle`,
`flake8-bugbear` and part of `bandit`. It finds bugs but does not check types, so `pyright`
runs alongside it. On `sonic-buildimage`, `ruff`'s pyflakes rules alone find 8,239 issues
including 445 guaranteed `NameError` sites; `pyright` finds a different class — wrong
argument counts, attribute access on the wrong type — that no linter can see.

`pyright` runs in `standard` mode. `basic` is too quiet on unannotated code to be worth
running, and `strict` would demand annotations that do not exist. It will report a lot on
first run; those findings are reported, not blocking, and they tell us what is worth
promoting later.

Both run in a standalone `Pretest` stage on the cheap `sonic-ubuntu-1c` pool, mirroring the
stage `sonic-utilities` already has. Neither needs a compiler or any build artifact, so
putting them in a build job would only slow them down. A full `ruff` pass over all 3,277
files takes **0.29 s**; `pyright` is the dominant cost at an expected 1–3 minutes, still
well short of the build stage that follows.

Developers reproduce any CI finding with:

```sh
sonic-analyze python              # whole repo, same rules as CI
sonic-analyze python --gate-only  # just the merge-blocking subset
```

##### 7.4.2 C/C++ — `clang-tidy`

One tool covering both kinds of C/C++ analysis. 119 of its 538 checks are the Clang Static
Analyzer, which traces execution paths to find null dereferences, leaks, and uninitialized
memory. The rest match code against known-bad shapes — `bugprone-*` (80), `cert-*` (39),
`performance-*` (19) and others — catching things like assignment inside an `if` condition
or string concatenation in a loop. The older `scan-build` covers only the first group, so
`clang-tidy` replaces it rather than joining it. `cppcheck` is not used; `clang-tidy`
subsumes nearly all of it.

**How it runs.**

```sh
# 1. Build normally, recording each compiler invocation.
bear --output compile_commands.json -- make -j$(nproc)

# 2. Analyse in parallel, replaying those invocations.
run-clang-tidy -j$(nproc) -quiet \
               -header-filter='^(?!.*/(third_party|generated)/).*' \
               -warnings-as-errors="$(sonic-analyze cpp --gate-list)"
```

Both steps go inside the existing build job, which has already installed the dependencies
and configured the tree. `bear` wraps the `make` that is already there.

**Preprocessor defines and feature flags are exact, not approximated.** The compilation
database records the real command used for each source file — every `-D`, `-I`, `-std` and
`-f*` flag `./configure` worked out — and `clang-tidy` replays it. Conditional compilation
and platform macros are seen exactly as the shipped object files see them. Autotools does
not produce this file, which is why `bear` is needed.

**Check selection.** Enabling `*` is unusable — it complains about identifier length and
magic numbers. `sonic-ci` enables `clang-analyzer-*`, `bugprone-*`, `performance-*` and
`cert-*`, leaving `readability-*`, `modernize-*`, `cppcoreguidelines-*` and the
vendor-specific families off.

**What it will not catch.** The analyzer follows paths within one source file and its
headers, not across files — a bug whose cause is in one `.cpp` and whose symptom is in
another is out of reach. (Clang can do cross-file analysis, but it is off by default and
marked experimental.) It also only sees the configuration CI builds; code compiled out by
`#ifdef` is never analyzed.

**Cost.** Roughly doubles the compile phase, since each file is parsed once by gcc and once
by `clang-tidy`. The R11 budget of 40% is against total job time, which for these
repositories is dominated by artifact downloads and unit tests rather than compilation.
Measured during the pilot and recorded here before fleet rollout.

##### 7.4.3 Rust — `clippy`

`cargo clippy` ships with the Rust toolchain already in the image. The gate is:

```sh
cargo clippy --all-targets --workspace -- --deny warnings
```

Each workspace adopts a shared lint block from `sonic-ci`. Every `allow` entry must carry a
comment saying why the lint does not apply; entries without one are rejected in review.
`unknown_lints = "allow"` is set because the image pins Rust 1.86, and lint names
introduced later would otherwise be hard errors. This is the model already running in
production in `sonic-nhcli`.

Rust is the one language starting fully strict, because it is the only one small enough to
clean up outright — 34, 26, 79 and 1 `.rs` files in `sonic-swss`, `sonic-swss-common`,
`sonic-dash-ha` and `sonic-host-services` — and it is the newest code in the tree, so it is
the cheapest moment to set the bar.

Runs as a step before `cargo build`, sharing the same `target/` directory, so the work is
not repeated.

##### 7.4.4 Go — `golangci-lint`

One binary aggregating `govet`, `staticcheck`, `errcheck`, `ineffassign`, `gosimple`,
`unused`, and `revive`, behind a single config file:

```yaml
version: "2"
linters:
  default: none
  enable: [govet, staticcheck, errcheck, ineffassign, gosimple, unused, revive]
```

Pinned to **v2.12.2**. The only constraint is that `golangci-lint` must be built with a Go
version at or above the code's — v2.12.2 is built with Go 1.25, the trixie slave is on Go
1.24.4. `sonic-ci`'s CI checks this on every change, so a future Go bump cannot silently
break the fleet. Details in [Appendix A.6](#appendix-a-measured-baseline).

Runs as a step in the existing build job, after code generation, with generated directories
excluded. `sonic-gnmi`'s existing `gofmt` check in its `Makefile` is left alone.

##### 7.4.5 Shell — `shellcheck`

`shellcheck` is already installed. It runs in the same `Pretest` stage as the Python
analysis: `error` blocks anywhere, `warning` blocks only if the PR introduces it, and
`info`/`style` are advisory. The surface is 460 `.sh` files in `sonic-buildimage` plus
~60 across the submodules.

#### 7.5 Suppressions (R7)

Three mechanisms, in order of preference:

1. **Inline, at the site.** `# noqa: F821` (Python), `// NOLINT(...)` (C/C++),
   `#[allow(clippy::...)]` (Rust), `//nolint:errcheck` (Go). Preferred because the
   suppression is visible to the next reader of the code and dies with the code.
2. **Repository-scoped, in a checked-in file.** `ruff.toml` `[tool.ruff.lint.per-file-ignores]`,
   `.golangci.yml` `issues.exclude-rules`, `[workspace.lints.clippy]` `allow` entries.
   Used for systematic, structural exemptions such as generated code or test fixtures.
3. **Fleet-wide, in `sonic-ci`.** Reserved for defects in the analyzers themselves. Every
   entry carries a comment and a link to the upstream tool issue.

Every suppression at any level must carry a justification comment. `ruff`'s `RUF100`
(unused `noqa`) is enabled as advisory so suppressions that are no longer needed become
visible rather than accumulating.

#### 7.6 Build dependency

Everything runs in `sonic-slave-trixie`. Most of what is needed is already installed —
`clang`, `shellcheck`, `nodejs`, Go 1.24.4, Rust 1.86 and Python 3.13. Five packages are
added:

| Package | For |
|---|---|
| `ruff` | Python linting (`pip3`, single binary) |
| `pyright` | Python type checking (`pip3`, uses the `nodejs` already present) |
| `clang-tidy` | C/C++ analysis. Debian ships this separately from `clang`; the unversioned package tracks the same LLVM the compiler uses (19 on trixie) |
| `bear` | Records the compilation database `clang-tidy` reads |
| `golangci-lint` | Go analysis (v2.12.2, self-contained binary) |

They go in the image rather than being installed per job, so no pipeline depends on network
access at run time. `pylint` stays even though `ruff` supersedes it, because
`sonic-mgmt-framework` invokes it from a build target. `cppcheck` stays but is unused.

One detail worth recording: `clang-tidy` silently ignores a `--checks` pattern that matches
nothing, and its check set changes between LLVM releases. Checks are therefore selected by
family glob (`bugprone-*`) wherever a whole family is wanted, and individually named checks
in `severity.yml` are validated against `clang-tidy --list-checks` by test UT1 — so a check
that disappears in a future LLVM fails `sonic-ci`'s CI instead of quietly ceasing to gate.

##### 7.6.1 Moving the remaining pipelines to trixie

Bookworm is not targeted, and cannot be: `sonic-gnmi`, `sonic-mgmt-common` and
`sonic-mgmt-framework` all declare `go 1.24.4`, while `rules/sonic-fips.mk` pins bookworm to
Go 1.19.8. Those repositories no longer build there.

Five repositories still default their `debian_version` parameter to `bookworm`, and moving
them is a **hard prerequisite**, sequenced into Phase 0. Four of the five already run trixie
jobs alongside their bookworm ones, so for those the change removes a build configuration
rather than adding one:

| Repository | Work required |
|---|---|
| `sonic-swss` | Flip the default, retire the bookworm legs (3 trixie jobs already running) |
| `sonic-swss-common` | Same |
| `sonic-sairedis` | Same |
| `sonic-dash-api` | Same |
| `sonic-dbsyncd` | A real port — it hardcodes the bookworm image and has no trixie job |

`sonic-dbsyncd` is not in the pilot set, so it can land anywhere in Phase 0.

#### 7.7 Rollout plan

**Phase 0 — Foundation.**
- **Prerequisite: move the five bookworm-defaulted pipelines to trixie.** `sonic-swss`,
  `sonic-swss-common`, `sonic-sairedis`, and `sonic-dash-api` already carry working trixie
  jobs, so this is a default flip plus retirement of the bookworm legs. `sonic-dbsyncd`
  requires an actual trixie port. Detail and evidence in
  [Section 7.6.1](#761-moving-the-remaining-pipelines-to-trixie). Nothing else in Phase 0 depends on this
  landing first, but the pilot does.
- Create `sonic-net/sonic-ci` with templates, configs, `severity.yml`, and `sonic-analyze`.
- Add the five missing analyzer packages to `sonic-slave-trixie`.
- Stand up `sonic-ci`'s own CI: templates are lint-checked, `sonic-analyze` is unit
  tested, and the pinned tool versions are validated against the current slave image.
- Tag `v1.0.0`.

**Phase 1 — Pilot (3 repositories, one per integration shape).**

| Repository | Exercises |
|------------|-----------|
| `sonic-utilities` | Python `Pretest` stage; replaces the existing non-blocking `flake8` pre-commit hook. Measured hard-gate backlog: **116**. |
| `sonic-swss` | C/C++ `clang-tidy` **and** Rust `clippy` steps inside one build job — the most complex case. Measured Python hard-gate backlog: 72. |
| `sonic-gnmi` | Go `golangci-lint` steps inside the build job, alongside the retained `gofmt` gate. |

The pilot's exit criteria are: each pilot repository's pipeline is green with the
hard-gate rules enforced; the `bear` + `clang-tidy` wall-clock and peak-RSS deltas on
`sonic-swss` are measured and recorded in this document against the R11 budget and
[Section 11](#11-memory-consumption); and the advisory findings baseline is published for
each pilot repository. Phase 2 does not begin until all three are met.

**Phase 2 — Fleet.** One mechanical PR per remaining in-scope repository, each adding the
~10-line `sonic-ci` reference and clearing that repository's hard-gate backlog. Measured
backlogs are small enough to make this tractable — `sonic-platform-common` 23,
`sonic-platform-daemons` 38, `sonic-host-services` 15, `sonic-snmpagent` 12,
`sonic-ztp` 10.

`sonic-buildimage` itself is sequenced last within phase 2, because it carries the
largest surface and depends on the Python 2 removal below.

**Repositories that cannot clear their backlog.** A repository adopts `sonic-ci` on
schedule regardless. If its hard-gate backlog is not cleared by then, the unresolved
checks are recorded as a repository-scoped exclusion in its `sonic-ci` reference, with a
named owner and a target release, and the gate is enforced for every other check. The
repository is never left un-onboarded, and the exclusion is visible in the repository's
own configuration rather than tracked out of band. Exclusions are reviewed at each release
cut; the list may only shrink, which is the same discipline applied to the Python 2
removal.

**Phase 3 — Python 2 removal.** The 56 in-tree Python 2 files listed in
[Appendix B](#appendix-b-python-2-files-proposed-for-removal) are proposed for **deletion**.

The rationale is that these files are already non-functional. SONiC has shipped Python 3
only since the 202012 release. A file containing `print e` or `except IOError, e:` raises
`SyntaxError` at import time on any supported image — it cannot have worked at any point
in the last several years, and no test exercises it. They are not a lint backlog; they are
dead code that a linter happens to have found.

**Process.** Removal follows the precedent SONiC already uses for retiring platform
support: an ordinary pull request. `sonic-buildimage` commit `df1163e4`
(*[cavium]: Remove support for cavium platform*, #21476, January 2025) removed an entire
platform — its `device/` tree, its `platform/` sources, and its README entry — in a single
PR from a vendor engineer, with no mailing-list announcement, deprecation notice, or
waiting period. SONiC has no documented deprecation process, and inventing one for this
change would hold it to a higher bar than the removal of a whole working platform.

Accordingly:

- One PR per vendor grouping, so each lands independently and a single unresponsive vendor
  blocks nothing.
- Each PR tags the owning vendor's SONiC maintainers as reviewers.
- Each PR description carries the evidence: the file list, the `SyntaxError` each file
  raises under Python 3, and the note that no test references them.
- A vendor that wants a file kept responds with a Python 3 port on that PR. Normal review
  applies; there is no separate window to administer.

The grouping, by file count: Inventec (11), Ufispace (10), CIG (6), Ragile (6),
Juniper (5), Accton (4), Celestica (3), Pegatron (2), Supermicro (2), Alphanetworks (2),
Netberg (2), Dell (2), Broadcom XLR-GTS (1).

Removing these files takes `sonic-buildimage`'s hard-gate backlog from 1,494 findings to
**525**, and is a prerequisite for enabling the Python gate there.

**Phase 4 — Promotion.** With the fleet reporting advisory findings, the community
promotes advisory rules to gating by editing `severity.yml` and bumping the `sonic-ci`
tag. The obvious first candidate is `ruff`'s `W605` (invalid escape sequence, 659
occurrences), which a future Python release turns into a hard error; moving it from
`gate-new` to `gate` forces the existing 659 to be fixed rather than merely contained.
The `clang-tidy` `readability-*` and `modernize-*` families, which ship disabled, are the
next candidates.

#### 7.8 Items explicitly not changed

- **DB and schema.** No APP_DB, ASIC_DB, COUNTERS_DB, LOGLEVEL_DB, CONFIG_DB, or STATE_DB
  changes.
- **SWSS and Syncd.** No functional changes. Only their pipelines and, where lint findings
  are fixed, their source.
- **Docker.** No change to any shipped container. Only the `sonic-slave-trixie` build image.
- **Linux dependencies and interfaces.** None.
- **Platform specificity.** The design is platform-independent. No platform vendor is
  required to implement anything to make it work. Vendors owning files in
  [Appendix B](#appendix-b-python-2-files-proposed-for-removal) are asked to act only if
  they wish to retain those files.
- **GitHub Actions CodeQL and Semgrep.** Left in place and untouched. This design neither
  depends on them nor consolidates them, and it does not claim they provide complementary
  coverage — per [Section 4.2.1](#421-the-existing-codeql-and-semgrep-workflows-are-not-gates),
  CodeQL's findings are 98% code-quality rather than security and overlap substantially
  with what `ruff` and `clang-tidy` cover, while Semgrep's full-tree result has been red
  continuously and acted on by no one.

  They are left alone because changing them is a separate decision with its own
  trade-offs — CodeQL feeds GitHub's security-events surface, which `sonic-ci` does not
  replicate — and bundling it here would widen the review without improving the result.
  The natural follow-on, once this is gating, is to narrow CodeQL to security queries only
  and to either fix or rescope Semgrep's 338 findings.

### 8. SAI API

No SAI API changes are required by this design. No new SAI APIs or objects are used, and
no silicon vendor SAI implementation work is implied.

### 9. Configuration and management

This design introduces no runtime configuration. It has no CLI, no YANG model, no
ConfigDB schema, no REST or gNMI surface, and no manifest.

The only "configuration" is developer-facing CI configuration, held in `sonic-ci` and
described in [Section 7.3](#73-the-severity-manifest).

#### 9.1. Manifest

Not applicable. This is not an Application Extension.

#### 9.2. CLI/YANG model Enhancements

None. No changes to `sonic-utilities` command surface, no Klish or Click changes, and no
update required to `sonic-utilities/doc/Command-Reference.md`.

The one developer-facing command is `sonic-analyze`, which lives in `sonic-ci` and runs on
a developer workstation or CI agent. It is not installed on a switch and is not part of
any shipped package.

#### 9.3. Config DB Enhancements

None. No CONFIG_DB tables are added, removed, or modified. There is no
backward-compatibility consideration.

### 10. Warmboot and Fastboot Design Impact

None. No code introduced by this design executes on a switch.

#### Warmboot and Fastboot Performance Impact

- **Stalls, sleeps, or IO in the boot critical chain:** none. No analyzer runs on a switch.
- **Additional CPU-heavy processing during boot:** none.
- **Third-party dependency updates affecting boot time:** none. `ruff`, `pyright`, and
  `golangci-lint` are installed into the `sonic-slave-trixie` build image only and are not present
  in any shipped image.
- **Can the feature be delayed?** Not applicable — there is no service or container.

Indirectly, this design is expected to *reduce* warmboot and fastboot risk. The
`undefined-name` defects documented in [Section 4.2](#42-why-this-matters--measured-evidence)
sit in platform plugin error paths, several of which are exercised during platform
initialization.

Note that removing the [Appendix B](#appendix-b-python-2-files-proposed-for-removal) files
changes image contents. Because those files raise `SyntaxError` on import under Python 3,
no working code path can depend on them; nonetheless, an image-diff verification is listed
in [Section 13](#13-testing-requirementsdesign).

### 11. Memory Consumption

No memory consumption on a switch, under any configuration, enabled or disabled. Nothing
described here is compiled into or packaged into a SONiC image.

Build-time resource impact:

- **Slave image size:** three additional binaries (`ruff`, `pyright` plus its node bundle,
  `golangci-lint`), on the order of 100–200 MB against an image already several gigabytes in size.
- **CI agent memory:** `clang-tidy` raises peak memory during C/C++ analysis, since the
  analyzer holds its own parse tree and path state for each source file alongside gcc's own
  compilation. Peak RSS on the existing `sonicso1ES-amd64` pool will be measured during the
  pilot and recorded here; if it exceeds the agents' capacity, analyzer parallelism is
  reduced independently of `make -j`.

### 12. Restrictions/Limitations

1. **Vendor-hosted platform submodules are not covered.** Arista, Nokia, Mellanox
   hw-mgmt, Marvell, and SAI-P4-BM repositories are outside the community's control.
   Their code is analyzed neither in their own repositories nor in `sonic-buildimage`.
   This is a deliberate scope decision, not an oversight.
2. **Vendored third-party source is not covered.** FRR, scapy, ptf, supervisor, and the
   p4 toolchain track upstream projects; findings must be fixed upstream.
3. **Static analysis is not sound.** All of these tools produce false positives and, more
   importantly, false negatives. A green gate means no *detected* defect, not no defect.
4. **Analysis coverage follows what the build compiles.** Code excluded by
   `configure` from the CI build configuration is not analyzed. Platform-conditional code
   compiled only for a specific ASIC is analyzed only if that configuration is built in
   CI.
5. **`pyright` on unannotated code is limited.** In `standard` mode, unannotated values
   are `Unknown` and most checks are suppressed against them. Analysis depth rises as
   annotations are added; it will be shallow initially.
6. **Cross-repository analysis is not performed.** Each repository is analyzed in
   isolation. A type error where `sonic-utilities` misuses a `sonic-platform-common` API
   is caught only if the dependency is installed in the analysis environment.
7. **Go toolchain coupling.** `golangci-lint` must be built with a Go version at or above
   the analyzed code's. Raising `FIPS_GOLANG_MAIN_VERSION` past the pinned tool's build Go
   requires a coordinated `sonic-ci` bump. This is guarded by a check in `sonic-ci`'s own
   CI but remains a coupling point.
8. **`sonic-ci` becomes a fleet-wide dependency.** A bad tag can break CI across many
   repositories at once. Mitigated by the tag pin — repositories move only when
   explicitly bumped — and by `sonic-ci` having its own gated CI.
9. **The advisory backlog is large and will stay large for some time.** 35,862 `ruff`
   findings in `sonic-buildimage` under the full rule set is not a backlog anyone will
   clear. The value is in preventing growth and in the gated subset, not in reaching zero.
10. **Analyzer results move when the toolchain moves.** Findings are a function of the
    analyzer version, not just the code. When trixie's LLVM advances, or when SONiC moves
    to a successor Debian suite, previously-clean code can begin reporting. Group-level
    family-glob check selection ([Section 7.6](#76-build-dependency)) keeps the invocation
    valid across versions but cannot keep the findings identical, so a toolchain bump may
    require a round of backlog clearing before the gate is green again.
    The same applies to Rust, where the slave pins 1.86 and newer `clippy` lint names must
    be tolerated via `unknown_lints = "allow"`.
11. **Only the trixie slave is covered.** Per [Section 7.6.1](#761-moving-the-remaining-pipelines-to-trixie),
    no analysis runs on `sonic-slave-bookworm`. Any branch or repository still building
    exclusively on bookworm receives no static analysis until it moves to trixie.

### 13. Testing Requirements/Design

#### 13.1. Unit Test cases

Within `sonic-ci`:

| ID | Test |
|----|------|
| UT1 | `severity.yml` parses, and every rule identifier it names is one the corresponding tool actually recognizes (guards against typo'd rule codes silently disabling a gate). |
| UT2 | `sonic-analyze` returns a non-zero exit status when, and only when, a rule in the `gate` list is violated. |
| UT3 | `sonic-analyze` returns zero when only advisory rules are violated, and still emits their findings. |
| UT4 | Each fixture in `tests/fixtures/<lang>/` containing a planted defect is detected by the corresponding analyzer. |
| UT5 | Each Azure template renders under `az pipelines runs show --open` validation. |
| UT6 | Pinned tool versions in `tool-versions.yml` match what is installed in the current `sonic-slave-trixie` image, and the pinned `golangci-lint`'s build Go version is greater than or equal to the image's `go version`. |
| UT7 | Suppression handling: a planted defect with an inline suppression does not fail the gate; the same defect without one does. |
| UT9 | Fingerprint stability: inserting lines above a set of findings, with no semantic change, yields zero new findings. Covers the 0-based/1-based line-origin difference between `pyright` and every other tool. |
| UT10 | Regression detection where the symptom is on an unchanged line: the `clang-analyzer` guard-removal case from [Section 7.3.1](#731-gate-scope-repo-wide-versus-regression-only) is reported as new. |
| UT11 | Editing a line carrying a pre-existing finding re-reports it as new; leaving it untouched does not. |
| UT12 | A renamed file's pre-existing findings are matched through `git diff -M` and not reported as new. |
| UT13 | An absent baseline fails nothing and records the current findings as the baseline. |

Within `sonic-buildimage`:

| ID | Test |
|----|------|
| UT8 | The slave `Dockerfile.j2` changes build, and each added analyzer runs `--version` successfully in the resulting image. |

#### 13.2. System Test cases

| ID | Test |
|----|------|
| ST1 | A PR to a pilot repository introducing a planted `F821` fails the pipeline, and the failure names the file, line, and rule. |
| ST2 | A PR introducing only an advisory-level finding passes, and the finding appears in the published pipeline output. |
| ST3 | The pipeline of each pilot repository is green on an unmodified `master` with the hard-gate rules enforced. |
| ST4 | Measured wall-clock delta per pilot repository is within the R11 budget. Recorded in this document before phase 2 begins. |
| ST5 | A `sonic-ci` tag bump that promotes an advisory rule to gating changes the result of an otherwise identical PR — proving the manifest is the effective control point. |
| ST6 | `sonic-analyze` run on a developer workstation reproduces the CI finding set for the same commit (R6). |
| ST7 | A fork with a different `repository_owner` runs the full gate, confirming no organization-specific guard was introduced (R14). |
| ST8 | An image built after the Appendix B removal is byte-diffed against one built before. The only differences are the removed files. |
| ST9 | Existing warmboot and fastboot regression suites pass unchanged on an image built after the Appendix B removal. |

#### 13.3. Regression testing

No new `sonic-mgmt` test cases are required; this design adds no runtime behavior. The
existing `sonic-mgmt` regression suite serves as the safety net for source changes made
to clear hard-gate backlogs. Any backlog-clearing PR is a normal code change and is
subject to normal review and regression requirements.

### 14. Open/Action items

None.

Every question raised during the design of this document has been resolved into the
sections above. The work this document proposes is sequenced in
[Section 7.7](#77-rollout-plan); the measurements the pilot must produce are stated as its
exit criteria there.

---

### Appendix A: Measured baseline

All figures produced with `ruff 0.16.3` on `sonic-buildimage` at commit `e782d9267`,
2026-08-17. `--isolated` was used so no repository configuration influenced the result.
Vendor-hosted and third-party submodule paths were excluded per
[Appendix C](#appendix-c-repository-coverage).

**A.1 — `sonic-buildimage` in-tree Python (3,277 files)**

| Rule set | Findings |
|----------|----------|
| All rules `ruff` implements | 35,862 |
| Pyflakes only (`--select F`) | 8,239 |
| Proposed hard-gate set (Section 7.3) | 1,494 |
| Proposed hard-gate set, excluding Python 2 files | **525** |

Full-tree `ruff` execution time: **0.29 s** (wall clock, 3,277 files, cold cache).

**A.2 — Hard-gate set breakdown, `sonic-buildimage`**

| Rule | Count | Meaning |
|------|-------|---------|
| *(invalid-syntax)* | 971 | Python 2 source; see Appendix B |
| `F821` | 445 | Undefined name — a guaranteed `NameError` |
| `F811` | 28 | Redefinition of an unused name |
| `B006` | 17 | Mutable argument default |
| `F601` | 10 | Repeated key in a dict literal |
| `F632` | 9 | `is` comparison against a literal |
| `B023` | 4 | Function does not bind the loop variable |
| `F507` | 4 | `%`-format positional count mismatch |
| `B012` | 3 | `break`/`continue`/`return` inside `finally` |
| `B017` | 3 | `assertRaises(Exception)` |

**A.3 — Most frequent advisory findings, `sonic-buildimage`**

| Rule | Count | Meaning |
|------|-------|---------|
| `UP031` | 7,831 | `printf`-style string formatting |
| `UP032` | 3,092 | Could use an f-string |
| `I001` | 2,946 | Unsorted imports |
| `BLE001` | 1,906 | Blind `except:` |
| `RUF012` | 1,620 | Mutable class attribute default |
| `UP024` | 1,576 | Deprecated `OSError` alias |
| `F401` | 1,342 | Unused import |
| `LOG015` | 1,184 | Call on the root logger |
| `EXE001` | 1,069 | Shebang present but file not executable |
| `SIM115` | 1,024 | `open()` without a context manager |
| `W605` | 659 | Invalid escape sequence in a string literal |

**A.4 — Per-repository hard-gate backlog**

| Repository | Hard-gate | All rules |
|------------|-----------|-----------|
| `sonic-utilities` | 116 | 7,015 |
| `sonic-swss` (Python portion) | 72 | 2,301 |
| `sonic-platform-daemons` | 38 | 1,605 |
| `sonic-platform-common` | 23 | 2,609 |
| `sonic-host-services` | 15 | 578 |
| `sonic-snmpagent` | 12 | 628 |
| `sonic-ztp` | 10 | 500 |

**A.5 — Analyzer availability in existing slave image**

Verified against `sonic-slave-trixie/Dockerfile.j2` and `rules/sonic-fips.mk`.

| Tool | `sonic-slave-trixie` |
|------|----------------------|
| `clang` | present (LLVM 19) |
| `clang-tidy` | **absent — must be added** |
| `cppcheck` | present (not used by this design) |
| `pylint` | present (retained — a `sonic-mgmt-framework` build target invokes it) |
| `shellcheck` | present |
| `nodejs` | present |
| Rust | 1.86.0 |
| Go | FIPS **1.24.4** (`FIPS_GOLANG_VERSION = 1.24.4-1+fips`) + `golang-go` |
| Python | FIPS **3.13.5** |
| `ruff` | **absent — must be added** |
| `pyright` | **absent — must be added** |
| `golangci-lint` | **absent — must be added** (v2.12.2) |

For contrast, `rules/sonic-fips.mk` pins `sonic-slave-bookworm` to FIPS Go **1.19.8** and
Python **3.11**, which is why the Go repositories' `go 1.24.4` directive cannot be
satisfied there. See [Section 7.6.1](#761-moving-the-remaining-pipelines-to-trixie).

**A.6 — `golangci-lint` build-Go compatibility**

Established from each release tag's `go.mod`. The governing rule, quoted from the tool's
documentation, is that "golangci-lint supports Go versions lower or equal to the Go version
used to compile it."

| Release | Built with Go | Covers `go 1.24.4`? |
|---|---|---|
| v2.1.0 | 1.23.0 | no |
| v2.2.0 | 1.23.0 | no |
| v2.3.0 | 1.23.0 | no |
| v2.4.0 | 1.24.0 | at language-version granularity only |
| v2.5.0 | 1.24.0 | at language-version granularity only |
| v2.6.0 | 1.24.0 | at language-version granularity only |
| v2.8.0 | 1.24.0 | at language-version granularity only |
| v2.10.0 | 1.25.0 | yes |
| **v2.12.2** (latest, 2026-05-06) | **1.25.0** | **yes — selected** |

### Appendix B: Python 2 files proposed for removal

56 files tracked directly in `sonic-buildimage` fail to parse as Python 3. Each raises
`SyntaxError` at import time on any supported SONiC image and therefore cannot be
functional. Rationale and process are in
[Section 7.7, Phase 3](#77-rollout-plan).

An additional 66 Python 2 files exist inside excluded vendor and third-party submodules
(`platform/p4/p4-hlir` 30, `platform/p4/SAI-P4-BM` 25, `platform/marvell-prestera/sonic-platform-marvell` 8,
`platform/p4/p4c-bm` 3). Those are out of scope and are listed here only for completeness.

**`device/` (11 files)**

```
device/celestica/x86_64-cel_ds2000-r0/plugins/sfputil.py
device/celestica/x86_64-cel_questone_2-r0/plugins/sfputil.py
device/dell/x86_64-dell_s3248t-r0/plugins/sfputil.py
device/netberg/x86_64-netberg_aurora_710-r0/plugins/psuutil.py
device/netberg/x86_64-netberg_aurora_710-r0/plugins/sfputil.py
device/ragile/x86_64-ragile_ra-b6510-32c-r0/fantlv.py
device/ragile/x86_64-ragile_ra-b6510-32c-r0/fru.py
device/ragile/x86_64-ragile_ra-b6510-32c-r0/monitor.py
device/ragile/x86_64-ragile_ra-b6510-32c-r0/systest.py
device/ragile/x86_64-ragile_ra-b6920-4s-r0/monitor.py
device/ragile/x86_64-ragile_ra-b6920-4s-r0/systest.py
```

**`platform/broadcom/` (36 files)**

```
platform/broadcom/sonic-platform-modules-accton/as6712-32x/utils/accton_as6712_monitor.py
platform/broadcom/sonic-platform-modules-accton/as7312-54xs/utils/accton_as7312_monitor.py
platform/broadcom/sonic-platform-modules-accton/as7312-54x/utils/accton_as7312_monitor.py
platform/broadcom/sonic-platform-modules-alphanetworks/snh60a0-320fv2/utils/alphanetworks_snh60a0_util.py
platform/broadcom/sonic-platform-modules-alphanetworks/snh60b0-640f/utils/alphanetworks_snh60b0_util.py
platform/broadcom/sonic-platform-modules-brcm-xlr-gts/utils/brcm-xlr-gts-create-eeprom-file.py
platform/broadcom/sonic-platform-modules-cel/ds3000/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-dell/n3248te/scripts/portiocfg.py
platform/broadcom/sonic-platform-modules-inventec/common/utils/led_proc.py
platform/broadcom/sonic-platform-modules-inventec/common/utils/transceiver_monitor.py
platform/broadcom/sonic-platform-modules-inventec/d6254qs/utils/inventec_d6254_util.py
platform/broadcom/sonic-platform-modules-inventec/d6332/utils/inventec_d6332_util.py
platform/broadcom/sonic-platform-modules-inventec/d6356/sonic_platform/qsfp.py
platform/broadcom/sonic-platform-modules-inventec/d6356/utils/inventec_d6356_util.py
platform/broadcom/sonic-platform-modules-inventec/d6556/utils/inventec_d6556_util.py
platform/broadcom/sonic-platform-modules-inventec/d7032q28b/utils/inventec_d7032_util.py
platform/broadcom/sonic-platform-modules-inventec/d7054q28b/sonic_platform/sfp.py
platform/broadcom/sonic-platform-modules-inventec/d7054q28b/utils/inventec_d7054_util.py
platform/broadcom/sonic-platform-modules-inventec/d7264q28b/utils/inventec_d7264_util.py
platform/broadcom/sonic-platform-modules-juniper/qfx5200/utils/juniper_qfx5200_monitor.py
platform/broadcom/sonic-platform-modules-juniper/qfx5200/utils/juniper_qfx5200_util.py
platform/broadcom/sonic-platform-modules-juniper/qfx5210/utils/juniper_qfx5210_monitor.py
platform/broadcom/sonic-platform-modules-juniper/sonic_platform/chassis.py
platform/broadcom/sonic-platform-modules-juniper/sonic_platform/platform.py
platform/broadcom/sonic-platform-modules-supermicro/sse-t8164/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-supermicro/sse-t8196/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s6301-56st/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s7801-54xs/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s8901-54xc/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9110-32x/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9300-32d/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9301-32db/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9301-32d/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9311-64d/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9321-64eo/utils/pddf_switch_svc.py
platform/broadcom/sonic-platform-modules-ufispace/s9321-64e/utils/pddf_switch_svc.py
```

**`platform/nephos/` (9 files)**

```
platform/nephos/sonic-platform-modules-accton/as7116-54x/utils/accton_as7116_util.py
platform/nephos/sonic-platform-modules-cig/cs5435-54p/utils/cig_cs5435_misc.py
platform/nephos/sonic-platform-modules-cig/cs5435-54p/utils/cig_cs5435_util.py
platform/nephos/sonic-platform-modules-cig/cs6436-54p/utils/cig_cs6436_misc.py
platform/nephos/sonic-platform-modules-cig/cs6436-54p/utils/cig_cs6436_util.py
platform/nephos/sonic-platform-modules-cig/cs6436-56p/utils/cig_cs6436_misc.py
platform/nephos/sonic-platform-modules-cig/cs6436-56p/utils/cig_cs6436_util.py
platform/nephos/sonic-platform-modules-pegatron/porsche/utils/pegatron_porsche_util.py
platform/nephos/sonic-platform-modules-pegatron/porsche/utils/porsche_sensors.py
```

### Appendix C: Repository coverage

**C.1 — Repositories excluded, and why**

*Vendor-hosted platform submodules.* Hosted in vendor-controlled GitHub organizations, so
the SONiC community can neither merge changes nor configure CI there. Code in
`sonic-buildimage` that *uses* these is still analyzed.

```
platform/broadcom/sonic-platform-modules-arista
platform/broadcom/sonic-platform-modules-nokia
platform/mellanox/hw-management/hw-mgmt
platform/marvell-prestera/sonic-platform-marvell
platform/marvell-teralynx/sonic-platform-marvell-teralynx
platform/barefoot/sonic-platform-modules-arista
platform/aspeed/sonic-platform-modules-arista
platform/p4/SAI-P4-BM
```

*Vendored upstream projects.* These track external repositories with their own quality
gates; findings have to be fixed upstream, not in SONiC.

```
src/sonic-frr/frr          src/scapy               src/ptf
src/ptf-py3                src/supervisor          src/redis-dump-load
src/wpasupplicant/sonic-wpa-supplicant             platform/p4/p4-hlir
platform/p4/p4c-bm
```

Note that three `platform/` submodules *are* community-owned and therefore in scope:
`platform/vpp`, `platform/alpinevs`, and `platform/broadcom/saibcm-modules`.

**C.2 — Branches and analysis types not covered**

- **Release branches.** `master` only; the `202xxx` branches do not adopt this and are not
  backported to. A release branch exists to stop changing, so a new gate there would either
  block cherry-picks of already-reviewed fixes or demand a backlog cleanup on a branch
  nobody wants to touch. Branches cut from `master` after this lands inherit it.
- **Runtime and dynamic analysis** (ASAN, valgrind, coverage). SONiC already has these via
  the `asan` build parameter and `archive_gcov`; this design does not touch them.
- **Secret scanning and dependency/CVE scanning.** Adjacent concerns, partially covered by
  the existing CodeQL and Semgrep workflows.

**C.3 — Per-repository language census**

Tracked source file counts, produced with `git ls-files` per submodule.

| Repository | Python | C/C++ | Go | Rust | Shell |
|------------|-------:|------:|---:|-----:|------:|
| `sonic-buildimage` (in-tree) | 3,277 | — | — | — | 460 |
| `sonic-utilities` | 623 | 0 | 0 | 0 | 9 |
| `sonic-platform-common` | 231 | 0 | 0 | 0 | 0 |
| `sonic-swss` | 165 | 564 | 0 | 34 | 7 |
| `sonic-platform-daemons` | 139 | 0 | 0 | 0 | 1 |
| `sonic-host-services` | 103 | 0 | 0 | 1 | 0 |
| `sonic-snmpagent` | 83 | 0 | 0 | 0 | 0 |
| `sonic-ztp` | 31 | 0 | 0 | 0 | 1 |
| `sonic-mgmt-framework` | 27 | 10 | 19 | 0 | 6 |
| `sonic-platform-pde` | 21 | 2 | 0 | 0 | 0 |
| `sonic-dbsyncd` | 13 | 0 | 0 | 0 | 0 |
| `sonic-py-swsssdk` | 13 | 0 | 0 | 0 | 0 |
| `sonic-swss-common` | 12 | 210 | 1 | 26 | 3 |
| `sonic-mgmt-common` | 11 | 0 | 183 | 0 | 6 |
| `sonic-redfish` | 10 | 43 | 0 | 0 | 1 |
| `sonic-gnmi` | 9 | 0 | 211 | 0 | 5 |
| `sonic-restapi` | 8 | 27 | 26 | 0 | 7 |
| `sonic-sairedis` | 3 | 583 | 0 | 0 | 14 |
| `sonic-dash-api` | 2 | 4 | 0 | 0 | 0 |
| `sonic-dash-ha` | 1 | 0 | 0 | 79 | 1 |
| `linkmgrd` | 0 | 108 | 0 | 0 | 0 |
| `sonic-bmp` | 0 | 54 | 0 | 0 | 0 |
| `sonic-stp` | 0 | 51 | 0 | 0 | 1 |
| `dhcprelay` | 0 | 33 | 0 | 0 | 0 |
| `dhcpmon` | 0 | 19 | 0 | 0 | 0 |
| `sonic-genl-packet` | 0 | 8 | 0 | 0 | 1 |

Of `sonic-buildimage`'s 3,277 in-tree Python files, 2,163 are under `platform/` (of which
1,538 are under `platform/broadcom/`) and the remainder are under `device/`, `src/`
build tooling, and `files/`. 300 of the 460 shell scripts are under `platform/`.
