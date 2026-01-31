# Work Scope of SONiC Release Manager 

### Rev 0.1 ###

### Revision ###

 | Rev |     Date    |           Author          | Change Description                |
 |:---:|:-----------:|:-------------------------:|-----------------------------------|
 | 0.1 |  2024-9-30  | Jiang Kang/Storm Liang    | Initial version                   |


## Overview

The release manager is responsible for the release of the community SONiC version, and is responsible for handling various matters during the release of the SONiC community version, including the integration of new features, PR management, CI/CD, etc., to ensure that the SONiC community version can be released normally

## Responsibilities 

### Determine the new features of the release version
* Taking the 202411 version as an example, one month before the version release fork time, the release manager checks the candidate features according to the 202411 dashborad which link is https://github.com/orgs/sonic-net/projects/18, to sorts out which features need to enter the 202411 version, and which features need to be removed from the 202411 version. Not all features will be merged into the 202411 version.
* The release manager is responsible for contacting the owner of the features that need to enter the release version, grasping the progress, and tracking the integration of feature source codes.
* The release manager is responsible for updating the feature list of the release version and reporting to the TSC meeting.
  
### PR Management
* The release manager is responsible for managing PRs, categorizing PRs into bugfix PRs and non-bugfix PRs (e.g. a feature PR), and categorizing PRs by functional category, such as platform/Routing/Switch, etc., to help find the right person to review the code.
* In principle, only bugfix PRs are accepted. For featrue PRs, they need to be approved by TSC meeting before they can be merged
* In principle, the code modification of a bugfix should be less than 200 lines. Bugfixes with more than 200 lines are recommended to be transferred to requirement tracking.
* For all merged bugfixes, corresponding sonic-mgmt test cases need to be provided to cover the modifications of the bugfix and ensure quality. This is the bottom line.
* The release manager needs to organize community experts to review the PR code. Only PRs that pass the code review are allowed to be merged.
* The release manager needs to ensure that the PR passes the community's CI/CD test and needs to handle the failure of the PR automated test to determine whether the community's test environment causes the PR to fail or the PR's own code problems cause the automated test to fail.
* PRs for other special cases that require integration into the release version need to be approved by the TSC meeting.







