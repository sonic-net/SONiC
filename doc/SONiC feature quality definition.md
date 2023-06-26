# SONiC Feature Quality Definition
This document defines the different quality level of SONiC features.
The document does not cover the SONiC development flow, but defines what is needed for a feature to qualified with a specific quality level. 

The following qualify levels are defined:
- Alpha
- Beta
- General Availability (aka GA)

## Qualify level definition

### Alpha level
- Code PRs must come with unit tests (VS tests if applicable) aligned to code coverage
- For standalone feature it should be considered to have a compilation flag in disabled mode. Feature requires enabled/disabled via config_db and set to disabled
- Can go to master branch only
- For feature based on ASIC vendor SAI implementation: SAI is not avaialble yet
- For feature based on Platform vendor API implementation: not avaialble yet.
- Should not cause any degradation on avaialble features. Need to run and ensure sonic-mgmt test suits is passing with no degradation

### Beta level
- Code PRs must come with unit tests aligned to code coverage
- For standalone feature it should be considered to have a compilation flag in enabled mode. Feature requires enabled/disabled via config_db and set to disable. 
- Can go to master branch only
- For features based on ASIC vendor SAI implementation: SAI is available for at least 1 vendor
- For feature based on Platform vendor API implementation: available for at least 1 vendor.
- Should not cause any degradation on production features use relevant sonic-mgmt. tests to confirm
- New sonic-mgmt. test plan has been reviewed but partially implemented

### GA level
- Code PRs must come unit tests aligned to code coverage 
- For standalone feature it should be considered to have a compilation flag in disabled mode. Feature requires enabled/disabled via config_db and set to enabled if HLD claims for it
- Can go to master branch and can be considered as backport feature if must
- For features based on ASIC vendor SAI implementation: SAI is available for at least 1 vendor
- For feature based on Platform vendor API implementation: available for at least 1 vendor 
- Should not cause any degradation on production features use relevant sonic-mgmt. tests to confirm
- New sonic-mgmt. test plan has been signed off and fully implemented

## Quality level exposed in SONiC Release Notes
Extend the SONiC Release Notes which already covers the new features added to a release, with the quality release. 
Adding that info the the Release Note will allow
- One way to declare features quality
- Contribution awareness for quality guarantee and aim for GA level
- Clear and simple way for SONiC end users (who are not in the details of the code itself)

So, instead of large list, use a table in the following format: 

| Feature Name | Feature Description | HLD PR / PR Tracking | Maturity |
|:--------------|:------------|:------------|:-----------|

- If Beta/GA level maturity, ensure to provide a sonic-mgmt. PR or code as reference. 
- If sonic-mgmt. tests comes after the Release note is released, it can still be modified
- Maturity to be approved by sonic test subgroup based on the availability of the test and the coverage it expects to gain
**Note:** quality can be provided only on tests results availability, and this is out of the scope of this discussion 

## Action items
- Suggest to improvde HLD template and include a section for memory consumption. Notes to be taken:
   - No memory consumption expected when the feature is disabled via compilation
   - No growing memory consumption while feature is disabled by configuration
- Feature should be delivered with the following ON/OFF flags
  - Feature can be runtime disabled/enabled via configuration. 
  - Disabled while work in progress and majority is not GA
  - Can be enabled by default (if agreed on HLD review) only in GA level only
- 202305 Release note should be aligned with the new suggestion. It will be used for sharing information on features and availability of the tests.
- Once TSC approves suggestion, take to SONiC community and inform contributors to align on 202311 feature contribution
- sonic-mgmt. group to decide on quality guarantee template. Ying Xie (Microsoft) and Roy Sror (Nvidia) to lead





