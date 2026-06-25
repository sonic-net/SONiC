# FRRouting Contribution Proposal for SONiC

**Author:** Patrice Brissette, Cisco  
**Date:** March 17, 2026  
**Version:** 1.1

---

## Executive Summary

This proposal addresses a gap in SONiC's contribution tracking system: substantial engineering work done in FRRouting (FRR)—SONiC's control plane—currently goes unrecognized, even when that work is specifically undertaken to enable SONiC features. We propose a straightforward solution that maintains existing standards while ensuring the full scope of feature development is properly attributed.

---

## Background

### SONiC Contribution Metrics

SONiC tracks contributions through a point-based system that recognizes various types of community engagement:
- **Code PRs:** Points based on size (S/M/L): 10 points, 20 points, or 50+ points (50 + 1 per 100 LoC above 300)
- **HLD PRs (merged):** 50 points per merged High-Level Design document
- **Code Reviews:** 2 points per review
- **Bug Reports:** Variable points based on severity

These metrics are used to measure contributor engagement and are tracked through the [SONiC Contribution Dashboard](https://sonic-net.github.io/SONiC/Contribution-Dashboard.html).

### FRR's Role in SONiC

FRRouting (FRR) is an IP routing protocol suite that serves as SONiC's control plane for Layer 2 and Layer 3 functionality. FRR provides implementations of:
- BGP (Border Gateway Protocol)
- EVPN-VxLAN, SR/SRv6
- IS-IS, RIP, PIM, LDP, BFD, and other routing protocols

SONiC integrates FRR through the `sonic-frr` repository, which includes FRR as a submodule with SONiC-specific patches. The architecture is:
```
SONiC Feature → BGP/FRR (Control Plane) → zebra (FRR) → fpmsyncd → APPL_DB → orchagent → SAI → ASIC
```

In this architecture, FRR is not just a library dependency—it's the control plane that makes SONiC's Layer 2 and Layer 3 features possible.

---

## Problem Statement

Many features developed for SONiC require substantial work in FRRouting (FRR), the routing protocol suite used as SONiC's control plane. However, under the existing contribution tracking system, work done in the FRRouting upstream repository is not counted toward SONiC contributions, even when that work is specifically undertaken to enable SONiC features.

This occurs because:
1. FRR is an independent open-source project with its own repository and community
2. SONiC contribution metrics only track work in SONiC GitHub organization repositories
3. The dependency relationship between SONiC features and their FRR prerequisites is not formally captured

When FRR serves as the control plane, these upstream contributions are prerequisites for delivering functional features in SONiC, yet they remain invisible in SONiC contribution metrics. This creates a blind spot where substantial engineering effort that directly enables SONiC capabilities goes unrecognized in the SONiC ecosystem.

### Examples of FRR Work Enabling SONiC Features

Recent features committed to FRR in the last year (2025-2026) that directly enable SONiC capabilities include:

- **EVPN IPv6 VTEP Support** - Multi-homed support for IPv6 underlay in EVPN-VxLAN deployments (PR #20116, merged Jan 2025; PR #19498)
- **EVPN-VxLAN Multi-Homing** - Enhanced multi-homing capabilities for EVPN deployments (PR #19438)
- **EVPN Flooding per VNI** - Per-VNI BUM flooding control instead of global only (FRR 10.5.0)
- **BGP SRv6/MPLS Coexistence** - Migration support for MPLS to SRv6 backbone (FRR 10.5.0)
- **Multiple SRv6 Locators** - Extended SID Manager capabilities (FRR 10.5.0)
- **Performance/Scalability** - Route table optimizations, epoll conversion, incremental JSON output (multiple PRs)

All of this work was essential for delivering SONiC features, yet none of it appears in SONiC contribution metrics.

---

## Proposed Solution

The solution is straightforward: recognize FRR work that directly enables SONiC features through the same rigorous process SONiC already uses for other contributions.

To properly account for FRRouting contributions that enable SONiC features, we propose a three-part approach:

### 1. Provide HLD Documentation in SONiC
Submit a High-Level Design (HLD) document in the SONiC documentation repository describing the solution where FRRouting contributes to enhancing SONiC. This ensures visibility of the complete feature implementation, including the upstream work. The HLD must be reviewed, approved and merged.

### 2. List CODE PRs
As part of the standard HLD process, include a comprehensive list of CODE PRs as part of the HLD PR descriptions, including code, review, and test PRs. This may include:
- FRRouting upstream PRs
- sonic-frr integration PRs (frr patches)
- Other SONiC component PRs as applicable

PRs must be tagged for SONiC contribution to be counted toward contribution metrics.

**Important:** Not all FRR PRs are counted toward SONiC contributions. Only PRs that directly enable or support SONiC features should be included. FRR infrastructure work, manageability features, APIs, or other enhancements that are unrelated to SONiC functionality should not be counted, even if they provide general improvements to FRR.

In some cases, the implementation may consist solely of FRRouting upstream PRs and/or sonic-frr changes that integrate upstream FRRouting work.

### 3. Account for FRRouting Delivery Points
Apply the standard SONiC contribution point system to the FRRouting work delivered. For instance,
- Use the existing PR size metrics (S/M/L): 10/20/(50 + 1 per 100 LoC above 300)
- Same approach for Merged HLD metric count: 50
- Count merged FRRouting PRs that directly enable the SONiC feature
- Include these points in the contributor's SONiC contribution metrics

This approach ensures that the full scope of work required to deliver SONiC features is recognized and properly attributed.

---

## Why This Makes Sense

### Community-Wide Benefits

This proposal benefits the entire SONiC ecosystem, not just individual contributors:

1. **Improved Visibility:** Captures the complete engineering investment required for SONiC features, providing a more accurate picture of project health and activity

2. **Encourages Upstream Contributions:** Incentivizes contributors to work upstream in FRR rather than carrying private patches, benefiting the broader routing community

3. **Better Resource Planning:** Organizations can better justify resource allocation when upstream work is properly recognized

4. **Knowledge Sharing:** Required HLD documentation ensures FRR-related design decisions are captured in SONiC documentation

5. **Reduces Technical Debt:** Encourages proper integration through FRR upstream rather than workarounds in SONiC-specific code

### Potential Concerns and Responses

**Concern:** *"This could inflate contribution numbers artificially."*

**Response:** The proposal requires the same rigor as existing contributions: merged HLDs with peer review, documented PRs, and adherence to the standard point system. The work is verified through the HLD review process.

**Concern:** *"Why should FRR work count toward SONiC metrics?"*

**Response:** When FRR work is a prerequisite for a SONiC feature, it is functionally part of SONiC development. The architecture uses FRR as the control plane—work there is as essential as work in orchagent or syncd for delivering the complete feature.

**Concern:** *"This sets a precedent for counting external work."*

**Response:** This is controlled through the requirement for a merged SONiC HLD that explicitly documents the feature and lists the PRs. It's bounded to work that directly enables documented SONiC features, not general-purpose dependencies.

**Concern:** *"How do we prevent double-counting?"*

**Response:** Each PR is linked to a specific HLD. The HLD review process validates that listed PRs are appropriate. Auditing is straightforward through the documented PR lists.

### Effect on Existing Metrics

- No retroactive changes to historical data
- Existing contribution types (SONiC repo PRs, reviews, HLDs) remain unchanged
- Adds a new category of recognizable work without diminishing existing contributions
- May increase total points in the ecosystem as hidden work becomes visible
- **No double-counting:** FRRouting upstream PRs are counted once when merged. Subsequent sonic-frr integration patches that apply these upstream changes to SONiC releases are not counted separately, as they represent the same work being integrated rather than new development

### Why FRR Is Special

This proposal is specific to FRR due to its unique architectural position in SONiC:

- **FRR is SONiC's control plane:** It's an architectural component, not just a library dependency. Work in FRR is as essential to SONiC features as work in orchagent or syncd.

- **Bidirectional integration:** SONiC features often require FRR enhancements designed specifically for SONiC use cases, making this a true partnership between projects.

- **HLD-gated accountability:** The requirement for a merged SONiC HLD with documented PRs prevents scope creep to arbitrary dependencies. Only work directly tied to documented SONiC features qualifies.

---

## Conclusion

This proposal provides a practical, auditable mechanism to recognize the full engineering effort required to deliver SONiC features. By requiring HLD documentation and maintaining the same rigorous standards SONiC already uses, it ensures proper attribution while preserving the integrity of the contribution tracking system. The result is better visibility into project health, stronger incentives for upstream collaboration, and more accurate representation of the work being done to advance SONiC.

