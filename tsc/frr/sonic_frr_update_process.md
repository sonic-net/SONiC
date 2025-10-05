# **SONiC Community FRR Upgrade Work Flow**

The current SONiC release program handles FRR upgrades and patching on an as-needed basis. This proposed FRR upgrade workflow aims to establish a formalized cadence and process for FRR upgrades in future SONiC releases. Any changes or updates to this workflow must first be discussed and agreed upon by the Routing Working Group to reach consensus.

# SONiC FRR Maintainers
Before 202511 release, the role of SONiC FRR Maintainer rotates among Broadcom, Microsoft, Alibaba, NVIDIA, and Dell, with each term lasting 12 months. Recent FRR upgrades include:

* Nvidia upgraded FRR to 8.5.1 in the 202311 release
* Broadcom upgraded FRR to 10.0.1 in the 202411 release
* Cisco upgraded FRR to 10.3 in the 202505 release

Given that FRR releases a new version approximately every four months and the SONiC community aims to incorporate more FRR features, we propose shortening the FRR Maintainer term to six months. This change would allow for more frequent evaluations of whether an FRR upgrade should be included in each 6-month SONiC release cycle. The assigned FRR Maintainer for a given release will remain responsible for addressing any FRR-related bugs discovered during that release’s lifecycle.

Additionally, we plan to expand the list of FRR Maintainers to include Cisco and Nexthop.AI. The proposed maintainer assignments for the next three SONiC releases are as follows:

* 202511 release: Alibaba (primary), shadowed by Nexthop.AI
* 202605 release: Microsoft
* 202611 release: Dell
* 202705 release: Nvidia
* 202711 release: Broadcom
* 202805 release: Cisco
* 202811 release: Alibaba
* 202905 release: Nexthop.AI
* 202911 release: Microsoft

If there is a large feature / commits from a member company, it is better to swap the FRR release maintainer duty to make FRR maintaining more smooth.

# SONiC Release and FRR version
| SONiC Release | FRR Version | FRR Maintainer |
---------------|-------------|--------------|
| 202311 | 8.5.1 | Nvidia |
| 202411 | 10.0.1 | Broadcom |
| 202505 | 10.3.0 | Cisco |
| 202511 | 10.4.1 | Alibaba, with help from Cisco and Nexthop.AI |

# FRR Project Release Cadence
-  FRR release numbering scheme x.y.z-s#
-  New FRR releases roughly every 4 months. FRR release information could be found from https://frrouting.org/release/
-  SONiC to stay out from major/minor releases (x.y) and use patch release (.z) for stability (eg, FRR 8.3.1 instead of 8.3 if it is for 202211 release). Another example, at the time of SONiC FRR upgrade, the following FRR versions are avaialble 9.0.1, 8.5.3, 9.0, the guidance is to upgrade with the latest patch release 9.0.1
-  For every sonic release, the recommendation is to update FRR to last stable minor release by default. If there is a need to change this guidance, the request needs to be discussed and approved in Routing Working Group.

  Note: 10.4.1 has been released in Aug 2025, and there are over 70 commits entering this release branch. It is better to ask FRR community to set 10.4.2, which could be used for 202511.

# FRR Patches
Regarding FRR patches, whenever a patch is introduced based on a fix from FRR, there should be a clearly defined timeline for its removal to prevent the accumulation of excessive patches in SONiC. Such patches should remain only for a maximum of two upgrade cycles. If a patch cannot be removed within this timeframe, explicit approval must be obtained from the Routing Working Group.

Currently, we prefix patch names with a patch number. To facilitate easy identification of long-lived patches, the Routing Working Group has agreed to retain these patch numbers even after a patch is removed during an upgrade. This practice helps to maintain traceability and simplifies tracking over time.


# SONiC Release FRR Upgrade
-   SONiC default to rebase FRR in every community release
-   SONiC FRR upgrade test requirements
	-   MANDATORY: Pass all Azure pipeline build test and LGTM as required by the standard code PR merge process
  	-   OPTIONAL: Additional tests in respect to specific changeset in the upgrade as deem necessary, manual tests should be automated and submitted to improve future test coverage
-   Rotate SONiC FRR maintenance duty among repo maintainer org and others (BRCM, MSFT, Alibaba, NVDA, DELL， Cisco, Nexthop.AI)
-   Responsibility of SONiC FRR release maintainer
	-   Default 6 months assignment
	-   Upgrade FRR version in SONiC release in needed, resolve SONiC FRR upgrade integration issues
	-   Triage and fix SONiC FRR issues when applicable. Fix may come from SONiC contributors or from FRR community, maintainer is responsible to drive the fix to unblock SONiC community
	-   Submit fixes to FRR project, submit new FRR topo test to FRR project if there is a gap
	-   Release maintainer to subscribe to FRR project, and be the FRR Point-of-Contact on behalf of SONiC
	-   Bring in FRR vulnerabilities and critical patches to SONiC

