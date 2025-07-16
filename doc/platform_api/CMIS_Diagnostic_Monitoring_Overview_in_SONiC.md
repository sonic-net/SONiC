# CMIS Diagnostic Monitoring Overview in SONiC

## 1. Overview

The CMIS (Common Management Interface Specification) diagnostic monitoring feature is a standard for monitoring the performance of optical transceivers. It provides a way to monitor the performance of optical transceivers in real time. SONiC periodically reads the diagnostic monitoring data from the optical transceivers and stores the data in the database. The data can be retrieved using the SONiC CLI or by querying the database directly.

The current scope of the CMIS diagnostic monitoring feature in SONiC includes the following parameters:

- **DOM (Digital Optical Monitoring) data:** Provides real-time monitoring of optical transceiver parameters such as temperature, voltage, and optical power.
- **VDM (Versatile Diagnostics Monitoring) data:** Offers versatile diagnostic information for enhanced monitoring and troubleshooting.
- **PM (Performance Monitoring) data:** Applicable only for C-CMIS transceivers, this includes performance metrics such as error counts and signal quality indicators.

## 2. Requirements, future enhancements Non-goals

### Requirements

The CMIS diagnostic monitoring feature in SONiC requires the following:

1. Capturing the diagnostic monitoring data from the optical transceivers and storing it in the database at regular intervals.
2. Providing a way to retrieve the diagnostic monitoring data using the SONiC CLI as well as by querying the database directly.
3. Optimizing the periodic update time for the diagnostic monitoring data by storing diagnostic information for only 1 subport from a breakout port group.
4. Storing the flag change count, last flag set and clear time for each flag in the database during a link change event. This is necessary because the periodic update time for the diagnostic monitoring data may not be frequent enough to capture the flag change event.
5. Updating the last table update time in the database whenever the diagnostic monitoring data is updated.
6. Capturing the real diagnostic update interval in the database for each port since this time can vary with multiple factors such as the number of optics plugged in, I2C latency, host handling of diagnostic data and various other factors.

### Future Enhancements

1. Creating a mechanism to store the flag change count and last flag set and clear time in the database so that this data is not lost during `xcvrd` warm restart or during device warm reboots. The current implementation deletes this data as part of the `xcvrd` shutdown process.

### Non-goals (Exceptions and Scope Beyond the Current Implementation)

1. **Handling Multiple Link Flaps In a Short Period to Update Flag Metadata**:
   - In the event of multiple link flaps occurring in a short period, the flag change count and the last flag set and clear time may not be accurate.
   - The short period refers to a scenario where the periodic update time for the diagnostic monitoring data is not frequent enough to capture the link change events through the `DomInfoUpdateTask` thread.
   - This behavior is due to the flags being clear-on-read latched values and the `DomInfoUpdateTask` thread being a single-threaded process that updates the flag metadata during link change events and periodically reads diagnostic data from the optics.

    **Example**

    The following table illustrates an example scenario where the last flag set time is not updated in line with link flap events:

    **Table 1: Example Scenario of Flag Metadata Update During Link Flap Events and Periodic Update Time**

    `X` refers to a specific type of flag on the module.  
    `DB` means database.

    | Time Event Number | Timestamp of Event            | DB Update Trigger (Periodic Polling or Link Change Event Handler) | Flag X Value on Module - Before SW Read | Flag X Value on Module - After SW Read | Flag X Value in DB After Reading from Module | Flag X Set Time in DB After Reading from Module | Flag X Clear Time in DB After Reading from Module | Flag X Change Count in DB After Reading from Module | Link Flap Count in APPL_DB |
    |-------------------|-------------------------------|------------------------------------------------------------------|-----------------------------------------|----------------------------------------|------------------------------------------------|-------------------------------------------------|--------------------------------------------------|----------------------------------------------------|----------------------------|
    | T1                | Wed Oct 16 03:46:41 2024      | Link DOWN event                                                  | Set                                     | Set                                    | Set                                            | Wed Oct 16 03:46:41 2024                        | Never                                            | 1                                                  | 1                          |
    | T2                | Wed Oct 16 03:46:42 2024      | Link UP event                                                    | Set                                     | Clear                                  | Set                                            | Wed Oct 16 03:46:41 2024                        | Never                                            | 1                                                  | 2                          |
    | T3                | Wed Oct 16 03:46:42 2024      | Link DOWN event                                                  | Set                                     | Set                                    | Set                                            | Wed Oct 16 03:46:41 2024                        | Never                                            | 1                                                  | 3                          |
    | T4                | Wed Oct 16 03:46:43 2024      | Link UP event                                                    | Set                                     | Clear                                  | Set                                            | Wed Oct 16 03:46:41 2024                        | Never                                            | 1                                                  | 4                          |
    | T5                | Wed Oct 16 03:46:44 2024      | Link DOWN event                                                  | Set                                     | Set                                    | Set                                            | Wed Oct 16 03:46:41 2024                        | Never                                            | 1                                                  | 5                          |
    | T6                | Wed Oct 16 03:46:55 2024      | Link UP event                                                    | Set                                     | Clear                                  | Set                                            | Wed Oct 16 03:46:41 2024                        | Never                                            | 1                                                  | 6                          |
    | T7                | Wed Oct 16 03:47:01 2024      | Periodic polling                                                 | Clear                                   | Clear                                  | Clear                                          | Wed Oct 16 03:46:41 2024                        | Wed Oct 16 03:47:01 2024                        | 2                                                  | 6                          |

    **Explanation**:

    - In the Table 1 scenario, the flag X value on the module is set during the link down event at time T1.
    - However, the flag set time is not updated even though, multiple link change events were detected.
    - The flag clear time in the database is updated during the periodic polling event at time T7 and not during all the link up events at times T2, T4, and T6.
    - The flag change count in the database is updated to 2 during the periodic polling event at time T7, even though the flag changed on the module 6 times.

