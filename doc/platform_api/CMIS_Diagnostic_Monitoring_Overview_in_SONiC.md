# CMIS Diagnostic Monitoring Overview in SONiC

## 1. Overview

The CMIS (Common Management Interface Specification) diagnostic monitoring feature is a standard for monitoring the performance of optical transceivers. It provides a way to monitor the performance of optical transceivers in real time. SONiC periodically reads the diagnostic monitoring data from the optical transceivers and stores the data in the database. The data can be retrieved using the SONiC CLI or by querying the database directly.

The current scope of the CMIS diagnostic monitoring feature in SONiC includes the following parameters:

- **DOM (Digital Optical Monitoring) data:** Provides real-time monitoring of optical transceiver parameters such as temperature, voltage, and optical power.
- **VDM (Vendor Diagnostic Monitoring) data:** Offers vendor-specific diagnostic information for enhanced monitoring and troubleshooting.
- **PM (Performance Monitoring) data:** Applicable only for C-CMIS transceivers, this includes performance metrics such as error counts and signal quality indicators.

## 2. STATE_DB Schema for CMIS Diagnostic Monitoring

The CMIS diagnostic monitoring data is stored in the `STATE_DB` database. The `STATE_DB` schema for the CMIS diagnostic monitoring feature includes the following tables:

- `TRANSCEIVER_DOM_SENSOR`: Stores real-time DOM data for the optical transceivers.
- `TRANSCEIVER_DOM_THRESHOLD`: Contains threshold values for DOM parameters.
- `TRANSCEIVER_DOM_FLAG`: Stores flags indicating the status of various DOM parameters.
- `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each DOM flag has changed.
- `TRANSCEIVER_DOM_FLAG_TIME_SET`: Records the timestamp when each DOM flag was set.
- `TRANSCEIVER_DOM_FLAG_TIME_CLEAR`: Records the timestamp when each DOM flag was cleared.
- `TRANSCEIVER_VDM_SAMPLE`: Stores VDM sample data.
- `TRANSCEIVER_VDM_THRESHOLD`: Contains threshold values for VDM parameters.
- `TRANSCEIVER_VDM_FLAG`: Stores flags indicating the status of various VDM parameters.
- `TRANSCEIVER_VDM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each VDM flag has changed.
- `TRANSCEIVER_VDM_FLAG_TIME_SET`: Records the timestamp when each VDM flag was set.
- `TRANSCEIVER_VDM_FLAG_TIME_CLEAR`: Records the timestamp when each VDM flag was cleared.
- `TRANSCEIVER_PM`: Stores performance monitoring data.
- `TRANSCEIVER_PM_THRESHOLD`: Contains threshold values for PM parameters.
- `TRANSCEIVER_PM_FLAG`: Stores flags indicating the status of various PM parameters.
- `TRANSCEIVER_PM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each PM flag has changed.
- `TRANSCEIVER_PM_FLAG_TIME_SET`: Records the timestamp when each PM flag was set.
- `TRANSCEIVER_PM_FLAG_TIME_CLEAR`: Records the timestamp when each PM flag was cleared.
- `TRANSCEIVER_STATUS`: Stores the status data of the transceivers.

### 2.1 Transceiver DOM Sensor Data

The `TRANSCEIVER_DOM_SENSOR` table stores the real-time DOM data for the optical transceivers.

lane_num: Represents the lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver DOM sensor information for a port
    key                          = TRANSCEIVER_DOM_SENSOR|ifname    ; information module DOM sensors on port
    ; field                      = value
    temperature                  = FLOAT                            ; temperature value in Celsius
    voltage                      = FLOAT                            ; voltage value in V
    tx{lane_num}power            = FLOAT                            ; tx power in dBm for each lane
    rx{lane_num}power            = FLOAT                            ; rx power in dBm for each lane
    tx{lane_num}bias             = FLOAT                            ; tx bias in mA for each lane
    laser_temperature            = FLOAT                            ; laser temperature value in Celsius
```

### 2.2 Transceiver DOM threshold data

The `TRANSCEIVER_DOM_THRESHOLD` table stores the threshold values for the DOM data.

```plaintext
    ; Defines Transceiver DOM threshold info for a port
    key                          = TRANSCEIVER_DOM_THRESHOLD|ifname ; DOM threshold information for module on port
    ; field                      = value
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

### 2.3 Transceiver DOM flag data

The `TRANSCEIVER_DOM_FLAG` table stores the flag status for the DOM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flags for a port
    key                          = TRANSCEIVER_DOM_FLAG|ifname    ; information module DOM flags on port
    ; field                      = value
    temphighalarm_flag                    = BOOLEAN            ; temperature high alarm flag 
    temphighwarning_flag                  = BOOLEAN            ; temperature high warning flag
    templowalarm_flag                     = BOOLEAN            ; temperature low alarm flag
    templowwarning_flag                   = BOOLEAN            ; temperature low warning flag
    vcchighalarm_flag                     = BOOLEAN            ; vcc high alarm flag
    vcchighwarning_flag                   = BOOLEAN            ; vcc high warning flag
    vcclowalarm_flag                      = BOOLEAN            ; vcc low alarm flag
    vcclowwarning_flag                    = BOOLEAN            ; vcc low warning flag
    txpowerhighalarm_flag{lane_num}       = BOOLEAN            ; tx power high alarm flag
    txpowerlowalarm_flag{lane_num}        = BOOLEAN            ; tx power low alarm flag
    txpowerhighwarning_flag{lane_num}     = BOOLEAN            ; tx power high warning flag
    txpowerlowwarning_flag{lane_num}      = BOOLEAN            ; tx power low alarm flag
    rxpowerhighalarm_flag{lane_num}       = BOOLEAN            ; rx power high alarm flag
    rxpowerlowalarm_flag{lane_num}        = BOOLEAN            ; rx power low alarm flag
    rxpowerhighwarning_flag{lane_num}     = BOOLEAN            ; rx power high warning flag
    rxpowerlowwarning_flag{lane_num}      = BOOLEAN            ; rx power low warning flag
    txbiashighalarm_flag{lane_num}        = BOOLEAN            ; tx bias high alarm flag
    txbiaslowalarm_flag{lane_num}         = BOOLEAN            ; tx bias low alarm flag
    txbiashighwarning_flag{lane_num}      = BOOLEAN            ; tx bias high warning flag
    txbiaslowwarning_flag{lane_num}       = BOOLEAN            ; tx bias low warning flag
    lasertemphighalarm_flag               = BOOLEAN            ; laser temperature high alarm flag
    lasertemplowalarm_flag                = BOOLEAN            ; laser temperature low alarm flag
    lasertemphighwarning_flag             = BOOLEAN            ; laser temperature high warning flag
    lasertemplowwarning_flag              = BOOLEAN            ; laser temperature low warning flag

    txfault{lane_num}                     = BOOLEAN            ; tx fault flag on media lane {lane_num}
    txlos_hostlane{lane_num}              = BOOLEAN            ; tx loss of signal flag on host lane {lane_num}
    txcdrlol_hostlane{lane_num}           = BOOLEAN            ; tx clock and data recovery loss of lock flag on host lane {lane_num}
    tx_eq_fault{lane_num}                 = BOOLEAN            ; tx equalization fault flag on host lane {lane_num}
    rxlos{lane_num}                       = BOOLEAN            ; rx loss of signal flag on media lane {lane_num}
    rxcdrlol{lane_num}                    = BOOLEAN            ; rx clock and data recovery loss of lock flag on media lane {lane_num}
```

### 2.4 Transceiver DOM flag change count data

The `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table stores the flag change count for the DOM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag change count for a port
    key                              = TRANSCEIVER_DOM_FLAG_CHANGE|ifname   ; information module DOM flags change count on port
    ; field                          = value
    temphighalarm_change_count                 = INTEGER           ; temperature high alarm change count
    temphighwarning_change_count               = INTEGER           ; temperature high warning change count
    templowalarm_change_count                  = INTEGER           ; temperature low alarm change count
    templowwarning_change_count                = INTEGER           ; temperature low warning change count
    vcchighalarm_change_count                  = INTEGER           ; vcc high alarm change count
    vcchighwarning_change_count                = INTEGER           ; vcc high warning change count
    vcclowalarm_change_count                   = INTEGER           ; vcc low alarm change count
    vcclowwarning_change_count                 = INTEGER           ; vcc low warning change count
    txpowerhighalarm_change_count{lane_num}    = INTEGER           ; tx power high alarm change count
    txpowerlowalarm_change_count{lane_num}     = INTEGER           ; tx power low alarm change count
    txpowerhighwarning_change_count{lane_num}  = INTEGER           ; tx power high warning change count
    txpowerlowwarning_change_count{lane_num}   = INTEGER           ; tx power low alarm change count
    rxpowerhighalarm_change_count{lane_num}    = INTEGER           ; rx power high alarm change count
    rxpowerlowalarm_change_count{lane_num}     = INTEGER           ; rx power low alarm change count
    rxpowerhighwarning_change_count{lane_num}  = INTEGER           ; rx power high warning change count
    rxpowerlowwarning_change_count{lane_num}   = INTEGER           ; rx power low warning change count
    txbiashighalarm_change_count{lane_num}     = INTEGER           ; tx bias high alarm change count
    txbiaslowalarm_change_count{lane_num}      = INTEGER           ; tx bias low alarm change count
    txbiashighwarning_change_count{lane_num}   = INTEGER           ; tx bias high warning change count
    txbiaslowwarning_change_count{lane_num}    = INTEGER           ; tx bias low warning change count
    lasertemphighalarm_change_count            = INTEGER           ; laser temperature high alarm change count
    lasertemplowalarm_change_count             = INTEGER           ; laser temperature low alarm change count
    lasertemphighwarning_change_count          = INTEGER           ; laser temperature high warning change count
    lasertemplowwarning_change_count           = INTEGER           ; laser temperature low warning change count

    txfault_change_count{lane_num}             = INTEGER           ; tx fault change count on media lane {lane_num}
    txlos_hostlane_change_count{lane_num}      = INTEGER           ; tx loss of signal change count on host lane {lane_num}
    txcdrlol_hostlane_change_count{lane_num}   = INTEGER           ; tx clock and data recovery loss of lock change count on host lane {lane_num}
    tx_eq_fault_change_count{lane_num}         = INTEGER           ; tx equalization fault change count on host lane {lane_num}
    rxlos_change_count{lane_num}               = INTEGER           ; rx loss of signal change count on media lane {lane_num}
    rxcdrlol_change_count{lane_num}            = INTEGER           ; rx clock and data recovery loss of lock change count on media lane {lane_num}
```

