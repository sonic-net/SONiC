# Technical Steering Committee (TSC) Election

   The SONiC Technical Steering Committee (TSC) is responsible for directing the technical aspects of the SONiC project by bringing together members from various segments of the SONiC community to advance its development. Serving as a TSC member entails a substantial time commitment, technical expertise, and a grasp of industry trends. Instead of overloading the TSC with a heavy process of candidate screening, voter’s eligibility assessment, voting weight assignment, vote counting, the TSC should be focused on better serving the community by driving the technical roadmap of SONiC.  

## Meritocracy Principle

   We embrace the principle of meritocracy and strive to ensure that the TSC is composed of organizations and individuals who are qualified and committed to the project.  To this angle, we would like to ensure the election process is through transparent and quantifiable attributes in the SONiC Community Ecosystem, the elected organizations are heavily invested and involved in the success of SONiC.  We invite individuals and organizations to participate in the TSC election process, and we will weigh their opinions according to their contributions to the SONiC project as a whole.  In the following, we describe how we quantify the contributions of each individual or organization based on the concept of "SONiC Influence Index (SII)".

$$
SONiC Influential Index (SII) = (Contribution \times Weight) + (Innovation \times Weight) + (SONiC Proliferation \times Weight )
$$

| Contribution (from past 5 years) | Category | Weight Multiplier |
|--------------------------------  |----------| -------- |
| Merged HLD [1] Count              | Development | 50 |
| Merged PR [2] Count (S/M/L)       | Development | 10/20/50 |
| PR Review Count (S/M/L)       | Development | 1/2/5    |
| PR cherry-picking [3] Count       | Development |  5 |
| Documentations (Release Notes/Meeting Minutes) | Development |  50/1  |
| New ASIC [4] Introduction Count | Development |  50 |
| Issues Opened Count               |  Quality [5] | 5 |
| Issues Triaged/Fixed Count        | Quality | 10 |
| Merged SONiC MGMT TEST Plan HLD [1] Count | Quality | 100 |
| Merged Test cases [2] (S/M/L)        | Quality | 20/40/100|
| TEST PR review count (S/M/L)     | Quality | 2/4/10 |
| Summit Presentation Count       | Innovation | 50  |
| Hackathon Participation Team Count | Innovation | 10 |
| SONiC Production Deployment (S/M/L) [6] | Proliferation | 10/100/500|

[1]: HLD are new or substantial changes reviewed in the SONiC community review meeting, minor amendment are counted towards merged PR

[2]: PR sizing Small/Medium/Large based on LoCs, each carries a different multiplier (Small: 1-50 LoCs, Medium: 51-300 LoCs, Large: >301 LoCs)

[3]: PR cherry-picking is release maintenance branch to ensure high quality of a release community branch.

[4]: ASIC support is a prerequisite of platform enablement and rollout of SONiC. ASIC support is from SAI binary distribution not accounted for in the merged PR contribution. Platform enablement/introduction will be accounted in merged PRs.

[5]: SONiC community view quality as the foundation to deliver a stable and reliable product. Therefore, we consciously attribute more weight to quality contribution.

[6]: SONiC Production Deployment Small/Medium/Large based on production network instances deployed within the organization (Small: 100 - 500, Medium: 501 - 50,000, Large: >50,001). Production Deployment score is counted per election cycle, eg, an organization with 1000 SONiC production nodes will add 100 points to its SII

There will be more forms of involvement and attributes to be accounted for as the SONiC project evolves, future changes to SII structure will require TSC approval.

## Voter Participation

   The TSC election process will be open to all SONiC community contributing members to participate as a voter. They can either participate as an unaffiliated individual or or at the organizational level as a single entity.  Every organization or individual participating the TSC election will calculate their SONiC Influential Index (SII) based on above mentioned formula, and their vote will be weighted according to their SII.  To avoid double counting, a community member can only participate in the election process as either an unaffiliated individual or an organization, but not both.

## Nominee Identification

1. **Organizational Nominee**:
   We recognize that fact that at this point most SONiC community members are contributing to the project as part of the overall effort of their respective organizations.  Therefore, those organizations can choose to participate in the TSC election process as a single entity.  However, we ask each organization to nominate ONE representative to serve on the TSC with sufficient time commitments.

   While individual community members may change their organizations or roles, the organizations themselves are more stable in their commitment to SONiC.  Therefore, the elected organizations will retain the right to nominate another community member as their organizational representative in the TSC later without an re-election being necessary.

2. **Individual Nominee**:
   We also recognize that there are individual community members who have contributed significantly to the project and are not affiliated with any organization. We welcome these individuals to nominate themselves for the TSC. We do not accept third-party nominations for individual community members to ensure the commitment from the nominee.

## Election Process

Each voting organization or individual will cast their vote to select 9 TSC members. Their vote will carry the weight according to the SII calculated.  The election process will be conducted in the following steps:

1. Nominee inform the community of their intention to run for the TSC by sending a nomination letter to the TSC chair and community manager. The nomination letter should include the following information:
   * Name
   * Organization
   * Email
   * A brief statement of why the nominee wants to serve on the TSC

2. Voters inform the community of their intention to vote by sending a vote letter to the TSC chair and community manager. The vote letter should include the following information:
   * Name
   * Organization
   * Email
   * SII (with information on how this is calculated)
   * A list of 9 nominees to vote for

The top 9 candidates with the highest total SII will be elected as TSC members.

The current TSC chair is Lihua Yuan [lihua@linux.com]) and community manager is Lucy Hyde [lhyde@linuxfoundation.org]). They will be responsible for organizing the election process in a transparent manner.  
