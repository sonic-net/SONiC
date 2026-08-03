# SONiC Repo Maintainer Process

A lightweight guideline for nominating and onboarding a maintainer for a SONiC repository. It complements the maintainer roster in [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md), the project [governance model](../../governance.md).

## Roles

- **Maintainer** — has merge rights to a repository's `master`/`main` branch and is accountable for its quality and direction. 

## Eligibility (guidance)

Maintainership is earned through sustained, high-quality contribution to the **specific repository**, in keeping with SONiC's meritocracy principle. Strong signals include:

- A track record of merged PRs in the repo.
- Consistent, helpful PR reviews.
- Authored or reviewed High Level Designs (HLDs) for the repo's domain.
- Demonstrated domain expertise and reliable responsiveness.

These map to the contribution categories used by the **SONiC Influence Index (SII)** in [TSC_Election.md](../TSC_Election.md). The SII categories are offered here as *guidance* for what "merit" looks like — there is no fixed SII score required to become a repo maintainer.

## Responsibilities & Expectations
- Code review - ensuring PRs align with components architecture and don't introduce breaking changes
- Actively Triaging bugs

## How to Nominate

A nominee may be put forward by **themselves, an existing maintainer of the repo, or a TSC member** (the roster records entries such as "Nominated by …").

1. Create a new PR against [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md).
2. Include:
   - Name
   - Organization
   - GitHub ID
   - Target repository
   - A brief justification of the nominee's contributions to that repo (links to PRs, reviews, or HLDs are encouraged).

## Review & Approval

1. Approval required by at least one existing maintainer approval and two TSC voting members.
2. There will be a four week window beginning upon opening of the PR, if there are no objections then the maintainership shall be approved.
3. Approved entries are recorded in [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md).

## Onboarding

Once approved:

1. A GitHub access invitation is sent to the new maintainer — the roster reflects this as `invitation sent`, then `enabled` once accepted.
3. Record the new entry in [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md) (repo, name, GitHub ID, status).

## Stepping Down, Removal, and Replacement

- A maintainer may step down voluntarily at any time; the maintainer should create a new PR against [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md) with removal request
- The TSC review the PR and approve

## References

- [Project Governance](../../governance.md)
- [TSC Election Process](../TSC_Election.md)
- [SONiC Repo Maintainer Roster](./SONiC_Repo_Maintainer.md)
