# **Detailed Steps to Upgrade FRR in SONiC**
## Introduction
This document records the tasks and procedures involved in upgrading FRR in SONiC, using the transition from 10.3 to 10.4.1 as a practical example, based on the work performed by ___Alibaba___.<br>
<br>
The content is organized in the chronological order of the upgrade process and covers four main aspects: branch management, patch application, pull request (PR) preparation, and testing procedure. By following the detailed steps outlined in this document, you can successfully complete the FRR upgrade work.<br>
It is highly recommended to maintain close coordination with the Routing Working Group throughout the upgrade process to ensure alignment with the correct direction and community best practices.<br>
<br>
We would like to express our special thanks to ___Cisco___, ___Nexthop___ ___AI___ and ___Microsoft___ for their valuable support in assisting ___Alibaba___ throughout this FRR upgrade from version 10.3 to 10.4.1.<br>
<br>




## 1 Branch
### 1.1 Create the `frr-10.4.1` branch in the `sonic-frr` repository
#### If you do NOT have push access to the `sonic-frr` repository
- Please contact the **release manager** to create the new branch.
#### If you have push access, you can proceed with the following steps to create and push the branch
- Clone the `sonic-frr` repository:
     ```bash
     git clone https://github.com/sonic-net/sonic-frr
     ```
- Navigate to the `sonic-frr` directory:
     ```bash
     cd sonic-frr
     ```
- Add the upstream **FRR** repository as a remote:
     ```bash
     git remote add upstream https://github.com/FRRouting/frr
     ```
- Fetch the `frr-10.4.1` tag from the upstream **FRR** repository:
     ```bash
     git fetch upstream --no-tags refs/tags/frr-10.4.1:refs/tags/frr-10.4.1
     ```
- Create a branch named `frr-10.4.1` based on the `frr-10.4.1` tag:
     ```bash
     git checkout -b frr-10.4.1 tags/frr-10.4.1
     ```
- Verify that the branch has been created correctly by checking the latest commit message (it should be **"FRR Release 10.4.1"**):
     ```bash
     git log --oneline -1
     ```
- Push the newly created `frr-10.4.1` branch to the `sonic-frr` repository:
     ```bash
     git push origin refs/heads/frr-10.4.1
     ```
     *Note: Git may become confused when a branch and a tag share the same name, so we explicitly specify the branch reference.*




### 1.2 Upgrade FRR version from 10.3 to 10.4.1 in `frr.mk` and `.gitmodules`
- Update FRRouting (frr) package in `sonic-buildimage/rule/frr.mk`
     ```makefile
     FRR_VERSION = 10.3     ->  FRR_VERSION = 10.4.1
     FRR_BRANCH = frr-10.3  ->  FRR_BRANCH = frr-10.4.1
     FRR_TAG = frr-10.3     ->  FRR_TAG = frr-10.4.1
     ```
- Update submodule branch in `sonic-buildimage/.gitmodules`
     ```ini
     [submodule "src/sonic-frr/frr"]
          path = src/sonic-frr/frr
          url = https://github.com/sonic-net/sonic-frr.git
          branch = frr-10.3  ->  branch = frr-10.4.1        // update here
     ```
- Update **FRR** submodule<br>
     Add and commit `src/sonic-frr/frr` folder change in `sonic-buildimage`, ensuring it points to the **"FRR Release 10.4.1"** commit.
<br>
<br>

## 2 Patches and Changes
###### Note: We will review the patches to determine which ones should be removed, retained, or added.
### 2.1 Port the FRR patches from 10.3 to 10.4.1
###### Note: This section focuses on handling the existing patches during the upgrade process.
- Navigate to the `sonic-frr/frr` directory:
     ```bash
     cd sonic-buildimage/src/sonic-frr/frr
     ```
- Switch to the `frr-10.3` branch:
     ```bash
     git checkout frr-10.3
     ```
- By default, StGit may truncate long patch names. To prevent this, configure it as follows:
     ```bash
     git config stgit.namelength 0
     ```
- Create a temporary branch for porting patches from FRR 10.3 to 10.4.1 using StGit:
     ```bash
     stg branch --create stgtmp
     ```
- Import the FRR patches into the new branch:
     ```bash
     stg import -S ../patch/series
     ```
- Rebase the stgtmp branch onto the `frr-10.4.1` branch. A text editor will open showing all the patches to be ported:
     ```bash
     stg rebase -i frr-10.4.1
     ```
