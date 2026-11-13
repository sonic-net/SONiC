# SONiC Feature Deprecation and Removal Policy

This document is the standing policy and procedure for deprecating and removing features from SONiC. It is release independent. It defines the verdicts a feature can be given, the steps a proposal goes through before anything is deleted, and the notification a removal owes the community.

It was proposed by the SONiC Security Working Group, whose goal is to shrink the attack surface of the image. Less code means fewer packages, fewer CVEs, and less to build and test. Deprecation is not only a security matter, so this policy covers any feature removal, whatever the reason for it.

Each release that acts on this policy files its own plan as a High Level Design under `doc/eol-planning/`, named `<release>-eol-and-deprecation.md`. The plan lists that release's candidates and nothing more. The process itself stays here, so that it is reviewed and changed on its own rather than being rewritten in every cycle. The first such plan is [202611](../../doc/eol-planning/202611-eol-and-deprecation.md).

## 1. Why we remove code

- The best fix for a CVE is to delete the code that carries it.
- Unmaintained code is a standing risk, because it rarely gets patched.
- Dead build wiring hides real problems and slows builds.
- Fewer features mean a smaller image, fewer scans to triage, and less CI.

## 2. Definitions

| Term | Meaning |
|------|---------|
| Deprecate | Mark a feature as going away. It still ships, but it warns of removal. |
| Remove | Delete the code and its build wiring. |
| Keep | The feature stays. Review turned up a reason not to remove it. |
| Candidate | A feature proposed for a verdict in a given release plan. |
| EOL | End of life. |
| TSC | Technical Steering Committee. |
| WG | Working group. |

Releases ship twice a year, in November (`YYYY11`) and in May (`YYYY05`). A removal release is always named by that identifier.

## 3. Verdicts

Every candidate carries exactly one of three verdicts.

- **Remove now.** Dead, broken, or EOL with no real users. Delete it this cycle.
- **Deprecate now, remove later.** Still has possible users or needs migration work. Name a removal release.
- **Keep.** The feature stays. Review turned up real usage, a dependency another feature relies on, or a gap that the proposed replacement does not cover.

## 4. The per-release cycle

For each release:

1. **Propose.** File a release plan HLD under `doc/eol-planning/` with the candidates for that release. Each candidate states what it is, what replaces it, the gap in what you lose, the exact paths to remove, and a verdict.
2. **Pick a verdict.** One of the three in section 3.
3. **Review.** The community reviews the plan, and it is scheduled at the weekly HLD review on Tuesdays. Component owners sign off. A feature is not removed without owner sign-off. Review can change a verdict in either direction, and moving a candidate to **Keep** is a normal outcome rather than a failure of the process. When that happens, record what the review turned up and why the feature stays, so that a later cycle does not have to rediscover it.
4. **Take platform removals to the TSC.** Platforms are special, because a platform is somebody's hardware and the people who own it are not always the people who read HLDs. Every platform removal is proposed to the TSC in addition to the steps above, and the TSC can reject it. Owner sign-off does not substitute for that, and the TSC decision is what settles a platform removal.
5. **Notify the mailing list.** After HLD review, send the proposal to `sonic-dev@lists.sonicfoundation.dev`. Not everyone with a stake attends HLD review, and the mailing list is how the rest of them find out while there is still time to object. Include the full candidate list, the verdict for each one, the named removal release, and a date by which responses are wanted.
6. **Notify the interested working groups.** Send each candidate to the working group that owns the area it touches, where one exists. A working group knows its own users, so it is the fastest way to turn "we think nobody runs this" into a real answer. Reach the routing group for routing stack and FRR changes, the telemetry group for telemetry changes, the management group for management interface changes, and the platform and hardware groups for platform removals. Sending the same item to more than one group is fine and is better than missing one.
7. **Notify again before the branch date.** Every notification above goes out a second time, no later than two months before the release branch is cut, and revised for whatever the first round turned up. Anyone who has since changed a verdict says so in that second round. This gives a user who missed the first notice a last chance to speak up while there is still time to revert a removal.
8. **Announce.** Deprecations go in the release notes.
9. **Remove** in the named release.

The goal of steps 4 through 7 is to over-communicate. It costs little to send the same proposal to one more list or one more group, and it costs a great deal to remove something that a user turns out to depend on. Nobody should learn that a feature is gone from the release notes, or from their build breaking.

## 5. Rules of thumb

These guide the calls above.

- "Not built by default" and "not in CI" are hints, not proof. We check real use before calling anything dead.
- A forced bump, such as a libyang, base image, submodule pointer, or mass format change, does not count as maintenance. A feature that has seen only those is unmaintained.
- If a replacement has a gap, we name it so users can speak up.
- Silence is not consent on its own. It counts only after the notifications above have gone out twice and the second round has had time to draw a response.
- A removal that touches configuration is not finished until `sonic-utilities/scripts/db_migrator.py` cleans up what it leaves behind in CONFIG_DB. A device that upgrades keeps whatever it already had, so without a migrator change it carries dead `FEATURE` rows and orphaned tables forever, a table that outlives its YANG model can fail config validation, and a setting whose supported values have narrowed can leave the device pointing at a value that no longer exists.
- A removal lands as its own pull request, per candidate, after review and sign-off. A release plan is documentation and removes nothing by itself.

## 6. What a release plan contains

A release plan is an HLD and follows [the HLD template](../../doc/guidelines/hld_template.md). The candidate list is the body of its High Level Design section, split into the verdicts from section 3. Each candidate stands on its own and states:

- What the feature is, and where it came from.
- Why it should go, with the evidence behind the call, such as CI coverage, last genuine change, size, and known users.
- What replaces it, and any gap in what a user loses.
- The exact paths, build rules, flags, and pipeline jobs to remove.
- Anything to keep, and anything to check or move first.
- For a deferred removal, the release it is removed in.

Beyond the candidates, a plan covers the CONFIG_DB migration the removals need, the CLI and YANG models that go with them, and how the result is tested.

## 7. Changing this policy

This policy is owned by the TSC. Changes are made by pull request against this file and are reviewed the same way a release plan is, at HLD review and with the TSC settling anything contested.
