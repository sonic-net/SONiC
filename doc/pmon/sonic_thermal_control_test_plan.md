# Thermal Control Test Plan

# Table of Content

- [Overview](#overview)
- [Scope](#scope)
- [Test Structure](#test-structure)
  - [Setup Configuration](#setup-configuration)
  - [Ansible and Pytest](#ansible-and-pytest)
- [Test Cases](#test-cases)
  - [PSU Absence Test](#psu-absence-test)
  - [Invalid Policy Test](#invalid-policy-test)


## Overview

The purpose is to test functionality of thermal control policy on the SONIC switch DUT. The thermal control policy is defined in a JSON file and loaded by thermal control daemon in pmon docker. Thermal control daemon collects thermal information and matches thermal conditions. Once some thermal conditions match, related thermal actions will be triggered. More detail on thermal control feature can be found in this [document](https://github.com/keboliu/SONiC/blob/thermal_control_design/thermal-control-design.md).

## Scope

This test is targeting a running SONIC system with fully functioning configuration. The purpose of the test is functional testing of thermal control on SONIC system, making sure that correct actions are executed once predefined conditions match.

## Test Structure

### Setup Configuration

Since this feature is not related to traffic and network topology, default configuration on a T0 topology is good enough for this test.

### Ansible and Pytest

No new Ansible YML test case will be added. The test will reuse current [platform test](https://github.com/Azure/sonic-mgmt/tree/master/tests/platform) in sonic-mgmt. New pytest test cases will be added to [test_platform_info.py](https://github.com/Azure/sonic-mgmt/blob/master/tests/platform/test_platform_info.py). In addition, valid_policy.json and invalid_policy.json will be added as thermal policy configuration file for test purpose.

## Test Cases

### PSU Absence Test

PSU absence test verifies that once any PSU absence, all FAN speed will be set to proper value according to policy file.

#### Procedure

1. Testbed setup.
2. Copy valid_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Stop a PSU.
5. Verify target speed of all Fans are set to value according to valid_policy.json.
6. Resume the PSU.
7. Verify target speed of all Fans are set to value according to valid_policy.json.

### Invalid Policy Test

Invalid policy test verifies that thermal control daemon does not exit when loading a invalid policy file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and Temperature monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Verify FAN status and temperature status still display normally. (By check command output of "show platform fanstatus" and "show platform temperature")
