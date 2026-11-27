# Directory-Specific Copilot Instructions for `platform/` and `device/`

## 1. Problem Statement
Create directory-specific `.github/copilot-instructions.md` (starting with `platform/` and `device/`) so Copilot and other AI tools generate changes aligned with SONiC conventions and CI expectations.

The repository currently has one root `.github/copilot-instructions.md` with general guidance. It says nothing about how `platform/` and `device/` are organized, so AI-generated changes there can copy templates instead of sharing them, forget the `.dep` file next to a new `.mk` file, commit binary files, or use the wrong commit format.

## 2. Solution
GitHub Copilot does not read a nested `copilot-instructions.md` placed inside a directory. The supported way to scope instructions to a directory is a path-specific file under `.github/instructions/` named `NAME.instructions.md`, with an `applyTo` glob in its frontmatter. This change adds one such file for `platform/` and one for `device/`. Copilot combines them with the unchanged root file, and they apply only when Copilot works on a matching file.

| Situation | Result |
| :--- | :--- |
| Copilot works on a file under `platform/` | `platform.instructions.md` is combined with the root instructions |
| Copilot works on a file under `device/` | `device.instructions.md` is combined with the root instructions |
| Copilot works on any other path | Only the root instructions apply |
| A nested `platform/.github/copilot-instructions.md` | Not used: it is not a location Copilot reads, hence `applyTo` files |
| AI tool proposes a binary file | Instructions point to the allowlist and to build-time fetching |
| AI tool adds a platform or a build job | Instructions require updating `PLATFORM_PATHS` in `scripts/selective_build.py` |

## 3. Files Involved

| File | Role | Status |
| :--- | :--- | :--- |
| `.github/instructions/platform.instructions.md` | `applyTo` `platform/**`. Build-rule layout, `.mk` and `.dep` pairs, cache flags, templates, submodules, binaries, and CI expectations. | New |
| `.github/instructions/device.instructions.md` | `applyTo` `device/**`. Platform and HWSKU layout, naming, shared symlinked templates, file validity, binaries, and commit format. | New |

## 4. Features Added
* **`platform.instructions.md`:** `rules.mk` is the entry point and must include every new `.mk`; each cached target has a `.dep` file; variables that change an output belong in the target's `_DEP_FLAGS` (CI audits this); reuse `platform/template/`; naming and tab rules.
* **`platform.instructions.md`:** Submodule directories are changed in their own repository and only the pointer is updated here.
* **`platform.instructions.md`:** CI expectations, namely the selective build mapping in `scripts/selective_build.py` and ensuring that shared files build every platform.
* **`device.instructions.md`:** Platform directory named after the ONIE platform string; typical platform files; one HWSKU directory per `default_sku` entry; new platforms use the Platform API instead of legacy plugins.
* **`device.instructions.md`:** Keep changesets small by sharing templates with relative symlinks to `device/common/profiles` or to a sibling HWSKU, and by parameterizing shared Jinja2 templates instead of forking them.
* **Both files:** No binaries except the allowlisted ones, shell and Python style, `[platform/<name>]` or `[device/<vendor>]` commit format, `Signed-off-by` on every commit, and one logical change per pull request.
* The root `.github/copilot-instructions.md` is left untouched; the new files add to it.