# SONiC Community Release Manager Roles

Divide the work between PM and Technical Lead in the following way:

- **Product Manager:** KO of the release and manage it till release content is declared and available including release documentation and bug triage.
- **Technical Lead:** KO the release branch and maintain the release activities including what gets in and what is not, what tests required, etc.

---

## SONiC Community Release Manager

### From Planning to Execution (Feature Freeze)

---

### Release Manager Responsibilities

#### Call for Participation
- Call for feature candidate in community and have GitHub project available for all community members to submit their features list

#### Feature Roadmap Review in Community and Kick-off
- Prior to the meeting, for each feature in the GitHub project ensure all details are available including roadmap for HLD, PRs and reviewers (GitHub id for each author and reviewer)

#### Feature Submission Follow-up

**Cadence:**
- Monthly follow-up on the first few months
- Bi-Monthly follow-up on the last 2 months

- The idea is to recheck, remind, remove features which has no HLDs 2 months before branch out. Release roadmap finalization & feature submission deadline
- Report via mail based on automated pre-defined KPI
- ? Need to decide if meeting should be set for the follow-up or this is offline based on report. If meeting should be set, need to define who is must to take part of it

---

#### Declare and Follow-up on New SAI Version Integration and Vendor Support

#### Release Readiness Review in TSC
- Release readiness with feature and master stability with TSC forum
- For each feature announce the expected quality level
- Announce final content of the release, status of pending PRs and what will get in after branch out
- Features without HLD are out, features with HLD and PRs should get in, prioritize the review, decide what to do if no review feedback, etc.

#### Master Stability Bug Triage
- Go over latest issues from previous, ask for information, assign owners, set target DD
- Mark issues with priority to continue follow up
- Follow-up on all issues with priority agreed that need to be fixed/handled before branch out

#### Announce Release Branch Out

#### Initiate Release Retrospective (Features and Bug) and Present to TSC
- Need to collect all the data from the GitHub project in automated way and discuss lessons learned for the next release

---

### SONiC Release Manager Role | Timeline

- Release retrospective
- Release branch out

---

## SONiC Community Release Manager

### Release Maintainer (from Feature Freeze to Complete Qual)

---

### Release Manager

Need to define the role and take into consideration the following:

- What bot/automation is needed to allow other TSC members?
- What does it mean to ship? T0 + x?
- What quality level assurance defined? By whom?
- Weekly/Bi-weekly release management meeting with at least all TSC (Vendors, main contributors) representative
- Monthly updates to the TSC
