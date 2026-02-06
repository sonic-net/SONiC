# Copilot Instructions for SONiC

This is the **master documentation and project coordination repository** for the SONiC (Software for Open Networking in the Cloud) project. It contains High-Level Design (HLD) documents, governance policies, release coordination, and the project website. Source code lives in separate repositories cataloged in `sourcecode.md`.

## Repository Structure

- `doc/` — 150+ feature HLD documents, test plans, configuration references, and design specs
- `tsc/` — Technical Steering Committee governance (elections, conformance)
- `*.html` — Project website pages (calendar, newsletters, presentations)
- `governance.md` — Project roles (Contributors, Maintainers, Project Leader) and conflict resolution
- `sourcecode.md` — Catalog of all SONiC source repositories and their purposes
- `sonic_docs_toc.md` — Table of contents for all documentation

## HLD Document Format

All High-Level Design documents in `doc/` follow a consistent template structure:

```
# Feature Name
## High Level Design Document
### Rev X.Y

# Table of Contents
# Revision History (table: Rev | Date | Author | Changes)
# About this Manual
# Scope
# Definitions/Abbreviation

# 1 Sub-system Overview
  ## 1.1 System Chart (architecture diagram)
  ## 1.2 Modules description

# 2 Feature Requirements
  ## 2.1 Functional requirements
  ## 2.2 Scalability requirements

# 3 Modules Design (detailed per-module)
# 4 Flows (data/control flow diagrams)
# 5 Configuration (JSON config_db examples)
# 6 Testing (environment, test cases)
# Appendix
```

When creating or editing HLD documents:
- Include a **revision history table** at the top
- Provide **Config DB schema** with JSON examples for any new configuration
- Document **App DB** and **SAI** interface changes where applicable
- Include **data/control flow diagrams** (SVG/PNG supported)
- Reference the test plan template at `doc/SONiC Test Plan Template.md` for new features

## File and Folder Naming

- **No spaces or special characters** in file or folder names. Use hyphens (`-`) or underscores (`_`) instead.
- Stick to alphanumeric characters, hyphens, underscores, and dots (e.g., `ACL-High-Level-Design.md`).
- Avoid characters that are invalid or problematic on Windows: `\ / : * ? " < > |`
- Keep paths under 260 characters total for Windows compatibility.
- Use consistent casing — prefer lowercase or Title-Case with hyphens, and avoid relying on case sensitivity to distinguish files.

## Markdown Conventions

The repo uses markdownlint with relaxed rules (`.markdownlint.json`):
- No line-length restriction
- Inline HTML is allowed
- Fenced code blocks don't require language tags

## Contribution Guidelines

- **Commit format**: `[component/folder touched]: Description of changes` with `Signed-off-by` line (`git commit -s`)
- **CLA required**: Contributors must sign the Individual Contributor License Agreement via Linux Foundation EasyCLA (automated bot check on PRs)
- **PR expectations**: Include tests (unit, integration, PTF), documentation updates, and follow the PR template in `.github/pr_template.md`
- **New features** require a completed test plan based on `doc/SONiC Test Plan Template.md`
- **Bugfixes** targeting release branches should be <200 lines and have sonic-mgmt test coverage
- PR review response time target: ~48 hours

## Key SONiC Ecosystem Repositories

The SONiC architecture is modular with Docker containers for each subsystem. Key repos:

| Repository | Purpose |
|---|---|
| **sonic-buildimage** | Main build system — image generation, Dockerfiles, platform drivers, build recipes |
| **sonic-swss** | Switch State Service — core orchestration (orchagent, portsyncd, neighsyncd) |
| **sonic-sairedis** | SAI Redis interface for hardware abstraction |
| **sonic-utilities** | CLI tools (config, show, clear commands) |
| **sonic-mgmt** | Test automation and management infrastructure |
| **sonic-linux-kernel** | Kernel patches and device drivers |
| **sonic-platform-common** | Platform abstraction APIs (EEPROM, LED, PSU, SFP, fan, watchdog) |

## CI/CD

Two scheduled GitHub Actions workflows run daily:
- `sonic_image_links_create_workflow.yml` — regenerates `sonic_image_links.json`
- `supported_devices_platforms_md.yml` — regenerates supported devices listing

## Release Branches

Active release branches follow the `YYYYMM` naming pattern (e.g., 202405, 202411, 202505, 202511). Only bugfixes (not features) are accepted on release branches unless TSC-approved.
