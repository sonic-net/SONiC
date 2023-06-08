# **SONiC Community FRR Upgrade Process Proposal**

FRR upgrade and patch cadence is largely on need basis in the current SONiC release program. This SONiC FRR upgrade process proposal is to formalize the FRR upgrade cadence and process for future SONiC release programs.  

# SONiC FRR Version Upgrade History

<p align=center>
<img src="img/frr.png" alt="">
</p>


# FRR Project Release Cadence
-   FRR release numbering scheme x.y.z-s#
-   New FRR releases roughly every 4 months
	- Apr 2023 - Release 8.5.1 (48 fixes)
	- Mar 2023 - Release 8.5 (947+ commits)
	- Jan 2023 - Release 8.4.2 (22 fixes)
	- Nov 2022 - Release 8.4.1 (16 fixes)
	- Nov 2022 - Release 8.4 (700+ commits)
	- Aug 2022 - Release 8.3.1 (14 fixes)
	- Jul 2022 - Release 8.3 (1000+ commits)
	- Mar 2022 - Release 8.2.2 (800+ commits)
	- Nov 2021 - Release 8.1.0 (1200+ commits)
	- Jul 2021 - Release 8.0.0 (2200+ commits)
    
-   SONiC to stay out from major/minor releases (x.y) and use patch release (.z) for stability (eg, FRR 8.3.1 instead of 8.3 if it is for 202211 release)

# SONiC Release FRR Upgrade
-   SONiC default to rebase FRR in every November community release
-   SONiC FRR upgrade test requirements
	-   Pass FRR upgrade acceptance test (eg, 4 node BGP topo traffic test, Spytest sonic-vs L3 testsuite)
	-   Pass existing Azure pipeline build test and LGTM
-   Rotate SONiC FRR maintenance duty among repo maintainer org and others (BRCM, MSFT, Alibaba, NVDA, DELL)
-   Responsibility of SONiC FRR release maintainer
	-   Default 12 months assignment (or until the next upgrade)
	-   Upgrade FRR version in Nov release, resolve SONiC FRR upgrade integration issues
	-   Triage and fix SONiC FRR issues
	-   Submit fixes to FRR project, submit new FRR topo test to FRR project if there is a gap
	-   Release maintainer to subscribe to FRR project, and be the FRR Point-of-Contact on behalf of SONiC
	-   Bring in FRR vulnerabilities and critical patches to SONiC

# SONiC FRR vulnerability and patch upgrade in between SONiC releases

-   FRR CVE Fixes
	-   Reference nvd.nist.gov cvss v3.x [rating](https://nvd.nist.gov/vuln-metrics/cvss#)
	-   Bring in Critical and High FRR CVE patches into SONiC
	-   Sample of [Critical](https://nvd.nist.gov/vuln/search/results?form_type=Advanced&results_type=overview&search_type=all&isCpeNameSearch=false&cpe_vendor=cpe%3A%2F%3Afrrouting&cpe_product=cpe%3A%2F%3A%3Afrrouting&cvss_version=3&cvss_v3_severity=CRITICAL), sample of [High](https://nvd.nist.gov/vuln/search/results?form_type=Advanced&results_type=overview&search_type=all&isCpeNameSearch=false&cpe_vendor=cpe%3A%2F%3Afrrouting&cpe_product=cpe%3A%2F%3A%3Afrrouting&cvss_version=3&cvss_v3_severity=HIGH)
	-   There are regular security scan in Azure pipeline, CVEs will be filed to sonic-buildimage/issues
	-   SONiC FRR release maintainer should subscribe to nvd.nist.gov for FRR alerts
	-   Need a process to bring in CVEs to earlier SONiC releases too (open to suggestions)
    
-   Patch FRR Bug Fixes
	-   SONiC FRR release maintainer should subscribe to FRR project to bring in critical patch

# SONiC FRR Upgrade Steps
-   Create sonic-frr branch for the target FRR version
	-   Contact release manager
-   Find new package dependencies
	  -   Upload newly required packages to a common location (azure?)
-   Submodule update to new FRR commit id.
-   Code changes
    -   Version change in Makefiles
    -   New Makefiles for new packages (if any.)
    -   Port the patches
	    -   Evaluate whether existing FRR patches still applicable to new FRR version
		 -   Apply the old patches into new FRR version, and generate new patch files
			 -   Keep original credentials
	    -   If the changes are already present in new FRR version, discard the old patch file
		-   If the patch does not apply, manually merge the changes and resolve any conflicts
    -   Build and verify
	    -   Use PTF on local server, – or –
	    -   Manually verify BGP, VRF, IPv4, IPv6 (on sonic-vs.)
    -   Create PR
-   FRR 8.2.2 upgrade PRs for reference  
    - [https://github.com/sonic-net/sonic-buildimage/pull/10691](https://github.com/sonic-net/sonic-buildimage/pull/10691)
    - [https://github.com/sonic-net/sonic-buildimage/pull/11502](https://github.com/sonic-net/sonic-buildimage/pull/11502)
    - [https://github.com/sonic-net/sonic-buildimage/pull/10947](https://github.com/sonic-net/sonic-buildimage/pull/10947)
    -
