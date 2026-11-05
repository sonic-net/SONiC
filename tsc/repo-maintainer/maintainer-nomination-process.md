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

A maintainer may step down or be proposed for removal in the following scenarios:

- **Voluntary step-down:** A maintainer may request to step down at any time by creating a PR to remove their entry from [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md).
- **Dormancy:** A maintainer who has made no contributions, performed no reviews, and undertaken no maintenance activities in the specific repository for six consecutive months or longer may be proposed for removal. An existing maintainer of the repository or a TSC member may create a PR to remove the dormant maintainer's entry from [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md), documenting the period of inactivity and supporting evidence.

All removal PRs, including voluntary step-down requests, follow the same approval procedure as nominations under [Review & Approval](#review--approval), except that the review window is at least one month rather than four weeks:

1. The PR must receive approval from at least one existing maintainer of the repository and two TSC voting members.
2. The PR must remain open for at least one month from the date it is opened to allow for review and objections. It may be merged only after this period has elapsed, the required approvals have been obtained, and there are no objections.
3. Once approved, the removal is recorded in [SONiC_Repo_Maintainer.md](./SONiC_Repo_Maintainer.md).

Any replacement maintainer follows the nomination and approval process above.

## References

- [Project Governance](../../governance.md)
- [TSC Election Process](../TSC_Election.md)
- [SONiC Repo Maintainer Roster](./SONiC_Repo_Maintainer.md)
