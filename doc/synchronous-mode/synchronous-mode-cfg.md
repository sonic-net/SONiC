# 1. Scope
This document describes the design for the configuration of synchronous mode between orchagent and syncd.

# 2. A brief of synchronous mode
An illustrative figure of the synchronous mode is shown below. The synchronous mode achieves a closed-loop execution if SAI APIs from orchagent. In contrast to the previous asynchronous mode which cannot properly handle SAI API failures, the synchronous mode can gracefully handle SAI API failures by conducting the proper actions in orchagent. Therefore, the synchronous mode can substantially improve the reliability of SONiC.

<img src="synchronous-mode-diagram.png" width="500">

# 3. Configuration design 
### 3.1 Configuration Requirements
1.	Allow users to enable or disable synchronous mode via CLI.
2.	Follow the image-specified mode when upgrading an image with cold/warm/fast-reboot if the synchronous mode configuration is not explicitly specified by users in configDB.
3.	Use the user-specified mode when an explicit configuration of synchronous mode exists in configDB.
4.	Support enabling/disabling the synchronous mode when parsing a minigraph and generating `config_db.json`.

Design details to achieve such requirements would presented in the following sections.

### 3.2 ConfigDB changes
The following field is added to `DEVICE_METADATA|localhost` in configDB to support the configuration of synchronous mode
```
DEVICE_METADATA|localhost
    "synchronous_mode": "enable|disable"
```
There are three possibilities for the field with the behavior as follows:
| Field value               | Behavior                              |
|---------------------------|---------------------------------------|
| enable                    | Enable synchronous mode.              |
| disable                   | Disable synchronous mode.             |
| Field does not exist      | Use the default mode defined by the image. This is expected if users only load images but never write the field in configDB with the minigraph parser or CLI command.|

The orchagent and syncd read the field and apply the configuration accordingly when `orchagent.sh` and ` syncd_init_common.sh` starts the two processes, respectively.

### 3.3 CLI command
A CLI command is provided to enable or disable synchronous mode: 

`config synchronous_mode {enable|disable}`

Note that the CLI command only writes the configuration into configDB. To further apply the configuration, it is required to restart swss. A message will be provided to the users to remind them of the need for swss restart after calling the command. The necessity of swss restart should also be included in the help message of the command line. This CLI command achieves requirement 1 in Section 3.1.

### 3.4 Configuration with SONiC images
A SONiC image does not write any configuration into `DEVICE_METADATA|localhost|synchronous_mode` by loading the image. 

If there is no previously defined synchronous mode configuration in configDB, the device applies the default mode defined by the image without the field `DEVICE_METADATA|localhost|synchronous_mode` exists in configDB. By loading an image with a different default mode, the device would execute the updated mode defined by the new image. As such, requirement 2 in Section 3.1 is achieved. 

When the synchronous mode configuration exists in configDB, the configuration in configDB would override the default mode specified by the image and be applied to the device. This achieves requirement 3 in Section 3.1.

### 3.5 Minigraph parser
The minigraph parser would explicitly write either "disable" or "enable" into `DEVICE_METADATA|localhost|synchronous_mode` in config_DB as the ground-truth configuration. And the configuration will be applied after swss restarts. Such a design complies with requirement 4 in Section 3.1.

### 3.6 Configuration with L2 switch mode
When configuring a device to [L2 Switch mode](https://github.com/sonic-net/SONiC/wiki/L2-Switch-mode), the configuration of synchronous mode in config_DB will be removed. In the scenario that there is no user-specified configuration for the synchronous mode in configDB before configuring to L2 Switch mode, the device will keep using the same default mode specified by the image after configuring to L2 switch mode. If the user would like to use a specific configuration for the synchronous mode, the user needs to specify the configuration with the CLI in Section 3.3 to explicitly wite the configuration into config_DB after configuring the switch to L2 switch mode.
