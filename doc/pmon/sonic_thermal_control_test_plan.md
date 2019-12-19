# Thermal Control Test Plan

## Table of Content

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

Since this feature is not related to traffic and network topology, all current topology is good for this test.

### Ansible and Pytest

No new Ansible YAML test case will be added. The test will reuse current [platform test](https://github.com/Azure/sonic-mgmt/tree/master/tests/platform) in sonic-mgmt. New pytest test cases will be added to [test_platform_info.py](https://github.com/Azure/sonic-mgmt/blob/master/tests/platform/test_platform_info.py). In addition, valid_policy.json,  invalid_format_policy.json and invalid_value_policy.json will be added as thermal policy configuration file for test purpose.

#### Valid policy file

In the valid policy file, two policies are defined. One is for "any PSU absence", the other is for "all PSU presence".

- For "any PSU absence", all FAN speed need be set to 100% and thermal control algorithm need to be disabled.
- For "all PSU absence", thermal control algorithm need to be enabled and FAN speed should be adjusted by it.

The valid_policy.json file content is like:

```json
{
    "info_types": [
        {
            "type": "fan_info"
        },
        {
            "type": "psu_info"
        }
    ],
    "policies": [
        {
            "name": "any PSU absence",
            "conditions": [
                {
                    "type": "fan.any.absence"
                }
            ],
            "actions": [
                {
                    "type": "thermal_control.control",
                    "status": "false"
                },
                {
                    "type": "fan.all.set_speed",
                    "speed": "100"
                }
            ]
        },
        {
            "name": "all FAN and PSU presence",
            "conditions": [
                {
                    "type": "fan.all.presence"
                },
                {
                    "type": "psu.all.presence"
                }
            ],
            "actions": [
                {
                    "type": "thermal_control.control",
                    "status": "true"
                },
                {
                    "type": "fan.all.set_speed",
                    "speed": "60"
                }
            ]
        }
    ]
}
```

#### Invalid format policy file

In invalid_format_policy.json, the file content is not valid JSON at all. A file with content "invalid" should be good for test purpose.

#### Invalid value policy file

In invalid_value_policy.json, the file content contains minus value of target speed. The invalid_value_policy.json content is like:

```json
{
    "info_types": [
        {
            "type": "fan_info"
        },
        {
            "type": "psu_info"
        }
    ],
    "policies": [
        {
            "name": "any PSU absence",
            "conditions": [
                {
                    "type": "fan.any.absence"
                }
            ],
            "actions": [
                {
                    "type": "fan.all.set_speed",
                    "speed": "-1"
                }
            ]
        }
    ]
}
```

## Test Cases

### PSU Absence Test

PSU absence test verifies that once any PSU absence, all FAN speed will be set to proper value according to policy file.

#### Procedure

1. Testbed setup.
2. Copy valid_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Stop two PSUs.
5. Wait for at least 60 seconds. Verify target speed of all FANs are set to 100% according to valid_policy.json.
6. Resume one PSU.
7. Wait for at least 60 seconds. Verify target speed of all FANs are still 100% because there is still one PSU absence.
8. Resume all PSU.
9. Verify target speed of all Fans are set to 60% according to valid_policy.json.

#### Note

- The reason that we wait at least 60 seconds is that thermal policy run every 60 seconds according to design.
- For switch who has only one PSU, step 6 and step 7 will be ignored.

### Invalid Policy Format Load Test

Invalid policy format test verifies that thermal control daemon does not exit when loading a invalid_format_policy.json file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and Temperature monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_format_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Verify FAN status and temperature status still display normally. (By check command output of "show platform fanstatus" and "show platform temperature")
5. Recover the original policy configuration file and restart pmon service

### Invalid Policy Value Load Test

Invalid policy format test verifies that thermal control daemon does not exit when loading a invalid_value_policy.json file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and Temperature monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_value_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Verify FAN status and temperature status still display normally. (By check command output of "show platform fanstatus" and "show platform temperature")
5. Recover the original policy configuration file and restart pmon service