- Remove any patches that are already included in FRR 10.4.1, by changing their status from **"keep"** to **"delete"**.<br>
     ```text
     - 0019-Revert-bgpd-upon-if-event-evaluate-bnc-with-matching.patch
     - 0020-staticd-add-cli-to-support-steering-of-ipv4-traffic-over-srv6-sid-list.patch
     - 0021-lib-Return-duplicate-prefix-list-entry-test.patch
     - 0023-isisd-lib-add-some-codepoints-usually-shared-with-other-vendors.patch
     - 0024-staticd-Add-support-for-SRv6-uA-behavior.patch
     - 0025-Fpm-problems.patch
     - 0028-zebra-ensure-proper-return-for-failure-for-Sid-allocation.patch
     - 0029-staticd-Fix-a-crash-that-occurs-when-modifying-an-SRv6-SID.patch
     - 0030-staticd-Avoid-requesting-SRv6-sid-from-zebra-when-loc-and-sid-block-dont-match.patch
     - 0031-isisd-fix-srv6-sid-memory-leak.patch
     - 0032-show-ipv6-route-json-displays-seg6local-flavors.patch
     - 0033-staticd-Install-known-nexthops-upon-connection-with-zebra.patch
     - 0034-staticd-Fix-an-issue-where-SRv6-SIDs-may-not-be-allocated-on-heavily-loaded-systems.patch
     - 0035-lib-Add-support-for-stream-buffer-to-expand.patch
     - 0036-zebra-zebra-crash-for-zapi-stream.patch
     - 0037-bgpd-Replace-per-peer-connection-error-with-per-bgp.patch
     - 0038-bgpd-remove-apis-from-bgp_route.h.patch
     - 0039-bgpd-batch-peer-connection-error-clearing.patch
     - 0040-zebra-move-peer-conn-error-list-to-connection-struct.patch
     - 0041-bgpd-Allow-batch-clear-to-do-partial-work-and-contin.patch
     - 0042-zebra-V6-RA-not-sent-anymore-after-interface-up-down.patch
     - 0043-bgpd-Paths-received-from-shutdown-peer-not-deleted.patch
     - 0044-bgpd-Modify-bgp-to-handle-packet-events-in-a-FIFO.patch
     - 0045-zebra-Limit-reading-packets-when-MetaQ-is-full.patch
     - 0046-bgpd-Delay-processing-MetaQ-in-some-events.patch
     - 0047-bgpd-Fix-holdtime-not-working-properly-when-busy.patch
     - 0048-bgpd-ensure-that-bgp_generate_updgrp_packets-shares-.patch
     - 0049-zebra-show-command-to-display-metaq-info.patch
     - 0050-bgpd-add-total-path-count-for-bgp-net-in-json-output.patch
     - 0051-lib-Add-nexthop_same_no_ifindex-comparison-function.patch
     - 0052-zebra-show-nexthop-count-in-nexthop-group-command.patch
     - 0053-zebra-Allow-nhg-s-to-be-reused-when-multiple-interfa.patch
     - 0054-zebra-Prevent-active-setting-if-interface-is-not-ope.patch
     - 0055-zebra-Add-nexthop-group-id-to-route-dump.patch
     - 0056-zebra-Display-interface-name-not-ifindex-in-nh-dump.patch
     - 0057-mgmtd-remove-bogus-hedge-code-which-corrupted-active.patch
     - 0058-mgmtd-normalize-argument-order-to-copy-dst-src.patch
     - 0059-zebra-Ensure-that-the-dplane-can-send-the-full-packe.patch
     ```
- Save the file and exit. StGit will start the rebase process.
- During the rebase, conflicts may appear. Resolve them and continue with the following commands:<br>
     ```bash
     stg add --update
     stg refresh
     stg goto 0061-bgpd-Fix-JSON-wrapper-brace-consistency-in-neighbor.patch    //the last patch
     ```
     Repeat this step until all the patches are applied.
- Export the updated patch series:
     ```bash
     stg export -d /tmp/patch_new
     ```
- Replace the old patch folder with the new one:
     ```bash
     rm -r ../patch
     mv /tmp/patch_new ../patch
     ```
- Use an editor (e.g. VS Code) to inspect each patch and verify the diffs, ensuring no important information is lost.<br>
  Be cautious of accidental deletions, such as author info, commit messages, or dates.
- You can manually verify whether the patches apply correctly on the `frr-10.4.1` branch:
     ```bash
     git checkout frr-10.4.1
     git reset --hard origin/frr-10.4.1
     stg import -S ../patch/series
     ```
     *Note: A warning may appear due to a naming conflict with a tag, but Git will switch to the local branch by default.*

