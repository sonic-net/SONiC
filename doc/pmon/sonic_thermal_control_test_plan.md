# Thermal Control Test Plan

## Table of Contents

- [Overview](#overview)
- [Scope](#scope)
- [Test Structure](#test-structure)
  - [Setup Configuration](#setup-configuration)
  - [Ansible and Pytest](#ansible-and-pytest)
- [Test Cases](#test-cases)
  - [Show FAN Status Test](#show-fan-status-test)
  - [Show Thermal Status Test](#show-thermal-status-test)
  - [FAN Test](#fan-test)
  - [PSU Absence Test](#psu-absence-test)
  - [Invalid Policy Format Load Test](#invalid-policy-format-load-test)
  - [Invalid Policy Value Load Test](#invalid-policy-value-load-test)


## Overview

The purpose is to test functionality of thermal control feature on the SONiC switch DUT. The thermal control feature contains 3 major functions: FAN status monitor, thermal status monitor and thermal control policy management.

- "FAN status monitor" reads FAN status via platform API every 60 seconds and saves it to redis database. User can fetch FAN status via command line `show platform fanstatus`.
- "Thermal status monitor" reads thermal status via platform API every 60 seconds and saves it to redis database. User can fetch thermal status via command line `show platform temperature`.
- The thermal control policy is defined in a JSON file and loaded by thermal control daemon in pmon docker. Thermal control daemon collects thermal information and matches thermal conditions. Once some thermal conditions match, related thermal actions will be triggered. 

A more detailed design and function description can be found in this [document](https://github.com/keboliu/SONiC/blob/thermal_control_design/thermal-control-design.md).

## Scope

This test is targeting a running SONiC system with fully functioning configuration. The purpose of the test is functional testing of thermal control on SONiC system, making sure that FAN status and thermal status can be shown to user and correct actions are executed once predefined thermal policy conditions match.

## Test Structure

### Setup Configuration

Since this feature is not related to traffic and network topology, all current topology can be applied for this test.

### Ansible and Pytest

This test plan is based on platform test infrastructure as additional cases. The test will reuse current [platform test](https://github.com/sonic-net/SONiC-mgmt/tree/master/tests/platform) in SONiC-mgmt. New pytest test cases will be added to [test_platform_info.py](https://github.com/sonic-net/SONiC-mgmt/blob/master/tests/platform/test_platform_info.py). In addition, valid_policy.json,  invalid_format_policy.json and invalid_value_policy.json will be added as thermal policy configuration file for test purpose.

#### Valid policy file

In the valid policy file, two policies are defined. One is for "any PSU absence", the other is for "all FAN and PSU presence".

- In the case of "any PSU absence", the expected behavior based on the design and implementation is that FAN speed is set to 100% and thermal control algorithm is disabled.
- In the case of "all FAN and PSU presence", the thermal control algorithm is enabled and the FAN speed is being adjusted by the thermal control.

The valid_policy.json file content is like:

```json
{
    "thermal_control_algorithm": {
        "run_at_boot_up": "false",
        "fan_speed_when_suspend": "60"
    },
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
            "name": "any FAN absence",
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
                    "speed": "65"
                }
            ]
        }
    ]
}
```

#### Invalid format policy file

In invalid_format_policy.json, the file content is not valid JSON at all. A file with content "invalid" should be good for test purpose.

#### Invalid value policy file

In invalid_value_policy.json, the file content contains minus value of target speed. We couldn't cover all invalid value here because there are too many possibilities. The major purpose of this configuration file is to verify thermal control daemon would not crash while loading such an invalid configuration files. For other negative test cases, they are already covered by unit test. The invalid_value_policy.json content is like:

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

### Show FAN Status Test

Show FAN status test verifies that all FAN related information can be shown correctly via `show platform fanstatus`.

#### Procedure

1. Testbed setup.
2. Mock random data for "presence", "speed", "status", "target_speed", "led status".
3. Issue command `show platform fanstatus`.
4. Record the command output.
5. Verify that command output matches the mock data.
6. Restore mock data.

### Show Thermal Status Test

Show thermal status test verifies that all thermal related information can be shown correctly via `show platform temperature`.

#### Procedure

1. Testbed setup.
2. Fill mock data for "temperature", "high_threshold", "high_critical_threshold".
3. Issue command `show platform temperature`.
4. Record the command output.
5. Verify that command output matches the mock data.
6. Restore mock data.

### FAN Test

FAN test verifies that proper action should be taken for conditions including: FAN absence, FAN over speed, FAN under speed.

#### Procedure

1. Testbed setup.
2. Copy valid_policy.json to pmon docker and backup the original one.
3. Restart thermal control daemon to reload policy configuration file. Verify thermal algorithm is disabled and FAN speed is set to 60% according to configuration file.
4. Make mock data: first FAN absence.
5. Wait for at least 65 seconds. Verify target speed of all FANs are set to 100% according to valid_policy.json. Verify there is a warning log for FAN absence.
6. Make mock data: first FAN presence.
7. Wait for at least 65 seconds. Verify target speed of all FANs are set to 65% according to valid_policy.json. Verify there is a notice log for FAN presence.
8. Make mock data: first FAN speed exceed threshold(speed < target speed), second FAN speed exceed threshold(speed > target speed).
9. Wait for at least 65 seconds. Verify led turns to red for first and second FAN. Verify there is a warning log for over speed and a warning log for under speed.
10. Make mock data: first and second FAN speed recover to normal.
11. Wait for at least 65 seconds. Verify led turns to green for first and second FAN. Verify there are two notice logs for speed recovery.
12. Restore the original policy file. Restore mock data.

> Note: The reason that we wait at least 65 seconds is that thermal policy run every 60 seconds according to design.

### PSU Absence Test

PSU absence test verifies that once any PSU absence, all FAN speed will be set to proper value according to policy file.

#### Procedure

1. Testbed setup.
2. Copy valid_policy.json to pmon docker and backup the original one.
3. Restart thermal control daemon to reload policy configuration file.
4. Turn off one PSUs.
5. Wait for at least 65 seconds. Verify target speed of all FANs are set to 100% according to valid_policy.json.
6. Turn on one PSU and turn off the other PSU.
7. Wait for at least 65 seconds. Verify target speed of all FANs are still 100% according to valid_policy.json.
8. Turn on all PSUs.
9. Wait for at least 65 seconds. Verify target speed of all Fans are set to 65% according to valid_policy.json.
10. Restore the original policy file.

> Note: The reason that we wait at least 65 seconds is that thermal policy run every 60 seconds according to design.
> For switch who has only one PSU, step 6 and step 7 will be ignored.

### Invalid Policy Format Load Test

Invalid policy format test verifies that thermal control daemon does not exit when loading a invalid_format_policy.json file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and thermal monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_format_policy.json to pmon docker and backup the original one.
3. Restart thermal control daemon to reload policy configuration file.
4. Verify thermal control daemon can be started up. Verify error log about loading invalid policy file is output.
5. Restore the original policy file.

### Invalid Policy Value Load Test

Invalid policy value test verifies that thermal control daemon does not exit when loading a invalid_value_policy.json file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and thermal monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_value_policy.json to pmon docker and backup the original one.
3. Restart thermal control daemon to reload policy configuration file.
4. Verify thermal control daemon can be started up. Verify error log about loading invalid policy file is output.
5. Restore the original policy file.
