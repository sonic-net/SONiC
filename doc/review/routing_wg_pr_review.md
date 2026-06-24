<h1 align="center"> Guidelines for SONiC Routing PR Reviews </h1>

# Table of Contents <!-- omit in toc -->
- [Revision](#revision)
- [Introduction](#introduction)
- [Get PR Visibility to SONiC Routing Working Group](#get-pr-visibility-to-sonic-routing-working-group)
- [Pass All PR Sanity Tests Before Starting Review](#pass-all-pr-sanity-tests-before-starting-review)
  - [Routing Working Group PR Review Process](#routing-working-group-pr-review-process)
    - [Bi-weekly Review Cycle](#bi-weekly-review-cycle)
    - [Review Process](#review-process)
    - [Expectations](#expectations)
- [Rewards for PR Review Contributions](#rewards-for-pr-review-contributions)

# Revision
| Rev  |   Date    |           Author           | Change Description      |
| :-- | :------- | :------------------------ | :--------------------- |
| 0.1  | 06/11/2026  | Eddie Ruan  |  Initial version        |

# Introduction
The SONiC Pull Request (PR) review process is currently experiencing delays due to multiple factors. This document provides guidelines for the SONiC Routing Working Group to help expedite the review of routing-related PRs.

# Get PR Visibility to SONiC Routing Working Group
Deepak has created the [SONiC Routing Dashboard](https://github.com/orgs/sonic-net/projects/41/views/4). The Routing Working Group uses the "Open PRs" view to track the review progress of routing-related PRs.

**PR Submitter Responsibilities:**
1. Add your PR to the "SONiC Routing Dashboard" project
2. Set the item type to "Code PR"
3. Fill in all required fields with relevant information
4. Set the initial PR status to "Todo"

# Pass All PR Sanity Tests Before Starting Review
It is the submitter's responsibility to ensure all sanity tests pass. **No code review will begin until existing sanity tests are passed.**

Once all sanity tests pass, the submitter should:
- Change the PR status to `routing-review-needed`

## Routing Working Group PR Review Process

### Bi-weekly Review Cycle
Every two weeks, the Routing Working Group reviews all PRs labeled as `routing-review-needed` to assess progress.

### Review Process

1. **Reviewer Assignment**:
   - Reviewers volunteer from Working Group members
   - If no volunteers emerge, the WG coordinator would try to assign reviewers in the next WG review meeting.

2. **Review Sessions**:
   - Standard reviews are conducted asynchronously via GitHub comments
   - For complex PRs, submitters can request a high-level walkthrough during a WG meeting by contacting the WG coordinators or posting requests in the working group channel.

3. **Approval & Next Steps**:
   - Once a WG member approves the PR (validating domain expertise), the submitter can request review from repo maintainers.
   - WG approval only helps repo maintainers by confirming technical correctness with domain experts. It is not a guarantee for merging PRs.
   - **Note**: The WG is not responsible for contacting repo maintainers; the submitter must initiate the maintainer review request

4. **Change Requests**:
   - If WG reviewers request changes, the submitter should address feedback promptly.
   - Once changes are made, update the PR status and re-request review

### Expectations
- WG reviewers aim to provide initial feedback within **5 business days**
- Submitters should respond to feedback within **3 business days**
- If a PR remains inactive for more than 2 weeks, it would be deprioritized and `routing-review-needed` would be removed.

# Rewards for PR Review Contributions
PR review efforts are counted towards SII score. Detailed information can be found at [SONiC TSC Repository](https://github.com/sonic-net/SONiC-tsc).

**SII Points for PR Reviews:**

| PR Review Size | Development Points |
|----------------|-------------------|
| Small (S)      | 1                 |
| Medium (M)     | 2                 |
| Large (L)      | 5                 |`

