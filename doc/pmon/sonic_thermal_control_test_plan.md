# Thermal Control Test Plan

## Table of Content

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

The purpose is to test functionality of thermal control feature on the SONIC switch DUT. The thermal control feature contains 3 major functions: FAN status monitor, thermal status monitor and thermal control policy management.

- FAN status monitor read FAN status via platform API every 60 seconds and save it to redis database. User can watch FAN status via command line `show platform fanstatus`.
- Thermal status monitor read thermal status via platform API every 60 seconds and save it to redis database. User can watch thermal status via command line `show platform temperature`.
- The thermal control policy is defined in a JSON file and loaded by thermal control daemon in pmon docker. Thermal control daemon collects thermal information and matches thermal conditions. Once some thermal conditions match, related thermal actions will be triggered. 

More detail on thermal control feature can be found in this [document](https://github.com/keboliu/SONiC/blob/thermal_control_design/thermal-control-design.md).

## Scope

This test is targeting a running SONIC system with fully functioning configuration. The purpose of the test is functional testing of thermal control on SONIC system, making sure that FAN status and thermal status can shown to user and correct actions are executed once predefined thermal policy conditions match.

## Test Structure

### Setup Configuration

Since this feature is not related to traffic and network topology, all current topology can be applied for this test.

### Ansible and Pytest

No new Ansible YAML test case will be added. The test will reuse current [platform test](https://github.com/Azure/sonic-mgmt/tree/master/tests/platform) in sonic-mgmt. New pytest test cases will be added to [test_platform_info.py](https://github.com/Azure/sonic-mgmt/blob/master/tests/platform/test_platform_info.py). In addition, valid_policy.json,  invalid_format_policy.json and invalid_value_policy.json will be added as thermal policy configuration file for test purpose.

#### Valid policy file

In the valid policy file, two policies are defined. One is for "any PSU absence", the other is for "all FAN and PSU presence".

- For "any PSU absence", all FAN speed need be set to 100% and thermal control algorithm need to be disabled.
- For "all FAN and PSU presence", thermal control algorithm need to be enabled and FAN speed should be adjusted by it.

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
2. Unlink FAN related sysfs and fill fake data for "presence", "speed", "status", "target_speed", "led status".
3. Issue command `show platform fanstatus`.
4. Record the command output.
5. Verify that command output matches the fake data.
6. Link FAN related sysfs.

### Show Thermal Status Test

Show thermal status test verifies that all thermal related information can be shown correctly via `show platform temperature`.

#### Procedure

1. Testbed setup.
2. Unlink thermal related sysfs and fill fake data for "temperature", "high_threshold", "high_critical_threshold".
3. Issue command `show platform temperature`.
4. Record the command output.
5. Verify that command output matches the fake data.
6. Link thermal related sysfs.

### FAN Test

FAN test verifies that proper action should be taken for conditions including: FAN absence, FAN over speed, FAN under speed.

#### Procedure

1. Testbed setup.
2. Copy valid_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Unlink FAN related sysfs and make fake data: first FAN absence.
5. Wait for at least 60 seconds. Verify target speed of all FANs are set to 100% according to valid_policy.json. 
6. Make fake data: first FAN presence.
7. Wait for at least 60 seconds. Verify target speed of all FANs are set to 60% according to valid_policy.json. 
8. Make fake data: first FAN speed exceed threshold(speed < target speed), second FAN speed exceed theshold(speed > target speed).
9. Wait for at least 60 seconds. Veify led turns to red for first and second FAN.
10. Make fack data: first and second FAN speed recover to normal.
11. Wait for at least 60 seconds. Veify led turns to green for first and second FAN.
12. Link FAN related sysfs. Restore the original policy file.

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
10. Restore the original policy file.

> Note: The reason that we wait at least 60 seconds is that thermal policy run every 60 seconds according to design.
> For switch who has only one PSU, step 6 and step 7 will be ignored.

### Invalid Policy Format Load Test

Invalid policy format test verifies that thermal control daemon does not exit when loading a invalid_format_policy.json file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and thermal monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_format_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Verify FAN status and thermal status still display normally. (By check command output of `show platform fanstatus` and `show platform temperature`)
5. Recover the original policy configuration file and restart pmon service

### Invalid Policy Value Load Test

Invalid policy value test verifies that thermal control daemon does not exit when loading a invalid_value_policy.json file. The thermal control daemon cannot perform any thermal policy in this case, but FAN monitor and thermal monitor should still work.

#### Procedure

1. Testbed setup.
2. Copy invalid_value_policy.json to pmon docker and backup the original one.
3. Restart pmon service to trigger thermal control daemon reload policy configuration file.
4. Verify FAN status and thermal status still display normally. (By check command output of `show platform fanstatus` and `show platform temperature`)
5. Recover the original policy configuration file and restart pmon service
