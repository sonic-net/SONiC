# CI Automation: Binary Artifact Check & Selective Commit-Gating Builds

---

## Part 1: Automated Binary Artifact Check for `sonic-buildimage` Pull Requests

### 1. Problem Statement
Automate reviewer work by adding checks for issues often found manually (for example, detecting binary artifacts introduced in a changeset).

Reviewers currently spot binary files in pull requests by hand: executables, libraries, object files, archives, and packages. They cannot be reviewed, they bloat the repository history for good, and they bypass the build system, which should produce them from source or fetch them at build time. Manual review misses them, especially in large device or platform changes with hundreds of files.

### 2. Solution
A new GitHub Actions workflow runs on every pull request to `master` and the `202xxx` branches. It calls `scripts/check_binary_artifacts.py`, which lists the files the PR adds or changes with `git`, reads the first 8000 bytes of each from the git object (so it does not depend on the checkout), and reports the files that look binary.

Findings appear as inline annotations on the PR and in the job summary, which also works for pull requests from forks. A file that has to be binary is added to `.github/binary-artifacts-allowlist.txt` in the same PR, so the exception is visible to reviewers.

| Situation | Result |
| :--- | :--- |
| New file starting with an executable or archive signature (ELF, Mach-O, PE, ar/.deb, gzip, bzip2, xz, zstd, zip, 7z, rar, tar, squashfs, rpm) | Reported, even when it is named like a text file |
| New file with a NUL byte in its first 8000 bytes (git's own binary heuristic) | Reported as binary data |
| New file with a build-artifact extension (`.o`, `.a`, `.so`, `.ko`, `.deb`, `.whl`, `.pyc`, ...) | Reported |
| Text file changed into a binary file | Reported |
| Existing binary that is only modified, renamed, or moved | Not reported: the PR does not introduce it |
| Deleted file, symlink, or submodule pointer | Skipped |
| Path matches a pattern in `.github/binary-artifacts-allowlist.txt` | Not reported |
| Ordinary text file | Passes |
| Findings exist | Job fails with one annotation per file; with `--warn-only` they are warnings and the job passes |
| Base branch or changeset cannot be read | Job fails with exit status 2 and an error message |

### 3. Files Involved

#### Implementation & Configuration Files
| File | Role | Status |
| :--- | :--- | :--- |
| `scripts/check_binary_artifacts.py` | Collects the changed files, detects binary content, applies the allowlist, and prints GitHub annotations and the job summary. Exit status: `0` clean, `1` findings, `2` could not inspect. | New |
| `.github/binary-artifacts-allowlist.txt` | `fnmatch` patterns of binary files that may be added. Seeded with the binaries already in the repository: Broadcom LED microcode, Cancun packages, Dell port locator, and Ragile firmware headers. | New |
| `.github/workflows/binary-artifacts-check.yml` | Runs the check and its unit tests on pull requests to `master` and the `202xxx` branches (read-only token, no submodules). | New |

#### Test Files
| Test File | Role | Status |
| :--- | :--- | :--- |
| `scripts/test_check_binary_artifacts.py` | Unit tests for the detection rules, the allowlist, and the command line, using throw-away git repositories. | New |

### 4. Features Added
* **Content-based detection:** Magic numbers first, then NUL bytes, then build-artifact extensions as a fallback.
* **Targeted reporting:** Only introduced binaries are reported (new files and text files turned binary). Modified, renamed, and moved binaries are not.
* **Fast & checkout-independent:** Reads blobs straight from git through one `git cat-file` process, so large pull requests stay fast and the result does not depend on the working tree.
* **External allowlist:** One pattern per line, comments allowed, reviewed like any other change. Seeded from a scan of `master` so existing device firmware does not fail new device pull requests.
* **Rich PR feedback:** Inline PR annotations (`::error file=...`) and a job summary table; paths are escaped so unusual file names cannot break the workflow commands.
* **Fork support:** Needs only a read-only token.
* **Gradual rollout option:** `--warn-only` switch to roll the check out as a warning first.
* **Standalone script:** Can be reused from Azure Pipelines or a local pre-commit hook.
* **Unit-tested:** 21 tests run with `python3 -m unittest scripts/test_check_binary_artifacts.py`.

### 5. Testing
The repository scenarios commit real files into a temporary git repository and run the same code the workflow runs. Run them with:
```bash
python3 -m unittest scripts/test_check_binary_artifacts.py
```

| Area | Tests | What is covered |
| :--- | :--- | :--- |
| Classification | 7 | Text, empty, and UTF-8 files pass; executable and archive magic; magic wins over the file name; NUL bytes; text starting with `MZ`; extension fallback. |
| Allowlist | 4 | Comments and blank lines; missing file; `*` matches across directories; unrelated paths do not match. |
| Raw diff parsing | 2 | Modified and renamed entries; empty diff. |
| Repository scenarios | 8 | New binaries reported; allowlisted file; modified binary; moved binary; text turned binary; deleted binary; symlink and submodule pointer; command-line exit status (`1`, `--warn-only`, allowlist option, `2` for an invalid base). |

---

## Part 2: Selective Commit-Gating Builds for SONiC Azure Pipeline

### 1. Problem Statement
Enable selective commit-gating tests by mapping changed paths to the minimum relevant builds/tests, avoiding running tests for untouched platforms.

Before this change, every pull request started all platform builds (VS, VPP, AlpineVS, Broadcom, Mellanox, Marvell ARM64 and ARMHF, NVIDIA BlueField, Aspeed) and the VS tests, even when the commit touched only one platform. This wastes build agents (including the slow ARM pools), delays PR feedback, and queues unrelated work.

### 2. Solution
A new first stage, `SelectiveDecision`, looks at the files changed in the PR and decides which build jobs and tests are needed. The decision is passed to the later stages as pipeline variables, and every job checks them in its own condition. Jobs for untouched platforms are skipped. Whenever the scope cannot be decided safely, the pipeline falls back to a wider build instead of skipping coverage.

| Situation | Result |
| :--- | :--- |
| Non-PR build (push, scheduled, manual), or `SELECTIVE_MODE = all` | All platforms and VS tests |
| A global file changed (`Makefile`, `slave.mk`, `rules/`, pipeline files, ...) | All platforms and VS tests |
| Only known platform paths changed | Only the mapped platforms; VS tests only if `vs` is mapped |
| Two files in one platform, duplicate paths | The platform is selected once |
| Shared directory `platform/marvell-prestera/` | Both `marvell-prestera-arm64` and `marvell-prestera-armhf` |
| Unknown path (docs, newly added platform directory) or no changed paths | `BuildVS` default: `vs`, `vpp`, `alpinevs`. Unknown paths are never silently skipped |
| Deleted or renamed files | Their paths (both the old and the new path of a rename) are used for the decision like any other change |

### 3. Files Involved

#### Implementation & Pipeline Files
| File | Role | Status |
| :--- | :--- | :--- |
| `scripts/selective_build.py` | Maps changed paths to platforms, applies the selection rules, and writes `selection.json` (`platforms`, `run_all`, `run_vs_tests`, `reasons`). | New |
| `azure-pipelines.yml` | `SelectiveDecision` stage runs the script and publishes outputs; `BuildVS`, `Build`, and `Test` stages consume them. Defines the `SELECTIVE_MODE` parameter (`path \| all`). | Modified |
| `.azure-pipelines/azure-pipelines-job-groups.yml` | Adds the per-job condition so only selected platform jobs run on PRs. | Modified |
| `.github/workflows/azp-rerun-without-selective-build.yml` | Lets a maintainer comment `/azp rerun Azure.selective-build-demo` on a PR to queue a full build with `SELECTIVE_MODE = all`. | New |

#### Test Files
| Test File | Role | Status |
| :--- | :--- | :--- |
| `scripts/test_selective_build.py` | Unit tests for the path mapping, the fallback rules, the git diff handling (adds, deletes, renames), and the command-line output. | New |

### 4. Features Added
* **Path-to-platform mapping:** Maps paths for all nine jobs so a PR builds only what it touches.
* **Per-job gating:** Jobs for untouched platforms are skipped on PRs in the job template.
* **Selective VS tests:** The `Test` stage runs on a PR only when the `vs` platform is selected.
* **Multi-platform changes:** Selected platforms are combined, deduplicated, and always output in the stable `ALL_PLATFORMS` order.
* **Shared source directory support:** `platform/marvell-prestera/` selects both Marvell ARM variants.
* **Global-file safety:** A change to a global build or pipeline file triggers every platform.
* **`BuildVS` default fallback:** Unknown paths, a newly added platform directory, documentation-only changes, and empty diffs build the `BuildVS` stage (`vs`, `vpp`, `alpinevs`) as baseline coverage instead of skipping or building everything.
* **Deletes and renames:** Included in the decision; a rename contributes both its old and its new path.
* **Full non-PR builds:** Push, scheduled, and manual builds always use all-platform mode.
* **Manual override:** `SELECTIVE_MODE` parameter (`path` or `all`) to override selection for a run.
* **Comment-triggered full rerun:** `/azp rerun Azure.selective-build-demo` queues an Azure build with `SELECTIVE_MODE = all`. It checks that the Azure settings exist and that the commenter has admin, maintain, write, or triage permission.
* **Traceable decisions:** `selection.json` records the changed paths and the reason for each selection, and is printed in the build log.
* **Unit-tested:** 24 tests run with `python3 -m unittest scripts/test_selective_build.py`.

### 5. Testing
The tests build throw-away git repositories so git handling is exercised for real. Run them with:
```bash
python3 -m unittest scripts/test_selective_build.py
```

| Area | Tests | What is covered |
| :--- | :--- | :--- |
| Mode handling | 2 | `all` mode selects every platform; an unsupported mode is rejected. |
| Platform paths | 9 | Every platform maps to its own job; `vs` selects the VS tests; `marvell-prestera` selects both variants; stable output order; duplicate and blank paths; the directory itself; lookalike directory names; reasons recorded. |
| Global paths | 4 | Every global path selects everything; a global path wins over platform and unknown paths; global names match exactly. |
| `BuildVS` default | 5 | No changed paths; documentation-only change; new platform directory; unknown path next to a platform; no duplicate platforms. |
| Git diff and command line | 4 | Added, modified, and deleted files; a rename reports both paths; `selection.json` output; `--mode all`. |