### 2.5 Transceiver DOM flag time set data

The `TRANSCEIVER_DOM_FLAG_TIME_SET` table stores the last set time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time set for a port
    key                          = TRANSCEIVER_DOM_FLAG_TIME_SET|ifname   ; information module DOM flag time set on port
    ; field                      = value
    temphighalarm_last_set_time                 = STR           ; temperature high alarm last set time
    temphighwarning_last_set_time               = STR           ; temperature high warning last set time
    templowalarm_last_set_time                  = STR           ; temperature low alarm last set time
    templowwarning_last_set_time                = STR           ; temperature low warning last set time
    vcchighalarm_last_set_time                  = STR           ; vcc high alarm last set time
    vcchighwarning_last_set_time                = STR           ; vcc high warning last set time
    vcclowalarm_last_set_time                   = STR           ; vcc low alarm last set time
    vcclowwarning_last_set_time                 = STR           ; vcc low warning last set time
    txpowerhighalarm_last_set_time{lane_num}    = STR           ; tx power high alarm last set time
    txpowerlowalarm_last_set_time{lane_num}     = STR           ; tx power low alarm last set time
    txpowerhighwarning_last_set_time{lane_num}  = STR           ; tx power high warning last set time
    txpowerlowwarning_last_set_time{lane_num}   = STR           ; tx power low warning last set time
    rxpowerhighalarm_last_set_time{lane_num}    = STR           ; rx power high alarm last set time
    rxpowerlowalarm_last_set_time{lane_num}     = STR           ; rx power low alarm last set time
    rxpowerhighwarning_last_set_time{lane_num}  = STR           ; rx power high warning last set time
    rxpowerlowwarning_last_set_time{lane_num}   = STR           ; rx power low warning last set time
    txbiashighalarm_last_set_time{lane_num}     = STR           ; tx bias high alarm last set time
    txbiaslowalarm_last_set_time{lane_num}      = STR           ; tx bias low alarm last set time
    txbiashighwarning_last_set_time{lane_num}   = STR           ; tx bias high warning last set time
    txbiaslowwarning_last_set_time{lane_num}    = STR           ; tx bias low warning last set time
    lasertemphighalarm_last_set_time            = STR           ; laser temperature high alarm last set time
    lasertemplowalarm_last_set_time             = STR           ; laser temperature low alarm last set time
    lasertemphighwarning_last_set_time          = STR           ; laser temperature high warning last set time
    lasertemplowwarning_last_set_time           = STR           ; laser temperature low warning last set time

    txfault_last_set_time{lane_num}             = STR           ; tx fault last set time on media lane {lane_num}
    txlos_hostlane_last_set_time{lane_num}      = STR           ; tx loss of signal last set time on host lane {lane_num}
    txcdrlol_hostlane_last_set_time{lane_num}   = STR           ; tx clock and data recovery loss of lock last set time on host lane {lane_num}
    tx_eq_fault_last_set_time{lane_num}         = STR           ; tx equalization fault last set time on host lane {lane_num}
    rxlos_last_set_time{lane_num}               = STR           ; rx loss of signal last set time on media lane {lane_num}
    rxcdrlol_last_set_time{lane_num}            = STR           ; rx clock and data recovery loss of lock last set time on media lane {lane_num}
```

### 2.6 Transceiver DOM flag time clear data

The `TRANSCEIVER_DOM_FLAG_TIME_CLEAR` table stores the last clear time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time clear for a port
    key                          = TRANSCEIVER_DOM_FLAG_TIME_CLEAR|ifname  ; information module DOM flag time clear on port
    ; field                      = value
    temphighalarm_last_clear_time                = STR          ; temperature high alarm last clear time
    temphighwarning_last_clear_time              = STR          ; temperature high warning last clear time
    templowalarm_last_clear_time                 = STR          ; temperature low alarm last clear time
    templowwarning_last_clear_time               = STR          ; temperature low warning last clear time
    vcchighalarm_last_clear_time                 = STR          ; vcc high alarm last clear time
    vcchighwarning_last_clear_time               = STR          ; vcc high warning last clear time
    vcclowalarm_last_clear_time                  = STR          ; vcc low alarm last clear time
    vcclowwarning_last_clear_time                = STR          ; vcc low warning last clear time
    txpowerhighalarm_last_clear_time{lane_num}   = STR          ; tx power high alarm last clear time
    txpowerlowalarm_last_clear_time{lane_num}    = STR          ; tx power low alarm last clear time
    txpowerhighwarning_last_clear_time{lane_num} = STR          ; tx power high warning last clear time
    txpowerlowwarning_last_clear_time{lane_num}  = STR          ; tx power low warning last clear time
    rxpowerhighalarm_last_clear_time{lane_num}   = STR          ; rx power high alarm last clear time
    rxpowerlowalarm_last_clear_time{lane_num}    = STR          ; rx power low alarm last clear time
    rxpowerhighwarning_last_clear_time{lane_num} = STR          ; rx power high warning last clear time
    rxpowerlowwarning_last_clear_time{lane_num}  = STR          ; rx power low warning last clear time
    txbiashighalarm_last_clear_time{lane_num}    = STR          ; tx bias high alarm last clear time
    txbiaslowalarm_last_clear_time{lane_num}     = STR          ; tx bias low alarm last clear time
    txbiashighwarning_last_clear_time{lane_num}  = STR          ; tx bias high warning last clear time
    txbiaslowwarning_last_clear_time{lane_num}   = STR          ; tx bias low warning last clear time
    lasertemphighalarm_last_clear_time           = STR          ; laser temperature high alarm last clear time
    lasertemplowalarm_last_clear_time            = STR          ; laser temperature low alarm last clear time
    lasertemphighwarning_last_clear_time         = STR          ; laser temperature high warning last clear time
    lasertemplowwarning_last_clear_time          = STR          ; laser temperature low warning last clear time

    txfault_last_clear_time{lane_num}            = STR          ; tx fault last clear time on media lane {lane_num}
    txlos_hostlane_last_clear_time{lane_num}     = STR          ; tx loss of signal last clear time on host lane {lane_num}
    txcdrlol_hostlane_last_clear_time{lane_num}  = STR          ; tx clock and data recovery loss of lock last clear time on host lane {lane_num}
    tx_eq_fault_last_clear_time{lane_num}        = STR          ; tx equalization fault last clear time on host lane {lane_num}
    rxlos_last_clear_time{lane_num}              = STR          ; rx loss of signal last clear time on media lane {lane_num}
    rxcdrlol_last_clear_time{lane_num}           = STR          ; rx clock and data recovery loss of lock last clear time on media lane {lane_num}
```

### 2.7 Transceiver VDM sample data