### 2.2 Update the `dplane_fpm_sonic.c`
###### Note: Except for the patches, we need to sync the necessary changes for `dplane_fpm_snoic.c`
- Review the commit history of `FRRouting/frr/dplane_fpm_nl.c` between FRR versions 10.3 and 10.4.1 to identify relevant differences.
  We would like to thank **[@Carmine](https://github.com/cscarpitta)**, the maintainer, for helping us determine which commits are needed.
- Apply the necessary changes to `dplane_fpm_sonic.c`, ensuring that the copyright information is clearly stated in the commit message.
     ```text
     [FRR]: Bring FPM fixes from FRR mainline

     Bring the following fix from FRR mainline and apply to dplane_fpm_sonic:
     - zebra: On dplane failure to write ctx, let zebra know (FRRouting@a1ce6a4)

     Signed-off-by: Yuqing Zhao <galadriel.zyq@alibaba-inc.com>
     ```
- The changes of the `dplane_fpm_sonic.c` can be summarized as in the following table.<br>
     |         Description Message                                 |         FRR Commit         |         Status in SONiC        |
     |-------------------------------------------------------------| --------------------------- | -------------------------------|
     |    zebra: Fix pass back of data from dplane through fpm pipe   |    [FRRouting/frr@b2fc167](https://github.com/FRRouting/frr/commit/b2fc167978189238e045d719e11202ab303d2f59)    |    NOT applicable to SONiC     |
     |    zebra: Limit mutex for obuf to when we access obuf    |    [FRRouting/frr@c58da10](https://github.com/FRRouting/frr/commit/c58da10d2a700164e329352c5c22a924af3fa45c)    |    Merged as [sonic-net@1f7896e](https://github.com/sonic-net/sonic-buildimage/commit/1f7896e91b5b283b0fa28bc4078f0e5fc38e943b)    |
     |    zebra: change fpm_read to batch the messages    |    [FRRouting/frr@7e8c18d](https://github.com/FRRouting/frr/commit/7e8c18d0b0149f879487d46255f279f14b20e52a)    |    Committed in this PR    |
     |    bgpd,zebra: remove use of the EVENT_OFF macro    |    [FRRouting/frr@e9a756f](https://github.com/FRRouting/frr/commit/e9a756ffe13f0b008603168a1c891305b3c5488b)    |    Committed in this PR    |
     |    zebra: Ensure that the dplane can send the full packet    |    [FRRouting/frr@c89c330](https://github.com/FRRouting/frr/commit/c89c330bd7eb548c024bf325ccdd54ae48a052db)    |    Merged as [sonic-net@6868762](https://github.com/sonic-net/sonic-buildimage/commit/686876262e5bb5ee672)    |
     |    zebra: On dplane failure to write ctx, let zebra know    |    [FRRouting/frr@a1ce6a4](https://github.com/FRRouting/frr/commit/a1ce6a4a635fc6f9e2ef4dd7080ffe0637a58efd)    |    Committed in this PR    |


### 2.3 Add new patches from FRR `stable/10.4` branch
###### Note: Only commits that have been merged into the FRR `stable/10.4` branch will be added as patches. This ensures stability and facilitates future patch integration.
- Review the `FRRouting/frr/tree/stable/10.4` branch and summarize the necessary commits (typically corresponding to pull requests).<br>
  We recommend using the **original PR** rather than the backported one, as it typically has a clearer commit message and is more suitable for generating a patch.
- Navigate to the `src/sonic-frr/frr` directory:
     ```bash
     cd sonic-buildimage/src/sonic-frr/frr
     ```
- Export the selected commits as patches (each patch corresponds to a single PR):
     - Locate the original PR and clone it using the command provided in the GitHub UI:
          ```bash
          git pr checkout [PR number]
          ```
     - Identify the **SHA** of the target commits within the PR and record them.
     - Switch to the `frr-10.4.1` branch, apply the realigned patches from **section 2.1**, and cherry-pick the desired commits:
          ```bash
          git checkout frr-10.4.1
          stg import -S ../patch/series
          git cherry-pick [first SHA]~..[last SHA]
          ```
     - Generate a patch file for the PR (choose a patch name based on the corresponding PR title):
          ```bash
          git format-patch -k [first SHA]~..[last SHA] --stdout > [patch-num-like-0010]-Title-of-the-corresponding-PR.patch
          ```
     - Repeat this process for all target PRs until all relevant changes are captured.
- Move the generated patches to the `sonic-frr/patch` directory:
     ```bash
     mv *.patch ../patch/
     ```
- Update the `sonic-frr/patch/series` file with the names of the newly added patches.
- Verify that the patches can be applied correctly on a clean `frr-10.4.1` branch:
     ```bash
     cd sonic-buildimage/src/sonic-frr/frr
     git reset --hard origin/frr-10.4.1
     stg import -S ../patch/series
     ```
*Note: Ensure that all new patches are well-formatted and do not introduce conflicts or unnecessary changes. It's good practice to review each patch before final submission.*


### 2.4 Sync up with Routing Working Group
- It is recommended to synchronize with the **Routing WG** to confirm that all necessary patches have been included.
<br>
<br>

## 3 About the Pull Request (PR)
###### The FRR upgrade process is finalized by merging a pull request in the `sonic-buildimage` repository. Therefore, it is necessary to open and submit a corresponding PR. The following section provides guidance for writing the PR description and organizing the commits within the PR.
###### The full implementation of FRR 10.4.1 upgrade is available in [sonic-buildimage: PR#24330](https://github.com/sonic-net/sonic-buildimage/pull/24330).
### 3.1 PR Description
When creating a pull request, we primarily follow the standard PR description guidelines that appear when initiating a new PR. However, in addition to the standard fields, there are several additional details that should be included to clearly communicate the changes made during the upgrade.<br>
<br>
Among these, the **most important part is the summary table**, which helps reviewers quickly understand what has been done.<br>
<br>
Looking back at the work completed so far:
- In **Section 2.1**, we identified and listed the patches that should be **removed**.
- We then generated a set of **realigned patches** from the remaining ones.
- In **Section 2.2**, we summarized the status of relevant commits in `dplane_fpm_sonic.c`.
- In **Section 2.3**, we added new patches based on updates from the FRR `stable/10.4` branch.

These four sets of information form the **key tables** that should be included in the PR description:
- **[Table 1] Removed Patches**
- **[Table 2] Realigned Patches**
- **[Table 3] Summary of **`dplane_fpm_sonic.c`** Changes**
- **[Table 4] New Patches Added**


#### 3.1.1 Removed Patches
A removed patch indicates that the corresponding fix or feature has already been implemented in the target FRR release. This table should include the patch name, along with a link to the relevant FRR commit or pull request where the change was introduced.<br>

###### [Table 1] Example: Removed Patches
|         Patch                                                    |         FRR Commit / Pull Request                             |
|------------------------------------------------------------------| --------------------------------------------------------------- |
| 0019-Revert-bgpd-upon-if-event-evaluate-bnc-with-matching.patch | [FRRouting/frr@052aea6](https://github.com/FRRouting/frr/commit/052aea624e8be80c7a20bb69cb0e1b79a8a28a88) |
| 0020-staticd-add-cli-to-support-steering-of-ipv4-traffic-over-srv6-sid-list.patch | [FRRouting/frr@6f52056](https://github.com/FRRouting/frr/commit/6f52056f70524a26e7ff72c06ca9be826763d603) |
| ... | ... |

*Note: The complete list of removed patches is provided in **[Appendix A](#appendix-a)**.*

#### 3.1.2 Realigned Patches
Realigned patches are typically the remaining patches after porting from the previous version. These patches will still be present after the upgrade and may fall into two categories:
- **Temporary (Temp)**: These patches are expected to be removed in future upgrades or once the underlying issue is resolved upstream.
- **Lasting**: These patches are intended to remain in SONiC permanently due to differences in logic or implementation requirements.

To distinguish between them:
- **Temporary patches** retain their original names.
- **Lasting patches** are prefixed with `SONiC-ONLY-` in their filenames.

###### [Table 2] Example: Realigned Patches
|         Patch                                                    |         Type              |      Reason                   |
|------------------------------------------------------------------| ------------------------ | ----------------------------------|
| 0001-SONiC-ONLY-Reduce-severity-of-Vty-connected-from-message.patch | Lasting | Different Logic |
| 0005-Add-support-of-bgp-l3vni-evpn.patch                            | Temp    | As shown in patch |
| 0014-SONiC-ONLY-Adding-changes-to-write-ip-nht-resolve-via-default-c.patch | Lasting | Feature added by SONiC |
| 0016-SONiC-ONLY-Set-multipath-to-514-and-disable-bgp-vnc-for-optimiz.patch | Lasting | Different Compilation |
| 0027-Dont-skip-kernel-routes-uninstall.patch | Temp | FRR Open issue: [FRRouting#19637](https://github.com/FRRouting/frr/issues/19637) |
| 0060-bgpd-Convert-bmp-path_info-tracking-from-hash-to-rbt.patch | Temp | Merged in FRR, <br> tagged frr-10.6.0 |
| ... | ...| ... |

*Note: The complete list of realigned patches is provided in **[Appendix B](#appendix-b)**.*

*It is recommended to also include a brief description of any conflict resolution steps taken during the patch application process. This helps reviewers understand how potential issues were addressed and ensures clarity for future maintenance.*


#### 3.1.3 Changes in `dplane_fpm_sonic.c`
This section refers to the work covered in **Section 2.2**, and the summary table from that section will be reused here as **Table 3**.
###### [Table 3] Example: Summary of dplane_fpm_sonic.c Changes
|         Description Message                                 |         FRR Commit         |         Status in SONiC        |
|-------------------------------------------------------------| --------------------------- | -------------------------------|
|    zebra: Fix pass back of data from dplane through fpm pipe   |    [FRRouting/frr@b2fc167](https://github.com/FRRouting/frr/commit/b2fc167978189238e045d719e11202ab303d2f59)    |    NOT applicable to SONiC     |
|    zebra: Limit mutex for obuf to when we access obuf    |    [FRRouting/frr@c58da10](https://github.com/FRRouting/frr/commit/c58da10d2a700164e329352c5c22a924af3fa45c)    |    Merged as [sonic-net@1f7896e](https://github.com/sonic-net/sonic-buildimage/commit/1f7896e91b5b283b0fa28bc4078f0e5fc38e943b)    |
| ... | ...| ...|

*Note: The complete list of dplane_fpm_sonic.c changes is provided in **[Appendix C](#appendix-c)**.*


#### 3.1.4 New Patches Added
This table contains the new patches added during the upgrade process (as described in **Section 2.3**). These patches typically bring features or fixes from the FRR stable branch — in this case, `stable/10.4`.<br>
Following the same classification as the realigned patches, we classify these new additions based on their expected lifecycle:
- **Temporary (Temp)**: Expected to be removed once the fix is available upstream.
- **Lasting**: Intended to remain in SONiC due to specific requirements or logic differences, also prefixed with `SONiC-ONLY-` in their filenames.

###### [Table 4] Example: New Patches Added
|         Patch                                                    |         Type              |      Reason                   |
|------------------------------------------------------------------| ------------------------ | ----------------------------------|
| 0064-bgpd-Prevent-unnecessary-re-install-of-routes.patch | Temp | Merged in FRR mainline [FRRouting/frr#19788](https://github.com/FRRouting/frr/pull/19788) |
| 0066-zebra-fix-up-memory-leak-in-dplane-shutdown-sequences.patch | Temp | From FRR stable/10.4 |
| ... | ...| ...|

*Note: The complete list of new patches added is provided in **[Appendix D](#appendix-d)**.*


### 3.2 PR Commits
There is no strict rule on how to divide the commits, but it is **strongly recommended** to structure them in a logical and meaningful way that makes the upgrade process clear and easy to review.<br>

###### Example: Commits of FRR 10.4.1 Upgrade
| Commit  | Commit Message                                          | Content               |
|----------| ------------------------------------------------------- |-----------------------|
| Commit 1 | [sonic-frr]: Port patches from frr-10.3 to frr-10.4.1   | Port existing patches |
| Commit 2 | Upgrade FRR from 10.3 to 10.4.1                         | Update .gitmodules, frr.mk and sonic-frr submodule |
| Commit 3 | [FRR]: Bring FPM changes from FRR mainline              | A change for dplane_fpm_sonic.c |
| Commit 4 | [FRR]: Bring FPM fixes from FRR mainline                | A fix for dplane_fpm_sonic.c |
| Commit 5 | [FRR]: Bring FPM fixes from FRR mainline                | A fix for dplane_fpm_sonic.c |
| Commit 6 | [FRR][PATCH] bgpd: Prevent unnecessary re-install of routes | Add a new patch |
| Commit 7 | Add 32 new patches from FRR stable/10.4 branch          | Add new patches from FRR stable/10.4 branch |

*Note: This example illustrates a typical commit structure for an FRR upgrade. Each commit should clearly reflect a specific task or change, making it easier for reviewers to follow the upgrade logic.*

###### You can also refer to the previous FRR upgrade work:
- [https://github.com/sonic-net/sonic-buildimage/pull/15965](https://github.com/sonic-net/sonic-buildimage/pull/15965)
- [https://github.com/sonic-net/sonic-buildimage/pull/10691](https://github.com/sonic-net/sonic-buildimage/pull/10691)
- [https://github.com/sonic-net/sonic-buildimage/pull/11502](https://github.com/sonic-net/sonic-buildimage/pull/11502)
- [https://github.com/sonic-net/sonic-buildimage/pull/10947](https://github.com/sonic-net/sonic-buildimage/pull/10947)
<br>
<br>

## 4 Building and Testing
### 4.1 Building
Build a local SONiC VS (Virtual Switch) image to ensure there are no building errors before opening a PR.
### 4.2 PR Sanity Tests
The PR Sanity Tests serve as the initial validation for the upgrade work. After submitting the PR, the Continuous Integration (CI) system will automatically run these tests. Please ensure that all test cases pass successfully — this is a **mandatory requirement** for merging the PR.
### 4.3 Longevity Tests
In addition to the standard `sonic-mgmt` test cases included in the PR, the following test cases must be executed as part of the longevity testing:

1. `bgp/test_bgp_stress_link_flap.py` — please run with `--completeness_level=thorough`. Based on Chun'ang Li's comments, SONiC repo PR test pipelines will run bgp/test_bgp_stress_link_flap.py.
     - This test is parameterized for 4 test_types:
          ```pathon
          @pytest.mark.parametrize("test_type", ["dut", "fanout", "neighbor", "all"])
          ```
     - Each type runs for 5 days (120 hours) when using --completeness_level='thorough'.
          ```python
          LOOP_TIMES_LEVEL_MAP = {
               'debug': 60,
               'basic': 3600,      # 1 hour
               'confident': 21600, # 6 hours
               'thorough': 432000  # 120 hours (5 days)
          }
          ```
          Currently, we are only using the DUT parameter for local runs to save time due to resource limitations.
     - You can specify the DUT parameter explicitly by running:
          ```python
          bgp/test_bgp_stress_link_flap.py::test_bgp_stress_link_flap[dut]
          ```

2. `bgp/test_bgp_suppress_fib.py` — please run with `--completeness_level=thorough`.
     - You can run all the test cases in this file.

<br>

*Note:*<br>
*1. Currently, we don't have Azure pipelines to run these two sanity checks. Need to ask Microsoft team's help to run it manually. This issue will bring up to TSC for allocate resources for setting up sanity check pipelines.*<br>
*2. Based on some Microsoft team's comments, race condition issues typically surface on lower-performance platforms. We need TSC to allocate some budget to build a dedicated lab for this purpose. The budget and decision for setting up additional testbed is not in the scope of this document. This needs to be brought up to TSC and board for discussion.*
<br>
<br>

## In the End

We hope this guide has been helpful in walking you through the process of upgrading FRR in SONiC.<br>
As always, feel free to reach out with any questions or feedback.

Thanks again for contributing to SONiC!

<br>
<br>
<br>

## Appendix
###### Note: This appendix contains the full versions of key tables of the FRR 10.4.1 upgrade, including Removed Patches, Realigned Patches, Summary of dplane_fpm_sonic.c Changes and New Patches Added.
### Appendix A
##### [Table 1] Removed Patches
|         Patch                                                    |         FRR <br>Commit / Pull Request                             |
|------------------------------------------------------------------| --------------------------------------------------------------- |
| 0019-Revert-bgpd-upon-if-event-evaluate-bnc-with-matching.patch | [FRRouting/frr@052aea6](https://github.com/FRRouting/frr/commit/052aea624e8be80c7a20bb69cb0e1b79a8a28a88) |
| 0020-staticd-add-cli-to-support-steering-of-ipv4-traffic-over-srv6-sid-list.patch | [FRRouting/frr@6f52056](https://github.com/FRRouting/frr/commit/6f52056f70524a26e7ff72c06ca9be826763d603) |
| 0021-lib-Return-duplicate-prefix-list-entry-test.patch | [FRRouting/frr@24ae7cd](https://github.com/FRRouting/frr/commit/24ae7cd30a055dc17fc9d75762320e1359e005b2) |
| 0023-isisd-lib-add-some-codepoints-usually-shared-with-other-vendors.patch | [FRRouting/frr@53263b4](https://github.com/FRRouting/frr/commit/53263b4b620095c0c52b13883f49521ae54dfe6f) |
| 0024-staticd-Add-support-for-SRv6-uA-behavior.patch | [FRRouting/frr@feff426](https://github.com/FRRouting/frr/commit/feff426771999343008afe05efe680aa7cf63985) |
| 0025-Fpm-problems.patch | [FRRouting/frr@b2fc167](https://github.com/FRRouting/frr/commit/b2fc167978189238e045d719e11202ab303d2f59) |
| 0028-zebra-ensure-proper-return-for-failure-for-Sid-allocation.patch | [FRRouting/frr@5a63cf4](https://github.com/FRRouting/frr/commit/5a63cf4c0d1e7b84f59003877599c6575ba08a25) |
| 0029-staticd-Fix-a-crash-that-occurs-when-modifying-an-SRv6-SID.patch | [FRRouting/frr@6037ea3](https://github.com/FRRouting/frr/commit/6037ea350c98fbce60d0a287720cd4e60f7a21ec) |
| 0030-staticd-Avoid-requesting-SRv6-sid-from-zebra-when-loc-and-sid-block-dont-match.patch | [FRRouting/frr@dbd9fed](https://github.com/FRRouting/frr/commit/dbd9fed0b30dd1d3475686f71f87d326eeafd26c) |
| 0031-isisd-fix-srv6-sid-memory-leak.patch | [FRRouting/frr@25c813a](https://github.com/FRRouting/frr/commit/25c813ac382ba79270f40b85e168cdbcad499e2d) |
| 0032-show-ipv6-route-json-displays-seg6local-flavors.patch | [FRRouting/frr@a95fd3e](https://github.com/FRRouting/frr/commit/a95fd3e76fc1e056c53752963017a7fd75ed99b2) |
| 0033-staticd-Install-known-nexthops-upon-connection-with-zebra.patch | [FRRouting/frr@918a1f8](https://github.com/FRRouting/frr/commit/918a1f85c2edac05aaa9ec4e10b1013f435c6311) |
| 0034-staticd-Fix-an-issue-where-SRv6-SIDs-may-not-be-allocated-on-heavily-loaded-systems.patch | [FRRouting/frr@9c011b5](https://github.com/FRRouting/frr/commit/9c011b5b958059a5fa84fd725dbf2f2ba4a74c49) |
| 0035-lib-Add-support-for-stream-buffer-to-expand.patch | [FRRouting/frr@c0c46ba](https://github.com/FRRouting/frr/commit/c0c46bad15a5f3f69032678177ac7d00b7cd31be) |
| 0036-zebra-zebra-crash-for-zapi-stream.patch | [FRRouting/frr@6fe9092](https://github.com/FRRouting/frr/commit/6fe9092eb312e196260ee8deefb73b3f864b1432) |
| 0037-bgpd-Replace-per-peer-connection-error-with-per-bgp.patch | [FRRouting/frr@6a5962e](https://github.com/FRRouting/frr/commit/6a5962e1f8cef5096b4657f5219d16d0ec475538) |
| 0038-bgpd-remove-apis-from-bgp_route.h.patch | [FRRouting/frr@020245b](https://github.com/FRRouting/frr/commit/020245befdd818859f743290c4947c767c30c028) |
| 0039-bgpd-batch-peer-connection-error-clearing.patch | [FRRouting/frr@58f924d](https://github.com/FRRouting/frr/commit/58f924d287ed65f3b950e6cdc35871998cdb2199) |
| 0040-zebra-move-peer-conn-error-list-to-connection-struct.patch | [FRRouting/frr@6206e7e](https://github.com/FRRouting/frr/commit/6206e7e7ed2212cab5072000345ca2b21e094d1b) |
| 0041-bgpd-Allow-batch-clear-to-do-partial-work-and-contin.patch | [FRRouting/frr@c527882](https://github.com/FRRouting/frr/commit/c527882012c4f1d88439ad5512fc858f9f588777) |
| 0042-zebra-V6-RA-not-sent-anymore-after-interface-up-down.patch | [FRRouting/frr@deb8476](https://github.com/FRRouting/frr/commit/deb8476f63231d40ed6e1544295d3c33a31e5550) |
| 0043-bgpd-Paths-received-from-shutdown-peer-not-deleted.patch | [FRRouting/frr@d2bec7a](https://github.com/FRRouting/frr/commit/d2bec7a691cf9651808d6fb57e1720f536330ab9) |
| 0044-bgpd-Modify-bgp-to-handle-packet-events-in-a-FIFO.patch | [FRRouting/frr@12bf042](https://github.com/FRRouting/frr/commit/12bf042c688fedf82637fab9ff77aa1eab271160) |
| 0045-zebra-Limit-reading-packets-when-MetaQ-is-full.patch | [FRRouting/frr@937a9fb](https://github.com/FRRouting/frr/commit/937a9fb3e923beb1cf0a795daddb178cb1fe0ec4) |
| 0046-bgpd-Delay-processing-MetaQ-in-some-events.patch | [FRRouting/frr@83a92c9](https://github.com/FRRouting/frr/commit/83a92c926e750e785eeef715c7c3bd0154c83dbc) |
| 0047-bgpd-Fix-holdtime-not-working-properly-when-busy.patch | [FRRouting/frr@9a26a56](https://github.com/FRRouting/frr/commit/9a26a56c5188fd1c95e244932bc17f97b9051935) |
| 0048-bgpd-ensure-that-bgp_generate_updgrp_packets-shares-.patch | [FRRouting/frr@681caee](https://github.com/FRRouting/frr/commit/681caee9442fc20e97dca40c430004ce16bedb32) |
| 0049-zebra-show-command-to-display-metaq-info.patch | [FRRouting/frr@751ae76](https://github.com/FRRouting/frr/commit/751ae766486e4f03ebfa623767e0aef043261170) |
| 0050-bgpd-add-total-path-count-for-bgp-net-in-json-output.patch | [FRRouting/frr@be3c6d3](https://github.com/FRRouting/frr/commit/be3c6d3d3d6220d6ef8600c966f9fca838e10521) |
| 0051-lib-Add-nexthop_same_no_ifindex-comparison-function.patch | [FRRouting/frr@66f552c](https://github.com/FRRouting/frr/commit/66f552ce857b6dbf6b3578b2e936b983cae2f9c7) |
| 0052-zebra-show-nexthop-count-in-nexthop-group-command.patch | [FRRouting/frr@da5703e](https://github.com/FRRouting/frr/commit/da5703ed2fb99c4d96bfaafdbdb0c14d746ac78c) |
| 0053-zebra-Allow-nhg-s-to-be-reused-when-multiple-interfa.patch | [FRRouting/frr@46044a4](https://github.com/FRRouting/frr/commit/46044a45a7a91e9c4f52887c03b5015c83719aa3) |
| 0054-zebra-Prevent-active-setting-if-interface-is-not-ope.patch | [FRRouting/frr@e5f4675](https://github.com/FRRouting/frr/commit/e5f467557c4ed2007f004a1ae855403e57b013e6) |
| 0055-zebra-Add-nexthop-group-id-to-route-dump.patch | [FRRouting/frr@b732ad2](https://github.com/FRRouting/frr/commit/b732ad2c23cd7dbc7ec81678da8693462561c8e3) |
| 0056-zebra-Display-interface-name-not-ifindex-in-nh-dump.patch | [FRRouting/frr@c891cd2](https://github.com/FRRouting/frr/commit/c891cd269e3114d2ad564c3f23381c1a9085fbe9) |
| 0057-mgmtd-remove-bogus-hedge-code-which-corrupted-active.patch | [FRRouting/frr@b12b4c2](https://github.com/FRRouting/frr/commit/b12b4c28b4c4a76cbc906b703ee5a694a082ab74) |
| 0058-mgmtd-normalize-argument-order-to-copy-dst-src.patch | [FRRouting/frr@59d2368](https://github.com/FRRouting/frr/commit/59d2368b0f055f28aeda8f6080d686acfa35c20b) |
| 0059-zebra-Ensure-that-the-dplane-can-send-the-full-packe.patch | [FRRouting/frr@c89c330](https://github.com/FRRouting/frr/commit/c89c330bd7eb548c024bf325ccdd54ae48a052db) |

### Appendix B
##### [Table 2] Realigned Patches
|         Patch                                                    |         Type              |      Reason                   |
|------------------------------------------------------------------| ------------------------ | ----------------------------------|
| 0001-SONiC-ONLY-Reduce-severity-of-Vty-connected-from-message.patch | Lasting | Different Logic |
| 0002-SONiC-ONLY-Allow-BGP-attr-NEXT_HOP-to-be-0.0.0.0-due-to-allevia.patch | Lasting | Diff logic |
| 0003-SONiC-ONLY-nexthops-compare-vrf-only-if-ip-type.patch | Lasting | Diff logic |
| 0004-SONiC-ONLY-frr-remove-frr-log-outchannel-to-var-log-frr.log.patch | Lasting | Diff logic |
| 0005-Add-support-of-bgp-l3vni-evpn.patch | Temp&ensp; | As shown in patch |
| 0006-SONiC-ONLY-Link-local-scope-was-not-set-while-binding-socket-for-bgp-ipv6-link-local-neighbors.patch | &ensp;Lasting&ensp; | Diff logic |
| 0007-SONiC-ONLY-ignore-route-from-default-table.patch | Lasting| Diff logic |
| 0008-SONiC-ONLY-Use-vrf_id-for-vrf-not-tabled_id.patch | Lasting| Diff logic |
| 0009-SONiC-ONLY-bgpd-Change-log-level-for-graceful-restart-events.patch | Lasting| Diff logic |
| 0010-SONiC-ONLY-Disable-ipv6-src-address-test-in-pceplib.patch | Lasting | Diff logic |
| 0011-SONiC-ONLY-cross-compile-changes.patch | Lasting| Diff compilation |
| 0012-SONiC-ONLY-build-dplane-fpm-sonic-module.patch | Lasting | Diff compilation |
| 0013-SONiC-ONLY-zebra-do-not-send-local-routes-to-fpm.patch | Lasting | Diff logic |
| 0014-SONiC-ONLY-Adding-changes-to-write-ip-nht-resolve-via-default-c.patch | Lasting | Feature added by SONiC |
| 0015-SONiC-ONLY-When-the-file-is-config-replayed-we-cannot-handle-th.patch | Lasting | Diff logic |
| 0016-SONiC-ONLY-Set-multipath-to-514-and-disable-bgp-vnc-for-optimiz.patch | Lasting | Diff compilation |
| 0017-SONiC-ONLY-Patch-to-send-tag-value-associated-with-route-via-ne.patch | Lasting | Diff logic |
| 0018-SONiC-ONLY-SRv6-vpn-route-and-sidlist-install.patch | Lasting | Feature added by SONiC |
| 0022-SONiC-ONLY-This-error-happens-when-we-try-to-write-to-a-socket.patch | Lasting | Diff logic |
| 0026-SONiC-ONLY-Translate-tableid-for-dplane-route-notify.patch | Lasting | Diff logic |
| 0027-Dont-skip-kernel-routes-uninstall.patch | &ensp;Temp&ensp;&ensp; | FRR Open issue:<br>[FRRouting#19637](https://github.com/FRRouting/frr/issues/19637) |
| 0060-bgpd-Convert-bmp-path_info-tracking-from-hash-to-rbt.patch | &ensp;Temp&ensp;&ensp; | Merged in FRR<br>tagged frr-10.6.0 |
| 0061-bgpd-Fix-JSON-wrapper-brace-consistency-in-neighbor.patch | &ensp;Temp&ensp;&ensp; | Merged in FRR<br>tagged frr-10.6.0 |
| 0062-zebra-if-speed-change-check-fix.patch | &ensp;Temp&ensp; | Backported to FRR stable/10.4 |

### Appendix C
##### [Table 3] Summary of dplane_fpm_sonic.c Changes
|         Description Message                                 |         FRR Commit         |         Status in SONiC        |
|-------------------------------------------------------------| --------------------------- | -------------------------------|
|    zebra: Fix pass back of data from dplane through fpm pipe   |    [FRRouting/frr@b2fc167](https://github.com/FRRouting/frr/commit/b2fc167978189238e045d719e11202ab303d2f59)    |    NOT applicable to SONiC     |
|    zebra: Limit mutex for obuf to when we access obuf    |    [FRRouting/frr@c58da10](https://github.com/FRRouting/frr/commit/c58da10d2a700164e329352c5c22a924af3fa45c)    |    Merged as [sonic-net@1f7896e](https://github.com/sonic-net/sonic-buildimage/commit/1f7896e91b5b283b0fa28bc4078f0e5fc38e943b)    |
|    zebra: change fpm_read to batch the messages    |    [FRRouting/frr@7e8c18d](https://github.com/FRRouting/frr/commit/7e8c18d0b0149f879487d46255f279f14b20e52a)    |    Committed in this PR    |
|    bgpd,zebra: remove use of the EVENT_OFF macro    |    [FRRouting/frr@e9a756f](https://github.com/FRRouting/frr/commit/e9a756ffe13f0b008603168a1c891305b3c5488b)    |    Committed in this PR    |
|    zebra: Ensure that the dplane can send the full packet    |    [FRRouting/frr@c89c330](https://github.com/FRRouting/frr/commit/c89c330bd7eb548c024bf325ccdd54ae48a052db)    |    Merged as [sonic-net@6868762](https://github.com/sonic-net/sonic-buildimage/commit/686876262e5bb5ee672)    |
|    zebra: On dplane failure to write ctx, let zebra know    |    [FRRouting/frr@a1ce6a4](https://github.com/FRRouting/frr/commit/a1ce6a4a635fc6f9e2ef4dd7080ffe0637a58efd)    |    Committed in this PR    |

### Appendix D
##### [Table 4] New Patches Added
|         Patch                                                    |         Type              |      Reason                   |
|------------------------------------------------------------------| ------------------------ | ----------------------------------|
| 0064-bgpd-Prevent-unnecessary-re-install-of-routes.patch | Temp | Merged in FRR mainline [FRRouting/frr#19788](https://github.com/FRRouting/frr/pull/19788) |
| 0065-bgpd-fix-DEREF_OF_NULL.EX.COND-in-community_list_dup.patch | Temp | From FRR stable/10.4 |
| 0066-zebra-fix-up-memory-leak-in-dplane-shutdown-sequences.patch  | Temp | From FRR stable/10.4 |
| 0067-bgpd-fix-overflow-when-decoding-zapi-nexthop-for-srv.patch | Temp | From FRR stable/10.4 |
| 0068-bgpd-fix-memory-leak-in-evpn-mh.patch | Temp | From FRR stable/10.4 |
| 0069-bgpd-Fix-default-vrf-check-while-configuring-md5-password-for-prefix-on-the-bgp-listen-socket.patch | Temp | From FRR stable/10.4 |
| 0070-Gr-test-fixup.patch | Temp | From FRR stable/10.4 |
| 0071-staticd-Fix-typo-in-SRv6-SIDs-debug-logs-for-interfa.patch | Temp | From FRR stable/10.4 |
| 0072-zebra-Reset-encapsulation-source-address-when-no-srv6-is-executed.patch | Temp | From FRR stable/10.4 |
| 0073-zebra-Explicitly-print-exit-at-the-end-of-srv6-encap.patch | Temp | From FRR stable/10.4 |
| 0074-bgpd-Fix-crash-due-to-dangling-pointer-in-bnc-nht_in.patch | Temp | From FRR stable/10.4 |
| 0075-zebra-Add-missing-debug-guard-in-rt-netlink-code.patch | Temp | From FRR stable/10.4 |
| 0076-zebra-Add-missing-debug-guard-in-if-netlink-code.patch | Temp | From FRR stable/10.4 |
| 0077-lib-remove-zlog-tmp-dirs-by-default-at-exit.patch | Temp | From FRR stable/10.4 |
| 0078-staticd-Fix-SRv6-SID-installation-for-default-VRF.patch | Temp | From FRR stable/10.4 |
| 0079-bgpd-don-t-use-stale-evpn-pointer-in-bgp_update.patch | Temp | From FRR stable/10.4 |
| 0080-lib-Return-a-valid-JSON-if-prefix-list-is-not-found.patch | Temp | From FRR stable/10.4 |
| 0081-Allow-notify-callback-on-non-presence-container.patch | Temp | From FRR stable/10.4 |
| 0082-bgpd-fix-refcounts-at-termination.patch | Temp | From FRR stable/10.4 |
| 0083-bgpd-add-NULL-check-in-evpn-mh-code.patch | Temp | From FRR stable/10.4 |
| 0084-Revert-bgpd-Enable-Link-Local-Next-Hop-capability-for-unnumbered-peers-implicitly.patch | Temp | From FRR stable/10.4 |
| 0085-zebra-Cleanup-early-route-Q-when-removing-routes.patch | Temp | From FRR stable/10.4 |
| 0086-doc-Fix-documentation-regarding-capability-link-loca.patch | Temp | From FRR stable/10.4 |
| 0087-zebra-fix-neighbor-table-name-length.patch | Temp | From FRR stable/10.4 |
| 0088-bgpd-Do-not-override-a-specified-rd.patch | Temp | From FRR stable/10.4 |
| 0089-bgpd-EVPN-fix-auto-derive-rd-when-user-cfg-removed.patch | Temp | From FRR stable/10.4 |
| 0090-zebra-EVPN-fix-alignment-of-access-vlan-cli-output.patch | Temp | From FRR stable/10.4 |
| 0091-bgpd-EVPN-MH-fix-ES-EVI-memleak-during-shutdown.patch | Temp | From FRR stable/10.4 |
| 0092-bgpd-Do-not-complain-in-the-logs-if-we-intentionally.patch | Temp | From FRR stable/10.4 |
| 0093-bgpd-Put-local-BGP-ID-when-sending-NNHN-TLV-for-NH-c.patch | Temp | From FRR  stable/10.4 |
| 0094-zebra-fix-yang-data-for-mcast-group.patch | Temp | From FRR stable/10.4 |
| 0095-bgpd-Crash-due-to-usage-of-freed-up-evpn_overlay-att.patch | Temp | From FRR stable/10.4 |
| 0096-bgpd-Notify-all-incoming-outgoing-on-peer-group-noti.patch | Temp | From FRR stable/10.4 |