2. **Updating Diagnostic Information During the CMIS Initialization Phase**:
    - Diagnostic information will not be updated if the port (even if only one subport of a breakout port group) is not in a [CMIS terminal state](https://github.com/sonic-net/sonic-platform-daemons/blob/0b0ea3b2a3ed60ef00f25305631a30314f59a6fe/sonic-xcvrd/xcvrd/xcvrd.py#L68). 

    - This behavior adheres to the CMIS specification, which recommends:  
        > "It is recommended that hosts minimize management operations while in this state. Dynamic Memory Map content may be unreliable while in this state and should not be read or written."

    - By following this guideline, SONiC ensures data reliability and avoids potential issues caused by accessing unstable diagnostic data during the initialization phase.

3. **Flag Clear Time Update**:
   - The clear time of the flag in the database will be updated after the second read of the flag register.
   - This is because the flag registers are clear-on-read latched values.

    **Example**:

    - In Table 1, consider the time events T6 and T7.
    - The flag X value on the module is cleared during the link up event at time T6.
    - The flag clear time in the database is updated during the periodic polling event at time T7.

## 3. STATE_DB Schema for CMIS Diagnostic Monitoring

The CMIS diagnostic monitoring data is stored in the `STATE_DB` database. Each logical port on the switch has a corresponding entry in the `STATE_DB` schema unless the device is configured in breakout mode. For devices configured in breakout mode, only the first port of the breakout group will have the diagnostic monitoring data stored in the `STATE_DB` schema since the diagnostic monitoring data is the same for all ports in the breakout group.

The `STATE_DB` schema for the CMIS diagnostic monitoring feature includes the following tables:

- `TRANSCEIVER_DOM_SENSOR`: Stores real-time DOM data for the optical transceivers.
- `TRANSCEIVER_DOM_THRESHOLD`: Contains threshold values for DOM parameters.
- `TRANSCEIVER_DOM_FLAG`: Stores flags indicating the status of various DOM parameters.
- `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each DOM flag has changed.
- `TRANSCEIVER_DOM_FLAG_SET_TIME`: Records the last timestamp when each DOM flag was set.
- `TRANSCEIVER_DOM_FLAG_CLEAR_TIME`: Records the last timestamp when each DOM flag was cleared.
- `TRANSCEIVER_VDM_REAL_VALUE`: Stores VDM sample data.
- `TRANSCEIVER_VDM_HALARM_THRESHOLD`: Stores the high alarm threshold values for the VDM data.
- `TRANSCEIVER_VDM_LALARM_THRESHOLD`: Stores the low alarm threshold values for the VDM data.
- `TRANSCEIVER_VDM_HWARN_THRESHOLD`: Stores the high warning threshold values for the VDM data.
- `TRANSCEIVER_VDM_LWARN_THRESHOLD`: Stores the low warning threshold values for the VDM data.
- `TRANSCEIVER_VDM_HALARM_FLAG`: Stores the high alarm flag for the VDM data.
- `TRANSCEIVER_VDM_LALARM_FLAG`: Stores the low alarm flag for the VDM data.
- `TRANSCEIVER_VDM_HWARN_FLAG`: Stores the high warning flag for the VDM data.
- `TRANSCEIVER_VDM_LWARN_FLAG`: Stores the low warning flag for the VDM data.
- `TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each VDM high alarm flag has changed.
- `TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each VDM low alarm flag has changed.
- `TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT`: Keeps a count of how many times each VDM high warning flag has changed.
- `TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT`: Keeps a count of how many times each VDM low warning flag has changed.
- `TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME`: Records the last timestamp when each VDM high alarm flag was set.
- `TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME`: Records the last timestamp when each VDM low alarm flag was set.
- `TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME`: Records the last timestamp when each VDM high warning flag was set.
- `TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME`: Records the last timestamp when each VDM low warning flag was set.
- `TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME`: Records the last timestamp when each VDM high alarm flag was cleared.
- `TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME`: Records the last timestamp when each VDM low alarm flag was cleared.
- `TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME`: Records the last timestamp when each VDM high warning flag was cleared.
- `TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME`: Records the last timestamp when each VDM low warning flag was cleared.
- `TRANSCEIVER_STATUS`: Stores the module and datapath state data along with various flags related to it. Also stores various Tx and Rx related status values.
- `TRANSCEIVER_STATUS_FLAG`: Stores the module and datapath status flags along with various Tx and Rx related status flags.
- `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT`: Stores the count of times the transceiver status flag has changed.
- `TRANSCEIVER_STATUS_FLAG_SET_TIME`: Records the timestamp when the transceiver status flag was set.
- `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME`: Records the timestamp when the transceiver status flag was cleared.
- `TRANSCEIVER_PM`: Stores performance monitoring data.

**Note**  

Tables with a `_FLAG` suffix store flag statuses for the corresponding data. All of these flags are clear-on-read latched registers, except for the SFF-8472 `TRANSCEIVER_STATUS_FLAG` table, which stores non-latched registers. Metadata tables (e.g., `_FLAG_CHANGE_COUNT`, `_FLAG_SET_TIME`, `_FLAG_CLEAR_TIME`) provide additional information about flag changes.

### 3.1 Transceiver DOM

#### 3.1.1 Transceiver DOM sensor data

The `TRANSCEIVER_DOM_SENSOR` table stores the real-time DOM data for the optical transceivers.

lane_num: Represents the lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver DOM sensor information for a port
    key                          = TRANSCEIVER_DOM_SENSOR|ifname    ; information module DOM sensors on port
    ; field                      = value
    last_update_time             = STR                              ; last update time for diagnostic data
    temperature                  = FLOAT                            ; temperature value in Celsius
    voltage                      = FLOAT                            ; voltage value in V
    tx{lane_num}power            = FLOAT                            ; tx power in dBm for each lane
    rx{lane_num}power            = FLOAT                            ; rx power in dBm for each lane
    tx{lane_num}bias             = FLOAT                            ; tx bias in mA for each lane
    laser_temperature            = FLOAT                            ; laser temperature value in Celsius

    ;C-CMIS specific fields
    laser_config_freq            = FLOAT                            ; laser configured frequency in MHz
    laser_curr_freq              = FLOAT                            ; laser current frequency in MHz
    tx_config_power              = FLOAT                            ; configured tx output power in dbm
```

#### 3.1.2 Transceiver DOM threshold data

The `TRANSCEIVER_DOM_THRESHOLD` table stores the threshold values for the DOM data.

```plaintext
    ; Defines Transceiver DOM threshold info for a port
    key                          = TRANSCEIVER_DOM_THRESHOLD|ifname ; DOM threshold information for module on port
    ; field                      = value
    last_update_time             = STR                              ; last update time for diagnostic data
    temphighalarm                = FLOAT                            ; temperature high alarm threshold in Celsius
    temphighwarning              = FLOAT                            ; temperature high warning threshold in Celsius
    templowalarm                 = FLOAT                            ; temperature low alarm threshold in Celsius
    templowwarning               = FLOAT                            ; temperature low warning threshold in Celsius
    vcchighalarm                 = FLOAT                            ; vcc high alarm threshold in V
    vcchighwarning               = FLOAT                            ; vcc high warning threshold in V
    vcclowalarm                  = FLOAT                            ; vcc low alarm threshold in V
    vcclowwarning                = FLOAT                            ; vcc low warning threshold in V
    txpowerhighalarm             = FLOAT                            ; tx power high alarm threshold in dBm
    txpowerlowalarm              = FLOAT                            ; tx power low alarm threshold in dBm
    txpowerhighwarning           = FLOAT                            ; tx power high warning threshold in dBm
    txpowerlowwarning            = FLOAT                            ; tx power low alarm threshold in dBm
    rxpowerhighalarm             = FLOAT                            ; rx power high alarm threshold in dBm
    rxpowerlowalarm              = FLOAT                            ; rx power low alarm threshold in dBm
    rxpowerhighwarning           = FLOAT                            ; rx power high warning threshold in dBm
    rxpowerlowwarning            = FLOAT                            ; rx power low warning threshold in dBm
    txbiashighalarm              = FLOAT                            ; tx bias high alarm threshold in mA
    txbiaslowalarm               = FLOAT                            ; tx bias low alarm threshold in mA
    txbiashighwarning            = FLOAT                            ; tx bias high warning threshold in mA
    txbiaslowwarning             = FLOAT                            ; tx bias low warning threshold in mA
    lasertemphighalarm           = FLOAT                            ; laser temperature high alarm threshold in Celsius
    lasertemplowalarm            = FLOAT                            ; laser temperature low alarm threshold in Celsius
    lasertemphighwarning         = FLOAT                            ; laser temperature high warning threshold in Celsius
    lasertemplowwarning          = FLOAT                            ; laser temperature low warning threshold in Celsius
```

#### 3.1.3 Transceiver DOM flag data

The `TRANSCEIVER_DOM_FLAG` table stores the flag status for the DOM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flags for a port
    key                          = TRANSCEIVER_DOM_FLAG|ifname    ; information module DOM flags on port
    ; field                      = value
    last_update_time                 = STR                ; last update time for diagnostic data
    tempHAlarm                       = BOOLEAN            ; temperature high alarm flag 
    tempHWarn                        = BOOLEAN            ; temperature high warning flag
    tempLAlarm                       = BOOLEAN            ; temperature low alarm flag
    tempLWarn                        = BOOLEAN            ; temperature low warning flag
    vccHAlarm                        = BOOLEAN            ; vcc high alarm flag
    vccHWarn                         = BOOLEAN            ; vcc high warning flag
    vccLAlarm                        = BOOLEAN            ; vcc low alarm flag
    vccLWarn                         = BOOLEAN            ; vcc low warning flag
    tx{lane_num}powerHAlarm          = BOOLEAN            ; tx power high alarm flag
    tx{lane_num}powerLAlarm          = BOOLEAN            ; tx power low alarm flag
    tx{lane_num}powerHWarn           = BOOLEAN            ; tx power high warning flag
    tx{lane_num}powerLWarn           = BOOLEAN            ; tx power low warning flag
    rx{lane_num}powerHAlarm          = BOOLEAN            ; rx power high alarm flag
    rx{lane_num}powerLAlarm          = BOOLEAN            ; rx power low alarm flag
    rx{lane_num}powerHWarn           = BOOLEAN            ; rx power high warning flag
    rx{lane_num}powerLWarn           = BOOLEAN            ; rx power low warning flag
    tx{lane_num}biasHAlarm           = BOOLEAN            ; tx bias high alarm flag
    tx{lane_num}biasLAlarm           = BOOLEAN            ; tx bias low alarm flag
    tx{lane_num}biasHWarn            = BOOLEAN            ; tx bias high warning flag
    tx{lane_num}biasLWarn            = BOOLEAN            ; tx bias low warning flag
    lasertempHAlarm                  = BOOLEAN            ; laser temperature high alarm flag
    lasertempLAlarm                  = BOOLEAN            ; laser temperature low alarm flag
    lasertempHWarn                   = BOOLEAN            ; laser temperature high warning flag
    lasertempLWarn                   = BOOLEAN            ; laser temperature low warning flag
```

#### 3.1.4 Transceiver DOM flag change count data

The `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table stores the flag change count for the DOM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag change count for a port
    key                              = TRANSCEIVER_DOM_FLAG_CHANGE_COUNT|ifname   ; information module DOM flags change count on port
    ; field                          = value
    tempHAlarm                       = INTEGER            ; temperature high alarm change count
    tempHWarn                        = INTEGER            ; temperature high warning change count
    tempLAlarm                       = INTEGER            ; temperature low alarm change count
    tempLWarn                        = INTEGER            ; temperature low warning change count
    vccHAlarm                        = INTEGER            ; vcc high alarm change count
    vccHWarn                         = INTEGER            ; vcc high warning change count
    vccLAlarm                        = INTEGER            ; vcc low alarm change count
    vccLWarn                         = INTEGER            ; vcc low warning change count
    tx{lane_num}powerHAlarm          = INTEGER            ; tx power high alarm change count
    tx{lane_num}powerLAlarm          = INTEGER            ; tx power low alarm change count
    tx{lane_num}powerHWarn           = INTEGER            ; tx power high warning change count
    tx{lane_num}powerLWarn           = INTEGER            ; tx power low warning change count
    rx{lane_num}powerHAlarm          = INTEGER            ; rx power high alarm change count
    rx{lane_num}powerLAlarm          = INTEGER            ; rx power low alarm change count
    rx{lane_num}powerHWarn           = INTEGER            ; rx power high warning change count
    rx{lane_num}powerLWarn           = INTEGER            ; rx power low warning change count
    tx{lane_num}biasHAlarm           = INTEGER            ; tx bias high alarm change count
    tx{lane_num}biasLAlarm           = INTEGER            ; tx bias low alarm change count
    tx{lane_num}biasHWarn            = INTEGER            ; tx bias high warning change count
    tx{lane_num}biasLWarn            = INTEGER            ; tx bias low warning change count
    lasertempHAlarm                  = INTEGER            ; laser temperature high alarm change count
    lasertempLAlarm                  = INTEGER            ; laser temperature low alarm change count
    lasertempHWarn                   = INTEGER            ; laser temperature high warning change count
    lasertempLWarn                   = INTEGER            ; laser temperature low warning change count
```

#### 3.1.5 Transceiver DOM flag time set data

The `TRANSCEIVER_DOM_FLAG_SET_TIME` table stores the last set time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time set for a port
    key                          = TRANSCEIVER_DOM_FLAG_SET_TIME|ifname   ; information module DOM flag time set on port
    ; field                      = value
    tempHAlarm                       = STR           ; temperature high alarm last set time
    tempHWarn                        = STR           ; temperature high warning last set time
    tempLAlarm                       = STR           ; temperature low alarm last set time
    tempLWarn                        = STR           ; temperature low warning last set time
    vccHAlarm                        = STR           ; vcc high alarm last set time
    vccHWarn                         = STR           ; vcc high warning last set time
    vccLAlarm                        = STR           ; vcc low alarm last set time
    vccLWarn                         = STR           ; vcc low warning last set time
    tx{lane_num}powerHAlarm          = STR           ; tx power high alarm last set time
    tx{lane_num}powerLAlarm          = STR           ; tx power low alarm last set time
    tx{lane_num}powerHWarn           = STR           ; tx power high warning last set time
    tx{lane_num}powerLWarn           = STR           ; tx power low warning last set time
    rx{lane_num}powerHAlarm          = STR           ; rx power high alarm last set time
    rx{lane_num}powerLAlarm          = STR           ; rx power low alarm last set time
    rx{lane_num}powerHWarn           = STR           ; rx power high warning last set time
    rx{lane_num}powerLWarn           = STR           ; rx power low warning last set time
    tx{lane_num}biasHAlarm           = STR           ; tx bias high alarm last set time
    tx{lane_num}biasLAlarm           = STR           ; tx bias low alarm last set time
    tx{lane_num}biasHWarn            = STR           ; tx bias high warning last set time
    tx{lane_num}biasLWarn            = STR           ; tx bias low warning last set time
    lasertempHAlarm                  = STR           ; laser temperature high alarm last set time
    lasertempLAlarm                  = STR           ; laser temperature low alarm last set time
    lasertempHWarn                   = STR           ; laser temperature high warning last set time
    lasertempLWarn                   = STR           ; laser temperature low warning last set time
```

#### 3.1.6 Transceiver DOM flag time clear data

The `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table stores the last clear time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time clear for a port
    key                          = TRANSCEIVER_DOM_FLAG_CLEAR_TIME|ifname  ; information module DOM flag time clear on port
    ; field                      = value
    tempHAlarm                       = STR          ; temperature high alarm last clear time
    tempHWarn                        = STR          ; temperature high warning last clear time
    tempLAlarm                       = STR          ; temperature low alarm last clear time
    tempLWarn                        = STR          ; temperature low warning last clear time
    vccHAlarm                        = STR          ; vcc high alarm last clear time
    vccHWarn                         = STR          ; vcc high warning last clear time
    vccLAlarm                        = STR          ; vcc low alarm last clear time
    vccLWarn                         = STR          ; vcc low warning last clear time
    tx{lane_num}powerHAlarm          = STR          ; tx power high alarm last clear time
    tx{lane_num}powerLAlarm          = STR          ; tx power low alarm last clear time
    tx{lane_num}powerHWarn           = STR          ; tx power high warning last clear time
    tx{lane_num}powerLWarn           = STR          ; tx power low warning last clear time
    rx{lane_num}powerHAlarm          = STR          ; rx power high alarm last clear time
    rx{lane_num}powerLAlarm          = STR          ; rx power low alarm last clear time
    rx{lane_num}powerHWarn           = STR          ; rx power high warning last clear time
    rx{lane_num}powerLWarn           = STR          ; rx power low warning last clear time
    tx{lane_num}biasHAlarm           = STR          ; tx bias high alarm last clear time
    tx{lane_num}biasLAlarm           = STR          ; tx bias low alarm last clear time
    tx{lane_num}biasHWarn            = STR          ; tx bias high warning last clear time
    tx{lane_num}biasLWarn            = STR          ; tx bias low warning last clear time
    lasertempHAlarm                  = STR          ; laser temperature high alarm last clear time
    lasertempLAlarm                  = STR          ; laser temperature low alarm last clear time
    lasertempHWarn                   = STR          ; laser temperature high warning last clear time
    lasertempLWarn                   = STR          ; laser temperature low warning last clear time
```

### 3.2 Transceiver VDM

#### 3.2.1 Transceiver VDM sample data

The `TRANSCEIVER_VDM_REAL_VALUE` table stores the real time VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM sample for a port
    key                                            = TRANSCEIVER_VDM_REAL_VALUE|ifname    ; information module VDM sample on port
    ; field                                        = value
    last_update_time                               = STR                    ; last update time for diagnostic data
    laser_temperature_media{lane_num}              = FLOAT                  ; laser temperature value in Celsius for media input
    esnr_media_input{lane_num}                     = FLOAT                  ; eSNR value in dB for media input
    esnr_host_input{lane_num}                      = FLOAT                  ; eSNR value in dB for host input
    pam4_level_transition_media_input{lane_num}    = FLOAT                  ; PAM4 level transition parameter in dB for media input
    pam4_level_transition_host_input{lane_num}     = FLOAT                  ; PAM4 level transition parameter in dB for host input
    prefec_ber_min_media_input{lane_num}           = FLOAT                  ; Pre-FEC BER minimum value for media input
    prefec_ber_max_media_input{lane_num}           = FLOAT                  ; Pre-FEC BER maximum value for media input
    prefec_ber_avg_media_input{lane_num}           = FLOAT                  ; Pre-FEC BER average value for media input
    prefec_ber_curr_media_input{lane_num}          = FLOAT                  ; Pre-FEC BER current value for media input
    prefec_ber_min_host_input{lane_num}            = FLOAT                  ; Pre-FEC BER minimum value for host input
    prefec_ber_max_host_input{lane_num}            = FLOAT                  ; Pre-FEC BER maximum value for host input
    prefec_ber_avg_host_input{lane_num}            = FLOAT                  ; Pre-FEC BER average value for host input
    prefec_ber_curr_host_input{lane_num}           = FLOAT                  ; Pre-FEC BER current value for host input
    errored_frames_min_media_input{lane_num}       = FLOAT                  ; Errored frames minimum value for media input
    errored_frames_max_media_input{lane_num}       = FLOAT                  ; Errored frames maximum value for media input
    errored_frames_avg_media_input{lane_num}       = FLOAT                  ; Errored frames average value for media input
    errored_frames_curr_media_input{lane_num}      = FLOAT                  ; Errored frames current value for media input
    errored_frames_min_host_input{lane_num}        = FLOAT                  ; Errored frames minimum value for host input
    errored_frames_max_host_input{lane_num}        = FLOAT                  ; Errored frames maximum value for host input
    errored_frames_avg_host_input{lane_num}        = FLOAT                  ; Errored frames average value for host input
    errored_frames_curr_host_input{lane_num}       = FLOAT                  ; Errored frames current value for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                               = FLOAT                  ; modulator bias xi in percentage
    biasxq{lane_num}                               = FLOAT                  ; modulator bias xq in percentage
    biasxp{lane_num}                               = FLOAT                  ; modulator bias xp in percentage
    biasyi{lane_num}                               = FLOAT                  ; modulator bias yi in percentage
    biasyq{lane_num}                               = FLOAT                  ; modulator bias yq in percentage
    biasyp{lane_num}                               = FLOAT                  ; modulator bias yq in percentage
    cdshort{lane_num}                              = FLOAT                  ; chromatic dispersion, high granularity, short link in ps/nm
    cdlong{lane_num}                               = FLOAT                  ; chromatic dispersion, high granularity, long link in ps/nm  
    dgd{lane_num}                                  = FLOAT                  ; differential group delay in ps
    sopmd{lane_num}                                = FLOAT                  ; second order polarization mode dispersion in ps^2
    soproc{lane_num}                               = FLOAT                  ; state of polarization rate of change in krad/s
    pdl{lane_num}                                  = FLOAT                  ; polarization dependent loss in db
    osnr{lane_num}                                 = FLOAT                  ; optical signal to noise ratio in db
    esnr{lane_num}                                 = FLOAT                  ; electrical signal to noise ratio in db
    cfo{lane_num}                                  = FLOAT                  ; carrier frequency offset in Hz
    txcurrpower{lane_num}                          = FLOAT                  ; tx current output power in dbm
    rxtotpower{lane_num}                           = FLOAT                  ; rx total power in  dbm
    rxsigpower{lane_num}                           = FLOAT                  ; rx signal power in dbm
```

#### 3.2.2 Transceiver VDM threshold data

##### 3.2.2.1 Transceiver VDM high alarm threshold data

The `TRANSCEIVER_VDM_HALARM_THRESHOLD` table stores the high alarm threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm threshold for a port
    key                                            = TRANSCEIVER_VDM_HALARM_THRESHOLD|ifname    ; information module VDM high alarm threshold on port
    ; field                                        = value
    last_update_time                              = STR            ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = FLOAT          ; laser temperature high alarm value in Celsius for media input
    esnr_media_input{lane_num}                    = FLOAT          ; eSNR high alarm value in dB for media input
    esnr_host_input{lane_num}                     = FLOAT          ; eSNR high alarm value in dB for host input
    pam4_level_transition_media_input{lane_num}   = FLOAT          ; PAM4 level transition high alarm value in dB for media input
    pam4_level_transition_host_input{lane_num}    = FLOAT          ; PAM4 level transition high alarm value in dB for host input
    prefec_ber_min_media_input{lane_num}          = FLOAT          ; Pre-FEC BER minimum high alarm value for media input
    prefec_ber_max_media_input{lane_num}          = FLOAT          ; Pre-FEC BER maximum high alarm value for media input
    prefec_ber_avg_media_input{lane_num}          = FLOAT          ; Pre-FEC BER average high alarm value for media input
    prefec_ber_curr_media_input{lane_num}         = FLOAT          ; Pre-FEC BER current high alarm value for media input
    prefec_ber_min_host_input{lane_num}           = FLOAT          ; Pre-FEC BER minimum high alarm value for host input
    prefec_ber_max_host_input{lane_num}           = FLOAT          ; Pre-FEC BER maximum high alarm value for host input
    prefec_ber_avg_host_input{lane_num}           = FLOAT          ; Pre-FEC BER average high alarm value for host input
    prefec_ber_curr_host_input{lane_num}          = FLOAT          ; Pre-FEC BER current high alarm value for host input
    errored_frames_min_media_input{lane_num}      = FLOAT          ; Errored frames minimum high alarm value for media input
    errored_frames_max_media_input{lane_num}      = FLOAT          ; Errored frames maximum high alarm value for media input
    errored_frames_avg_media_input{lane_num}      = FLOAT          ; Errored frames average high alarm value for media input
    errored_frames_curr_media_input{lane_num}     = FLOAT          ; Errored frames current high alarm value for media input
    errored_frames_min_host_input{lane_num}       = FLOAT          ; Errored frames minimum high alarm value for host input
    errored_frames_max_host_input{lane_num}       = FLOAT          ; Errored frames maximum high alarm value for host input
    errored_frames_avg_host_input{lane_num}       = FLOAT          ; Errored frames average high alarm value for host input
    errored_frames_curr_host_input{lane_num}      = FLOAT          ; Errored frames current high alarm value for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                             = FLOAT         ; modulator bias xi in percentage (high alarm)
    biasxq{lane_num}                             = FLOAT         ; modulator bias xq in percentage (high alarm)
    biasxp{lane_num}                             = FLOAT         ; modulator bias xp in percentage (high alarm)
    biasyi{lane_num}                             = FLOAT         ; modulator bias yi in percentage (high alarm)
    biasyq{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high alarm)
    biasyp{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high alarm)
    cdshort{lane_num}                            = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (high alarm)
    cdlong{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (high alarm)
    dgd{lane_num}                                = FLOAT         ; differential group delay in ps (high alarm)
    sopmd{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (high alarm)
    soproc{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (high alarm)
    pdl{lane_num}                                = FLOAT         ; polarization dependent loss in db (high alarm)
    osnr{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (high alarm)
    esnr{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (high alarm)
    cfo{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (high alarm)
    txcurrpower{lane_num}                        = FLOAT         ; tx current output power in dbm (high alarm)
    rxtotpower{lane_num}                         = FLOAT         ; rx total power in  dbm (high alarm)
    rxsigpower{lane_num}                         = FLOAT         ; rx signal power in dbm (high alarm)
```

##### 3.2.2.2 Transceiver VDM low alarm threshold data

The `TRANSCEIVER_VDM_LALARM_THRESHOLD` table stores the low alarm threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm threshold for a port
    key                                            = TRANSCEIVER_VDM_LALARM_THRESHOLD|ifname    ; information module VDM low alarm threshold on port
    ; field                                        = value
    last_update_time                              = STR            ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = FLOAT          ; laser temperature low alarm value in Celsius for media input
    esnr_media_input{lane_num}                    = FLOAT          ; eSNR low alarm value in dB for media input
    esnr_host_input{lane_num}                     = FLOAT          ; eSNR low alarm value in dB for host input
    pam4_level_transition_media_input{lane_num}   = FLOAT          ; PAM4 level transition low alarm value in dB for media input
    pam4_level_transition_host_input{lane_num}    = FLOAT          ; PAM4 level transition low alarm value in dB for host input
    prefec_ber_min_media_input{lane_num}          = FLOAT          ; Pre-FEC BER minimum low alarm value for media input
    prefec_ber_max_media_input{lane_num}          = FLOAT          ; Pre-FEC BER maximum low alarm value for media input
    prefec_ber_avg_media_input{lane_num}          = FLOAT          ; Pre-FEC BER average low alarm value for media input
    prefec_ber_curr_media_input{lane_num}         = FLOAT          ; Pre-FEC BER current low alarm value for media input
    prefec_ber_min_host_input{lane_num}           = FLOAT          ; Pre-FEC BER minimum low alarm value for host input
    prefec_ber_max_host_input{lane_num}           = FLOAT          ; Pre-FEC BER maximum low alarm value for host input
    prefec_ber_avg_host_input{lane_num}           = FLOAT          ; Pre-FEC BER average low alarm value for host input
    prefec_ber_curr_host_input{lane_num}          = FLOAT          ; Pre-FEC BER current low alarm value for host input
    errored_frames_min_media_input{lane_num}      = FLOAT          ; Errored frames minimum low alarm value for media input
    errored_frames_max_media_input{lane_num}      = FLOAT          ; Errored frames maximum low alarm value for media input
    errored_frames_avg_media_input{lane_num}      = FLOAT          ; Errored frames average low alarm value for media input
    errored_frames_curr_media_input{lane_num}     = FLOAT          ; Errored frames current low alarm value for media input
    errored_frames_min_host_input{lane_num}       = FLOAT          ; Errored frames minimum low alarm value for host input
    errored_frames_max_host_input{lane_num}       = FLOAT          ; Errored frames maximum low alarm value for host input
    errored_frames_avg_host_input{lane_num}       = FLOAT          ; Errored frames average low alarm value for host input
    errored_frames_curr_host_input{lane_num}      = FLOAT          ; Errored frames current low alarm value for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                             = FLOAT         ; modulator bias xi in percentage (low alarm)
    biasxq{lane_num}                             = FLOAT         ; modulator bias xq in percentage (low alarm)
    biasxp{lane_num}                             = FLOAT         ; modulator bias xp in percentage (low alarm)
    biasyi{lane_num}                             = FLOAT         ; modulator bias yi in percentage (low alarm)
    biasyq{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low alarm)
    biasyp{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low alarm)
    cdshort{lane_num}                            = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (low alarm)
    cdlong{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (low alarm)
    dgd{lane_num}                                = FLOAT         ; differential group delay in ps (low alarm)
    sopmd{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (low alarm)
    soproc{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (low alarm)
    pdl{lane_num}                                = FLOAT         ; polarization dependent loss in db (low alarm)
    osnr{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (low alarm)
    esnr{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (low alarm)
    cfo{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (low alarm)
    txcurrpower{lane_num}                        = FLOAT         ; tx current output power in dbm (low alarm)
    rxtotpower{lane_num}                         = FLOAT         ; rx total power in  dbm (low alarm)
    rxsigpower{lane_num}                         = FLOAT         ; rx signal power in dbm (low alarm)
```

##### 3.2.2.3 Transceiver VDM high warning threshold data

The `TRANSCEIVER_VDM_HWARN_THRESHOLD` table stores the high warning threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning threshold for a port
    key                                            = TRANSCEIVER_VDM_HWARN_THRESHOLD|ifname    ; information module VDM high warning threshold on port
    ; field                                        = value
    last_update_time                              = STR            ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = FLOAT          ; laser temperature high warning value in Celsius for media input
    esnr_media_input{lane_num}                    = FLOAT          ; eSNR high warning value in dB for media input
    esnr_host_input{lane_num}                     = FLOAT          ; eSNR high warning value in dB for host input
    pam4_level_transition_media_input{lane_num}   = FLOAT          ; PAM4 level transition high warning value in dB for media input
    pam4_level_transition_host_input{lane_num}    = FLOAT          ; PAM4 level transition high warning value in dB for host input
    prefec_ber_min_media_input{lane_num}          = FLOAT          ; Pre-FEC BER minimum high warning value for media input
    prefec_ber_max_media_input{lane_num}          = FLOAT          ; Pre-FEC BER maximum high warning value for media input
    prefec_ber_avg_media_input{lane_num}          = FLOAT          ; Pre-FEC BER average high warning value for media input
    prefec_ber_curr_media_input{lane_num}         = FLOAT          ; Pre-FEC BER current high warning value for media input
    prefec_ber_min_host_input{lane_num}           = FLOAT          ; Pre-FEC BER minimum high warning value for host input
    prefec_ber_max_host_input{lane_num}           = FLOAT          ; Pre-FEC BER maximum high warning value for host input
    prefec_ber_avg_host_input{lane_num}           = FLOAT          ; Pre-FEC BER average high warning value for host input
    prefec_ber_curr_host_input{lane_num}          = FLOAT          ; Pre-FEC BER current high warning value for host input
    errored_frames_min_media_input{lane_num}      = FLOAT          ; Errored frames minimum high warning value for media input
    errored_frames_max_media_input{lane_num}      = FLOAT          ; Errored frames maximum high warning value for media input
    errored_frames_avg_media_input{lane_num}      = FLOAT          ; Errored frames average high warning value for media input
    errored_frames_curr_media_input{lane_num}     = FLOAT          ; Errored frames current high warning value for media input
    errored_frames_min_host_input{lane_num}       = FLOAT          ; Errored frames minimum high warning value for host input
    errored_frames_max_host_input{lane_num}       = FLOAT          ; Errored frames maximum high warning value for host input
    errored_frames_avg_host_input{lane_num}       = FLOAT          ; Errored frames average high warning value for host input
    errored_frames_curr_host_input{lane_num}      = FLOAT          ; Errored frames current high warning value for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                             = FLOAT         ; modulator bias xi in percentage (high warning)
    biasxq{lane_num}                             = FLOAT         ; modulator bias xq in percentage (high warning)
    biasxp{lane_num}                             = FLOAT         ; modulator bias xp in percentage (high warning)
    biasyi{lane_num}                             = FLOAT         ; modulator bias yi in percentage (high warning)
    biasyq{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high warning)
    biasyp{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high warning)
    cdshort_hwar{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (high warning)
    cdlong{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (high warning)
    dgd{lane_num}                                = FLOAT         ; differential group delay in ps (high warning)
    sopmd{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (high warning)
    soproc{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (high warning)
    pdl{lane_num}                                = FLOAT         ; polarization dependent loss in db (high warning)
    osnr{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (high warning)
    esnr{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (high warning)
    cfo{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (high warning)
    txcurrpower{lane_num}                        = FLOAT         ; tx current output power in dbm (high warning)
    rxtotpower{lane_num}                         = FLOAT         ; rx total power in  dbm (high warning)
    rxsigpower{lane_num}                         = FLOAT         ; rx signal power in dbm (high warning)
```

##### 3.2.2.4 Transceiver VDM low warning threshold data

The `TRANSCEIVER_VDM_LWARN_THRESHOLD` table stores the low warning threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning threshold for a port
    key                                            = TRANSCEIVER_VDM_LWARN_THRESHOLD|ifname    ; information module VDM low warning threshold on port
    ; field                                        = value
    last_update_time                              = STR            ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = FLOAT          ; laser temperature low warning value in Celsius for media input
    esnr_media_input{lane_num}                    = FLOAT          ; eSNR low warning value in dB for media input
    esnr_host_input{lane_num}                     = FLOAT          ; eSNR low warning value in dB for host input
    pam4_level_transition_media_input{lane_num}   = FLOAT          ; PAM4 level transition low warning value in dB for media input
    pam4_level_transition_host_input{lane_num}    = FLOAT          ; PAM4 level transition low warning value in dB for host input
    prefec_ber_min_media_input{lane_num}          = FLOAT          ; Pre-FEC BER minimum low warning value for media input
    prefec_ber_max_media_input{lane_num}          = FLOAT          ; Pre-FEC BER maximum low warning value for media input
    prefec_ber_avg_media_input{lane_num}          = FLOAT          ; Pre-FEC BER average low warning value for media input
    prefec_ber_curr_media_input{lane_num}         = FLOAT          ; Pre-FEC BER current low warning value for media input
    prefec_ber_min_host_input{lane_num}           = FLOAT          ; Pre-FEC BER minimum low warning value for host input
    prefec_ber_max_host_input{lane_num}           = FLOAT          ; Pre-FEC BER maximum low warning value for host input
    prefec_ber_avg_host_input{lane_num}           = FLOAT          ; Pre-FEC BER average low warning value for host input
    prefec_ber_curr_host_input{lane_num}          = FLOAT          ; Pre-FEC BER current low warning value for host input
    errored_frames_min_media_input{lane_num}      = FLOAT          ; Errored frames minimum low warning value for media input
    errored_frames_max_media_input{lane_num}      = FLOAT          ; Errored frames maximum low warning value for media input
    errored_frames_avg_media_input{lane_num}      = FLOAT          ; Errored frames average low warning value for media input
    errored_frames_curr_media_input{lane_num}     = FLOAT          ; Errored frames current low warning value for media input
    errored_frames_min_host_input{lane_num}       = FLOAT          ; Errored frames minimum low warning value for host input
    errored_frames_max_host_input{lane_num}       = FLOAT          ; Errored frames maximum low warning value for host input
    errored_frames_avg_host_input{lane_num}       = FLOAT          ; Errored frames average low warning value for host input
    errored_frames_curr_host_input{lane_num}      = FLOAT          ; Errored frames current low warning value for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                             = FLOAT         ; modulator bias xi in percentage (low warning)
    biasxq{lane_num}                             = FLOAT         ; modulator bias xq in percentage (low warning)
    biasxp{lane_num}                             = FLOAT         ; modulator bias xp in percentage (low warning)
    biasyi{lane_num}                             = FLOAT         ; modulator bias yi in percentage (low warning)
    biasyq{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low warning)
    biasyp{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low warning)
    cdshort{lane_num}                            = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (low warning)
    cdlong{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (low warning)
    dgd{lane_num}                                = FLOAT         ; differential group delay in ps (low warning)
    sopmd{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (low warning)
    soproc{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (low warning)
    pdl{lane_num}                                = FLOAT         ; polarization dependent loss in db (low warning)
    osnr{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (low warning)
    esnr{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (low warning)
    cfo{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (low warning)
    txcurrpower{lane_num}                        = FLOAT         ; tx current output power in dbm (low warning)
    rxtotpower{lane_num}                         = FLOAT         ; rx total power in  dbm (low warning)
    rxsigpower{lane_num}                         = FLOAT         ; rx signal power in dbm (low warning)
```

#### 3.2.3 Transceiver VDM flag data

##### 3.2.3.1 Transceiver VDM high alarm flag data

The `TRANSCEIVER_VDM_HALARM_FLAG` table stores the flag status for the VDM data.

```plaintext
    ;Defines Transceiver VDM high alarm flag for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG|ifname
    ; field                      = value
    last_update_time                              = STR     ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = BOOLEAN ; laser temperature high alarm flag for media input
    esnr_media_input{lane_num}                    = BOOLEAN ; eSNR high alarm flag for media input
    esnr_host_input{lane_num}                     = BOOLEAN ; eSNR high alarm flag for host input
    pam4_level_transition_media_input{lane_num}   = BOOLEAN ; PAM4 level transition high alarm flag for media input
    pam4_level_transition_host_input{lane_num}    = BOOLEAN ; PAM4 level transition high alarm flag for host input
    prefec_ber_min_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high alarm flag for media input
    prefec_ber_max_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high alarm flag for media input
    prefec_ber_avg_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER average high alarm flag for media input
    prefec_ber_curr_media_input{lane_num}         = BOOLEAN ; Pre-FEC BER current high alarm flag for media input
    prefec_ber_min_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high alarm flag for host input
    prefec_ber_max_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high alarm flag for host input
    prefec_ber_avg_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER average high alarm flag for host input
    prefec_ber_curr_host_input{lane_num}          = BOOLEAN ; Pre-FEC BER current high alarm flag for host input
    errored_frames_min_media_input{lane_num}      = BOOLEAN ; Errored frames minimum high alarm flag for media input
    errored_frames_max_media_input{lane_num}      = BOOLEAN ; Errored frames maximum high alarm flag for media input
    errored_frames_avg_media_input{lane_num}      = BOOLEAN ; Errored frames average high alarm flag for media input
    errored_frames_curr_media_input{lane_num}     = BOOLEAN ; Errored frames current high alarm flag for media input
    errored_frames_min_host_input{lane_num}       = BOOLEAN ; Errored frames minimum high alarm flag for host input
    errored_frames_max_host_input{lane_num}       = BOOLEAN ; Errored frames maximum high alarm flag for host input
    errored_frames_avg_host_input{lane_num}       = BOOLEAN ; Errored frames average high alarm flag for host input
    errored_frames_curr_host_input{lane_num}      = BOOLEAN ; Errored frames current high alarm flag for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (high alarm flag)
    biasxq{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (high alarm flag)
    biasxp{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (high alarm flag)
    biasyi{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (high alarm flag)
    biasyq{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high alarm flag)
    biasyp{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high alarm flag)
    cdshort{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (high alarm flag)
    cdlong{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (high alarm flag)
    dgd{lane_num}                                 = BOOLEAN ; differential group delay in ps (high alarm flag)
    sopmd{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (high alarm flag)
    soproc{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (high alarm flag)
    pdl{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (high alarm flag)
    osnr{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (high alarm flag)
    esnr{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (high alarm flag)
    cfo{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (high alarm flag)
    txcurrpower{lane_num}                         = BOOLEAN ; tx current output power in dbm (high alarm flag)
    rxtotpower{lane_num}                          = BOOLEAN ; rx total power in  dbm (high alarm flag)
    rxsigpower{lane_num}                          = BOOLEAN; rx signal power in dbm (high alarm flag)
```

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

##### 3.2.3.2 Transceiver VDM low alarm flag data

The `TRANSCEIVER_VDM_LALARM_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm flag for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG|ifname
    ; field                      = value
    last_update_time                              = STR     ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = BOOLEAN ; laser temperature low alarm flag for media input
    esnr_media_input{lane_num}                    = BOOLEAN ; eSNR low alarm flag for media input
    esnr_host_input{lane_num}                     = BOOLEAN ; eSNR low alarm flag for host input
    pam4_level_transition_media_input{lane_num}   = BOOLEAN ; PAM4 level transition low alarm flag for media input
    pam4_level_transition_host_input{lane_num}    = BOOLEAN ; PAM4 level transition low alarm flag for host input
    prefec_ber_min_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low alarm flag for media input
    prefec_ber_max_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low alarm flag for media input
    prefec_ber_avg_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER average low alarm flag for media input
    prefec_ber_curr_media_input{lane_num}         = BOOLEAN ; Pre-FEC BER current low alarm flag for media input
    prefec_ber_min_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low alarm flag for host input
    prefec_ber_max_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low alarm flag for host input
    prefec_ber_avg_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER average low alarm flag for host input
    prefec_ber_curr_host_input{lane_num}          = BOOLEAN ; Pre-FEC BER current low alarm flag for host input
    errored_frames_min_media_input{lane_num}      = BOOLEAN ; Errored frames minimum low alarm flag for media input
    errored_frames_max_media_input{lane_num}      = BOOLEAN ; Errored frames maximum low alarm flag for media input
    errored_frames_avg_media_input{lane_num}      = BOOLEAN ; Errored frames average low alarm flag for media input
    errored_frames_curr_media_input{lane_num}     = BOOLEAN ; Errored frames current low alarm flag for media input
    errored_frames_min_host_input{lane_num}       = BOOLEAN ; Errored frames minimum low alarm flag for host input
    errored_frames_max_host_input{lane_num}       = BOOLEAN ; Errored frames maximum low alarm flag for host input
    errored_frames_avg_host_input{lane_num}       = BOOLEAN ; Errored frames average low alarm flag for host input
    errored_frames_curr_host_input{lane_num}      = BOOLEAN ; Errored frames current low alarm flag for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (low alarm flag)
    biasxq{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (low alarm flag)
    biasxp{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (low alarm flag)
    biasyi{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (low alarm flag)
    biasyq{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low alarm flag)
    biasyp{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low alarm flag)
    cdshort{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (low alarm flag)
    cdlong{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (low alarm flag)
    dgd{lane_num}                                 = BOOLEAN ; differential group delay in ps (low alarm flag)
    sopmd{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (low alarm flag)
    soproc{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (low alarm flag)
    pdl{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (low alarm flag)
    osnr{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (low alarm flag)
    esnr{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (low alarm flag)
    cfo{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (low alarm flag)
    txcurrpower{lane_num}                         = BOOLEAN ; tx current output power in dbm (low alarm flag)
    rxtotpower{lane_num}                          = BOOLEAN ; rx total power in  dbm (low alarm flag)
    rxsigpower{lane_num}                          = BOOLEAN; rx signal power in dbm (low alarm flag)
```

##### 3.2.3.3 Transceiver VDM high warning flag data

The `TRANSCEIVER_VDM_HWARN_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning flag for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG|ifname
    ; field                      = value
    last_update_time                              = STR     ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = BOOLEAN ; laser temperature high warning flag for media input
    esnr_media_input{lane_num}                    = BOOLEAN ; eSNR high warning flag for media input
    esnr_host_input{lane_num}                     = BOOLEAN ; eSNR high warning flag for host input
    pam4_level_transition_media_input{lane_num}   = BOOLEAN ; PAM4 level transition high warning flag for media input
    pam4_level_transition_host_input{lane_num}    = BOOLEAN ; PAM4 level transition high warning flag for host input
    prefec_ber_min_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high warning flag for media input
    prefec_ber_max_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high warning flag for media input
    prefec_ber_avg_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER average high warning flag for media input
    prefec_ber_curr_media_input{lane_num}         = BOOLEAN ; Pre-FEC BER current high warning flag for media input
    prefec_ber_min_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high warning flag for host input
    prefec_ber_max_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high warning flag for host input
    prefec_ber_avg_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER average high warning flag for host input
    prefec_ber_curr_host_input{lane_num}          = BOOLEAN ; Pre-FEC BER current high warning flag for host input
    errored_frames_min_media_input{lane_num}      = BOOLEAN ; Errored frames minimum high warning flag for media input
    errored_frames_max_media_input{lane_num}      = BOOLEAN ; Errored frames maximum high warning flag for media input
    errored_frames_avg_media_input{lane_num}      = BOOLEAN ; Errored frames average high warning flag for media input
    errored_frames_curr_media_input{lane_num}     = BOOLEAN ; Errored frames current high warning flag for media input
    errored_frames_min_host_input{lane_num}       = BOOLEAN ; Errored frames minimum high warning flag for host input
    errored_frames_max_host_input{lane_num}       = BOOLEAN ; Errored frames maximum high warning flag for host input
    errored_frames_avg_host_input{lane_num}       = BOOLEAN ; Errored frames average high warning flag for host input
    errored_frames_curr_host_input{lane_num}      = BOOLEAN ; Errored frames current high warning flag for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (high warning flag)
    biasxq{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (high warning flag)
    biasxp{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (high warning flag)
    biasyi{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (high warning flag)
    biasyq{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high warning flag)
    biasyp{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high warning flag)
    cdshort{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (high warning flag)
    cdlong{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (high warning flag)
    dgd{lane_num}                                 = BOOLEAN ; differential group delay in ps (high warning flag)
    sopmd{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (high warning flag)
    soproc{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (high warning flag)
    pdl{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (high warning flag)
    osnr{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (high warning flag)
    esnr{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (high warning flag)
    cfo{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (high warning flag)
    txcurrpower{lane_num}                         = BOOLEAN ; tx current output power in dbm (high warning flag)
    rxtotpower{lane_num}                          = BOOLEAN ; rx total power in  dbm (high warning flag)
    rxsigpower{lane_num}                          = BOOLEAN; rx signal power in dbm (high warning flag)
```

##### 3.2.3.4 Transceiver VDM low warning flag data

The `TRANSCEIVER_VDM_LWARN_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning flag for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG|ifname
    ; field                      = value
    last_update_time                              = STR     ; last update time for diagnostic data
    laser_temperature_media{lane_num}             = BOOLEAN ; laser temperature low warning flag for media input
    esnr_media_input{lane_num}                    = BOOLEAN ; eSNR low warning flag for media input
    esnr_host_input{lane_num}                     = BOOLEAN ; eSNR low warning flag for host input
    pam4_level_transition_media_input{lane_num}   = BOOLEAN ; PAM4 level transition low warning flag for media input
    pam4_level_transition_host_input{lane_num}    = BOOLEAN ; PAM4 level transition low warning flag for host input
    prefec_ber_min_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low warning flag for media input
    prefec_ber_max_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low warning flag for media input
    prefec_ber_avg_media_input{lane_num}          = BOOLEAN ; Pre-FEC BER average low warning flag for media input
    prefec_ber_curr_media_input{lane_num}         = BOOLEAN ; Pre-FEC BER current low warning flag for media input
    prefec_ber_min_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low warning flag for host input
    prefec_ber_max_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low warning flag for host input
    prefec_ber_avg_host_input{lane_num}           = BOOLEAN ; Pre-FEC BER average low warning flag for host input
    prefec_ber_curr_host_input{lane_num}          = BOOLEAN ; Pre-FEC BER current low warning flag for host input
    errored_frames_min_media_input{lane_num}      = BOOLEAN ; Errored frames minimum low warning flag for media input
    errored_frames_max_media_input{lane_num}      = BOOLEAN ; Errored frames maximum low warning flag for media input
    errored_frames_avg_media_input{lane_num}      = BOOLEAN ; Errored frames average low warning flag for media input
    errored_frames_curr_media_input{lane_num}     = BOOLEAN ; Errored frames current low warning flag for media input
    errored_frames_min_host_input{lane_num}       = BOOLEAN ; Errored frames minimum low warning flag for host input
    errored_frames_max_host_input{lane_num}       = BOOLEAN ; Errored frames maximum low warning flag for host input
    errored_frames_avg_host_input{lane_num}       = BOOLEAN ; Errored frames average low warning flag for host input
    errored_frames_curr_host_input{lane_num}      = BOOLEAN ; Errored frames current low warning flag for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (low warning flag)
    biasxq{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (low warning flag)
    biasxp{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (low warning flag)
    biasyi{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (low warning flag)
    biasyq{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low warning flag)
    biasyp{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low warning flag)
    cdshort{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (low warning flag)
    cdlong{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (low warning flag)
    dgd{lane_num}                                 = BOOLEAN ; differential group delay in ps (low warning flag)
    sopmd{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (low warning flag)
    soproc{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (low warning flag)
    pdl{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (low warning flag)
    osnr{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (low warning flag)
    esnr{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (low warning flag)
    cfo{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (low warning flag)
    txcurrpower{lane_num}                         = BOOLEAN ; tx current output power in dbm (low warning flag)
    rxtotpower{lane_num}                          = BOOLEAN ; rx total power in  dbm (low warning flag)
    rxsigpower{lane_num}                          = BOOLEAN; rx signal power in dbm (low warning flag)
```

#### 3.2.4 Transceiver VDM flag change count data

##### 3.2.4.1 Transceiver VDM high alarm flag change count data

The `TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT` table stores the flag change count for high alarm flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm flag change count for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = INTEGER ; laser temperature high alarm flag change count for media input
    esnr_media_input{lane_num}                    = INTEGER ; eSNR high alarm flag change count for media input
    esnr_host_input{lane_num}                     = INTEGER ; eSNR high alarm flag change count for host input
    pam4_level_transition_media_input{lane_num}   = INTEGER ; PAM4 level transition high alarm flag change count for media input
    pam4_level_transition_host_input{lane_num}    = INTEGER ; PAM4 level transition high alarm flag change count for host input
    prefec_ber_min_media_input{lane_num}          = INTEGER ; Pre-FEC BER minimum high alarm flag change count for media input
    prefec_ber_max_media_input{lane_num}          = INTEGER ; Pre-FEC BER maximum high alarm flag change count for media input
    prefec_ber_avg_media_input{lane_num}          = INTEGER ; Pre-FEC BER average high alarm flag change count for media input
    prefec_ber_curr_media_input{lane_num}         = INTEGER ; Pre-FEC BER current high alarm flag change count for media input
    prefec_ber_min_host_input{lane_num}           = INTEGER ; Pre-FEC BER minimum high alarm flag change count for host input
    prefec_ber_max_host_input{lane_num}           = INTEGER ; Pre-FEC BER maximum high alarm flag change count for host input
    prefec_ber_avg_host_input{lane_num}           = INTEGER ; Pre-FEC BER average high alarm flag change count for host input
    prefec_ber_curr_host_input{lane_num}          = INTEGER ; Pre-FEC BER current high alarm flag change count for host input
    errored_frames_min_media_input{lane_num}      = INTEGER ; Errored frames minimum high alarm flag change count for media input
    errored_frames_max_media_input{lane_num}      = INTEGER ; Errored frames maximum high alarm flag change count for media input
    errored_frames_avg_media_input{lane_num}      = INTEGER ; Errored frames average high alarm flag change count for media input
    errored_frames_curr_media_input{lane_num}     = INTEGER ; Errored frames current high alarm flag change count for media input
    errored_frames_min_host_input{lane_num}       = INTEGER ; Errored frames minimum high alarm flag change count for host input
    errored_frames_max_host_input{lane_num}       = INTEGER ; Errored frames maximum high alarm flag change count for host input
    errored_frames_avg_host_input{lane_num}       = INTEGER ; Errored frames average high alarm flag change count for host input
    errored_frames_curr_host_input{lane_num}      = INTEGER ; Errored frames current high alarm flag change count for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = INTEGER ; modulator bias xi in percentage (high alarm flag change count)
    biasxq{lane_num}                              = INTEGER ; modulator bias xq in percentage (high alarm flag change count)
    biasxp{lane_num}                              = INTEGER ; modulator bias xp in percentage (high alarm flag change count)
    biasyi{lane_num}                              = INTEGER ; modulator bias yi in percentage (high alarm flag change count)
    biasyq{lane_num}                              = INTEGER ; modulator bias yq in percentage (high alarm flag change count)
    biasyp{lane_num}                              = INTEGER ; modulator bias yq in percentage (high alarm flag change count)
    cdshort{lane_num}                             = INTEGER ; chromatic dispersion, high granularity, short link in ps/nm (high alarm flag change count)
    cdlong{lane_num}                              = INTEGER ; chromatic dispersion, high granularity, long link in ps/nm (high alarm flag change count)
    dgd{lane_num}                                 = INTEGER ; differential group delay in ps (high alarm flag change count)
    sopmd{lane_num}                               = INTEGER ; second order polarization mode dispersion in ps^2 (high alarm flag change count)
    soproc{lane_num}                              = INTEGER ; state of polarization rate of change in krad/s (high alarm flag change count)
    pdl{lane_num}                                 = INTEGER ; polarization dependent loss in db (high alarm flag change count)
    osnr{lane_num}                                = INTEGER ; optical signal to noise ratio in db (high alarm flag change count)
    esnr{lane_num}                                = INTEGER ; electrical signal to noise ratio in db (high alarm flag change count)
    cfo{lane_num}                                 = INTEGER ; carrier frequency offset in Hz (high alarm flag change count)
    txcurrpower{lane_num}                         = INTEGER ; tx current output power in dbm (high alarm flag change count)
    rxtotpower{lane_num}                          = INTEGER ; rx total power in  dbm (high alarm flag change count)
    rxsigpower{lane_num}                          = INTEGER; rx signal power in dbm (high alarm flag change count)
```

##### 3.2.4.2 Transceiver VDM low alarm flag change count data

The `TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT` table stores the flag change count for low alarm flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm flag change count for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = INTEGER ; laser temperature low alarm flag change count for media input
    esnr_media_input{lane_num}                    = INTEGER ; eSNR low alarm flag change count for media input
    esnr_host_input{lane_num}                     = INTEGER ; eSNR low alarm flag change count for host input
    pam4_level_transition_media_input{lane_num}   = INTEGER ; PAM4 level transition low alarm flag change count for media input
    pam4_level_transition_host_input{lane_num}    = INTEGER ; PAM4 level transition low alarm flag change count for host input
    prefec_ber_min_media_input{lane_num}          = INTEGER ; Pre-FEC BER minimum low alarm flag change count for media input
    prefec_ber_max_media_input{lane_num}          = INTEGER ; Pre-FEC BER maximum low alarm flag change count for media input
    prefec_ber_avg_media_input{lane_num}          = INTEGER ; Pre-FEC BER average low alarm flag change count for media input
    prefec_ber_curr_media_input{lane_num}         = INTEGER ; Pre-FEC BER current low alarm flag change count for media input
    prefec_ber_min_host_input{lane_num}           = INTEGER ; Pre-FEC BER minimum low alarm flag change count for host input
    prefec_ber_max_host_input{lane_num}           = INTEGER ; Pre-FEC BER maximum low alarm flag change count for host input
    prefec_ber_avg_host_input{lane_num}           = INTEGER ; Pre-FEC BER average low alarm flag change count for host input
    prefec_ber_curr_host_input{lane_num}          = INTEGER ; Pre-FEC BER current low alarm flag change count for host input
    errored_frames_min_media_input{lane_num}      = INTEGER ; Errored frames minimum low alarm flag change count for media input
    errored_frames_max_media_input{lane_num}      = INTEGER ; Errored frames maximum low alarm flag change count for media input
    errored_frames_avg_media_input{lane_num}      = INTEGER ; Errored frames average low alarm flag change count for media input
    errored_frames_curr_media_input{lane_num}     = INTEGER ; Errored frames current low alarm flag change count for media input
    errored_frames_min_host_input{lane_num}       = INTEGER ; Errored frames minimum low alarm flag change count for host input
    errored_frames_max_host_input{lane_num}       = INTEGER ; Errored frames maximum low alarm flag change count for host input
    errored_frames_avg_host_input{lane_num}       = INTEGER ; Errored frames average low alarm flag change count for host input
    errored_frames_curr_host_input{lane_num}      = INTEGER ; Errored frames current low alarm flag change count for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = INTEGER ; modulator bias xi in percentage (low alarm flag change count)
    biasxq{lane_num}                              = INTEGER ; modulator bias xq in percentage (low alarm flag change count)
    biasxp{lane_num}                              = INTEGER ; modulator bias xp in percentage (low alarm flag change count)
    biasyi{lane_num}                              = INTEGER ; modulator bias yi in percentage (low alarm flag change count)
    biasyq{lane_num}                              = INTEGER ; modulator bias yq in percentage (low alarm flag change count)
    biasyp{lane_num}                              = INTEGER ; modulator bias yq in percentage (low alarm flag change count)
    cdshort{lane_num}                             = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (low alarm flag change count)
    cdlong{lane_num}                              = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (low alarm flag change count)
    dgd{lane_num}                                 = INTEGER ; differential group delay in ps (low alarm flag change count)
    sopmd{lane_num}                               = INTEGER ; second order polarization mode dispersion in ps^2 (low alarm flag change count)
    soproc{lane_num}                              = INTEGER ; state of polarization rate of change in krad/s (low alarm flag change count)
    pdl{lane_num}                                 = INTEGER ; polarization dependent loss in db (low alarm flag change count)
    osnr{lane_num}                                = INTEGER ; optical signal to noise ratio in db (low alarm flag change count)
    esnr{lane_num}                                = INTEGER ; electrical signal to noise ratio in db (low alarm flag change count)
    cfo{lane_num}                                 = INTEGER ; carrier frequency offset in Hz (low alarm flag change count)
    txcurrpower{lane_num}                         = INTEGER ; tx current output power in dbm (low alarm flag change count)
    rxtotpower{lane_num}                          = INTEGER ; rx total power in  dbm (low alarm flag change count)
    rxsigpower{lane_num}                          = INTEGER; rx signal power in dbm (low alarm flag change count)
```

##### 3.2.4.3 Transceiver VDM high warning flag change count data

The `TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT` table stores the flag change count for high warning flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning flag change count for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = INTEGER ; laser temperature high warning flag change count for media input
    esnr_media_input{lane_num}                    = INTEGER ; eSNR high warning flag change count for media input
    esnr_host_input{lane_num}                     = INTEGER ; eSNR high warning flag change count for host input
    pam4_level_transition_media_input{lane_num}   = INTEGER ; PAM4 level transition high warning flag change count for media input
    pam4_level_transition_host_input{lane_num}    = INTEGER ; PAM4 level transition high warning flag change count for host input
    prefec_ber_min_media_input{lane_num}          = INTEGER ; Pre-FEC BER minimum high warning flag change count for media input
    prefec_ber_max_media_input{lane_num}          = INTEGER ; Pre-FEC BER maximum high warning flag change count for media input
    prefec_ber_avg_media_input{lane_num}          = INTEGER ; Pre-FEC BER average high warning flag change count for media input
    prefec_ber_curr_media_input{lane_num}         = INTEGER ; Pre-FEC BER current high warning flag change count for media input
    prefec_ber_min_host_input{lane_num}           = INTEGER ; Pre-FEC BER minimum high warning flag change count for host input
    prefec_ber_max_host_input{lane_num}           = INTEGER ; Pre-FEC BER maximum high warning flag change count for host input
    prefec_ber_avg_host_input{lane_num}           = INTEGER ; Pre-FEC BER average high warning flag change count for host input
    prefec_ber_curr_host_input{lane_num}          = INTEGER ; Pre-FEC BER current high warning flag change count for host input
    errored_frames_min_media_input{lane_num}      = INTEGER ; Errored frames minimum high warning flag change count for media input
    errored_frames_max_media_input{lane_num}      = INTEGER ; Errored frames maximum high warning flag change count for media input
    errored_frames_avg_media_input{lane_num}      = INTEGER ; Errored frames average high warning flag change count for media input
    errored_frames_curr_media_input{lane_num}     = INTEGER ; Errored frames current high warning flag change count for media input
    errored_frames_min_host_input{lane_num}       = INTEGER ; Errored frames minimum high warning flag change count for host input
    errored_frames_max_host_input{lane_num}       = INTEGER ; Errored frames maximum high warning flag change count for host input
    errored_frames_avg_host_input{lane_num}       = INTEGER ; Errored frames average high warning flag change count for host input
    errored_frames_curr_host_input{lane_num}      = INTEGER ; Errored frames current high warning flag change count for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                                        = INTEGER ; modulator bias xi in percentage (high warning flag change count)
    biasxq{lane_num}                                        = INTEGER ; modulator bias xq in percentage (high warning flag change count)
    biasxp{lane_num}                                        = INTEGER ; modulator bias xp in percentage (high warning flag change count)
    biasyi{lane_num}                                        = INTEGER ; modulator bias yi in percentage (high warning flag change count)
    biasyq{lane_num}                                        = INTEGER ; modulator bias yq in percentage (high warning flag change count)
    biasyp{lane_num}                                        = INTEGER ; modulator bias yq in percentage (high warning flag change count)
    cdshort{lane_num}                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (high warning flag change count)
    cdlong{lane_num}                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (high warning flag change count)
    dgd{lane_num}                                           = INTEGER ; differential group delay in ps (high warning flag change count)
    sopmd{lane_num}                                         = INTEGER ; second order polarization mode dispersion in ps^2 (high warning flag change count)
    soproc{lane_num}                                        = INTEGER ; state of polarization rate of change in krad/s (high warning flag change count)
    pdl{lane_num}                                           = INTEGER ; polarization dependent loss in db (high warning flag change count)
    osnr{lane_num}                                          = INTEGER ; optical signal to noise ratio in db (high warning flag change count)
    esnr{lane_num}                                          = INTEGER ; electrical signal to noise ratio in db (high warning flag change count)
    cfo{lane_num}                                           = INTEGER ; carrier frequency offset in Hz (high warning flag change count)
    txcurrpower{lane_num}                                   = INTEGER ; tx current output power in dbm (high warning flag change count)
    rxtotpower{lane_num}                                    = INTEGER ; rx total power in  dbm (high warning flag change count)
    rxsigpower{lane_num}                                    = INTEGER; rx signal power in dbm (high warning flag change count)
```

##### 3.2.4.4 Transceiver VDM low warning flag change count data

The `TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT` table stores the flag change count for low warning flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning flag change count for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = INTEGER ; laser temperature low warning flag change count for media input
    esnr_media_input{lane_num}                    = INTEGER ; eSNR low warning flag change count for media input
    esnr_host_input{lane_num}                     = INTEGER ; eSNR low warning flag change count for host input
    pam4_level_transition_media_input{lane_num}   = INTEGER ; PAM4 level transition low warning flag change count for media input
    pam4_level_transition_host_input{lane_num}    = INTEGER ; PAM4 level transition low warning flag change count for host input
    prefec_ber_min_media_input{lane_num}          = INTEGER ; Pre-FEC BER minimum low warning flag change count for media input
    prefec_ber_max_media_input{lane_num}          = INTEGER ; Pre-FEC BER maximum low warning flag change count for media input
    prefec_ber_avg_media_input{lane_num}          = INTEGER ; Pre-FEC BER average low warning flag change count for media input
    prefec_ber_curr_media_input{lane_num}         = INTEGER ; Pre-FEC BER current low warning flag change count for media input
    prefec_ber_min_host_input{lane_num}           = INTEGER ; Pre-FEC BER minimum low warning flag change count for host input
    prefec_ber_max_host_input{lane_num}           = INTEGER ; Pre-FEC BER maximum low warning flag change count for host input
    prefec_ber_avg_host_input{lane_num}           = INTEGER ; Pre-FEC BER average low warning flag change count for host input
    prefec_ber_curr_host_input{lane_num}          = INTEGER ; Pre-FEC BER current low warning flag change count for host input
    errored_frames_min_media_input{lane_num}      = INTEGER ; Errored frames minimum low warning flag change count for media input
    errored_frames_max_media_input{lane_num}      = INTEGER ; Errored frames maximum low warning flag change count for media input
    errored_frames_avg_media_input{lane_num}      = INTEGER ; Errored frames average low warning flag change count for media input
    errored_frames_curr_media_input{lane_num}     = INTEGER ; Errored frames current low warning flag change count for media input
    errored_frames_min_host_input{lane_num}       = INTEGER ; Errored frames minimum low warning flag change count for host input
    errored_frames_max_host_input{lane_num}       = INTEGER ; Errored frames maximum low warning flag change count for host input
    errored_frames_avg_host_input{lane_num}       = INTEGER ; Errored frames average low warning flag change count for host input
    errored_frames_curr_host_input{lane_num}      = INTEGER ; Errored frames current low warning flag change count for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                                        = INTEGER ; modulator bias xi in percentage (low warning flag change count)
    biasxq{lane_num}                                        = INTEGER ; modulator bias xq in percentage (low warning flag change count)
    biasxp{lane_num}                                        = INTEGER ; modulator bias xp in percentage (low warning flag change count)
    biasyi{lane_num}                                        = INTEGER ; modulator bias yi in percentage (low warning flag change count)
    biasyq{lane_num}                                        = INTEGER ; modulator bias yq in percentage (low warning flag change count)
    biasyp{lane_num}                                        = INTEGER ; modulator bias yq in percentage (low warning flag change count)
    cdshort{lane_num}                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (low warning flag change count)
    cdlong{lane_num}                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (low warning flag change count)
    dgd{lane_num}                                           = INTEGER ; differential group delay in ps (low warning flag change count)
    sopmd{lane_num}                                         = INTEGER ; second order polarization mode dispersion in ps^2 (low warning flag change count)
    soproc{lane_num}                                        = INTEGER ; state of polarization rate of change in krad/s (low warning flag change count)
    pdl{lane_num}                                           = INTEGER ; polarization dependent loss in db (low warning flag change count)
    osnr{lane_num}                                          = INTEGER ; optical signal to noise ratio in db (low warning flag change count)
    esnr{lane_num}                                          = INTEGER ; electrical signal to noise ratio in db (low warning flag change count)
    cfo{lane_num}                                           = INTEGER ; carrier frequency offset in Hz (low warning flag change count)
    txcurrpower{lane_num}                                   = INTEGER ; tx current output power in dbm (low warning flag change count)
    rxtotpower{lane_num}                                    = INTEGER ; rx total power in  dbm (low warning flag change count)
    rxsigpower{lane_num}                                    = INTEGER; rx signal power in dbm (low warning flag change count)
```

#### 3.2.5 Transceiver VDM flag time set data

##### 3.2.5.1 Transceiver VDM high alarm flag time set data

The `TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME` table stores the last set time for the VDM high alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm last set time for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature high alarm last set time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR high alarm last set time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR high alarm last set time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition high alarm last set time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition high alarm last set time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum high alarm last set time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum high alarm last set time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average high alarm last set time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current high alarm last set time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum high alarm last set time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum high alarm last set time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average high alarm last set time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current high alarm last set time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum high alarm last set time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum high alarm last set time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average high alarm last set time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current high alarm last set time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum high alarm last set time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum high alarm last set time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average high alarm last set time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current high alarm last set time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = STR ; modulator bias xi in percentage (high alarm last set time)
    biasxq{lane_num}                              = STR ; modulator bias xq in percentage (high alarm last set time)
    biasxp{lane_num}                              = STR ; modulator bias xp in percentage (high alarm last set time)
    biasyi{lane_num}                              = STR ; modulator bias yi in percentage (high alarm last set time)
    biasyq{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last set time)
    biasyp{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last set time)
    cdshort{lane_num}                             = STR ; chromatic dispersion, high granularity, short link in ps/nm (high alarm last set time)
    cdlong{lane_num}                              = STR ; chromatic dispersion, high granularity, long link in ps/nm (high alarm last set time)
    dgd{lane_num}                                 = STR ; differential group delay in ps (high alarm last set time)
    sopmd{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (high alarm last set time)
    soproc{lane_num}                              = STR ; state of polarization rate of change in krad/s (high alarm last set time)
    pdl{lane_num}                                 = STR ; polarization dependent loss in db (high alarm last set time)
    osnr{lane_num}                                = STR ; optical signal to noise ratio in db (high alarm last set time)
    esnr{lane_num}                                = STR ; electrical signal to noise ratio in db (high alarm last set time)
    cfo{lane_num}                                 = STR ; carrier frequency offset in Hz (high alarm last set time)
    txcurrpower{lane_num}                         = STR ; tx current output power in dbm (high alarm last set time)
    rxtotpower{lane_num}                          = STR ; rx total power in  dbm (high alarm last set time)
    rxsigpower{lane_num}                          = STR; rx signal power in dbm (high alarm last set time)
```

##### 3.2.5.2 Transceiver VDM low alarm flag time set data

The `TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME` table stores the last set time for the VDM low alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm last set time for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature low alarm last set time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR low alarm last set time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR low alarm last set time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition low alarm last set time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition low alarm last set time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum low alarm last set time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum low alarm last set time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average low alarm last set time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current low alarm last set time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum low alarm last set time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum low alarm last set time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average low alarm last set time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current low alarm last set time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum low alarm last set time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum low alarm last set time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average low alarm last set time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current low alarm last set time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum low alarm last set time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum low alarm last set time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average low alarm last set time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current low alarm last set time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = STR ; modulator bias xi in percentage (low alarm last set time)
    biasxq{lane_num}                              = STR ; modulator bias xq in percentage (low alarm last set time)
    biasxp{lane_num}                              = STR ; modulator bias xp in percentage (low alarm last set time)
    biasyi{lane_num}                              = STR ; modulator bias yi in percentage (low alarm last set time)
    biasyq{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last set time)
    biasyp{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last set time)
    cdshort{lane_num}                             = STR ; chromatic dispersion, low granularity, short link in ps/nm (low alarm last set time)
    cdlong{lane_num}                              = STR ; chromatic dispersion, low granularity, long link in ps/nm (low alarm last set time)
    dgd{lane_num}                                 = STR ; differential group delay in ps (low alarm last set time)
    sopmd{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (low alarm last set time)
    soproc{lane_num}                              = STR ; state of polarization rate of change in krad/s (low alarm last set time)
    pdl{lane_num}                                 = STR ; polarization dependent loss in db (low alarm last set time)
    osnr{lane_num}                                = STR ; optical signal to noise ratio in db (low alarm last set time)
    esnr{lane_num}                                = STR ; electrical signal to noise ratio in db (low alarm last set time)
    cfo{lane_num}                                 = STR ; carrier frequency offset in Hz (low alarm last set time)
    txcurrpower{lane_num}                         = STR ; tx current output power in dbm (low alarm last set time)
    rxtotpower{lane_num}                          = STR ; rx total power in  dbm (low alarm last set time)
    rxsigpower{lane_num}                          = STR; rx signal power in dbm (low alarm last set time)
```

##### 3.2.5.3 Transceiver VDM high warning flag time set data

The `TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME` table stores the last set time for the VDM high warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning last set time for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature high warning last set time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR high warning last set time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR high warning last set time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition high warning last set time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition high warning last set time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum high warning last set time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum high warning last set time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average high warning last set time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current high warning last set time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum high warning last set time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum high warning last set time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average high warning last set time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current high warning last set time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum high warning last set time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum high warning last set time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average high warning last set time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current high warning last set time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum high warning last set time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum high warning last set time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average high warning last set time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current high warning last set time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                                        = STR ; modulator bias xi in percentage (high warning last set time)
    biasxq{lane_num}                                        = STR ; modulator bias xq in percentage (high warning last set time)
    biasxp{lane_num}                                        = STR ; modulator bias xp in percentage (high warning last set time)
    biasyi{lane_num}                                        = STR ; modulator bias yi in percentage (high warning last set time)
    biasyq{lane_num}                                        = STR ; modulator bias yq in percentage (high warning last set time)
    biasyp{lane_num}                                        = STR ; modulator bias yq in percentage (high warning last set time)
    cdshort{lane_num}                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (high warning last set time)
    cdlong{lane_num}                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (high warning last set time)
    dgd{lane_num}                                           = STR ; differential group delay in ps (high warning last set time)
    sopmd{lane_num}                                         = STR ; second order polarization mode dispersion in ps^2 (high warning last set time)
    soproc{lane_num}                                        = STR ; state of polarization rate of change in krad/s (high warning last set time)
    pdl{lane_num}                                           = STR ; polarization dependent loss in db (high warning last set time)
    osnr{lane_num}                                          = STR ; optical signal to noise ratio in db (high warning last set time)
    esnr{lane_num}                                          = STR ; electrical signal to noise ratio in db (high warning last set time)
    cfo{lane_num}                                           = STR ; carrier frequency offset in Hz (high warning last set time)
    txcurrpower{lane_num}                                   = STR ; tx current output power in dbm (high warning last set time)
    rxtotpower{lane_num}                                    = STR ; rx total power in  dbm (high warning last set time)
    rxsigpower{lane_num}                                    = STR; rx signal power in dbm (high warning last set time)
```

##### 3.2.5.4 Transceiver VDM low warning flag time set data

The `TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME` table stores the last set time for the VDM low warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning last set time for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature low warning last set time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR low warning last set time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR low warning last set time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition low warning last set time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition low warning last set time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum low warning last set time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum low warning last set time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average low warning last set time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current low warning last set time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum low warning last set time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum low warning last set time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average low warning last set time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current low warning last set time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum low warning last set time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum low warning last set time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average low warning last set time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current low warning last set time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum low warning last set time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum low warning last set time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average low warning last set time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current low warning last set time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                                        = STR ; modulator bias xi in percentage (low warning last set time)
    biasxq{lane_num}                                        = STR ; modulator bias xq in percentage (low warning last set time)
    biasxp{lane_num}                                        = STR ; modulator bias xp in percentage (low warning last set time)
    biasyi{lane_num}                                        = STR ; modulator bias yi in percentage (low warning last set time)
    biasyq{lane_num}                                        = STR ; modulator bias yq in percentage (low warning last set time)
    biasyp{lane_num}                                        = STR ; modulator bias yq in percentage (low warning last set time)
    cdshort{lane_num}                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low warning last set time)
    cdlong{lane_num}                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low warning last set time)
    dgd{lane_num}                                           = STR ; differential group delay in ps (low warning last set time)
    sopmd{lane_num}                                         = STR ; second order polarization mode dispersion in ps^2 (low warning last set time)
    soproc{lane_num}                                        = STR ; state of polarization rate of change in krad/s (low warning last set time)
    pdl{lane_num}                                           = STR ; polarization dependent loss in db (low warning last set time)
    osnr{lane_num}                                          = STR ; optical signal to noise ratio in db (low warning last set time)
    esnr{lane_num}                                          = STR ; electrical signal to noise ratio in db (low warning last set time)
    cfo{lane_num}                                           = STR ; carrier frequency offset in Hz (low warning last set time)
    txcurrpower{lane_num}                                   = STR ; tx current output power in dbm (low warning last set time)
    rxtotpower{lane_num}                                    = STR ; rx total power in  dbm (low warning last set time)
    rxsigpower{lane_num}                                    = STR; rx signal power in dbm (low warning last set time)
```

#### 3.2.6 Transceiver VDM flag time clear data

##### 3.2.6.1 Transceiver VDM high alarm flag time clear data

The `TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME` table stores the last clear time for the VDM high alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm last clear time for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature high alarm last clear time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR high alarm last clear time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR high alarm last clear time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition high alarm last clear time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition high alarm last clear time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum high alarm last clear time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum high alarm last clear time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average high alarm last clear time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current high alarm last clear time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum high alarm last clear time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum high alarm last clear time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average high alarm last clear time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current high alarm last clear time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum high alarm last clear time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum high alarm last clear time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average high alarm last clear time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current high alarm last clear time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum high alarm last clear time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum high alarm last clear time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average high alarm last clear time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current high alarm last clear time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = STR ; modulator bias xi in percentage (high alarm last clear time)
    biasxq{lane_num}                              = STR ; modulator bias xq in percentage (high alarm last clear time)
    biasxp{lane_num}                              = STR ; modulator bias xp in percentage (high alarm last clear time)
    biasyi{lane_num}                              = STR ; modulator bias yi in percentage (high alarm last clear time)
    biasyq{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last clear time)
    biasyp{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last clear time)
    cdshort{lane_num}                             = STR ; chromatic dispersion, high granularity, short link in ps/nm (high alarm last clear time)
    cdlong{lane_num}                              = STR ; chromatic dispersion, high granularity, long link in ps/nm (high alarm last clear time)
    dgd{lane_num}                                 = STR ; differential group delay in ps (high alarm last clear time)
    sopmd{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (high alarm last clear time)
    soproc{lane_num}                              = STR ; state of polarization rate of change in krad/s (high alarm last clear time)
    pdl{lane_num}                                 = STR ; polarization dependent loss in db (high alarm last clear time)
    osnr{lane_num}                                = STR ; optical signal to noise ratio in db (high alarm last clear time)
    esnr{lane_num}                                = STR ; electrical signal to noise ratio in db (high alarm last clear time)
    cfo{lane_num}                                 = STR ; carrier frequency offset in Hz (high alarm last clear time)
    txcurrpower{lane_num}                         = STR ; tx current output power in dbm (high alarm last clear time)
    rxtotpower{lane_num}                          = STR ; rx total power in  dbm (high alarm last clear time)
    rxsigpower{lane_num}                          = STR; rx signal power in dbm (high alarm last clear time)
```

##### 3.2.6.2 Transceiver VDM low alarm flag time clear data

The `TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME` table stores the last clear time for the VDM low alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm last clear time for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature low alarm last clear time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR low alarm last clear time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR low alarm last clear time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition low alarm last clear time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition low alarm last clear time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum low alarm last clear time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum low alarm last clear time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average low alarm last clear time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current low alarm last clear time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum low alarm last clear time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum low alarm last clear time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average low alarm last clear time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current low alarm last clear time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum low alarm last clear time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum low alarm last clear time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average low alarm last clear time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current low alarm last clear time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum low alarm last clear time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum low alarm last clear time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average low alarm last clear time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current low alarm last clear time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                              = STR ; modulator bias xi in percentage (low alarm last clear time)
    biasxq{lane_num}                              = STR ; modulator bias xq in percentage (low alarm last clear time)
    biasxp{lane_num}                              = STR ; modulator bias xp in percentage (low alarm last clear time)
    biasyi{lane_num}                              = STR ; modulator bias yi in percentage (low alarm last clear time)
    biasyq{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last clear time)
    biasyp{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last clear time)
    cdshort{lane_num}                             = STR ; chromatic dispersion, low granularity, short link in ps/nm (low alarm last clear time)
    cdlong{lane_num}                              = STR ; chromatic dispersion, low granularity, long link in ps/nm (low alarm last clear time)
    dgd{lane_num}                                 = STR ; differential group delay in ps (low alarm last clear time)
    sopmd{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (low alarm last clear time)
    soproc{lane_num}                              = STR ; state of polarization rate of change in krad/s (low alarm last clear time)
    pdl{lane_num}                                 = STR ; polarization dependent loss in db (low alarm last clear time)
    osnr{lane_num}                                = STR ; optical signal to noise ratio in db (low alarm last clear time)
    esnr{lane_num}                                = STR ; electrical signal to noise ratio in db (low alarm last clear time)
    cfo{lane_num}                                 = STR ; carrier frequency offset in Hz (low alarm last clear time)
    txcurrpower{lane_num}                         = STR ; tx current output power in dbm (low alarm last clear time)
    rxtotpower{lane_num}                          = STR ; rx total power in  dbm (low alarm last clear time)
    rxsigpower{lane_num}                          = STR; rx signal power in dbm (low alarm last clear time)
```

##### 3.2.6.3 Transceiver VDM high warning flag time clear data

The `TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME` table stores the last clear time for the VDM high warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning last clear time for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature high warning last clear time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR high warning last clear time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR high warning last clear time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition high warning last clear time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition high warning last clear time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum high warning last clear time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum high warning last clear time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average high warning last clear time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current high warning last clear time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum high warning last clear time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum high warning last clear time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average high warning last clear time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current high warning last clear time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum high warning last clear time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum high warning last clear time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average high warning last clear time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current high warning last clear time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum high warning last clear time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum high warning last clear time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average high warning last clear time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current high warning last clear time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                                        = STR ; modulator bias xi in percentage (high warning last clear time)
    biasxq{lane_num}                                        = STR ; modulator bias xq in percentage (high warning last clear time)
    biasxp{lane_num}                                        = STR ; modulator bias xp in percentage (high warning last clear time)
    biasyi{lane_num}                                        = STR ; modulator bias yi in percentage (high warning last clear time)
    biasyq{lane_num}                                        = STR ; modulator bias yq in percentage (high warning last clear time)
    biasyp{lane_num}                                        = STR ; modulator bias yq in percentage (high warning last clear time)
    cdshort{lane_num}                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (high warning last clear time)
    cdlong{lane_num}                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (high warning last clear time)
    dgd{lane_num}                                           = STR ; differential group delay in ps (high warning last clear time)
    sopmd{lane_num}                                         = STR ; second order polarization mode dispersion in ps^2 (high warning last clear time)
    soproc{lane_num}                                        = STR ; state of polarization rate of change in krad/s (high warning last clear time)
    pdl{lane_num}                                           = STR ; polarization dependent loss in db (high warning last clear time)
    osnr{lane_num}                                          = STR ; optical signal to noise ratio in db (high warning last clear time)
    esnr{lane_num}                                          = STR ; electrical signal to noise ratio in db (high warning last clear time)
    cfo{lane_num}                                           = STR ; carrier frequency offset in Hz (high warning last clear time)
    txcurrpower{lane_num}                                   = STR ; tx current output power in dbm (high warning last clear time)
    rxtotpower{lane_num}                                    = STR ; rx total power in  dbm (high warning last clear time)
    rxsigpower{lane_num}                                    = STR; rx signal power in dbm (high warning last clear time)
```

##### 3.2.6.4 Transceiver VDM low warning flag time clear data

The `TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME` table stores the last clear time for the VDM low warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning last clear time for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media{lane_num}             = STR ; laser temperature low warning last clear time for media input
    esnr_media_input{lane_num}                    = STR ; eSNR low warning last clear time for media input
    esnr_host_input{lane_num}                     = STR ; eSNR low warning last clear time for host input
    pam4_level_transition_media_input{lane_num}   = STR ; PAM4 level transition low warning last clear time for media input
    pam4_level_transition_host_input{lane_num}    = STR ; PAM4 level transition low warning last clear time for host input
    prefec_ber_min_media_input{lane_num}          = STR ; Pre-FEC BER minimum low warning last clear time for media input
    prefec_ber_max_media_input{lane_num}          = STR ; Pre-FEC BER maximum low warning last clear time for media input
    prefec_ber_avg_media_input{lane_num}          = STR ; Pre-FEC BER average low warning last clear time for media input
    prefec_ber_curr_media_input{lane_num}         = STR ; Pre-FEC BER current low warning last clear time for media input
    prefec_ber_min_host_input{lane_num}           = STR ; Pre-FEC BER minimum low warning last clear time for host input
    prefec_ber_max_host_input{lane_num}           = STR ; Pre-FEC BER maximum low warning last clear time for host input
    prefec_ber_avg_host_input{lane_num}           = STR ; Pre-FEC BER average low warning last clear time for host input
    prefec_ber_curr_host_input{lane_num}          = STR ; Pre-FEC BER current low warning last clear time for host input
    errored_frames_min_media_input{lane_num}      = STR ; Errored frames minimum low warning last clear time for media input
    errored_frames_max_media_input{lane_num}      = STR ; Errored frames maximum low warning last clear time for media input
    errored_frames_avg_media_input{lane_num}      = STR ; Errored frames average low warning last clear time for media input
    errored_frames_curr_media_input{lane_num}     = STR ; Errored frames current low warning last clear time for media input
    errored_frames_min_host_input{lane_num}       = STR ; Errored frames minimum low warning last clear time for host input
    errored_frames_max_host_input{lane_num}       = STR ; Errored frames maximum low warning last clear time for host input
    errored_frames_avg_host_input{lane_num}       = STR ; Errored frames average low warning last clear time for host input
    errored_frames_curr_host_input{lane_num}      = STR ; Errored frames current low warning last clear time for host input

    ;C-CMIS specific fields
    biasxi{lane_num}                                        = STR ; modulator bias xi in percentage (low warning last clear time)
    biasxq{lane_num}                                        = STR ; modulator bias xq in percentage (low warning last clear time)
    biasxp{lane_num}                                        = STR ; modulator bias xp in percentage (low warning last clear time)
    biasyi{lane_num}                                        = STR ; modulator bias yi in percentage (low warning last clear time)
    biasyq{lane_num}                                        = STR ; modulator bias yq in percentage (low warning last clear time)
    biasyp{lane_num}                                        = STR ; modulator bias yq in percentage (low warning last clear time)
    cdshort{lane_num}                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low warning last clear time)
    cdlong{lane_num}                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low warning last clear time)
    dgd{lane_num}                                           = STR ; differential group delay in ps (low warning last clear time)
    sopmd{lane_num}                                         = STR ; second order polarization mode dispersion in ps^2 (low warning last clear time)
    soproc{lane_num}                                        = STR ; state of polarization rate of change in krad/s (low warning last clear time)
    pdl{lane_num}                                           = STR ; polarization dependent loss in db (low warning last clear time)
    osnr{lane_num}                                          = STR ; optical signal to noise ratio in db (low warning last clear time)
    esnr{lane_num}                                          = STR ; electrical signal to noise ratio in db (low warning last clear time)
    cfo{lane_num}                                           = STR ; carrier frequency offset in Hz (low warning last clear time)
    txcurrpower{lane_num}                                   = STR ; tx current output power in dbm (low warning last clear time)
    rxtotpower{lane_num}                                    = STR ; rx total power in  dbm (low warning last clear time)
    rxsigpower{lane_num}                                    = STR; rx signal power in dbm (low warning last clear time)
```

### 3.3 Transceiver status data (Hardware)

This section describes the tables used to store data primarily retrieved from the transceiver hardware.

#### 3.3.1 Transceiver status data to store module and data path status

The `TRANSCEIVER_STATUS` table stores the status of the transceiver.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS|ifname        ; Error information for module on port
    ; field                                 = value
    last_update_time                        = STR               ; last update time for diagnostic data
    diagnostics_update_interval             = INTEGER           ; DOM thread update interval in seconds
    tx{lane_num}disable                     = BOOLEAN           ; TX disable state on media lane {lane_num}
    tx_disabled_channel                     = INTEGER           ; TX disable field
    module_state                            = 1*255VCHAR        ; current module state (ModuleLowPwr, ModulePwrUp, ModuleReady, ModulePwrDn, Fault)
    module_fault_cause                      = 1*255VCHAR        ; reason of entering the module fault state
    DP{lane_num}State                       = 1*255VCHAR        ; data path state indicator on host lane {lane_num}
    tx{lane_num}OutputStatus                = BOOLEAN           ; tx output status on media lane {lane_num}
    rx{lane_num}OutputStatusHostlane        = BOOLEAN           ; rx output status on host lane {lane_num}
    config_state_hostlane{lane_num}         = 1*255VCHAR        ; configuration status for the data path of host line {lane_num}
    dpdeinit_hostlane{lane_num}             = BOOLEAN           ; data path deinitialized status on host lane {lane_num}
    dpinit_pending_hostlane{lane_num}       = BOOLEAN           ; data path configuration updated on host lane {lane_num}

    ;C-CMIS specific fields
    tuning_in_progress                      = BOOLEAN           ; tuning in progress status
    wavelength_unlock_status                = BOOLEAN           ; laser unlocked status
```

#### 3.3.2 Transceiver status data to store module and data path flag status

The `TRANSCEIVER_STATUS_FLAG` table stores the status of the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS_FLAG|ifname        ; Flag information for module on port
    ; field                                 = value
    last_update_time                        = STR               ; last update time for diagnostic data
    datapath_firmware_fault                 = BOOLEAN           ; datapath (DSP) firmware fault
    module_firmware_fault                   = BOOLEAN           ; module firmware fault
    module_state_changed                    = BOOLEAN           ; module state changed
    tx{lane_num}fault                       = BOOLEAN           ; tx fault flag on media lane {lane_num}
    rx{lane_num}los                         = BOOLEAN           ; rx loss of signal flag on media lane {lane_num}
    tx{lane_num}los_hostlane                = BOOLEAN           ; tx loss of signal flag on host lane {lane_num}
    tx{lane_num}cdrlol_hostlane             = BOOLEAN           ; tx clock and data recovery loss of lock flag on host lane {lane_num}
    tx{lane_num}_eq_fault                   = BOOLEAN           ; tx equalization fault flag on host lane {lane_num}
    rx{lane_num}cdrlol                      = BOOLEAN           ; rx clock and data recovery loss of lock flag on media lane {lane_num}

    ;C-CMIS specific fields
    target_output_power_oor                 = BOOLEAN           ; target output power out of range flag
    fine_tuning_oor                         = BOOLEAN           ; fine tuning out of range flag
    tuning_not_accepted                     = BOOLEAN           ; tuning not accepted flag
    invalid_channel_num                     = BOOLEAN           ; invalid channel number flag
    tuning_complete                         = BOOLEAN           ; tuning complete flag
```

#### 3.3.3 Transceiver status data to store module and data path change count

The `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` table stores the change count for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT|ifname        ; Flag information for module on port
    ; field                                 = value
    datapath_firmware_fault           = INTEGER           ; datapath (DSP) firmware fault change count
    module_firmware_fault             = INTEGER           ; module firmware fault change count
    module_state_changed              = INTEGER           ; module state changed change count
    tx{lane_num}fault                 = INTEGER           ; tx fault flag on media lane {lane_num} change count
    rx{lane_num}los                   = INTEGER           ; rx loss of signal flag on media lane {lane_num} change count
    tx{lane_num}los_hostlane          = INTEGER           ; tx loss of signal flag on host lane {lane_num} change count
    tx{lane_num}cdrlol_hostlane       = INTEGER           ; tx clock and data recovery loss of lock flag on host lane {lane_num} change count
    tx{lane_num}_eq_fault             = INTEGER           ; tx equalization fault flag on host lane {lane_num} change count
    rx{lane_num}cdrlol                = INTEGER           ; rx clock and data recovery loss of lock flag on media lane {lane_num} change count

    ;C-CMIS specific fields
    target_output_power_oor           = INTEGER           ; target output power out of range flag change count
    fine_tuning_oor                   = INTEGER           ; fine tuning out of range flag change count
    tuning_not_accepted               = INTEGER           ; tuning not accepted flag change count
    invalid_channel_num               = INTEGER           ; invalid channel number flag change count
    tuning_complete                   = INTEGER           ; tuning complete flag change count
```

#### 3.3.4 Transceiver status data to store module and data path flag set time

The `TRANSCEIVER_STATUS_FLAG_SET_TIME` table stores the last set time for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                        = TRANSCEIVER_STATUS_FLAG_SET_TIME|ifname        ; Flag information for module on port
    ; field                                    = value
    datapath_firmware_fault           = STR           ; datapath (DSP) firmware fault set time
    module_firmware_fault             = STR           ; module firmware fault set time
    module_state_changed              = STR           ; module state changed set time
    tx{lane_num}fault                 = STR           ; tx fault flag on media lane {lane_num} set time
    rx{lane_num}los                   = STR           ; rx loss of signal flag on media lane {lane_num} set time
    tx{lane_num}los_hostlane          = STR           ; tx loss of signal flag on host lane {lane_num} set time
    tx{lane_num}cdrlol_hostlane       = STR           ; tx clock and data recovery loss of lock flag on host lane {lane_num} set time
    tx{lane_num}_eq_fault             = STR           ; tx equalization fault flag on host lane {lane_num} set time
    rx{lane_num}cdrlol                = STR           ; rx clock and data recovery loss of lock flag on media lane {lane_num} set time

    ;C-CMIS specific fields
    target_output_power_oor           = STR           ; target output power out of range flag set time
    fine_tuning_oor                   = STR           ; fine tuning out of range flag set time
    tuning_not_accepted               = STR           ; tuning not accepted flag set time
    invalid_channel_num               = STR           ; invalid channel number flag set time
    tuning_complete                   = STR           ; tuning complete flag set time
```

#### 3.3.5 Transceiver status data to store module and data path flag clear time

The `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` table stores the last clear time for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                        = TRANSCEIVER_STATUS_FLAG_CLEAR_TIME|ifname        ; Flag information for module on port
    ; field                                    = value
    datapath_firmware_fault           = STR           ; datapath (DSP) firmware fault clear time
    module_firmware_fault             = STR           ; module firmware fault clear time
    module_state_changed              = STR           ; module state changed clear time
    tx{lane_num}fault                 = STR           ; tx fault flag on media lane {lane_num} clear time
    rx{lane_num}los                   = STR           ; rx loss of signal flag on media lane {lane_num} clear time
    tx{lane_num}los_hostlane          = STR           ; tx loss of signal flag on host lane {lane_num} clear time
    tx{lane_num}cdrlol_hostlane       = STR           ; tx clock and data recovery loss of lock flag on host lane {lane_num} clear time
    tx{lane_num}_eq_fault             = STR           ; tx equalization fault flag on host lane {lane_num} clear time
    rx{lane_num}cdrlol                = STR           ; rx clock and data recovery loss of lock flag on media lane {lane_num} clear time

    ;C-CMIS specific fields
    target_output_power_oor           = STR           ; target output power out of range flag clear time
    fine_tuning_oor                   = STR           ; fine tuning out of range flag clear time
    tuning_not_accepted               = STR           ; tuning not accepted flag clear time
    invalid_channel_num               = STR           ; invalid channel number flag clear time
    tuning_complete                   = STR           ; tuning complete flag clear time
```

### 3.4 Transceiver Status Data (Software)

#### 3.4.1 Transceiver Status Data Maintained by the `xcvrd` Daemon

The `TRANSCEIVER_STATUS_SW` table stores the status of the transceiver as maintained by the `xcvrd` daemon.

Unlike other tables in the HLD, which are controlled by a single thread, the `TRANSCEIVER_STATUS_SW` table is controlled by multiple threads (`SfpStateUpdateTask` and `CmisManagerTask`). Adding a `last_update_time` field to this table could cause concurrency issues since multiple threads update the same field. To avoid this, the `last_update_time` field is not included in the `TRANSCEIVER_STATUS_SW` table.

Additionally, this table exists for all subports of a port breakout group, unlike other tables which exist only for the first subport of a port breakout group.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS_SW|ifname; 
    ; field                                 = value
    cmis_state                              = 1*255VCHAR        ; Software CMIS state of the module
    status                                  = 1*255VCHAR        ; code of the module status (plug in, plug out)
    error                                   = 1*255VCHAR        ; module error (N/A or a string consisting of error descriptions joined by "|", like "error1 | error2" )
```

### 3.5 Transceiver PM data

The `TRANSCEIVER_PM` table stores the performance monitoring data of the transceiver. This table is exists only for C-CMIS transceivers.

```plaintext
    ; Defines Transceiver PM information for a port
    key                          = TRANSCEIVER_PM|ifname            ; information of PM on port
    ; field                      = value 
    last_update_time             = STR                              ; last update time for diagnostic data
    prefec_ber_avg               = FLOAT                            ; prefec ber avg
    prefec_ber_min               = FLOAT                            ; prefec ber min
    prefec_ber_max               = FLOAT                            ; prefec ber max
    uncorr_frames_avg            = FLOAT                            ; uncorrected frames ratio avg
    uncorr_frames_min            = FLOAT                            ; uncorrected frames ratio min
    uncorr_frames_max            = FLOAT                            ; uncorrected frames ratio max
    cd_avg                       = FLOAT                            ; chromatic dispersion avg
    cd_min                       = FLOAT                            ; chromatic dispersion min
    cd_max                       = FLOAT                            ; chromatic dispersion max
    dgd_avg                      = FLOAT                            ; differential group delay avg
    dgd_min                      = FLOAT                            ; differential group delay min
    dgd_max                      = FLOAT                            ; differential group delay max
    sopmd_avg                    = FLOAT                            ; second order polarization mode dispersion avg
    sopmd_min                    = FLOAT                            ; second order polarization mode dispersion min
    sopmd_max                    = FLOAT                            ; second order polarization mode dispersion max
    pdl_avg                      = FLOAT                            ; polarization dependent loss avg
    pdl_min                      = FLOAT                            ; polarization dependent loss min
    pdl_max                      = FLOAT                            ; polarization dependent loss max
    osnr_avg                     = FLOAT                            ; optical signal to noise ratio avg
    osnr_min                     = FLOAT                            ; optical signal to noise ratio min
    osnr_max                     = FLOAT                            ; optical signal to noise ratio max
    esnr_avg                     = FLOAT                            ; electrical signal to noise ratio avg
    esnr_min                     = FLOAT                            ; electrical signal to noise ratio min
    esnr_max                     = FLOAT                            ; electrical signal to noise ratio max
    cfo_avg                      = FLOAT                            ; carrier frequency offset avg
    cfo_min                      = FLOAT                            ; carrier frequency offset min
    cfo_max                      = FLOAT                            ; carrier frequency offset max
    soproc_avg                   = FLOAT                            ; state of polarization rate of change avg
    soproc_min                   = FLOAT                            ; state of polarization rate of change min
    soproc_max                   = FLOAT                            ; state of polarization rate of change max
    tx_power_avg                 = FLOAT                            ; tx output power avg
    tx_power_min                 = FLOAT                            ; tx output power min
    tx_power_max                 = FLOAT                            ; tx output power max
    rx_tot_power_avg             = FLOAT                            ; rx total power avg
    rx_tot_power_min             = FLOAT                            ; rx total power min
    rx_tot_power_max             = FLOAT                            ; rx total power max
    rx_sig_power_avg             = FLOAT                            ; rx signal power avg
    rx_sig_power_min             = FLOAT                            ; rx signal power min
    rx_sig_power_max             = FLOAT                            ; rx signal power max 
```

## 4. CLI Commands for CMIS Diagnostic Monitoring

For devices with breakout ports, the CLI handler will always fetch diagnostic monitoring data from the first port of the breakout group.

### 4.1 CLI Commands for DOM Monitoring

#### 4.1.1 `show interfaces transceiver dom PORT`

This CLI shows the transceiver DOM and threshold values for a given port.

```plaintext
CLI output format:
Current System Time: Day Mon DD HH:MM:SS YYYY
Update interval: SS seconds
Last updated: Day Mon DD HH:MM:SS YYYY

                                     High Alarm   High Warning   Low Warning   Low Alarm
                    Paramter_Name    Threshold    Threshold      Threshold     Threshold
Port         Lane   (Unit)           (Unit)       (Unit)         (Unit)        (Unit)
-----------  -----  ---------------  --------     --------       --------      --------

Example:
admin@sonic#show interfaces transceiver dom Ethernet1
Current System Time: Wed Oct 17 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024

                                     High Alarm   High Warning   Low Warning   Low Alarm
                    Temperature      Threshold    Threshold      Threshold     Threshold
Port         Lane   (Celsius)        (Celsius)    (Celsius)      (Celsius)     (Celsius)
-----------  -----  ---------------  --------     --------       --------      --------
Ethernet1    N/A    50              90           80             -10           -20
                                     High Alarm   High Warning   Low Warning   Low Alarm
                    Temperature      Threshold    Threshold      Threshold     Threshold
Port         Lane   (Celsius)        (Celsius)    (Celsius)      (Celsius)     (Celsius)
-----------  -----  ---------------  --------     --------       --------      --------
Ethernet1    N/A    3.295            3.6          3.465           3.135        3.105
                    Tx Bias          High Alarm   High Warning   Low Warning   Low Alarm
                    Current          Threshold    Threshold      Threshold     Threshold
Port         Lane   (mA)             (mA)         (mA)           (mA)          (mA)
-----------  -----  ---------------  --------     --------       --------      --------
Ethernet1    1      106.952          340.0        320.0          60.0          50.0
             2      106.952          340.0        320.0          60.0          50.0
             3      106.952          340.0        320.0          60.0          50.0
             4      106.952          340.0        320.0          60.0          50.0
             5      106.952          340.0        320.0          60.0          50.0
             6      106.952          340.0        320.0          60.0          50.0
             7      106.952          340.0        320.0          60.0          50.0
             8      106.952          340.0        320.0          60.0          50.0
                                     High Alarm   High Warning   Low Warning   Low Alarm
                    TX Power         Threshold    Threshold      Threshold     Threshold
Port         Lane   (dBm)            (dBm)        (dBm)          (dBm)         (dBm)
-----------  -----  ---------------  --------     --------       --------      --------
Ethernet1    1      2.929            6.0          5.0            -10           -20.202
             2      2.929            6.0          5.0            -10           -20.202
             3      2.929            6.0          5.0            -10           -20.202
             4      2.929            6.0          5.0            -10           -20.202
             5      2.929            6.0          5.0            -10           -20.202
             6      2.929            6.0          5.0            -10           -20.202
             7      2.929            6.0          5.0            -10           -20.202
             8      2.929            6.0          5.0            -10           -20.202
                                       High Alarm   High Warning   Low Warning   Low Alarm
                      RX Power         Threshold    Threshold      Threshold     Threshold
Port         Lane     (dBm)            (dBm)        (dBm)          (dBm)         (dBm)
-----------  -----    ---------------  --------     --------       --------      --------
Ethernet1    1        2.01             4.5           3.0           -3.903        -4.903
             2        2.01             4.5           3.0           -3.903        -4.903
             3        2.01             4.5           3.0           -3.903        -4.903
             4        2.01             4.5           3.0           -3.903        -4.903
             5        2.01             4.5           3.0           -3.903        -4.903
             6        2.01             4.5           3.0           -3.903        -4.903
             7        2.01             4.5           3.0           -3.903        -4.903
             8        2.01             4.5           3.0           -3.903        -4.903
                              High Alarm   High Warning   Low Warning   Low Alarm
             Laser Temp       Threshold    Threshold      Threshold     Threshold
Port         (Celsius)        (Celsius)    (Celsius)      (Celsius)     (Celsius)
-----------  ---------------  --------     --------       --------      --------
Ethernet1    50               90           80             -10           -20
             Laser config     High Alarm   High Warning   Low Warning   Low Alarm
             frequency        Threshold    Threshold      Threshold     Threshold
Port         (GHz)            (GHz)        (GHz)          (GHz)         (GHz)
-----------  ---------------  --------     --------       --------      --------
Ethernet1    195.5            N/A          N/A            N/A           N/A
             Laser current    High Alarm   High Warning   Low Warning   Low Alarm
Port         (GHz)            (GHz)        (GHz)          (GHz)         (GHz)
-----------  ---------------  --------     --------       --------      --------
Ethernet1    195.5            N/A          N/A            N/A           N/A
             Tx config        High Alarm   High Warning   Low Warning   Low Alarm
             power            Threshold    Threshold      Threshold     Threshold
Port         (dBm)            (dBm)        (dBm)          (dBm)         (dBm)
-----------  ---------------  --------     --------       --------      --------
Ethernet1    195.5            N/A          N/A            N/A           N/A
```

#### 4.1.2 `show interfaces transceiver dom flag PORT`

This CLI shows the transceiver DOM flags for a given port.

```plaintext
CLI output format:
Current System Time: Day Mon DD HH:MM:SS YYYY
Update interval: SS seconds
Last updated: Day Mon DD HH:MM:SS YYYY
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Parameter_Name   Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  ---------------  ---------------  ---------------  ---------------

Example:
admin@sonic#show interfaces transceiver dom flag Ethernet1
Current System Time: Wed Oct 17 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024

                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Parameter_Name   Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  -------------------------  -------------------------  -------------------------  -------------------------
Ethernet1    Temperature      True/                      False/                     False/                     False/
                              1/                         0/                         0/                         0/
                              Wed Oct 16 03:46:41 2024/  never                      never                      never
                              never                      Wed Oct 16 03:46:41 2024   Wed Oct 16 03:46:41 2024   Wed Oct 16 03:46:41 2024
Ethernet1    Voltage          False/                     False/                     False/                     False/
                              0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 1           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 2           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 3           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 4           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 5           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 6           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 7           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Bias Current  False/                     False/                     False/                     False/
             Lane 8           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 1           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 2           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 3           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 4           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 5           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 6           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 7           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Tx Power         False/                     False/                     False/                     False/
             Lane 8           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 1           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 2           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 3           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 4           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 5           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 6           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 7           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Rx Power         False/                     False/                     False/                     False/
             Lane 8           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never                      never                      never
Ethernet1    Laser            False/                     False/                     False/                     False/
             Temperature      0/                         0/                         1/                         1/
                              never/                     never/                     Wed Oct 16 03:46:41 2024/  never/
                              never                      never                      never                      never
```

### 4.2 CLI Commands for VDM Monitoring

#### 4.2.1 `show interfaces transceiver vdm PORT`

This CLI shows the transceiver VDM and threshold values for a given port.
The CLI will show VDM data for observables which are supported by the module vendor. If the module vendor does not support a particular observable, the CLI will not show data for that observable.

```plaintext
CLI output format:
Current System Time: Day Mon DD HH:MM:SS YYYY
Update interval: SS seconds
Last updated: Day Mon DD HH:MM:SS YYYY
                              High Alarm   High Warning   Low Warning   Low Alarm
             Observable_Name  Threshold    Threshold      Threshold     Threshold
Port         (Unit)           (Unit)       (Unit)         (Unit)        (Unit)
-----------  ---------------  --------     --------       --------      --------

Example:
admin@sonic#show interfaces transceiver vdm Ethernet1
Current System Time: Wed Oct 17 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024
                    eSNR Media       High Alarm   High Warning   Low Warning   Low Alarm
                    Input            Threshold    Threshold      Threshold     Threshold
Port         Lane   (dB)             (dB)         (dB)           (dB)          (dB)
-----------  -----  ---------------  --------     --------       --------      --------
Ethernet1    1      23.480468        0            0              0             0
             2      23.480468        0            0              0             0
             3      23.480468        0            0              0             0
             4      23.480468        0            0              0             0
             5      23.480468        0            0              0             0
             6      23.480468        0            0              0             0
             7      23.480468        0            0              0             0
             8      23.480468        0            0              0             0
                    eSNR Media       High Alarm   High Warning   Low Warning   Low Alarm
                    Output           Threshold    Threshold      Threshold     Threshold
Port         Lane   (dB)             (dB)         (dB)           (dB)          (dB)
-----------  -----  ---------------  --------     --------       --------      --------
Ethernet1    1      23.480468        0            0              0             0
             2      23.480468        0            0              0             0
             3      23.480468        0            0              0             0
             4      23.480468        0            0              0             0
             5      23.480468        0            0              0             0
             6      23.480468        0            0              0             0
             7      23.480468        0            0              0             0
             8      23.480468        0            0              0             0
.
.
.
Upto all observables supported by the module vendor
```

#### 4.2.2 `show interfaces transceiver vdm flag PORT`

This CLI shows the transceiver VDM flags for a given port.
For a given observable, the CLI will show data only for only 1 lane if one or more lanes has a flag set to true. If none of the lanes have a flag set to true, no data will be shown for that observable.
The `--detail` option can be used to show the data for all lanes and observables irrespective of the flag status. Please refer to the next section for the details on the usage of this option.

```plaintext
CLI output format:
Current System Time: Day Mon DD HH:MM:SS YYYY
Update interval: SS seconds
Last updated: Day Mon DD HH:MM:SS YYYY
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Observable_Name  Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  ---------------  ---------------  ---------------  ---------------

Example:
admin@sonic#show interfaces transceiver vdm flag Ethernet1
Current System Time: Wed Oct 17 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Observable_Name  Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  -------------------------  -------------------------  -------------------------  -------------------------
Ethernet1    Laser Temp Media True/                      False/                     False/                     False/
             Lane 1           1/                         0/                         2/                         0/
                              Wed Oct 16 03:46:41 2024/  never/                     Wed Oct 16 02:46:41 2024   never/
                              never                      never/                     Wed Oct 16 03:46:41 2024   never
Ethernet1   PAM4 Level        False                      True                       False/                     False/
            Transition        0/                         1/                         0/                         0/
            Media Input       never/                     Wed Oct 16 03:46:41 2024/  never/                     never/
            Lane 2            never                      never                      never                      never
.
.
.
Upto all observables with at least one lane having a flag set to true
```

##### 4.2.2.1 VDM flags dump using the `--detail` option

With the `--detail` option, the VDM data for all types of observables will be displayed. With this option, the CLI will show data for all lanes and supported observables (irrespective of the flag status). For unsupported observables, the CLI will show `N/A` for the data.

```plaintext
admin@sonic#show interfaces transceiver vdm flag Ethernet1 --detail
Current System Time: Wed Oct 17 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Observable_Name  Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  -------------------------  -------------------------  -------------------------  -------------------------
Ethernet1    Laser Temp Media True/                      False/                     False/                     False/
             Lane 1           1/                         0/                         2/                         0/
                              Wed Oct 16 03:46:41 2024/  never/                     Wed Oct 16 02:46:41 2024   never/
                              never                      never/                     Wed Oct 16 03:46:41 2024   never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 2           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 3           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 4           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 5           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 6           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 7           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
Ethernet1    Laser Temp Media False/                     False/                     False/                     False/
             Lane 8           0/                         0/                         0/                         0/
                              never/                     never/                     never/                     never/
                              never                      never/                     never                      never
.
.
.
Upto all observables for all lanes
```

### 4.3 CLI Commands for transceiver status monitoring

#### 4.3.1 `show interfaces transceiver status PORT`

Shows the module and datapath state data along with various flags related to it. Also stores various Tx and Rx related flags.

```plaintext
Example:
admin@sonic:/home/admin# show int transceiver status Ethernet0
Current System Time: Wed Oct 16 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024
Ethernet0: 
        CMIS State (SW): READY
        TX disable status on lane 1: False
        TX disable status on lane 2: False
        TX disable status on lane 3: False
        TX disable status on lane 4: False
        TX disable status on lane 5: False
        TX disable status on lane 6: False
        TX disable status on lane 7: False
        TX disable status on lane 8: False
        Disabled TX channels: 0
        Current module state: ModuleReady
        Reason of entering the module fault state: No Fault detected
        Data path state indicator on host lane 1: DataPathActivated
        Data path state indicator on host lane 2: DataPathActivated
        Data path state indicator on host lane 3: DataPathActivated
        Data path state indicator on host lane 4: DataPathActivated
        Data path state indicator on host lane 5: DataPathActivated
        Data path state indicator on host lane 6: DataPathActivated
        Data path state indicator on host lane 7: DataPathActivated
        Data path state indicator on host lane 8: DataPathActivated
        Tx output status on media lane 1: True
        Tx output status on media lane 2: True
        Tx output status on media lane 3: True
        Tx output status on media lane 4: True
        Tx output status on media lane 5: True
        Tx output status on media lane 6: True
        Tx output status on media lane 7: True
        Tx output status on media lane 8: True
        Rx output status on host lane 1: True
        Rx output status on host lane 2: True
        Rx output status on host lane 3: True
        Rx output status on host lane 4: True
        Rx output status on host lane 5: True
        Rx output status on host lane 6: True
        Rx output status on host lane 7: True
        Rx output status on host lane 8: True
        Configuration status for the data path of host line 1: ConfigSuccess
        Configuration status for the data path of host line 2: ConfigSuccess
        Configuration status for the data path of host line 3: ConfigSuccess
        Configuration status for the data path of host line 4: ConfigSuccess
        Configuration status for the data path of host line 5: ConfigSuccess
        Configuration status for the data path of host line 6: ConfigSuccess
        Configuration status for the data path of host line 7: ConfigSuccess
        Configuration status for the data path of host line 8: ConfigSuccess
        Data path deinit status on host lane 1: False
        Data path deinit status on host lane 2: False
        Data path deinit status on host lane 3: False
        Data path deinit status on host lane 4: False
        Data path deinit status on host lane 5: False
        Data path deinit status on host lane 6: False
        Data path deinit status on host lane 7: False
        Data path deinit status on host lane 8: False
        Data path configuration updated on host lane 1: False
        Data path configuration updated on host lane 2: False
        Data path configuration updated on host lane 3: False
        Data path configuration updated on host lane 4: False
        Data path configuration updated on host lane 5: False
        Data path configuration updated on host lane 6: False
        Data path configuration updated on host lane 7: False
        Data path configuration updated on host lane 8: False
        Tuning in progress status: False
        Laser unlocked status: True
        VDM Support: True
        VDM Fine Interval Length: 10000
```

#### 4.3.2 `show interfaces transceiver status flag PORT`

This CLI shows the various module and datapath state flags for a given port along with the change count and set/clear time.

```plaintext
admin@sonic:/home/admin# show int transceiver status flag Ethernet0
Current System Time: Wed Oct 17 03:46:41 2024
Update interval: 10 seconds
Last updated: Wed Oct 17 03:46:41 2024
Port         Observable_Name                  Flag Status/  Change Count/  Last Set Time/  Last Clear Time
-----------  ---------------------------      -------------------------------------------------------
Ethernet0    Tx fault on media Lane 1         False/  1/  Wed Oct 16 03:46:41 2024/  never
Ethernet0    Tx fault on media Lane 2         False/  0/  never/  never
Ethernet0    Tx fault on media Lane 3         False/  0/  never/  never
Ethernet0    Tx fault on media Lane 4         False/  0/  never/  never
Ethernet0    Tx fault on media Lane 5         False/  0/  never/  never
Ethernet0    Tx fault on media Lane 6         False/  0/  never/  never
Ethernet0    Tx fault on media Lane 7         False/  0/  never/  never
Ethernet0    Tx fault on media Lane 8         False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 1           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 2           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 3           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 4           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 5           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 6           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 7           False/  0/  never/  never
Ethernet0    Rx LOS on media Lane 8           False/  0/  never/  never
Ethernet0    Datapath firmware fault          False/  0/  never/  never
Ethernet0    Module firmware fault            False/  0/  never/  never
Ethernet0    Module state changed             False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 1            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 2            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 3            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 4            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 5            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 6            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 7            False/  0/  never/  never
Ethernet0    Tx LOS on host Lane 8            False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 1        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 2        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 3        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 4        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 5        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 6        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 7        False/  0/  never/  never
Ethernet0    Tx CDR LOL on host Lane 8        False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 1       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 2       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 3       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 4       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 5       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 6       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 7       False/  0/  never/  never
Ethernet0    Tx EQ fault on host Lane 8       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 1       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 2       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 3       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 4       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 5       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 6       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 7       False/  0/  never/  never
Ethernet0    Rx CDR LOL on media Lane 8       False/  0/  never/  never
Ethernet0    Target output power out of range False/  0/  never/  never
Ethernet0    Fine tuning out of range flag    False/  0/  never/  never
Ethernet0    Tuning not accepted flag         False/  0/  never/  never
Ethernet0    Invalid channel number flag      False/  0/  never/  never
Ethernet0    Tuning complete flag             False/  0/  never/  never
```

## 5. SONiC CMIS diagnostic monitoring workflow

### 5.1 Static Diagnostic Information

The `SfpStateUpdateTask` thread is responsible for updating the static diagnostic information for all the transceivers in the system. The static diagnostic information, such as threshold values for DOM, VDM and PM, are read from the transceiver and updated in the `redis-db` during `xcvrd` boot-up and during transceiver removal and insertion.

The following tables are updated by the `SfpStateUpdateTask` thread:

1. `TRANSCEIVER_DOM_THRESHOLD`
2. `TRANSCEIVER_VDM_XXX_THRESHOLD` where `XXX` is the threshold type (`highalarm`, `highwarning`, `lowwarning`, `lowalarm`)

### 5.2 Dynamic Diagnostic Information

The `DomInfoUpdateTask` thread is responsible for updating the dynamic diagnostic information for all the transceivers in the system. The following events drive the dynamic update of the diagnostic information:

1. **Periodic update of the diagnostic information:**
    - The `DomInfoUpdateTask` thread periodically updates the diagnostic information for all the ports.
    - The update period interval can be retrieved by reading the `dom_info_update_periodic_secs` field from the `/usr/share/sonic/device/{platform}/pmon_daemon_control.json` file.
    - If this field or the file is absent, the default timer value is 0 seconds.

2. **Link change event:**
    - Only the **flag-related diagnostic information** is updated for a port when a link change event is detected by the `DomInfoUpdateTask` thread. Further details on the tables updated during a link change event are provided in the `Diagnostic Information Update During Link Change Event` section.
    - Updating flag information during a link change event ensures that the flag change time is captured in a timely manner. The periodic update can take more time to update the diagnostic information since it reads the diagnostic information for all the ports in a sequential manner.
    - The `DomInfoUpdateTask` thread may fail to update flag metadata and flag status if there are mutiple link change events happening in a short period of time. Please refer to the Non-goals section for more details.
    - Since the flag registers are clear-on-read latched values, the `DomInfoUpdateTask` thread will require two reads to update the flag value, last clear time, and change count once the flagged condition is no longer present. Hence, it is expected that the flag status change in the database will be delayed by two update cycles when the flagged condition is no longer present on the module. Please refer to the Non-goals section for more details.

#### 5.2.1 High-Level Steps for Updating Dynamic Diagnostic Information

1. The `DomInfoUpdateTask` thread is created by the `xcvrd` process.
2. The `dom_info_update_periodic_secs` value is retrieved from the `pmon_daemon_control.json` file to determine the interval for updating the diagnostic information for all the ports. If the `dom_info_update_periodic_secs` field is absent or set to 0, the diagnostic information will be updated continuously without any delay between updates.
3. The `DomInfoUpdateTask` thread starts polling for the diagnostic information of the ports in a sequential manner:
    - It first checks if the `dom_info_update_periodic_secs` value is set. If not, it defaults to 0 seconds.
    - The thread then enters a loop that continues until the `task_stopping_event` is set.
    - Within the loop, it checks if the current time has exceeded the `expiration_time`. If so, it sets a flag to update all diagnostic information in the database.
    - It iterates over all physical ports, handling any port update events for ports that have undergone a link change and updating the flag-related tables accordingly.
    - If the flag to update all diagnostic information is set, it reads the diagnostic information for the current port.
    - After processing all ports, it resets the flag and updates the `expiration_time` to the current time plus the `dom_info_update_periodic_secs` interval.

The following steps are performed to update all diagnostic information for a port:

1. Ensure DOM monitoring is enabled for the port (in case of breakout port, port refers to the first subport of the breakout port group). If DOM monitoring is disabled, skip updating the diagnostic information for the port.
2. Read the transceiver firmware information from the module and update the `TRANSCEIVER_FIRMWARE_INFO` table.
3. Read the transceiver DOM sensor data from the module and update the `TRANSCEIVER_DOM_SENSOR` table.
4. Read the transceiver DOM flag data from the module, record the timestamp, and update the `TRANSCEIVER_DOM_FLAG` table (update the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables as well).
5. Read the transceiver status data from the module and update the `TRANSCEIVER_STATUS` table.
6. Read the transceiver status flag data from the module, record the timestamp, and update the `TRANSCEIVER_STATUS_FLAG` table (update the `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT`, `TRANSCEIVER_STATUS_FLAG_SET_TIME`, and `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` tables as well).
7. If the transceiver supports VDM monitoring, perform the following steps:
    1. Freeze the statistics by calling the CMIS API (`freeze_vdm_stats`) and wait for `FreezeDone` by calling `get_vdm_freeze_status`. The wait will continue until 1s (defined through `MAX_VDM_FREEZE_UNFREEZE_TIME_MSECS`) or until the `FreezeDone` bit is set. If the `FreezeDone` bit is not set within the timeout, the unfreeze operation will performed along with displaying an error message.
    2. Once the statistics are frozen, read the VDM real values, flags, and PM data from the module and update the `TRANSCEIVER_VDM_REAL_VALUE`, `TRANSCEIVER_VDM_FLAG`, and `TRANSCEIVER_PM` tables respectively.
    3. Update the VDM flag, change count, and time-related tables by comparing the current data with the previous data.
    4. Unfreeze the statistics by calling the CMIS API (`unfreeze_vdm_stats`) and wait for `UnfreezeDone` by calling `get_vdm_unfreeze_status`. The wait will continue until 1s (defined through `MAX_VDM_FREEZE_UNFREEZE_TIME_MSECS`) or until the `UnfreezeDone` bit is set. If the `UnfreezeDone` bit is not set within the timeout, an error message will be displayed.

Pseudo code:

```python
# Retrieve the update period interval
dom_info_update_periodic_secs = parse_field_from_pmon_daemon_control('dom_info_update_periodic_secs')
if dom_info_update_periodic_secs is None:
    dom_info_update_periodic_secs = 0

next_periodic_db_update_time = time.time() + dom_info_update_periodic_secs

while not dom_mgr.task_stopping_event.is_set():
    if next_periodic_db_update_time <= time.time():
        is_periodic_db_update_needed = True

    for physical_port, logical_ports in self.port_mapping.physical_to_logical.items():
        if has_link_status_changed_for_any_port():
            # After 1s post link change event, update the flag-related tables
            # for the affected ports
            update_flag_related_tables(ports_going_through_link_change)

        if is_periodic_db_update_needed:
            read_diagnostic_info(physical_port)

    if is_periodic_db_update_needed:
        next_periodic_db_update_time = time.time() + dom_info_update_periodic_secs
        is_periodic_db_update_needed = False
```

#### 5.2.2 Link Change Event Detection

This section details how the `DomInfoUpdateTask` thread detects link change events and handles them. It expands on the logic of the `has_link_status_changed_for_any_port` function described earlier.

The `DomInfoUpdateTask` thread periodically monitors the `flap_count` field in the `PORT_TABLE` within the `APPL_DB` to detect link changes:

- **Detection**:  
  The thread periodically reads the `flap_count` for all logical ports and caches these values. On each iteration, it compares the current `flap_count` to the cached value. If there is a difference between the current value and the cached value, a link change event is detected for that port.

- **Event Handling**:  
  When a link change is detected, the thread updates the flag-related diagnostic data for the affected ports. For breakout port groups, if multiple subports have an updated `flap_count` in a single iteration, the handler updates the flag information only once for the entire breakout group rather than individually for each subport.

  This is achieved by maintaining a dictionary (`link_change_affected_ports`) where:
  - **Key**: The physical port.
  - **Value**: The time at which the database update is planned.

  The database update time is set to **1 second** after the link change event is detected. This delay ensures that the module has sufficient time to update the relevant flag registers before the database update occurs.

- **Cache Update**:  
  After processing every port, the cached `flap_count` value is updated. This ensures that the thread correctly captures any link changes that occur during processing and prevents missing events.

- **Cache Initialization**:  
  The cache is initialized with the current `flap_count` values for all logical ports at the start of the thread. This ensures that the thread can detect link changes that occur before the first iteration.

**Reason for not relying on PORT_TABLE notifications for link change detection:**

An alternative mechanism to detect link changes is to subscribe to updates of the `natdev_oper_status` field in the `PORT_TABLE` within the `STATE_DB`. However, this method has significant limitations:

- **Delayed Processing**:  
  If the `DomInfoUpdateTask` thread is busy processing diagnostics for a port when multiple link flaps occur, it may miss some link change events. This is because:
  - The thread does not process `PORT_TABLE` changes in real-time while it is occupied.
  - By the time the thread resumes processing, it only detects a link change if the `natdev_oper_status` value differs from the last value read before it went busy.

- **Limited Subscription Granularity**:  
  The current database subscription mechanism supports monitoring changes to entire tables rather than specific fields. This means that the `DomInfoUpdateTask` thread would receive notifications for any modification in the `PORT_TABLE` rather than exclusively for link status changes.

#### 5.2.3 Diagnostic Information Update During Link Change Event

**Note:**  
All diagnostic tables planned to be updated as part of link change event handling will be updated 1 second after the link change event is processed. This delay allows the module to update the relevant flag registers post link change event.

The following tables are updated during a link change event:

##### 5.2.3.1 DOM Related Fields

The DOM flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link change event:

- `temperature`
- `voltage`
- `tx{lane_num}power`
- `rx{lane_num}power`
- `tx{lane_num}bias`
- `laser_temperature`

**Example:**

The following fields related to `temperature` are updated in the `redis-db` during a link change event:

- `temphighalarm` in `TRANSCEIVER_DOM_FLAG` table
- `temphighwarning` in `TRANSCEIVER_DOM_FLAG` table
- `templowwarning` in `TRANSCEIVER_DOM_FLAG` table
- `templowalarm` in `TRANSCEIVER_DOM_FLAG` table
- `temphighalarm` in `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table
- `temphighwarning` in `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table
- `templowwarning` in `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table
- `templowalarm` in `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table
- `temphighalarm` in `TRANSCEIVER_DOM_FLAG_SET_TIME` table
- `temphighwarning` in `TRANSCEIVER_DOM_FLAG_SET_TIME` table
- `templowwarning` in `TRANSCEIVER_DOM_FLAG_SET_TIME` table
- `templowalarm` in `TRANSCEIVER_DOM_FLAG_SET_TIME` table
- `temphighalarm` in `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table
- `temphighwarning` in `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table
- `templowwarning` in `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table
- `templowalarm` in `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table

##### 5.2.3.2 VDM Related Fields

The VDM flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link change event:

- `laser_temperature_media{lane_num}`
- `esnr_media_input`
- `pam4_level_transition_media_input`
- `prefec_ber_min_media_input`
- `prefec_ber_max_media_input`
- `prefec_ber_avg_media_input`
- `prefec_ber_curr_media_input`
- `errored_frames_min_media_input`
- `errored_frames_max_media_input`
- `errored_frames_avg_media_input`
- `errored_frames_curr_media_input`
- `esnr_host_input`
- `pam4_level_transition_host_input`
- `prefec_ber_min_host_input`
- `prefec_ber_max_host_input`
- `prefec_ber_avg_host_input`
- `prefec_ber_curr_host_input`
- `errored_frames_min_host_input`
- `errored_frames_max_host_input`
- `errored_frames_avg_host_input`
- `errored_frames_curr_host_input`

**Example:**

The following fields related to `esnr_media_input` are updated in the `redis-db` during a link change event:

- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME` table
- `esnr_media_input{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME` table

##### 5.2.3.3 Transceiver Status Related Fields

The transceiver status flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link change event:

- `datapath_firmware_fault`
- `module_firmware_fault`
- `module_state_changed`
- `tx{lane_num}fault`
- `rx{lane_num}los`
- `tx{lane_num}los_hostlane`
- `tx{lane_num}cdrlol_hostlane`
- `tx{lane_num}_eq_fault`
- `rx{lane_num}cdrlol`

**Example:**

The following fields related to `datapath_firmware_fault` are updated in the `redis-db` during a link change event:

- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG` table
- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` table
- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG_SET_TIME` table
- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` table

#### 5.2.3 Details of Flag Analysis of Tables

**Note**: For simplicity, this section uses DOM as an example. However, the same analysis is applicable for VDM and Status related flags as well.

**Purpose of Flag Analysis:**

The purpose of flag analysis is to track the status of various parameters and to count the number of times each DOM flag has changed. It also records the timestamp when each DOM flag was set and cleared.

**Tables Used for Flag Analysis:**

- `TRANSCEIVER_DOM_FLAG`: This table stores flags indicating the status of various DOM parameters.
- `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`: This table keeps a count of how many times each DOM flag has changed. Upon initialization of `xcvrd`, the count is set to 0.
- `TRANSCEIVER_DOM_FLAG_SET_TIME`: This table records the timestamp (in UTC timezone) when each DOM flag was set. The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`. During initialization, the timestamp is set to `never`. Since SONiC does not support flag-based interrupt handling, the timestamp refers to either:
  - The timestamp at which the link status was changed, or
  - The polling event timestamp if the flag was set during the routine polling by the `DomInfoUpdateTask` thread.
- `TRANSCEIVER_DOM_FLAG_CLEAR_TIME`: This table records the timestamp (in UTC timezone) when each DOM flag was cleared. The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`. During initialization, the timestamp is set to `never`. Since SONiC does not support flag-based interrupt handling, the timestamp refers to either:
  - The timestamp at which the link status was changed, or
  - The polling event timestamp if the flag was cleared during the routine polling by the `DomInfoUpdateTask` thread.

**Example of Table Updates:**

- **TRANSCEIVER_DOM_FLAG_CHANGE_COUNT:**
  - Each time a flag in the `TRANSCEIVER_DOM_FLAG` table changes (either set or cleared), the corresponding count in this table is incremented.
- **TRANSCEIVER_DOM_FLAG_SET_TIME:**
  - When a flag is set for the first time since it was cleared in the `TRANSCEIVER_DOM_FLAG` table, the relevant timestamp (in UTC timezone) is recorded in the corresponding value field of the table. Please note that this timestamp indicates when `xcvrd` detected the flag change, not the actual time when the module set the flag.
- **TRANSCEIVER_DOM_FLAG_CLEAR_TIME:**
  - When a flag is cleared for the first time since it was set in the `TRANSCEIVER_DOM_FLAG` table, the relevant timestamp (in UTC timezone) is recorded in the corresponding value field of the table. Please note that this timestamp indicates when `xcvrd` detected the flag change, not the actual time when the module cleared the flag.

##### 5.2.3.1 Flag Change Count and Time Set/Clear Behavior During `xcvrd` Restart

During `xcvrd` stop, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are deleted by the `xcvrd` process. When `xcvrd` is restarted, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are recreated and the flag change count and set/clear time are updated based on the current flag status (i.e. the value of these fields are not cached between `xcvrd` restarts).

##### 5.2.3.2 Flag Change Count and Time Set/Clear Behavior During Transceiver Removal and Insertion

When a transceiver is removed, `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are deleted by the `SfpStateUpdateTask` thread.

When the transceiver is inserted back, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are recreated through the periodic polling routine of `DomInfoUpdateTask` and the flag change count and set/clear time are updated based on the current flag status.

#### 5.2.4 Diagnostic Information Last Update Timestamp and Interval Period by `DomInfoUpdateTask`

All the diagnostic tables (except for the metadata tables storing change count and last set/clear time) contain the `last_update_time` field to capture the last update timestamp.
Specifically, the `TRANSCEIVER_STATUS` table contains the `diagnostics_update_interval` field to capture the interval period at which the diagnostic information is updated by the `DomInfoUpdateTask` thread for a port. This field is not present in the other diagnostic tables since the diagnostic information is updated for all ports in a sequential manner.

1. **`last_update_time`**:
   - This field records the timestamp (in UTC timezone) at which the corresponding diagnostic information was last updated by the `DomInfoUpdateTask` thread for a port.
   - The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`.

2. **`diagnostics_update_interval`**:
   - This field records the interval period (in seconds) at which the diagnostic information is updated by the `DomInfoUpdateTask` thread for a port.
   - Unlike the `dom_info_update_periodic_secs` value, this field is updated dynamically to reflect the actual time taken to update the diagnostic information for a port in the `redis-db`.
   - The time taken to read the diagnostic information from the transceiver can vary between successive polls based on:
     - Transceiver type
     - Number of diagnostic parameters supported by the transceiver
     - Device platform (which can affect I2C read/write speed)
     - Number of ports with transceivers plugged in
     - Number of ports in the breakout port group
     - Number of link change events between successive polls

#### Calculation of `diagnostics_update_interval`

Since diagnostic monitoring is a frequent event, retrieving the average diagnostic interval would require the `DomInfoUpdateTask` to maintain a large cache of last update times for every poll. To reduce the overhead of maintaining such a large cache, we use the Exponentially Weighted Moving Average (EWMA) to calculate the `diagnostics_update_interval`. This approach provides a smooth and responsive average of the update intervals, allowing us to store a single `diagnostics_update_interval` and retrieve the average diagnostic update interval efficiently. An alpha value of 0.1 is used for the EWMA calculation to provide a smooth average while still being responsive to changes in the udpate intervals.

**Formula:**

`EWMA = ALPHA * VALUE + (1 - ALPHA) * EWMA_last`

Where:

- `EMA` is the current `diagnostics_update_interval`.
- `VALUE` is the current update interval (time taken to read the diagnostic information).
- `EWMA_last` is the previous `diagnostics_update_interval`.
- `ALPHA` is the smoothing factor (0 < α ≤ 1).

**Steps:**

1. **Initial Update**: The `diagnostics_update_interval` is initially set to `0` during table creation.
2. **Subsequent Updates**: After the second diagnostic information update for a port, the `diagnostics_update_interval` is updated using the EWMA formula.