# Logivity Test for each SONiC FRR release
Besides the regular sonic-mgmt test cases in PR, we need run the following cases as longevity:

1. bgp/test_bgp_stress_link_flap.py — please run with --completeness_level=confident
2. bgp/test_bgp_suppress_fib.py — please run with --completeness_level=thorough

# SONiC FRR vulnerability and patch upgrade in between SONiC releases

-   FRR CVE Fixes
	-   Reference nvd.nist.gov cvss v3.x [rating](https://nvd.nist.gov/vuln-metrics/cvss#)
	-   Bring in Critical and High FRR CVE patches into SONiC
	-   Sample of [Critical](https://nvd.nist.gov/vuln/search/results?form_type=Advanced&results_type=overview&search_type=all&isCpeNameSearch=false&cpe_vendor=cpe%3A%2F%3Afrrouting&cpe_product=cpe%3A%2F%3A%3Afrrouting&cvss_version=3&cvss_v3_severity=CRITICAL), sample of [High](https://nvd.nist.gov/vuln/search/results?form_type=Advanced&results_type=overview&search_type=all&isCpeNameSearch=false&cpe_vendor=cpe%3A%2F%3Afrrouting&cpe_product=cpe%3A%2F%3A%3Afrrouting&cvss_version=3&cvss_v3_severity=HIGH)
	-   There are regular security scan in Azure pipeline, CVEs will be filed to sonic-buildimage/issues
	-   SONiC FRR release maintainer should subscribe to nvd.nist.gov for FRR alerts
	-   Need a process to bring in CVEs to earlier SONiC releases too (open to suggestions)

-   Patch FRR Bug Fixes
	-  Each FRR release branch will be supported for one year. The first six months will be managed by the current release manager, and the subsequent six months will be overseen by the next release manager.
	-  Each FRR release maintainer is responsible for tracking critical fixes across two FRR release branches: the current branch and the previous branch they were assigned to maintain.
	-  The SONiC FRR release maintainer should subscribe to the FRR project to identify and incorporate critical patches relevant to SONiC from the monitored branches. It is recommended to monitor the two active FRR release branches on a monthly basis. If there is uncertainty about whether a fix qualifies as critical, this issue would be discussed in the Routing Working Group. Only critical fixes will be backported to the SONiC FRR release to ensure code stability.

# SONiC FRR Upgrade Steps
-   Create sonic-frr branch for the target FRR version
	-   Contact release manager
-   Find new package dependencies
	-   Upload newly required packages to a common location (Azure)
-   Submodule update to new FRR commit id
-   Code changes
    -   Version change in Makefiles
    -   New Makefiles for new packages (if any)
    -   Port patches
	-   Evaluate whether existing FRR patches still applicable to new FRR version
	-   Apply the old patches into new FRR version, and generate new patch files. Keep original credentials
	-   If the changes are already present in new FRR version, discard the old patch file
	-   If the patch does not apply, manually merge the changes and resolve any conflicts
    -    Review the existing FRR commands in SONiC techsupport. Add, Remove or modify the FRR commands in the generate_dump script based on the new FRR version. https://github.com/sonic-net/sonic-utilities/blob/master/scripts/generate_dump
    -    Build and verify
	    -   Use PTF on local server, – or –
	    -   Manually verify BGP, VRF, IPv4, IPv6 (on sonic-vs.)
    -   Create PR with the following template
		- [https://github.com/sonic-net/sonic-buildimage/pull/15965](https://github.com/sonic-net/sonic-buildimage/pull/15965)
-   FRR upgrade PRs for reference
    - [https://github.com/sonic-net/sonic-buildimage/pull/15965](https://github.com/sonic-net/sonic-buildimage/pull/15965)
    - [https://github.com/sonic-net/sonic-buildimage/pull/10691](https://github.com/sonic-net/sonic-buildimage/pull/10691)
    - [https://github.com/sonic-net/sonic-buildimage/pull/11502](https://github.com/sonic-net/sonic-buildimage/pull/11502)
    - [https://github.com/sonic-net/sonic-buildimage/pull/10947](https://github.com/sonic-net/sonic-buildimage/pull/10947)

# SONiC FRR Version Upgrade History

<p align=center>
<img src="frr.png" alt="">
</p>