The `TRANSCEIVER_VDM_SAMPLE` table stores the real time VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM sample for a port
    key                                            = TRANSCEIVER_VDM_SAMPLE|ifname    ; information module VDM sample on port
    ; field                                        = value
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
```

### 2.8 Transceiver VDM threshold data

The `TRANSCEIVER_VDM_THRESHOLD` table stores the threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM sample for a port
    key                                            = TRANSCEIVER_VDM_THRESHOLD|ifname    ; information module VDM sample on port
    ; field                                        = value
    esnr_media_input_highalarm{lane_num}           = FLOAT                  ; eSNR high alarm value in dB for media input
    esnr_media_input_lowalarm{lane_num}            = FLOAT                  ; eSNR low alarm value in dB for media input
    esnr_media_input_highwarning{lane_num}         = FLOAT                  ; eSNR high warning value in dB for media input
    esnr_media_input_lowwarning{lane_num}          = FLOAT                  ; eSNR low warning value in dB for media input
    esnr_host_input_highalarm{lane_num}            = FLOAT                  ; eSNR high alarm value in dB for host input
    esnr_host_input_lowalarm{lane_num}             = FLOAT                  ; eSNR low alarm value in dB for host input
    esnr_host_input_highwarning{lane_num}          = FLOAT                  ; eSNR high warning value in dB for host input
    esnr_host_input_lowwarning{lane_num}           = FLOAT                  ; eSNR low warning value in dB for host input
    pam4_level_transition_media_input_highalarm{lane_num} = FLOAT          ; PAM4 level transition high alarm value in dB for media input
    pam4_level_transition_media_input_lowalarm{lane_num}  = FLOAT          ; PAM4 level transition low alarm value in dB for media input
    pam4_level_transition_media_input_highwarning{lane_num} = FLOAT       ; PAM4 level transition high warning value in dB for media input
    pam4_level_transition_media_input_lowwarning{lane_num}  = FLOAT          ; PAM4 level transition low warning value in dB for media input
    pam4_level_transition_host_input_highalarm{lane_num}    = FLOAT          ; PAM4 level transition high alarm value in dB for host input
    pam4_level_transition_host_input_lowalarm{lane_num}     = FLOAT          ; PAM4 level transition low alarm value in dB for host input
    pam4_level_transition_host_input_highwarning{lane_num}  = FLOAT          ; PAM4 level transition high warning value in dB for host input
    pam4_level_transition_host_input_lowwarning{lane_num}   = FLOAT          ; PAM4 level transition low warning value in dB for host input
    prefec_ber_min_media_input_highalarm{lane_num}          = FLOAT          ; Pre-FEC BER minimum high alarm value for media input
    prefec_ber_min_media_input_lowalarm{lane_num}           = FLOAT          ; Pre-FEC BER minimum low alarm value for media input
    prefec_ber_min_media_input_highwarning{lane_num}        = FLOAT          ; Pre-FEC BER minimum high warning value for media input
    prefec_ber_min_media_input_lowwarning{lane_num}         = FLOAT          ; Pre-FEC BER minimum low warning value for media input
    prefec_ber_max_media_input_highalarm{lane_num}          = FLOAT          ; Pre-FEC BER maximum high alarm value for media input
    prefec_ber_max_media_input_lowalarm{lane_num}           = FLOAT          ; Pre-FEC BER maximum low alarm value for media input
    prefec_ber_max_media_input_highwarning{lane_num}        = FLOAT          ; Pre-FEC BER maximum high warning value for media input
    prefec_ber_max_media_input_lowwarning{lane_num}         = FLOAT          ; Pre-FEC BER maximum low warning value for media input
    prefec_ber_avg_media_input_highalarm{lane_num}          = FLOAT          ; Pre-FEC BER average high alarm value for media input
    prefec_ber_avg_media_input_lowalarm{lane_num}           = FLOAT          ; Pre-FEC BER average low alarm value for media input
    prefec_ber_avg_media_input_highwarning{lane_num}        = FLOAT          ; Pre-FEC BER average high warning value for media input
    prefec_ber_avg_media_input_lowwarning{lane_num}         = FLOAT          ; Pre-FEC BER average low warning value for media input
    prefec_ber_curr_media_input_highalarm{lane_num}         = FLOAT          ; Pre-FEC BER current high alarm value for media input
    prefec_ber_curr_media_input_lowalarm{lane_num}          = FLOAT          ; Pre-FEC BER current low alarm value for media input
    prefec_ber_curr_media_input_highwarning{lane_num}       = FLOAT          ; Pre-FEC BER current high warning value for media input
    prefec_ber_curr_media_input_lowwarning{lane_num}        = FLOAT          ; Pre-FEC BER current low warning value for media input
    prefec_ber_min_host_input_highalarm{lane_num}           = FLOAT          ; Pre-FEC BER minimum high alarm value for host input
    prefec_ber_min_host_input_lowalarm{lane_num}            = FLOAT          ; Pre-FEC BER minimum low alarm value for host input
    prefec_ber_min_host_input_highwarning{lane_num}         = FLOAT          ; Pre-FEC BER minimum high warning value for host input
    prefec_ber_min_host_input_lowwarning{lane_num}          = FLOAT          ; Pre-FEC BER minimum low warning value for host input
    prefec_ber_max_host_input_highalarm{lane_num}           = FLOAT          ; Pre-FEC BER maximum high alarm value for host input
    prefec_ber_max_host_input_lowalarm{lane_num}            = FLOAT          ; Pre-FEC BER maximum low alarm value for host input
    prefec_ber_max_host_input_highwarning{lane_num}         = FLOAT          ; Pre-FEC BER maximum high warning value for host input
    prefec_ber_max_host_input_lowwarning{lane_num}          = FLOAT          ; Pre-FEC BER maximum low warning value for host input
    prefec_ber_avg_host_input_highalarm{lane_num}           = FLOAT          ; Pre-FEC BER average high alarm value for host input
    prefec_ber_avg_host_input_lowalarm{lane_num}            = FLOAT          ; Pre-FEC BER average low alarm value for host input
    prefec_ber_avg_host_input_highwarning{lane_num}         = FLOAT          ; Pre-FEC BER average high warning value for host input
    prefec_ber_avg_host_input_lowwarning{lane_num}          = FLOAT          ; Pre-FEC BER average low warning value for host input
    prefec_ber_curr_host_input_highalarm{lane_num}          = FLOAT          ; Pre-FEC BER current high alarm value for host input
    prefec_ber_curr_host_input_lowalarm{lane_num}           = FLOAT          ; Pre-FEC BER current low alarm value for host input
    prefec_ber_curr_host_input_highwarning{lane_num}        = FLOAT          ; Pre-FEC BER current high warning value for host input
    prefec_ber_curr_host_input_lowwarning{lane_num}         = FLOAT          ; Pre-FEC BER current low warning value for host input
    errored_frames_min_media_input_highalarm{lane_num}      = FLOAT          ; Errored frames minimum high alarm value for media input
    errored_frames_min_media_input_lowalarm{lane_num}       = FLOAT          ; Errored frames minimum low alarm value for media input
    errored_frames_min_media_input_highwarning{lane_num}    = FLOAT          ; Errored frames minimum high warning value for media input
    errored_frames_min_media_input_lowwarning{lane_num}     = FLOAT          ; Errored frames minimum low warning value for media input
    errored_frames_max_media_input_highalarm{lane_num}      = FLOAT          ; Errored frames maximum high alarm value for media input
    errored_frames_max_media_input_lowalarm{lane_num}       = FLOAT          ; Errored frames maximum low alarm value for media input
    errored_frames_max_media_input_highwarning{lane_num}    = FLOAT          ; Errored frames maximum high warning value for media input
    errored_frames_max_media_input_lowwarning{lane_num}     = FLOAT          ; Errored frames maximum low warning value for media input
    errored_frames_avg_media_input_highalarm{lane_num}      = FLOAT          ; Errored frames average high alarm value for media input
    errored_frames_avg_media_input_lowalarm{lane_num}       = FLOAT          ; Errored frames average low alarm value for media input
    errored_frames_avg_media_input_highwarning{lane_num}    = FLOAT          ; Errored frames average high warning value for media input
    errored_frames_avg_media_input_lowwarning{lane_num}     = FLOAT          ; Errored frames average low warning value for media input
    errored_frames_curr_media_input_highalarm{lane_num}     = FLOAT          ; Errored frames current high alarm value for media input
    errored_frames_curr_media_input_lowalarm{lane_num}      = FLOAT          ; Errored frames current low alarm value for media input
    errored_frames_curr_media_input_highwarning{lane_num}   = FLOAT          ; Errored frames current high warning value for media input
    errored_frames_curr_media_input_lowwarning{lane_num}    = FLOAT          ; Errored frames current low warning value for media input
    errored_frames_min_host_input_highalarm{lane_num}       = FLOAT          ; Errored frames minimum high alarm value for host input
    errored_frames_min_host_input_lowalarm{lane_num}        = FLOAT          ; Errored frames minimum low alarm value for host input
    errored_frames_min_host_input_highwarning{lane_num}     = FLOAT          ; Errored frames minimum high warning value for host input
    errored_frames_min_host_input_lowwarning{lane_num}      = FLOAT          ; Errored frames minimum low warning value for host input
    errored_frames_max_host_input_highalarm{lane_num}       = FLOAT          ; Errored frames maximum high alarm value for host input
    errored_frames_max_host_input_lowalarm{lane_num}        = FLOAT          ; Errored frames maximum low alarm value for host input
    errored_frames_max_host_input_highwarning{lane_num}     = FLOAT          ; Errored frames maximum high warning value for host input
    errored_frames_max_host_input_lowwarning{lane_num}      = FLOAT          ; Errored frames maximum low warning value for host input
    errored_frames_avg_host_input_highalarm{lane_num}       = FLOAT          ; Errored frames average high alarm value for host input
    errored_frames_avg_host_input_lowalarm{lane_num}        = FLOAT          ; Errored frames average low alarm value for host input
    errored_frames_avg_host_input_highwarning{lane_num}     = FLOAT          ; Errored frames average high warning value for host input
    errored_frames_avg_host_input_lowwarning{lane_num}      = FLOAT          ; Errored frames average low warning value for host input
    errored_frames_curr_host_input_highalarm{lane_num}      = FLOAT          ; Errored frames current high alarm value for host input
    errored_frames_curr_host_input_lowalarm{lane_num}       = FLOAT          ; Errored frames current low alarm value for host input
    errored_frames_curr_host_input_highwarning{lane_num}    = FLOAT          ; Errored frames current high warning value for host input
    errored_frames_curr_host_input_lowwarning{lane_num}     = FLOAT          ; Errored frames current low warning value for host input

### 2.9 Transceiver VDM flag data

The `TRANSCEIVER_VDM_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

    ;Defines Transceiver VDM flag for a port
    key                          = TRANSCEIVER_VDM_FLAG|ifname    ; information module VDM flag on port
    ; field                      = value
    esnr_media_input_highalarm_flag{lane_num}           = BOOLEAN          ; eSNR high alarm flag for media input
    esnr_media_input_lowalarm_flag{lane_num}            = BOOLEAN          ; eSNR low alarm flag for media input
    esnr_media_input_highwarning_flag{lane_num}         = BOOLEAN          ; eSNR high warning flag for media input
    esnr_media_input_lowwarning_flag{lane_num}          = BOOLEAN          ; eSNR low warning flag for media input
    esnr_host_input_highalarm_flag{lane_num}            = BOOLEAN          ; eSNR high alarm flag for host input
    esnr_host_input_lowalarm_flag{lane_num}             = BOOLEAN          ; eSNR low alarm flag for host input
    esnr_host_input_highwarning_flag{lane_num}          = BOOLEAN          ; eSNR high warning flag for host input
    esnr_host_input_lowwarning_flag{lane_num}           = BOOLEAN          ; eSNR low warning flag for host input
    pam4_level_transition_media_input_highalarm_flag{lane_num} = BOOLEAN  ; PAM4 level transition high alarm flag for media input
    pam4_level_transition_media_input_lowalarm_flag{lane_num}  = BOOLEAN  ; PAM4 level transition low alarm flag for media input
    pam4_level_transition_media_input_highwarning_flag{lane_num} = BOOLEAN ; PAM4 level transition high warning flag for media input
    pam4_level_transition_media_input_lowwarning_flag{lane_num}  = BOOLEAN ; PAM4 level transition low warning flag for media input
    pam4_level_transition_host_input_highalarm_flag{lane_num}    = BOOLEAN ; PAM4 level transition high alarm flag for host input
    pam4_level_transition_host_input_lowalarm_flag{lane_num}     = BOOLEAN ; PAM4 level transition low alarm flag for host input
    pam4_level_transition_host_input_highwarning_flag{lane_num}  = BOOLEAN ; PAM4 level transition high warning flag for host input
    pam4_level_transition_host_input_lowwarning_flag{lane_num}   = BOOLEAN ; PAM4 level transition low warning flag for host input
    prefec_ber_min_media_input_highalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high alarm flag for media input
    prefec_ber_min_media_input_lowalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low alarm flag for media input
    prefec_ber_min_media_input_highwarning_flag{lane_num}        = BOOLEAN ; Pre-FEC BER minimum high warning flag for media input
    prefec_ber_min_media_input_lowwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER minimum low warning flag for media input
    prefec_ber_max_media_input_highalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high alarm flag for media input
    prefec_ber_max_media_input_lowalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low alarm flag for media input
    prefec_ber_max_media_input_highwarning_flag{lane_num}        = BOOLEAN ; Pre-FEC BER maximum high warning flag for media input
    prefec_ber_max_media_input_lowwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER maximum low warning flag for media input
    prefec_ber_avg_media_input_highalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER average high alarm flag for media input
    prefec_ber_avg_media_input_lowalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER average low alarm flag for media input
    prefec_ber_avg_media_input_highwarning_flag{lane_num}        = BOOLEAN ; Pre-FEC BER average high warning flag for media input
    prefec_ber_avg_media_input_lowwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER average low warning flag for media input
    prefec_ber_curr_media_input_highalarm_flag{lane_num}         = BOOLEAN ; Pre-FEC BER current high alarm flag for media input
    prefec_ber_curr_media_input_lowalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER current low alarm flag for media input
    prefec_ber_curr_media_input_highwarning_flag{lane_num}       = BOOLEAN ; Pre-FEC BER current high warning flag for media input
    prefec_ber_curr_media_input_lowwarning_flag{lane_num}        = BOOLEAN ; Pre-FEC BER current low warning flag for media input
    prefec_ber_min_host_input_highalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high alarm flag for host input
    prefec_ber_min_host_input_lowalarm_flag{lane_num}            = BOOLEAN ; Pre-FEC BER minimum low alarm flag for host input
    prefec_ber_min_host_input_highwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER minimum high warning flag for host input
    prefec_ber_min_host_input_lowwarning_flag{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low warning flag for host input
    prefec_ber_max_host_input_highalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high alarm flag for host input
    prefec_ber_max_host_input_lowalarm_flag{lane_num}            = BOOLEAN ; Pre-FEC BER maximum low alarm flag for host input
    prefec_ber_max_host_input_highwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER maximum high warning flag for host input
    prefec_ber_max_host_input_lowwarning_flag{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low warning flag for host input
    prefec_ber_avg_host_input_highalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER average high alarm flag for host input
    prefec_ber_avg_host_input_lowalarm_flag{lane_num}            = BOOLEAN ; Pre-FEC BER average low alarm flag for host input
    prefec_ber_avg_host_input_highwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER average high warning flag for host input
    prefec_ber_avg_host_input_lowwarning_flag{lane_num}          = BOOLEAN ; Pre-FEC BER average low warning flag for host input
    prefec_ber_curr_host_input_highalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER current high alarm flag for host input
    prefec_ber_curr_host_input_lowalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER current low alarm flag for host input
    prefec_ber_curr_host_input_highwarning_flag{lane_num}        = BOOLEAN ; Pre-FEC BER current high warning flag for host input
    prefec_ber_curr_host_input_lowwarning_flag{lane_num}         = BOOLEAN ; Pre-FEC BER current low warning flag for host input
    errored_frames_min_media_input_highalarm_flag{lane_num}      = BOOLEAN ; Errored frames minimum high alarm flag for media input
    errored_frames_min_media_input_lowalarm_flag{lane_num}       = BOOLEAN ; Errored frames minimum low alarm flag for media input
    errored_frames_min_media_input_highwarning_flag{lane_num}    = BOOLEAN ; Errored frames minimum high warning flag for media input
    errored_frames_min_media_input_lowwarning_flag{lane_num}     = BOOLEAN ; Errored frames minimum low warning flag for media input
    errored_frames_max_media_input_highalarm_flag{lane_num}      = BOOLEAN ; Errored frames maximum high alarm flag for media input
    errored_frames_max_media_input_lowalarm_flag{lane_num}       = BOOLEAN ; Errored frames maximum low alarm flag for media input
    errored_frames_max_media_input_highwarning_flag{lane_num}    = BOOLEAN ; Errored frames maximum high warning flag for media input
    errored_frames_max_media_input_lowwarning_flag{lane_num}     = BOOLEAN ; Errored frames maximum low warning flag for media input
    errored_frames_avg_media_input_highalarm_flag{lane_num}      = BOOLEAN ; Errored frames average high alarm flag for media input
    errored_frames_avg_media_input_lowalarm_flag{lane_num}       = BOOLEAN ; Errored frames average low alarm flag for media input
    errored_frames_avg_media_input_highwarning_flag{lane_num}    = BOOLEAN ; Errored frames average high warning flag for media input
    errored_frames_avg_media_input_lowwarning_flag{lane_num}     = BOOLEAN ; Errored frames average low warning flag for media input
    errored_frames_curr_media_input_highalarm_flag{lane_num}     = BOOLEAN ; Errored frames current high alarm flag for media input
    errored_frames_curr_media_input_lowalarm_flag{lane_num}      = BOOLEAN ; Errored frames current low alarm flag for media input
    errored_frames_curr_media_input_highwarning_flag{lane_num}   = BOOLEAN ; Errored frames current high warning flag for media input
    errored_frames_curr_media_input_lowwarning_flag{lane_num}    = BOOLEAN ; Errored frames current low warning flag for media input
    errored_frames_min_host_input_highalarm_flag{lane_num}       = BOOLEAN ; Errored frames minimum high alarm flag for host input
    errored_frames_min_host_input_lowalarm_flag{lane_num}        = BOOLEAN ; Errored frames minimum low alarm flag for host input
    errored_frames_min_host_input_highwarning_flag{lane_num}     = BOOLEAN ; Errored frames minimum high warning flag for host input
    errored_frames_min_host_input_lowwarning_flag{lane_num}      = BOOLEAN ; Errored frames minimum low warning flag for host input
    errored_frames_max_host_input_highalarm_flag{lane_num}       = BOOLEAN ; Errored frames maximum high alarm flag for host input
    errored_frames_max_host_input_lowalarm_flag{lane_num}        = BOOLEAN ; Errored frames maximum low alarm flag for host input
    errored_frames_max_host_input_highwarning_flag{lane_num}     = BOOLEAN ; Errored frames maximum high warning flag for host input
    errored_frames_max_host_input_lowwarning_flag{lane_num}      = BOOLEAN ; Errored frames maximum low warning flag for host input
    errored_frames_avg_host_input_highalarm_flag{lane_num}       = BOOLEAN ; Errored frames average high alarm flag for host input
    errored_frames_avg_host_input_lowalarm_flag{lane_num}        = BOOLEAN ; Errored frames average low alarm flag for host input
    errored_frames_avg_host_input_highwarning_flag{lane_num}     = BOOLEAN ; Errored frames average high warning flag for host input
    errored_frames_avg_host_input_lowwarning_flag{lane_num}      = BOOLEAN ; Errored frames average low warning flag for host input
    errored_frames_curr_host_input_highalarm_flag{lane_num}      = BOOLEAN ; Errored frames current high alarm flag for host input
    errored_frames_curr_host_input_lowalarm_flag{lane_num}       = BOOLEAN ; Errored frames current low alarm flag for host input
    errored_frames_curr_host_input_highwarning_flag{lane_num}    = BOOLEAN ; Errored frames current high warning flag for host input
    errored_frames_curr_host_input_lowwarning_flag{lane_num}     = BOOLEAN ; Errored frames current low warning flag for host input
```

### 2.10 Transceiver VDM flag change count data

The `TRANSCEIVER_VDM_FLAG_CHANGE_COUNT` table stores the flag change count for the VDM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM flag change count for a port
    key                                            = TRANSCEIVER_VDM_FLAG_CHANGE_COUNT|ifname    ; information module VDM flags change count on port
    ; field                                        = value
    esnr_media_input_highalarm_change_count{lane_num}           = INTEGER          ; eSNR high alarm change count for media input
    esnr_media_input_lowalarm_change_count{lane_num}            = INTEGER          ; eSNR low alarm change count for media input
    esnr_media_input_highwarning_change_count{lane_num}         = INTEGER          ; eSNR high warning change count for media input
    esnr_media_input_lowwarning_change_count{lane_num}          = INTEGER          ; eSNR low warning change count for media input
    esnr_host_input_highalarm_change_count{lane_num}            = INTEGER          ; eSNR high alarm change count for host input
    esnr_host_input_lowalarm_change_count{lane_num}             = INTEGER          ; eSNR low alarm change count for host input
    esnr_host_input_highwarning_change_count{lane_num}          = INTEGER          ; eSNR high warning change count for host input
    esnr_host_input_lowwarning_change_count{lane_num}           = INTEGER          ; eSNR low warning change count for host input
    pam4_level_transition_media_input_highalarm_change_count{lane_num} = INTEGER  ; PAM4 level transition high alarm change count for media input
    pam4_level_transition_media_input_lowalarm_change_count{lane_num}  = INTEGER  ; PAM4 level transition low alarm change count for media input
    pam4_level_transition_media_input_highwarning_change_count{lane_num} = INTEGER ; PAM4 level transition high warning change count for media input
    pam4_level_transition_media_input_lowwarning_change_count{lane_num}  = INTEGER ; PAM4 level transition low warning change count for media input
    pam4_level_transition_host_input_highalarm_change_count{lane_num}    = INTEGER ; PAM4 level transition high alarm change count for host input
    pam4_level_transition_host_input_lowalarm_change_count{lane_num}     = INTEGER ; PAM4 level transition low alarm change count for host input
    pam4_level_transition_host_input_highwarning_change_count{lane_num}  = INTEGER ; PAM4 level transition high warning change count
    pam4_level_transition_host_input_lowwarning_change_count{lane_num}   = INTEGER ; PAM4 level transition low warning change count for host input
    prefec_ber_min_media_input_highalarm_change_count{lane_num}          = INTEGER ; Pre-FEC BER minimum high alarm change count for media input
    prefec_ber_min_media_input_lowalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER minimum low alarm change count for media input
    prefec_ber_min_media_input_highwarning_change_count{lane_num}        = INTEGER ; Pre-FEC BER minimum high warning change count for media input
    prefec_ber_min_media_input_lowwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER minimum low warning change count for media input
    prefec_ber_max_media_input_highalarm_change_count{lane_num}          = INTEGER ; Pre-FEC BER maximum high alarm change count for media input
    prefec_ber_max_media_input_lowalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER maximum low alarm change count for media input
    prefec_ber_max_media_input_highwarning_change_count{lane_num}        = INTEGER ; Pre-FEC BER maximum high warning change count for media input
    prefec_ber_max_media_input_lowwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER maximum low warning change count for media input
    prefec_ber_avg_media_input_highalarm_change_count{lane_num}          = INTEGER ; Pre-FEC BER average high alarm change count for media input
    prefec_ber_avg_media_input_lowalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER average low alarm change count for media input
    prefec_ber_avg_media_input_highwarning_change_count{lane_num}        = INTEGER ; Pre-FEC BER average high warning change count for media input
    prefec_ber_avg_media_input_lowwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER average low warning change count for media input
    prefec_ber_curr_media_input_highalarm_change_count{lane_num}         = INTEGER ; Pre-FEC BER current high alarm change count for media input
    prefec_ber_curr_media_input_lowalarm_change_count{lane_num}          = INTEGER ; Pre-FEC BER current low alarm change count for media input
    prefec_ber_curr_media_input_highwarning_change_count{lane_num}       = INTEGER ; Pre-FEC BER current high warning change count for media input
    prefec_ber_curr_media_input_lowwarning_change_count{lane_num}        = INTEGER ; Pre-FEC BER current low warning change count for media input
    prefec_ber_min_host_input_highalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER minimum high alarm change count for host input
    prefec_ber_min_host_input_lowalarm_change_count{lane_num}            = INTEGER ; Pre-FEC BER minimum low alarm change count for host input
    prefec_ber_min_host_input_highwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER minimum high warning change count for host input
    prefec_ber_min_host_input_lowwarning_change_count{lane_num}          = INTEGER ; Pre-FEC BER minimum low warning change count for host input
    prefec_ber_max_host_input_highalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER maximum high alarm change count for host input
    prefec_ber_max_host_input_lowalarm_change_count{lane_num}            = INTEGER ; Pre-FEC BER maximum low alarm change count for host input
    prefec_ber_max_host_input_highwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER maximum high warning change count for host input
    prefec_ber_max_host_input_lowwarning_change_count{lane_num}          = INTEGER ; Pre-FEC BER maximum low warning change count for host input
    prefec_ber_avg_host_input_highalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER average high alarm change count for host input
    prefec_ber_avg_host_input_lowalarm_change_count{lane_num}            = INTEGER ; Pre-FEC BER average low alarm change count for host input
    prefec_ber_avg_host_input_highwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER average high warning change count for host input
    prefec_ber_avg_host_input_lowwarning_change_count{lane_num}          = INTEGER ; Pre-FEC BER average low warning change count for host input
    prefec_ber_curr_host_input_highalarm_change_count{lane_num}          = INTEGER ; Pre-FEC BER current high alarm change count for host input
    prefec_ber_curr_host_input_lowalarm_change_count{lane_num}           = INTEGER ; Pre-FEC BER current low alarm change count for host input
    prefec_ber_curr_host_input_highwarning_change_count{lane_num}        = INTEGER ; Pre-FEC BER current high warning change count for host input
    prefec_ber_curr_host_input_lowwarning_change_count{lane_num}         = INTEGER ; Pre-FEC BER current low warning change count for host input
    errored_frames_min_media_input_highalarm_change_count{lane_num}      = INTEGER ; Errored frames minimum high alarm change count for media input
    errored_frames_min_media_input_lowalarm_change_count{lane_num}       = INTEGER ; Errored frames minimum low alarm change count for media input
    errored_frames_min_media_input_highwarning_change_count{lane_num}    = INTEGER ; Errored frames minimum high warning change count for media input
    errored_frames_min_media_input_lowwarning_change_count{lane_num}     = INTEGER ; Errored frames minimum low warning change count for media input
    errored_frames_max_media_input_highalarm_change_count{lane_num}      = INTEGER ; Errored frames maximum high alarm change count for media input
    errored_frames_max_media_input_lowalarm_change_count{lane_num}       = INTEGER ; Errored frames maximum low alarm change count for media input
    errored_frames_max_media_input_highwarning_change_count{lane_num}    = INTEGER ; Errored frames maximum high warning change count for media input
    errored_frames_max_media_input_lowwarning_change_count{lane_num}     = INTEGER ; Errored frames maximum low warning change count for media input
    errored_frames_avg_media_input_highalarm_change_count{lane_num}      = INTEGER ; Errored frames average high alarm change count for media input
    errored_frames_avg_media_input_lowalarm_change_count{lane_num}       = INTEGER ; Errored frames average low alarm change count for media input
    errored_frames_avg_media_input_highwarning_change_count{lane_num}    = INTEGER ; Errored frames average high warning change count for media input
    errored_frames_avg_media_input_lowwarning_change_count{lane_num}     = INTEGER ; Errored frames average low warning change count for media input
    errored_frames_curr_media_input_highalarm_change_count{lane_num}     = INTEGER ; Errored frames current high alarm change count for media input
    errored_frames_curr_media_input_lowalarm_change_count{lane_num}      = INTEGER ; Errored frames current low alarm change count for media input
    errored_frames_curr_media_input_highwarning_change_count{lane_num}   = INTEGER ; Errored frames current high warning change count for media input
    errored_frames_curr_media_input_lowwarning_change_count{lane_num}    = INTEGER ; Errored frames current low warning change count for media input
    errored_frames_min_host_input_highalarm_change_count{lane_num}       = INTEGER ; Errored frames minimum high alarm change count for host input
    errored_frames_min_host_input_lowalarm_change_count{lane_num}        = INTEGER ; Errored frames minimum low alarm change count for host input
    errored_frames_min_host_input_highwarning_change_count{lane_num}     = INTEGER ; Errored frames minimum high warning change count for host input
    errored_frames_min_host_input_lowwarning_change_count{lane_num}      = INTEGER ; Errored frames minimum low warning change count for host input
    errored_frames_max_host_input_highalarm_change_count{lane_num}       = INTEGER ; Errored frames maximum high alarm change count for host input
    errored_frames_max_host_input_lowalarm_change_count{lane_num}        = INTEGER ; Errored frames maximum low alarm change count for host input
    errored_frames_max_host_input_highwarning_change_count{lane_num}     = INTEGER ; Errored frames maximum high warning change count for host input
    errored_frames_max_host_input_lowwarning_change_count{lane_num}      = INTEGER ; Errored frames maximum low warning change count for host input
    errored_frames_avg_host_input_highalarm_change_count{lane_num}       = INTEGER ; Errored frames average high alarm change count for host input
    errored_frames_avg_host_input_lowalarm_change_count{lane_num}        = INTEGER ; Errored frames average low alarm change count for host input
    errored_frames_avg_host_input_highwarning_change_count{lane_num}     = INTEGER ; Errored frames average high warning change count for host input
    errored_frames_avg_host_input_lowwarning_change_count{lane_num}      = INTEGER ; Errored frames average low warning change count for host input
    errored_frames_curr_host_input_highalarm_change_count{lane_num}      = INTEGER ; Errored frames current high alarm change count for host input
    errored_frames_curr_host_input_lowalarm_change_count{lane_num}       = INTEGER ; Errored frames current low alarm change count for host input
    errored_frames_curr_host_input_highwarning_change_count{lane_num}    = INTEGER ; Errored frames current high warning change count for host input
    errored_frames_curr_host_input_lowwarning_change_count{lane_num}     = INTEGER ; Errored frames current low warning change count for host input
```

### 2.11 Transceiver VDM flag time set data

The `TRANSCEIVER_VDM_FLAG_TIME_SET` table stores the flag time set for the VDM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM flag time set for a port
    key                                            = TRANSCEIVER_VDM_FLAG_TIME_SET|ifname    ; information module VDM flags time set on port
    ; field                                        = value
    esnr_media_input_highalarm_last_set_time{lane_num}           = STR          ; eSNR high alarm last set time for media input
    esnr_media_input_lowalarm_last_set_time{lane_num}            = STR          ; eSNR low alarm last set time for media input
    esnr_media_input_highwarning_last_set_time{lane_num}         = STR          ; eSNR high warning last set time for media input
    esnr_media_input_lowwarning_last_set_time{lane_num}          = STR          ; eSNR low warning last set time for media input
    esnr_host_input_highalarm_last_set_time{lane_num}            = STR          ; eSNR high alarm last set time for host input
    esnr_host_input_lowalarm_last_set_time{lane_num}             = STR          ; eSNR low alarm last set time for host input
    esnr_host_input_highwarning_last_set_time{lane_num}          = STR          ; eSNR high warning last set time for host input
    esnr_host_input_lowwarning_last_set_time{lane_num}           = STR          ; eSNR low warning last set time for host input
    pam4_level_transition_media_input_highalarm_last_set_time{lane_num} = STR  ; PAM4 level transition high alarm last set time for media input
    pam4_level_transition_media_input_lowalarm_last_set_time{lane_num}  = STR  ; PAM4 level transition low alarm last set time for media input
    pam4_level_transition_media_input_highwarning_last_set_time{lane_num} = STR ; PAM4 level transition high warning last set time for media input
    pam4_level_transition_media_input_lowwarning_last_set_time{lane_num}  = STR ; PAM4 level transition low warning last set time for media input
    pam4_level_transition_host_input_highalarm_last_set_time{lane_num}    = STR ; PAM4 level transition high alarm last set time for host input
    pam4_level_transition_host_input_lowalarm_last_set_time{lane_num}     = STR ; PAM4 level transition low alarm last set time for host input
    pam4_level_transition_host_input_highwarning_last_set_time{lane_num}  = STR ; PAM4 level transition high warning last set time for host input
    pam4_level_transition_host_input_lowwarning_last_set_time{lane_num}   = STR ; PAM4 level transition low warning last set time for host input
    prefec_ber_min_media_input_highalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER minimum high alarm last set time for media input
    prefec_ber_min_media_input_lowalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER minimum low alarm last set time for media input
    prefec_ber_min_media_input_highwarning_last_set_time{lane_num}        = STR ; Pre-FEC BER minimum high warning last set time for media input
    prefec_ber_min_media_input_lowwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER minimum low warning last set time for media input
    prefec_ber_max_media_input_highalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER maximum high alarm last set time for media input
    prefec_ber_max_media_input_lowalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER maximum low alarm last set time for media input
    prefec_ber_max_media_input_highwarning_last_set_time{lane_num}        = STR ; Pre-FEC BER maximum high warning last set time for media input
    prefec_ber_max_media_input_lowwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER maximum low warning last set time for media input
    prefec_ber_avg_media_input_highalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER average high alarm last set time for media input
    prefec_ber_avg_media_input_lowalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER average low alarm last set time for media input
    prefec_ber_avg_media_input_highwarning_last_set_time{lane_num}        = STR ; Pre-FEC BER average high warning last set time for media input
    prefec_ber_avg_media_input_lowwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER average low warning last set time for media input
    prefec_ber_curr_media_input_highalarm_last_set_time{lane_num}         = STR ; Pre-FEC BER current high alarm last set time for media input
    prefec_ber_curr_media_input_lowalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER current low alarm last set time for media input
    prefec_ber_curr_media_input_highwarning_last_set_time{lane_num}       = STR ; Pre-FEC BER current high warning last set time for media input
    prefec_ber_curr_media_input_lowwarning_last_set_time{lane_num}        = STR ; Pre-FEC BER current low warning last set time for media input
    prefec_ber_min_host_input_highalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER minimum high alarm last set time for host input
    prefec_ber_min_host_input_lowalarm_last_set_time{lane_num}            = STR ; Pre-FEC BER minimum low alarm last set time for host input
    prefec_ber_min_host_input_highwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER minimum high warning last set time for host input
    prefec_ber_min_host_input_lowwarning_last_set_time{lane_num}          = STR ; Pre-FEC BER minimum low warning last set time for host input
    prefec_ber_max_host_input_highalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER maximum high alarm last set time for host input
    prefec_ber_max_host_input_lowalarm_last_set_time{lane_num}            = STR ; Pre-FEC BER maximum low alarm last set time for host input
    prefec_ber_max_host_input_highwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER maximum high warning last set time for host input
    prefec_ber_max_host_input_lowwarning_last_set_time{lane_num}          = STR ; Pre-FEC BER maximum low warning last set time for host input
    prefec_ber_avg_host_input_highalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER average high alarm last set time for host input
    prefec_ber_avg_host_input_lowalarm_last_set_time{lane_num}            = STR ; Pre-FEC BER average low alarm last set time for host input
    prefec_ber_avg_host_input_highwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER average high warning last set time for host input
    prefec_ber_avg_host_input_lowwarning_last_set_time{lane_num}          = STR ; Pre-FEC BER average low warning last set time for host input
    prefec_ber_curr_host_input_highalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER current high alarm last set time for host input
    prefec_ber_curr_host_input_lowalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER current low alarm last set time for host input
    prefec_ber_curr_host_input_highwarning_last_set_time{lane_num}        = STR ; Pre-FEC BER current high warning last set time for host input
    prefec_ber_curr_host_input_lowwarning_last_set_time{lane_num}         = STR ; Pre-FEC BER current low warning last set time for host input
    errored_frames_min_media_input_highalarm_last_set_time{lane_num}      = STR ; Errored frames minimum high alarm last set time for media input
    errored_frames_min_media_input_lowalarm_last_set_time{lane_num}       = STR ; Errored frames minimum low alarm last set time for media input
    errored_frames_min_media_input_highwarning_last_set_time{lane_num}    = STR ; Errored frames minimum high warning last set time for media input
    errored_frames_min_media_input_lowwarning_last_set_time{lane_num}     = STR ; Errored frames minimum low warning last set time for media input
    errored_frames_max_media_input_highalarm_last_set_time{lane_num}      = STR ; Errored frames maximum high alarm last set time for media input
    errored_frames_max_media_input_lowalarm_last_set_time{lane_num}       = STR ; Errored frames maximum low alarm last set time for media input
    errored_frames_max_media_input_highwarning_last_set_time{lane_num}    = STR ; Errored frames maximum high warning last set time for media input
    errored_frames_max_media_input_lowwarning_last_set_time{lane_num}     = STR ; Errored frames maximum low warning last set time for media input
    errored_frames_avg_media_input_highalarm_last_set_time{lane_num}      = STR ; Errored frames average high alarm last set time for media input
    errored_frames_avg_media_input_lowalarm_last_set_time{lane_num}       = STR ; Errored frames average low alarm last set time for media input
    errored_frames_avg_media_input_highwarning_last_set_time{lane_num}    = STR ; Errored frames average high warning last set time for media input
    errored_frames_avg_media_input_lowwarning_last_set_time{lane_num}     = STR ; Errored frames average low warning last set time for media input
    errored_frames_curr_media_input_highalarm_last_set_time{lane_num}     = STR ; Errored frames current high alarm last set time for media input
    errored_frames_curr_media_input_lowalarm_last_set_time{lane_num}      = STR ; Errored frames current low alarm last set time for media input
    errored_frames_curr_media_input_highwarning_last_set_time{lane_num}   = STR ; Errored frames current high warning last set time for media input
    errored_frames_curr_media_input_lowwarning_last_set_time{lane_num}    = STR ; Errored frames current low warning last set time for media input
    errored_frames_min_host_input_highalarm_last_set_time{lane_num}       = STR ; Errored frames minimum high alarm last set time for host input
    errored_frames_min_host_input_lowalarm_last_set_time{lane_num}        = STR ; Errored frames minimum low alarm last set time for host input
    errored_frames_min_host_input_highwarning_last_set_time{lane_num}     = STR ; Errored frames minimum high warning last set time for host input
    errored_frames_min_host_input_lowwarning_last_set_time{lane_num}      = STR ; Errored frames minimum low warning last set time for host input
    errored_frames_max_host_input_highalarm_last_set_time{lane_num}       = STR ; Errored frames maximum high alarm last set time for host input
    errored_frames_max_host_input_lowalarm_last_set_time{lane_num}        = STR ; Errored frames maximum low alarm last set time for host input
    errored_frames_max_host_input_highwarning_last_set_time{lane_num}     = STR ; Errored frames maximum high warning last set time for host input
    errored_frames_max_host_input_lowwarning_last_set_time{lane_num}      = STR ; Errored frames maximum low warning last set time for host input
    errored_frames_avg_host_input_highalarm_last_set_time{lane_num}       = STR ; Errored frames average high alarm last set time for host input
    errored_frames_avg_host_input_lowalarm_last_set_time{lane_num}        = STR ; Errored frames average low alarm last set time for host input
    errored_frames_avg_host_input_highwarning_last_set_time{lane_num}     = STR ; Errored frames average high warning last set time for host input
    errored_frames_avg_host_input_lowwarning_last_set_time{lane_num}      = STR ; Errored frames average low warning last set time for host input
    errored_frames_curr_host_input_highalarm_last_set_time{lane_num}      = STR ; Errored frames current high alarm last set time for host input
    errored_frames_curr_host_input_lowalarm_last_set_time{lane_num}       = STR ; Errored frames current low alarm last set time for host input
    errored_frames_curr_host_input_highwarning_last_set_time{lane_num}    = STR ; Errored frames current high warning last set time for host input
    errored_frames_curr_host_input_lowwarning_last_set_time{lane_num}     = STR ; Errored frames current low warning last set time for host input
```

### 2.12 Transceiver VDM flag time clear data

The `TRANSCEIVER_VDM_FLAG_TIME_CLEAR` table stores the flag time clear for the VDM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM flag time clear for a port
    key                                            = TRANSCEIVER_VDM_FLAG_TIME_CLEAR|ifname    ; information module VDM flags time clear on port
    ; field                                        = value
    esnr_media_input_highalarm_last_clear_time{lane_num}           = STR          ; eSNR high alarm last clear time for media input
    esnr_media_input_lowalarm_last_clear_time{lane_num}            = STR          ; eSNR low alarm last clear time for media input
    esnr_media_input_highwarning_last_clear_time{lane_num}         = STR          ; eSNR high warning last clear time for media input
    esnr_media_input_lowwarning_last_clear_time{lane_num}          = STR          ; eSNR low warning last clear time for media input
    esnr_host_input_highalarm_last_clear_time{lane_num}            = STR          ; eSNR high alarm last clear time for host input
    esnr_host_input_lowalarm_last_clear_time{lane_num}             = STR          ; eSNR low alarm last clear time for host input
    esnr_host_input_highwarning_last_clear_time{lane_num}          = STR          ; eSNR high warning last clear time for host input
    esnr_host_input_lowwarning_last_clear_time{lane_num}           = STR          ; eSNR low warning last clear time for host input
    pam4_level_transition_media_input_highalarm_last_clear_time{lane_num} = STR  ; PAM4 level transition high alarm last clear time for media input
    pam4_level_transition_media_input_lowalarm_last_clear_time{lane_num}  = STR  ; PAM4 level transition low alarm last clear time for media input
    pam4_level_transition_media_input_highwarning_last_clear_time{lane_num} = STR ; PAM4 level transition high warning last clear time for media input
    pam4_level_transition_media_input_lowwarning_last_clear_time{lane_num}  = STR ; PAM4 level transition low warning last clear time for media input
    pam4_level_transition_host_input_highalarm_last_clear_time{lane_num}    = STR ; PAM4 level transition high alarm last clear time for host input
    pam4_level_transition_host_input_lowalarm_last_clear_time{lane_num}     = STR ; PAM4 level transition low alarm last clear time for host input
    pam4_level_transition_host_input_highwarning_last_clear_time{lane_num}  = STR ; PAM4 level transition high warning last clear time for host input
    pam4_level_transition_host_input_lowwarning_last_clear_time{lane_num}   = STR ; PAM4 level transition low warning last clear time for host input
    prefec_ber_min_media_input_highalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER minimum high alarm last clear time for media input
    prefec_ber_min_media_input_lowalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER minimum low alarm last clear time for media input
    prefec_ber_min_media_input_highwarning_last_clear_time{lane_num}        = STR ; Pre-FEC BER minimum high warning last clear time for media input
    prefec_ber_min_media_input_lowwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER minimum low warning last clear time for media input
    prefec_ber_max_media_input_highalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER maximum high alarm last clear time for media input
    prefec_ber_max_media_input_lowalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER maximum low alarm last clear time for media input
    prefec_ber_max_media_input_highwarning_last_clear_time{lane_num}        = STR ; Pre-FEC BER maximum high warning last clear time for media input
    prefec_ber_max_media_input_lowwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER maximum low warning last clear time for media input
    prefec_ber_avg_media_input_highalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER average high alarm last clear time for media input
    prefec_ber_avg_media_input_lowalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER average low alarm last clear time for media input
    prefec_ber_avg_media_input_highwarning_last_clear_time{lane_num}        = STR ; Pre-FEC BER average high warning last clear time for media input
    prefec_ber_avg_media_input_lowwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER average low warning last clear time for media input
    prefec_ber_curr_media_input_highalarm_last_clear_time{lane_num}         = STR ; Pre-FEC BER current high alarm last clear time for media input
    prefec_ber_curr_media_input_lowalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER current low alarm last clear time for media input
    prefec_ber_curr_media_input_highwarning_last_clear_time{lane_num}       = STR ; Pre-FEC BER current high warning last clear time for media input
    prefec_ber_curr_media_input_lowwarning_last_clear_time{lane_num}        = STR ; Pre-FEC BER current low warning last clear time for media input
    prefec_ber_min_host_input_highalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER minimum high alarm last clear time for host input
    prefec_ber_min_host_input_lowalarm_last_clear_time{lane_num}            = STR ; Pre-FEC BER minimum low alarm last clear time for host input
    prefec_ber_min_host_input_highwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER minimum high warning last clear time for host input
    prefec_ber_min_host_input_lowwarning_last_clear_time{lane_num}          = STR ; Pre-FEC BER minimum low warning last clear time for host input
    prefec_ber_max_host_input_highalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER maximum high alarm last clear time for host input
    prefec_ber_max_host_input_lowalarm_last_clear_time{lane_num}            = STR ; Pre-FEC BER maximum low alarm last clear time for host input
    prefec_ber_max_host_input_highwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER maximum high warning last clear time for host input
    prefec_ber_max_host_input_lowwarning_last_clear_time{lane_num}          = STR ; Pre-FEC BER maximum low warning last clear time for host input
    prefec_ber_avg_host_input_highalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER average high alarm last clear time for host input
    prefec_ber_avg_host_input_lowalarm_last_clear_time{lane_num}            = STR ; Pre-FEC BER average low alarm last clear time for host input
    prefec_ber_avg_host_input_highwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER average high warning last clear time for host input
    prefec_ber_avg_host_input_lowwarning_last_clear_time{lane_num}          = STR ; Pre-FEC BER average low warning last clear time for host input
    prefec_ber_curr_host_input_highalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER current high alarm last clear time for host input
    prefec_ber_curr_host_input_lowalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER current low alarm last clear time for host input
    prefec_ber_curr_host_input_highwarning_last_clear_time{lane_num}        = STR ; Pre-FEC BER current high warning last clear time for host input
    prefec_ber_curr_host_input_lowwarning_last_clear_time{lane_num}         = STR ; Pre-FEC BER current low warning last clear time for host input
    errored_frames_min_media_input_highalarm_last_clear_time{lane_num}      = STR ; Errored frames minimum high alarm last clear time for media input
    errored_frames_min_media_input_lowalarm_last_clear_time{lane_num}       = STR ; Errored frames minimum low alarm last clear time for media input
    errored_frames_min_media_input_highwarning_last_clear_time{lane_num}    = STR ; Errored frames minimum high warning last clear time for media input
    errored_frames_min_media_input_lowwarning_last_clear_time{lane_num}     = STR ; Errored frames minimum low warning last clear time for media input
    errored_frames_max_media_input_highalarm_last_clear_time{lane_num}      = STR ; Errored frames maximum high alarm last clear time for media input
    errored_frames_max_media_input_lowalarm_last_clear_time{lane_num}       = STR ; Errored frames maximum low alarm last clear time for media input
    errored_frames_max_media_input_highwarning_last_clear_time{lane_num}    = STR ; Errored frames maximum high warning last clear time for media input
    errored_frames_max_media_input_lowwarning_last_clear_time{lane_num}     = STR ; Errored frames maximum low warning last clear time for media input
    errored_frames_avg_media_input_highalarm_last_clear_time{lane_num}      = STR ; Errored frames average high alarm last clear time for media input
    errored_frames_avg_media_input_lowalarm_last_clear_time{lane_num}       = STR ; Errored frames average low alarm last clear time for media input
    errored_frames_avg_media_input_highwarning_last_clear_time{lane_num}    = STR ; Errored frames average high warning last clear time for media input
    errored_frames_avg_media_input_lowwarning_last_clear_time{lane_num}     = STR ; Errored frames average low warning last clear time for media input
    errored_frames_curr_media_input_highalarm_last_clear_time{lane_num}     = STR ; Errored frames current high alarm last clear time for media input
    errored_frames_curr_media_input_lowalarm_last_clear_time{lane_num}      = STR ; Errored frames current low alarm last clear time for media input
    errored_frames_curr_media_input_highwarning_last_clear_time{lane_num}   = STR ; Errored frames current high warning last clear time for media input
    errored_frames_curr_media_input_lowwarning_last_clear_time{lane_num}    = STR ; Errored frames current low warning last clear time for media input
    errored_frames_min_host_input_highalarm_last_clear_time{lane_num}       = STR ; Errored frames minimum high alarm last clear time for host input
    errored_frames_min_host_input_lowalarm_last_clear_time{lane_num}        = STR ; Errored frames minimum low alarm last clear time for host input
    errored_frames_min_host_input_highwarning_last_clear_time{lane_num}     = STR ; Errored frames minimum high warning last clear time for host input
    errored_frames_min_host_input_lowwarning_last_clear_time{lane_num}      = STR ; Errored frames minimum low warning last clear time for host input
    errored_frames_max_host_input_highalarm_last_clear_time{lane_num}       = STR ; Errored frames maximum high alarm last clear time for host input
    errored_frames_max_host_input_lowalarm_last_clear_time{lane_num}        = STR ; Errored frames maximum low alarm last clear time for host input
    errored_frames_max_host_input_highwarning_last_clear_time{lane_num}     = STR ; Errored frames maximum high warning last clear time for host input
    errored_frames_max_host_input_lowwarning_last_clear_time{lane_num}      = STR ; Errored frames maximum low warning last clear time for host input
    errored_frames_avg_host_input_highalarm_last_clear_time{lane_num}       = STR ; Errored frames average high alarm last clear time for host input
    errored_frames_avg_host_input_lowalarm_last_clear_time{lane_num}        = STR ; Errored frames average low alarm last clear time for host input
    errored_frames_avg_host_input_highwarning_last_clear_time{lane_num}     = STR ; Errored frames average high warning last clear time for host input
    errored_frames_avg_host_input_lowwarning_last_clear_time{lane_num}      = STR ; Errored frames average low warning last clear time for host input
    errored_frames_curr_host_input_highalarm_last_clear_time{lane_num}      = STR ; Errored frames current high alarm last clear time for host input
    errored_frames_curr_host_input_lowalarm_last_clear_time{lane_num}       = STR ; Errored frames current low alarm last clear time for host input
    errored_frames_curr_host_input_highwarning_last_clear_time{lane_num}    = STR ; Errored frames current high warning last clear time for host input
    errored_frames_curr_host_input_lowwarning_last_clear_time{lane_num}     = STR ; Errored frames current low warning last clear time for host input
```

### 2.13 Transceiver status data

The `TRANSCEIVER_STATUS` table stores the status of the transceiver.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS|ifname        ; Error information for module on port
    ; field                                 = value
    status                                  = 1*255VCHAR        ; code of the module status (plug in, plug out)
    error                                   = 1*255VCHAR        ; module error (N/A or a string consisting of error descriptions joined by "|", like "error1 | error2" )
    module_state                            = 1*255VCHAR        ; current module state (ModuleLowPwr, ModulePwrUp, ModuleReady, ModulePwrDn, Fault)
    module_fault_cause                      = 1*255VCHAR        ; reason of entering the module fault state
    datapath_firmware_fault                 = BOOLEAN           ; datapath (DSP) firmware fault
    module_firmware_fault                   = BOOLEAN           ; module firmware fault
    module_state_changed                    = BOOLEAN           ; module state changed
    DP{lane_num}State                       = 1*255VCHAR        ; data path state indicator on host lane {lane_num}
    txoutput_status{lane_num}               = BOOLEAN           ; tx output status on media lane {lane_num}
    rxoutput_status_hostlane{lane_num}      = BOOLEAN           ; rx output status on host lane {lane_num}
    tx{lane_num}disable                     = BOOLEAN           ; TX disable state on media lane {lane_num}
    tx_disabled_channel                     = INTEGER           ; TX disable field
    config_state_hostlane{lane_num}         = 1*255VCHAR        ; configuration status for the data path of host line {lane_num}
    dpinit_pending_hostlane{lane_num}       = BOOLEAN           ; data path configuration updated on host lane {lane_num}
    tuning_in_progress                      = BOOLEAN           ; tuning in progress status
    wavelength_unlock_status                = BOOLEAN           ; laser unlocked status
    target_output_power_oor                 = BOOLEAN           ; target output power out of range flag
    fine_tuning_oor                         = BOOLEAN           ; fine tuning  out of range flag
    tuning_not_accepted                     = BOOLEAN           ; tuning not accepted flag
    invalid_channel_num                     = BOOLEAN           ; invalid channel number flag
    tuning_complete                         = BOOLEAN           ; tuning complete flag

### 2.14 Transceiver PM data

The `TRANSCEIVER_PM` table stores the performance monitoring data of the transceiver. This table is exists only for C-CMIS transceivers.

    ; Defines Transceiver PM information for a port
    key                          = TRANSCEIVER_PM|ifname            ; information of PM on port
    ; field                      = value 
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

## 3. CLI Commands for CMIS Diagnostic Monitoring

### 3.1 CLI Commands for DOM Monitoring

#### 3.1.1 `show interfaces transceiver dom PORT`

This CLI shows the transceiver DOM and threshold values for a given port.

```plaintext
CLI output format:
                              High Alarm   High Warning   Low Warning   Low Alarm
             Paramter_Name    Threshold    Threshold      Threshold     Threshold
Port         (Unit)           (Unit)       (Unit)         (Unit)        (Unit)
-----------  ---------------  --------     --------       --------      --------

Example:
admin@sonic#show interfaces transceiver dom Ethernet1
                              High Alarm   High Warning   Low Warning   Low Alarm
             Temperature      Threshold    Threshold      Threshold     Threshold
Port         (Celsius)        (Celsius)    (Celsius)      (Celsius)     (Celsius)
-----------  ---------------  --------     --------       --------      --------
Ethernet1    100              90           80             -10            -20
```

#### 3.1.2 `show interfaces transceiver dom flag PORT`

This CLI shows the transceiver DOM flags for a given port.

```plaintext
CLI output format:
                              High Alarm   High Warning   Low Warning   Low Alarm
Port         Paramter_Name    Flag         Flag           Flag          Flag
-----------  ---------------  --------     --------       --------      --------

Example:
admin@sonic#show interfaces transceiver dom flag Ethernet1
                              High Alarm   High Warning   Low Warning   Low Alarm
Port         Paramter_Name    Flag         Flag           Flag          Flag
-----------  ---------------  --------     --------       --------      --------
Ethernet1    Temperature      False        False          False         False
```

### 3.2 CLI Commands for VDM Monitoring

#### 3.2.1 `show interfaces transceiver vdm PORT`

This CLI shows the transceiver VDM and threshold values for a given port.

```plaintext
CLI output format:
                              High Alarm   High Warning   Low Warning   Low Alarm
             Paramter_Name    Threshold    Threshold      Threshold     Threshold
Port         (Unit)           (Unit)       (Unit)         (Unit)        (Unit)
-----------  ---------------  --------     --------       --------      --------

Example:
admin@sonic#show interfaces transceiver vdm Ethernet1
Basic Values:
                              High Alarm   High Warning   Low Warning   Low Alarm
             eSNR Media Input Threshold    Threshold      Threshold     Threshold
Port         (dB)             (dB)         (dB)           (dB)          (dB)
-----------  ---------------  --------     --------       --------      --------
Ethernet1    23.48046875      0            0              0             0
```

#### 3.2.2 `show interfaces transceiver vdm flag PORT`

This CLI shows the transceiver VDM flags for a given port.

```plaintext
CLI output format:
                              High Alarm   High Warning   Low Warning   Low Alarm
Port         Paramter_Name    Flag         Flag           Flag          Flag
-----------  ---------------  --------     --------       --------      --------

Example:
admin@sonic#show interfaces transceiver vdm flag Ethernet1
                              High Alarm   High Warning   Low Warning   Low Alarm
Port         Paramter_Name    Flag         Flag           Flag          Flag
-----------  ---------------  --------     --------       --------      --------
Ethernet1    eSNR Media Input False        False          False         False
```

## 4. SONiC CMIS diagnostic monitoring workflow

### 4.1 Static Diagnostic Information

The `SfpStateUpdateTask` thread is responsible for updating the static diagnostic information for all the transceivers in the system. The static diagnostic information, such as threshold values for DOM, VDM and PM, are read from the transceiver and updated in the `redis-db` during `xcvrd` boot-up and during transceiver removal and insertion.

The following tables are updated by the `SfpStateUpdateTask` thread:

1. `TRANSCEIVER_DOM_THRESHOLD`
2. `TRANSCEIVER_VDM_THRESHOLD`
3. `TRANSCEIVER_PM_THRESHOLD`

### 4.2 Dynamic Diagnostic Information

The `DomInfoUpdateTask` thread is responsible for updating the dynamic diagnostic information for all the transceivers in the system. The `DomInfoUpdateTask` thread is triggered by a timer (`DOM_INFO_UPDATE_PERIOD_SECS`), which is set to 60 seconds by default. The `DomInfoUpdateTask` thread reads the diagnostic information from the transceiver and updates the relevant tables in `redis-db`.

#### 4.2.1 High-Level Steps for Updating Dynamic Diagnostic Information

1. The `DomInfoUpdateTask` thread is created by the `xcvrd` process.
2. A timer (`DOM_INFO_UPDATE_PERIOD_SECS`) is set to read the diagnostic information from the transceiver every 60 seconds.
3. With every timer expiry, the `DomInfoUpdateTask` thread reads the diagnostic information from the transceiver and updates the relevant tables in `redis-db` for all the ports. The steps performed to update the diagnostic information for a port are as follows:
    1. Ensure DOM monitoring is enabled for the port. If DOM monitoring is disabled, skip updating the diagnostic information for the port.
    2. If the current port is the first port from its breakout port group to be polled, clear the cached diagnostic information. For all subsequent ports in the breakout port group, use the cached diagnostic information to update the `redis-db`.
    3. Read the transceiver firmware information from the module and update the `TRANSCEIVER_FIRMWARE_INFO` table.
    4. Read the transceiver DOM sensor data from the module and update the `TRANSCEIVER_DOM_SENSOR` table.
    5. Read the transceiver DOM flag data from the module, record the timestamp, and update the `TRANSCEIVER_DOM_FLAG` table.
    6. Analyze the transceiver DOM flag data by comparing the current flag data with the previous flag data and update the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_TIME_SET`, and `TRANSCEIVER_DOM_FLAG_TIME_CLEAR` tables.
    7. Read the transceiver status data from the module and update the `TRANSCEIVER_STATUS` table.
    8. If the transceiver supports VDM monitoring, perform the following steps:
        1. Freeze the statistics by calling the CMIS API and wait for `FreezeDone`. Once the statistics are frozen, record the timestamp and copy the VDM and PM statistics from the transceiver.
        2. Unfreeze the statistics by calling the CMIS API.
        3. Update the `TRANSCEIVER_VDM_SAMPLE` and `TRANSCEIVER_PM` tables with the VDM and PM statistics respectively.
        4. Analyze the VDM flags by comparing the current statistics with the previous statistics and update the `TRANSCEIVER_VDM_FLAG`, `TRANSCEIVER_VDM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_VDM_FLAG_TIME_SET`, and `TRANSCEIVER_VDM_FLAG_TIME_CLEAR` tables.
        5. Analyze the PM flags by comparing the current statistics with the previous statistics and update the `TRANSCEIVER_PM_FLAG`, `TRANSCEIVER_PM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_PM_FLAG_TIME_SET`, and `TRANSCEIVER_PM_FLAG_TIME_CLEAR` tables.

#### 4.2.2 Details of Flag Analysis of Tables

**Note**: For simplicity, this section uses VDM as an example. However, the same analysis is applicable for DOM and PM as well.

**Purpose of Flag Analysis:**

The purpose of flag analysis is to track the status of various parameters and to count the number of times each VDM flag has changed. It also records the timestamp when each VDM flag was set and cleared.

**Tables Used for Flag Analysis:**

- `TRANSCEIVER_VDM_FLAG`: This table stores flags indicating the status of various VDM parameters.
- `TRANSCEIVER_VDM_FLAG_CHANGE_COUNT`: This table keeps a count of how many times each VDM flag has changed.
- `TRANSCEIVER_VDM_FLAG_TIME_SET`: This table records the timestamp when each VDM flag was set.
- `TRANSCEIVER_VDM_FLAG_TIME_CLEAR`: This table records the timestamp when each VDM flag was cleared.

**Example of Table Updates:**

- **TRANSCEIVER_VDM_FLAG_CHANGE_COUNT:**
  - Each time a flag in the `TRANSCEIVER_VDM_FLAG` table changes (either set or cleared), the corresponding count in this table is incremented.
- **TRANSCEIVER_VDM_FLAG_TIME_SET:**
  - When a flag is set in the `TRANSCEIVER_VDM_FLAG` table, the current timestamp is recorded in this table.
- **TRANSCEIVER_VDM_FLAG_TIME_CLEAR:**
  - When a flag is cleared in the `TRANSCEIVER_VDM_FLAG` table, the current timestamp is recorded in this table.
