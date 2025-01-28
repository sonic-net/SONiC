# CMIS Diagnostic Monitoring Overview in SONiC

## 1. Overview

The CMIS (Common Management Interface Specification) diagnostic monitoring feature is a standard for monitoring the performance of optical transceivers. It provides a way to monitor the performance of optical transceivers in real time. SONiC periodically reads the diagnostic monitoring data from the optical transceivers and stores the data in the database. The data can be retrieved using the SONiC CLI or by querying the database directly.

The current scope of the CMIS diagnostic monitoring feature in SONiC includes the following parameters:

- **DOM (Digital Optical Monitoring) data:** Provides real-time monitoring of optical transceiver parameters such as temperature, voltage, and optical power.
- **VDM (Versatile Diagnostics Monitoring) data:** Offers versatile diagnostic information for enhanced monitoring and troubleshooting.
- **PM (Performance Monitoring) data:** Applicable only for C-CMIS transceivers, this includes performance metrics such as error counts and signal quality indicators.

## 2. STATE_DB Schema for CMIS Diagnostic Monitoring

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

### 2.1 Transceiver DOM

#### 2.1.1 Transceiver DOM sensor data

The `TRANSCEIVER_DOM_SENSOR` table stores the real-time DOM data for the optical transceivers.

lane_num: Represents the lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver DOM sensor information for a port
    key                          = TRANSCEIVER_DOM_SENSOR|ifname    ; information module DOM sensors on port
    ; field                      = value
    table_last_update_time       = STR                              ; last update time for diagnostic data
    temperature                  = FLOAT                            ; temperature value in Celsius
    voltage                      = FLOAT                            ; voltage value in V
    tx{lane_num}power            = FLOAT                            ; tx power in dBm for each lane
    rx{lane_num}power            = FLOAT                            ; rx power in dBm for each lane
    tx{lane_num}bias             = FLOAT                            ; tx bias in mA for each lane
    laser_temperature            = FLOAT                            ; laser temperature value in Celsius

    laser_config_freq            = FLOAT                            ; laser configured frequency in MHz
    laser_curr_freq              = FLOAT                            ; laser current frequency in MHz
    tx_config_power              = FLOAT                            ; configured tx output power in dbm
```

#### 2.1.2 Transceiver DOM threshold data

The `TRANSCEIVER_DOM_THRESHOLD` table stores the threshold values for the DOM data.

```plaintext
    ; Defines Transceiver DOM threshold info for a port
    key                          = TRANSCEIVER_DOM_THRESHOLD|ifname ; DOM threshold information for module on port
    ; field                      = value
    table_last_update_time       = STR                              ; last update time for diagnostic data
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

#### 2.1.3 Transceiver DOM flag data

The `TRANSCEIVER_DOM_FLAG` table stores the flag status for the DOM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flags for a port
    key                          = TRANSCEIVER_DOM_FLAG|ifname    ; information module DOM flags on port
    ; field                      = value
    table_last_update_time           = STR                ; last update time for diagnostic data
    temphighalarm                    = BOOLEAN            ; temperature high alarm flag 
    temphighwarning                  = BOOLEAN            ; temperature high warning flag
    templowalarm                     = BOOLEAN            ; temperature low alarm flag
    templowwarning                   = BOOLEAN            ; temperature low warning flag
    vcchighalarm                     = BOOLEAN            ; vcc high alarm flag
    vcchighwarning                   = BOOLEAN            ; vcc high warning flag
    vcclowalarm                      = BOOLEAN            ; vcc low alarm flag
    vcclowwarning                    = BOOLEAN            ; vcc low warning flag
    txpowerhighalarm{lane_num}       = BOOLEAN            ; tx power high alarm flag
    txpowerlowalarm{lane_num}        = BOOLEAN            ; tx power low alarm flag
    txpowerhighwarning{lane_num}     = BOOLEAN            ; tx power high warning flag
    txpowerlowwarning{lane_num}      = BOOLEAN            ; tx power low alarm flag
    rxpowerhighalarm{lane_num}       = BOOLEAN            ; rx power high alarm flag
    rxpowerlowalarm{lane_num}        = BOOLEAN            ; rx power low alarm flag
    rxpowerhighwarning{lane_num}     = BOOLEAN            ; rx power high warning flag
    rxpowerlowwarning{lane_num}      = BOOLEAN            ; rx power low warning flag
    txbiashighalarm{lane_num}        = BOOLEAN            ; tx bias high alarm flag
    txbiaslowalarm{lane_num}         = BOOLEAN            ; tx bias low alarm flag
    txbiashighwarning{lane_num}      = BOOLEAN            ; tx bias high warning flag
    txbiaslowwarning{lane_num}       = BOOLEAN            ; tx bias low warning flag
    lasertemphighalarm               = BOOLEAN            ; laser temperature high alarm flag
    lasertemplowalarm                = BOOLEAN            ; laser temperature low alarm flag
    lasertemphighwarning             = BOOLEAN            ; laser temperature high warning flag
    lasertemplowwarning              = BOOLEAN            ; laser temperature low warning flag
```

#### 2.1.4 Transceiver DOM flag change count data

The `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table stores the flag change count for the DOM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag change count for a port
    key                              = TRANSCEIVER_DOM_FLAG_CHANGE_COUNT|ifname   ; information module DOM flags change count on port
    ; field                          = value
    temphighalarm                 = INTEGER           ; temperature high alarm change count
    temphighwarning               = INTEGER           ; temperature high warning change count
    templowalarm                  = INTEGER           ; temperature low alarm change count
    templowwarning                = INTEGER           ; temperature low warning change count
    vcchighalarm                  = INTEGER           ; vcc high alarm change count
    vcchighwarning                = INTEGER           ; vcc high warning change count
    vcclowalarm                   = INTEGER           ; vcc low alarm change count
    vcclowwarning                 = INTEGER           ; vcc low warning change count
    txpowerhighalarm{lane_num}    = INTEGER           ; tx power high alarm change count
    txpowerlowalarm{lane_num}     = INTEGER           ; tx power low alarm change count
    txpowerhighwarning{lane_num}  = INTEGER           ; tx power high warning change count
    txpowerlowwarning{lane_num}   = INTEGER           ; tx power low alarm change count
    rxpowerhighalarm{lane_num}    = INTEGER           ; rx power high alarm change count
    rxpowerlowalarm{lane_num}     = INTEGER           ; rx power low alarm change count
    rxpowerhighwarning{lane_num}  = INTEGER           ; rx power high warning change count
    rxpowerlowwarning{lane_num}   = INTEGER           ; rx power low warning change count
    txbiashighalarm{lane_num}     = INTEGER           ; tx bias high alarm change count
    txbiaslowalarm{lane_num}      = INTEGER           ; tx bias low alarm change count
    txbiashighwarning{lane_num}   = INTEGER           ; tx bias high warning change count
    txbiaslowwarning{lane_num}    = INTEGER           ; tx bias low warning change count
    lasertemphighalarm            = INTEGER           ; laser temperature high alarm change count
    lasertemplowalarm             = INTEGER           ; laser temperature low alarm change count
    lasertemphighwarning          = INTEGER           ; laser temperature high warning change count
    lasertemplowwarning           = INTEGER           ; laser temperature low warning change count
```

#### 2.1.5 Transceiver DOM flag time set data

The `TRANSCEIVER_DOM_FLAG_SET_TIME` table stores the last set time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time set for a port
    key                          = TRANSCEIVER_DOM_FLAG_SET_TIME|ifname   ; information module DOM flag time set on port
    ; field                      = value
    temphighalarm                 = STR           ; temperature high alarm last set time
    temphighwarning               = STR           ; temperature high warning last set time
    templowalarm                  = STR           ; temperature low alarm last set time
    templowwarning                = STR           ; temperature low warning last set time
    vcchighalarm                  = STR           ; vcc high alarm last set time
    vcchighwarning                = STR           ; vcc high warning last set time
    vcclowalarm                   = STR           ; vcc low alarm last set time
    vcclowwarning                 = STR           ; vcc low warning last set time
    txpowerhighalarm{lane_num}    = STR           ; tx power high alarm last set time
    txpowerlowalarm{lane_num}     = STR           ; tx power low alarm last set time
    txpowerhighwarning{lane_num}  = STR           ; tx power high warning last set time
    txpowerlowwarning{lane_num}   = STR           ; tx power low warning last set time
    rxpowerhighalarm{lane_num}    = STR           ; rx power high alarm last set time
    rxpowerlowalarm{lane_num}     = STR           ; rx power low alarm last set time
    rxpowerhighwarning{lane_num}  = STR           ; rx power high warning last set time
    rxpowerlowwarning{lane_num}   = STR           ; rx power low warning last set time
    txbiashighalarm{lane_num}     = STR           ; tx bias high alarm last set time
    txbiaslowalarm{lane_num}      = STR           ; tx bias low alarm last set time
    txbiashighwarning{lane_num}   = STR           ; tx bias high warning last set time
    txbiaslowwarning{lane_num}    = STR           ; tx bias low warning last set time
    lasertemphighalarm            = STR           ; laser temperature high alarm last set time
    lasertemplowalarm             = STR           ; laser temperature low alarm last set time
    lasertemphighwarning          = STR           ; laser temperature high warning last set time
    lasertemplowwarning           = STR           ; laser temperature low warning last set time
```

#### 2.1.6 Transceiver DOM flag time clear data

The `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table stores the last clear time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time clear for a port
    key                          = TRANSCEIVER_DOM_FLAG_CLEAR_TIME|ifname  ; information module DOM flag time clear on port
    ; field                      = value
    temphighalarm                = STR          ; temperature high alarm last clear time
    temphighwarning              = STR          ; temperature high warning last clear time
    templowalarm                 = STR          ; temperature low alarm last clear time
    templowwarning               = STR          ; temperature low warning last clear time
    vcchighalarm                 = STR          ; vcc high alarm last clear time
    vcchighwarning               = STR          ; vcc high warning last clear time
    vcclowalarm                  = STR          ; vcc low alarm last clear time
    vcclowwarning                = STR          ; vcc low warning last clear time
    txpowerhighalarm{lane_num}   = STR          ; tx power high alarm last clear time
    txpowerlowalarm{lane_num}    = STR          ; tx power low alarm last clear time
    txpowerhighwarning{lane_num} = STR          ; tx power high warning last clear time
    txpowerlowwarning{lane_num}  = STR          ; tx power low warning last clear time
    rxpowerhighalarm{lane_num}   = STR          ; rx power high alarm last clear time
    rxpowerlowalarm{lane_num}    = STR          ; rx power low alarm last clear time
    rxpowerhighwarning{lane_num} = STR          ; rx power high warning last clear time
    rxpowerlowwarning{lane_num}  = STR          ; rx power low warning last clear time
    txbiashighalarm{lane_num}    = STR          ; tx bias high alarm last clear time
    txbiaslowalarm{lane_num}     = STR          ; tx bias low alarm last clear time
    txbiashighwarning{lane_num}  = STR          ; tx bias high warning last clear time
    txbiaslowwarning{lane_num}   = STR          ; tx bias low warning last clear time
    lasertemphighalarm           = STR          ; laser temperature high alarm last clear time
    lasertemplowalarm            = STR          ; laser temperature low alarm last clear time
    lasertemphighwarning         = STR          ; laser temperature high warning last clear time
    lasertemplowwarning          = STR          ; laser temperature low warning last clear time
```

### 2.2 Transceiver VDM

#### 2.2.1 Transceiver VDM sample data

The `TRANSCEIVER_VDM_REAL_VALUE` table stores the real time VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM sample for a port
    key                                            = TRANSCEIVER_VDM_REAL_VALUE|ifname    ; information module VDM sample on port
    ; field                                        = value
    table_last_update_time                         = STR                    ; last update time for diagnostic data
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

#### 2.2.2 Transceiver VDM threshold data

##### 2.2.2.1 Transceiver VDM high alarm threshold data

The `TRANSCEIVER_VDM_HALARM_THRESHOLD` table stores the high alarm threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm threshold for a port
    key                                            = TRANSCEIVER_VDM_HALARM_THRESHOLD|ifname    ; information module VDM high alarm threshold on port
    ; field                                        = value
    table_last_update_time                               = STR            ; last update time for diagnostic data
    laser_temperature_media_halarm{lane_num}             = FLOAT          ; laser temperature high alarm value in Celsius for media input
    esnr_media_input_halarm{lane_num}                    = FLOAT          ; eSNR high alarm value in dB for media input
    esnr_host_input_halarm{lane_num}                     = FLOAT          ; eSNR high alarm value in dB for host input
    pam4_level_transition_media_input_halarm{lane_num}   = FLOAT          ; PAM4 level transition high alarm value in dB for media input
    pam4_level_transition_host_input_halarm{lane_num}    = FLOAT          ; PAM4 level transition high alarm value in dB for host input
    prefec_ber_min_media_input_halarm{lane_num}          = FLOAT          ; Pre-FEC BER minimum high alarm value for media input
    prefec_ber_max_media_input_halarm{lane_num}          = FLOAT          ; Pre-FEC BER maximum high alarm value for media input
    prefec_ber_avg_media_input_halarm{lane_num}          = FLOAT          ; Pre-FEC BER average high alarm value for media input
    prefec_ber_curr_media_input_halarm{lane_num}         = FLOAT          ; Pre-FEC BER current high alarm value for media input
    prefec_ber_min_host_input_halarm{lane_num}           = FLOAT          ; Pre-FEC BER minimum high alarm value for host input
    prefec_ber_max_host_input_halarm{lane_num}           = FLOAT          ; Pre-FEC BER maximum high alarm value for host input
    prefec_ber_avg_host_input_halarm{lane_num}           = FLOAT          ; Pre-FEC BER average high alarm value for host input
    prefec_ber_curr_host_input_halarm{lane_num}          = FLOAT          ; Pre-FEC BER current high alarm value for host input
    errored_frames_min_media_input_halarm{lane_num}      = FLOAT          ; Errored frames minimum high alarm value for media input
    errored_frames_max_media_input_halarm{lane_num}      = FLOAT          ; Errored frames maximum high alarm value for media input
    errored_frames_avg_media_input_halarm{lane_num}      = FLOAT          ; Errored frames average high alarm value for media input
    errored_frames_curr_media_input_halarm{lane_num}     = FLOAT          ; Errored frames current high alarm value for media input
    errored_frames_min_host_input_halarm{lane_num}       = FLOAT          ; Errored frames minimum high alarm value for host input
    errored_frames_max_host_input_halarm{lane_num}       = FLOAT          ; Errored frames maximum high alarm value for host input
    errored_frames_avg_host_input_halarm{lane_num}       = FLOAT          ; Errored frames average high alarm value for host input
    errored_frames_curr_host_input_halarm{lane_num}      = FLOAT          ; Errored frames current high alarm value for host input

    ;C-CMIS specific fields
    biasxi_halarm{lane_num}                             = FLOAT         ; modulator bias xi in percentage (high alarm)
    biasxq_halarm{lane_num}                             = FLOAT         ; modulator bias xq in percentage (high alarm)
    biasxp_halarm{lane_num}                             = FLOAT         ; modulator bias xp in percentage (high alarm)
    biasyi_halarm{lane_num}                             = FLOAT         ; modulator bias yi in percentage (high alarm)
    biasyq_halarm{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high alarm)
    biasyp_halarm{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high alarm)
    cdshort_halarm{lane_num}                            = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (high alarm)
    cdlong_halarm{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (high alarm)
    dgd_halarm{lane_num}                                = FLOAT         ; differential group delay in ps (high alarm)
    sopmd_halarm{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (high alarm)
    soproc_halarm{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (high alarm)
    pdl_halarm{lane_num}                                = FLOAT         ; polarization dependent loss in db (high alarm)
    osnr_halarm{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (high alarm)
    esnr_halarm{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (high alarm)
    cfo_halarm{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (high alarm)
    txcurrpower_halarm{lane_num}                        = FLOAT         ; tx current output power in dbm (high alarm)
    rxtotpower_halarm{lane_num}                         = FLOAT         ; rx total power in  dbm (high alarm)
    rxsigpower_halarm{lane_num}                         = FLOAT         ; rx signal power in dbm (high alarm)
```

##### 2.2.2.2 Transceiver VDM low alarm threshold data

The `TRANSCEIVER_VDM_LALARM_THRESHOLD` table stores the low alarm threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm threshold for a port
    key                                            = TRANSCEIVER_VDM_LALARM_THRESHOLD|ifname    ; information module VDM low alarm threshold on port
    ; field                                        = value
    table_last_update_time                               = STR            ; last update time for diagnostic data
    laser_temperature_media_lalarm{lane_num}             = FLOAT          ; laser temperature low alarm value in Celsius for media input
    esnr_media_input_lalarm{lane_num}                    = FLOAT          ; eSNR low alarm value in dB for media input
    esnr_host_input_lalarm{lane_num}                     = FLOAT          ; eSNR low alarm value in dB for host input
    pam4_level_transition_media_input_lalarm{lane_num}   = FLOAT          ; PAM4 level transition low alarm value in dB for media input
    pam4_level_transition_host_input_lalarm{lane_num}    = FLOAT          ; PAM4 level transition low alarm value in dB for host input
    prefec_ber_min_media_input_lalarm{lane_num}          = FLOAT          ; Pre-FEC BER minimum low alarm value for media input
    prefec_ber_max_media_input_lalarm{lane_num}          = FLOAT          ; Pre-FEC BER maximum low alarm value for media input
    prefec_ber_avg_media_input_lalarm{lane_num}          = FLOAT          ; Pre-FEC BER average low alarm value for media input
    prefec_ber_curr_media_input_lalarm{lane_num}         = FLOAT          ; Pre-FEC BER current low alarm value for media input
    prefec_ber_min_host_input_lalarm{lane_num}           = FLOAT          ; Pre-FEC BER minimum low alarm value for host input
    prefec_ber_max_host_input_lalarm{lane_num}           = FLOAT          ; Pre-FEC BER maximum low alarm value for host input
    prefec_ber_avg_host_input_lalarm{lane_num}           = FLOAT          ; Pre-FEC BER average low alarm value for host input
    prefec_ber_curr_host_input_lalarm{lane_num}          = FLOAT          ; Pre-FEC BER current low alarm value for host input
    errored_frames_min_media_input_lalarm{lane_num}      = FLOAT          ; Errored frames minimum low alarm value for media input
    errored_frames_max_media_input_lalarm{lane_num}      = FLOAT          ; Errored frames maximum low alarm value for media input
    errored_frames_avg_media_input_lalarm{lane_num}      = FLOAT          ; Errored frames average low alarm value for media input
    errored_frames_curr_media_input_lalarm{lane_num}     = FLOAT          ; Errored frames current low alarm value for media input
    errored_frames_min_host_input_lalarm{lane_num}       = FLOAT          ; Errored frames minimum low alarm value for host input
    errored_frames_max_host_input_lalarm{lane_num}       = FLOAT          ; Errored frames maximum low alarm value for host input
    errored_frames_avg_host_input_lalarm{lane_num}       = FLOAT          ; Errored frames average low alarm value for host input
    errored_frames_curr_host_input_lalarm{lane_num}      = FLOAT          ; Errored frames current low alarm value for host input

    ;C-CMIS specific fields
    biasxi_lalarm{lane_num}                             = FLOAT         ; modulator bias xi in percentage (low alarm)
    biasxq_lalarm{lane_num}                             = FLOAT         ; modulator bias xq in percentage (low alarm)
    biasxp_lalarm{lane_num}                             = FLOAT         ; modulator bias xp in percentage (low alarm)
    biasyi_lalarm{lane_num}                             = FLOAT         ; modulator bias yi in percentage (low alarm)
    biasyq_lalarm{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low alarm)
    biasyp_lalarm{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low alarm)
    cdshort_lalarm{lane_num}                            = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (low alarm)
    cdlong_lalarm{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (low alarm)
    dgd_lalarm{lane_num}                                = FLOAT         ; differential group delay in ps (low alarm)
    sopmd_lalarm{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (low alarm)
    soproc_lalarm{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (low alarm)
    pdl_lalarm{lane_num}                                = FLOAT         ; polarization dependent loss in db (low alarm)
    osnr_lalarm{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (low alarm)
    esnr_lalarm{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (low alarm)
    cfo_lalarm{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (low alarm)
    txcurrpower_lalarm{lane_num}                        = FLOAT         ; tx current output power in dbm (low alarm)
    rxtotpower_lalarm{lane_num}                         = FLOAT         ; rx total power in  dbm (low alarm)
    rxsigpower_lalarm{lane_num}                         = FLOAT         ; rx signal power in dbm (low alarm)
```

##### 2.2.2.3 Transceiver VDM high warning threshold data

The `TRANSCEIVER_VDM_HWARN_THRESHOLD` table stores the high warning threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning threshold for a port
    key                                            = TRANSCEIVER_VDM_HWARN_THRESHOLD|ifname    ; information module VDM high warning threshold on port
    ; field                                        = value
    table_last_update_time                              = STR            ; last update time for diagnostic data
    laser_temperature_media_hwarn{lane_num}             = FLOAT          ; laser temperature high warning value in Celsius for media input
    esnr_media_input_hwarn{lane_num}                    = FLOAT          ; eSNR high warning value in dB for media input
    esnr_host_input_hwarn{lane_num}                     = FLOAT          ; eSNR high warning value in dB for host input
    pam4_level_transition_media_input_hwarn{lane_num}   = FLOAT          ; PAM4 level transition high warning value in dB for media input
    pam4_level_transition_host_input_hwarn{lane_num}    = FLOAT          ; PAM4 level transition high warning value in dB for host input
    prefec_ber_min_media_input_hwarn{lane_num}          = FLOAT          ; Pre-FEC BER minimum high warning value for media input
    prefec_ber_max_media_input_hwarn{lane_num}          = FLOAT          ; Pre-FEC BER maximum high warning value for media input
    prefec_ber_avg_media_input_hwarn{lane_num}          = FLOAT          ; Pre-FEC BER average high warning value for media input
    prefec_ber_curr_media_input_hwarn{lane_num}         = FLOAT          ; Pre-FEC BER current high warning value for media input
    prefec_ber_min_host_input_hwarn{lane_num}           = FLOAT          ; Pre-FEC BER minimum high warning value for host input
    prefec_ber_max_host_input_hwarn{lane_num}           = FLOAT          ; Pre-FEC BER maximum high warning value for host input
    prefec_ber_avg_host_input_hwarn{lane_num}           = FLOAT          ; Pre-FEC BER average high warning value for host input
    prefec_ber_curr_host_input_hwarn{lane_num}          = FLOAT          ; Pre-FEC BER current high warning value for host input
    errored_frames_min_media_input_hwarn{lane_num}      = FLOAT          ; Errored frames minimum high warning value for media input
    errored_frames_max_media_input_hwarn{lane_num}      = FLOAT          ; Errored frames maximum high warning value for media input
    errored_frames_avg_media_input_hwarn{lane_num}      = FLOAT          ; Errored frames average high warning value for media input
    errored_frames_curr_media_input_hwarn{lane_num}     = FLOAT          ; Errored frames current high warning value for media input
    errored_frames_min_host_input_hwarn{lane_num}       = FLOAT          ; Errored frames minimum high warning value for host input
    errored_frames_max_host_input_hwarn{lane_num}       = FLOAT          ; Errored frames maximum high warning value for host input
    errored_frames_avg_host_input_hwarn{lane_num}       = FLOAT          ; Errored frames average high warning value for host input
    errored_frames_curr_host_input_hwarn{lane_num}      = FLOAT          ; Errored frames current high warning value for host input

    ;C-CMIS specific fields
    biasxi_hwarn{lane_num}                             = FLOAT         ; modulator bias xi in percentage (high warning)
    biasxq_hwarn{lane_num}                             = FLOAT         ; modulator bias xq in percentage (high warning)
    biasxp_hwarn{lane_num}                             = FLOAT         ; modulator bias xp in percentage (high warning)
    biasyi_hwarn{lane_num}                             = FLOAT         ; modulator bias yi in percentage (high warning)
    biasyq_hwarn{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high warning)
    biasyp_hwarn{lane_num}                             = FLOAT         ; modulator bias yq in percentage (high warning)
    cdshort_hwar{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (high warning)
    cdlong_hwarn{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (high warning)
    dgd_hwarn{lane_num}                                = FLOAT         ; differential group delay in ps (high warning)
    sopmd_hwarn{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (high warning)
    soproc_hwarn{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (high warning)
    pdl_hwarn{lane_num}                                = FLOAT         ; polarization dependent loss in db (high warning)
    osnr_hwarn{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (high warning)
    esnr_hwarn{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (high warning)
    cfo_hwarn{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (high warning)
    txcurrpower_hwarn{lane_num}                        = FLOAT         ; tx current output power in dbm (high warning)
    rxtotpower_hwarn{lane_num}                         = FLOAT         ; rx total power in  dbm (high warning)
    rxsigpower_hwarn{lane_num}                         = FLOAT         ; rx signal power in dbm (high warning)
```

##### 2.2.2.4 Transceiver VDM low warning threshold data

The `TRANSCEIVER_VDM_LWARN_THRESHOLD` table stores the low warning threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning threshold for a port
    key                                            = TRANSCEIVER_VDM_LWARN_THRESHOLD|ifname    ; information module VDM low warning threshold on port
    ; field                                        = value
    table_last_update_time                              = STR            ; last update time for diagnostic data
    laser_temperature_media_lwarn{lane_num}             = FLOAT          ; laser temperature low warning value in Celsius for media input
    esnr_media_input_lwarn{lane_num}                    = FLOAT          ; eSNR low warning value in dB for media input
    esnr_host_input_lwarn{lane_num}                     = FLOAT          ; eSNR low warning value in dB for host input
    pam4_level_transition_media_input_lwarn{lane_num}   = FLOAT          ; PAM4 level transition low warning value in dB for media input
    pam4_level_transition_host_input_lwarn{lane_num}    = FLOAT          ; PAM4 level transition low warning value in dB for host input
    prefec_ber_min_media_input_lwarn{lane_num}          = FLOAT          ; Pre-FEC BER minimum low warning value for media input
    prefec_ber_max_media_input_lwarn{lane_num}          = FLOAT          ; Pre-FEC BER maximum low warning value for media input
    prefec_ber_avg_media_input_lwarn{lane_num}          = FLOAT          ; Pre-FEC BER average low warning value for media input
    prefec_ber_curr_media_input_lwarn{lane_num}         = FLOAT          ; Pre-FEC BER current low warning value for media input
    prefec_ber_min_host_input_lwarn{lane_num}           = FLOAT          ; Pre-FEC BER minimum low warning value for host input
    prefec_ber_max_host_input_lwarn{lane_num}           = FLOAT          ; Pre-FEC BER maximum low warning value for host input
    prefec_ber_avg_host_input_lwarn{lane_num}           = FLOAT          ; Pre-FEC BER average low warning value for host input
    prefec_ber_curr_host_input_lwarn{lane_num}          = FLOAT          ; Pre-FEC BER current low warning value for host input
    errored_frames_min_media_input_lwarn{lane_num}      = FLOAT          ; Errored frames minimum low warning value for media input
    errored_frames_max_media_input_lwarn{lane_num}      = FLOAT          ; Errored frames maximum low warning value for media input
    errored_frames_avg_media_input_lwarn{lane_num}      = FLOAT          ; Errored frames average low warning value for media input
    errored_frames_curr_media_input_lwarn{lane_num}     = FLOAT          ; Errored frames current low warning value for media input
    errored_frames_min_host_input_lwarn{lane_num}       = FLOAT          ; Errored frames minimum low warning value for host input
    errored_frames_max_host_input_lwarn{lane_num}       = FLOAT          ; Errored frames maximum low warning value for host input
    errored_frames_avg_host_input_lwarn{lane_num}       = FLOAT          ; Errored frames average low warning value for host input
    errored_frames_curr_host_input_lwarn{lane_num}      = FLOAT          ; Errored frames current low warning value for host input

    ;C-CMIS specific fields
    biasxi_lwarn{lane_num}                             = FLOAT         ; modulator bias xi in percentage (low warning)
    biasxq_lwarn{lane_num}                             = FLOAT         ; modulator bias xq in percentage (low warning)
    biasxp_lwarn{lane_num}                             = FLOAT         ; modulator bias xp in percentage (low warning)
    biasyi_lwarn{lane_num}                             = FLOAT         ; modulator bias yi in percentage (low warning)
    biasyq_lwarn{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low warning)
    biasyp_lwarn{lane_num}                             = FLOAT         ; modulator bias yq in percentage (low warning)
    cdshort_lwarn{lane_num}                            = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (low warning)
    cdlong_lwarn{lane_num}                             = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (low warning)
    dgd_lwarn{lane_num}                                = FLOAT         ; differential group delay in ps (low warning)
    sopmd_lwarn{lane_num}                              = FLOAT         ; second order polarization mode dispersion in ps^2 (low warning)
    soproc_lwarn{lane_num}                             = FLOAT         ; state of polarization rate of change in krad/s (low warning)
    pdl_lwarn{lane_num}                                = FLOAT         ; polarization dependent loss in db (low warning)
    osnr_lwarn{lane_num}                               = FLOAT         ; optical signal to noise ratio in db (low warning)
    esnr_lwarn{lane_num}                               = FLOAT         ; electrical signal to noise ratio in db (low warning)
    cfo_lwarn{lane_num}                                = FLOAT         ; carrier frequency offset in Hz (low warning)
    txcurrpower_lwarn{lane_num}                        = FLOAT         ; tx current output power in dbm (low warning)
    rxtotpower_lwarn{lane_num}                         = FLOAT         ; rx total power in  dbm (low warning)
    rxsigpower_lwarn{lane_num}                         = FLOAT         ; rx signal power in dbm (low warning)
```

#### 2.2.3 Transceiver VDM flag data

##### 2.2.3.1 Transceiver VDM high alarm flag data

The `TRANSCEIVER_VDM_HALARM_FLAG` table stores the flag status for the VDM data.

```plaintext
    ;Defines Transceiver VDM high alarm flag for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG|ifname
    ; field                      = value
    table_last_update_time                               = STR     ; last update time for diagnostic data
    laser_temperature_media_halarm{lane_num}             = BOOLEAN ; laser temperature high alarm flag for media input
    esnr_media_input_halarm{lane_num}                    = BOOLEAN ; eSNR high alarm flag for media input
    esnr_host_input_halarm{lane_num}                     = BOOLEAN ; eSNR high alarm flag for host input
    pam4_level_transition_media_input_halarm{lane_num}   = BOOLEAN ; PAM4 level transition high alarm flag for media input
    pam4_level_transition_host_input_halarm{lane_num}    = BOOLEAN ; PAM4 level transition high alarm flag for host input
    prefec_ber_min_media_input_halarm{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high alarm flag for media input
    prefec_ber_max_media_input_halarm{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high alarm flag for media input
    prefec_ber_avg_media_input_halarm{lane_num}          = BOOLEAN ; Pre-FEC BER average high alarm flag for media input
    prefec_ber_curr_media_input_halarm{lane_num}         = BOOLEAN ; Pre-FEC BER current high alarm flag for media input
    prefec_ber_min_host_input_halarm{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high alarm flag for host input
    prefec_ber_max_host_input_halarm{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high alarm flag for host input
    prefec_ber_avg_host_input_halarm{lane_num}           = BOOLEAN ; Pre-FEC BER average high alarm flag for host input
    prefec_ber_curr_host_input_halarm{lane_num}          = BOOLEAN ; Pre-FEC BER current high alarm flag for host input
    errored_frames_min_media_input_halarm{lane_num}      = BOOLEAN ; Errored frames minimum high alarm flag for media input
    errored_frames_max_media_input_halarm{lane_num}      = BOOLEAN ; Errored frames maximum high alarm flag for media input
    errored_frames_avg_media_input_halarm{lane_num}      = BOOLEAN ; Errored frames average high alarm flag for media input
    errored_frames_curr_media_input_halarm{lane_num}     = BOOLEAN ; Errored frames current high alarm flag for media input
    errored_frames_min_host_input_halarm{lane_num}       = BOOLEAN ; Errored frames minimum high alarm flag for host input
    errored_frames_max_host_input_halarm{lane_num}       = BOOLEAN ; Errored frames maximum high alarm flag for host input
    errored_frames_avg_host_input_halarm{lane_num}       = BOOLEAN ; Errored frames average high alarm flag for host input
    errored_frames_curr_host_input_halarm{lane_num}      = BOOLEAN ; Errored frames current high alarm flag for host input

    ;C-CMIS specific fields
    biasxi_halarm{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (high alarm flag)
    biasxq_halarm{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (high alarm flag)
    biasxp_halarm{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (high alarm flag)
    biasyi_halarm{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (high alarm flag)
    biasyq_halarm{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high alarm flag)
    biasyp_halarm{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high alarm flag)
    cdshort_halarm{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (high alarm flag)
    cdlong_halarm{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (high alarm flag)
    dgd_halarm{lane_num}                                 = BOOLEAN ; differential group delay in ps (high alarm flag)
    sopmd_halarm{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (high alarm flag)
    soproc_halarm{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (high alarm flag)
    pdl_halarm{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (high alarm flag)
    osnr_halarm{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (high alarm flag)
    esnr_halarm{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (high alarm flag)
    cfo_halarm{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (high alarm flag)
    txcurrpower_halarm{lane_num}                         = BOOLEAN ; tx current output power in dbm (high alarm flag)
    rxtotpower_halarm{lane_num}                          = BOOLEAN ; rx total power in  dbm (high alarm flag)
    rxsigpower_halarm{lane_num}                          = BOOLEAN; rx signal power in dbm (high alarm flag)
```

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

##### 2.2.3.2 Transceiver VDM low alarm flag data

The `TRANSCEIVER_VDM_LALARM_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm flag for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG|ifname
    ; field                      = value
    table_last_update_time                               = STR     ; last update time for diagnostic data
    laser_temperature_media_lalarm{lane_num}             = BOOLEAN ; laser temperature low alarm flag for media input
    esnr_media_input_lalarm{lane_num}                    = BOOLEAN ; eSNR low alarm flag for media input
    esnr_host_input_lalarm{lane_num}                     = BOOLEAN ; eSNR low alarm flag for host input
    pam4_level_transition_media_input_lalarm{lane_num}   = BOOLEAN ; PAM4 level transition low alarm flag for media input
    pam4_level_transition_host_input_lalarm{lane_num}    = BOOLEAN ; PAM4 level transition low alarm flag for host input
    prefec_ber_min_media_input_lalarm{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low alarm flag for media input
    prefec_ber_max_media_input_lalarm{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low alarm flag for media input
    prefec_ber_avg_media_input_lalarm{lane_num}          = BOOLEAN ; Pre-FEC BER average low alarm flag for media input
    prefec_ber_curr_media_input_lalarm{lane_num}         = BOOLEAN ; Pre-FEC BER current low alarm flag for media input
    prefec_ber_min_host_input_lalarm{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low alarm flag for host input
    prefec_ber_max_host_input_lalarm{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low alarm flag for host input
    prefec_ber_avg_host_input_lalarm{lane_num}           = BOOLEAN ; Pre-FEC BER average low alarm flag for host input
    prefec_ber_curr_host_input_lalarm{lane_num}          = BOOLEAN ; Pre-FEC BER current low alarm flag for host input
    errored_frames_min_media_input_lalarm{lane_num}      = BOOLEAN ; Errored frames minimum low alarm flag for media input
    errored_frames_max_media_input_lalarm{lane_num}      = BOOLEAN ; Errored frames maximum low alarm flag for media input
    errored_frames_avg_media_input_lalarm{lane_num}      = BOOLEAN ; Errored frames average low alarm flag for media input
    errored_frames_curr_media_input_lalarm{lane_num}     = BOOLEAN ; Errored frames current low alarm flag for media input
    errored_frames_min_host_input_lalarm{lane_num}       = BOOLEAN ; Errored frames minimum low alarm flag for host input
    errored_frames_max_host_input_lalarm{lane_num}       = BOOLEAN ; Errored frames maximum low alarm flag for host input
    errored_frames_avg_host_input_lalarm{lane_num}       = BOOLEAN ; Errored frames average low alarm flag for host input
    errored_frames_curr_host_input_lalarm{lane_num}      = BOOLEAN ; Errored frames current low alarm flag for host input

    ;C-CMIS specific fields
    biasxi_lalarm{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (low alarm flag)
    biasxq_lalarm{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (low alarm flag)
    biasxp_lalarm{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (low alarm flag)
    biasyi_lalarm{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (low alarm flag)
    biasyq_lalarm{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low alarm flag)
    biasyp_lalarm{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low alarm flag)
    cdshort_lalarm{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (low alarm flag)
    cdlong_lalarm{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (low alarm flag)
    dgd_lalarm{lane_num}                                 = BOOLEAN ; differential group delay in ps (low alarm flag)
    sopmd_lalarm{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (low alarm flag)
    soproc_lalarm{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (low alarm flag)
    pdl_lalarm{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (low alarm flag)
    osnr_lalarm{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (low alarm flag)
    esnr_lalarm{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (low alarm flag)
    cfo_lalarm{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (low alarm flag)
    txcurrpower_lalarm{lane_num}                         = BOOLEAN ; tx current output power in dbm (low alarm flag)
    rxtotpower_lalarm{lane_num}                          = BOOLEAN ; rx total power in  dbm (low alarm flag)
    rxsigpower_lalarm{lane_num}                          = BOOLEAN; rx signal power in dbm (low alarm flag)
```

##### 2.2.3.3 Transceiver VDM high warning flag data

The `TRANSCEIVER_VDM_HWARN_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning flag for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG|ifname
    ; field                      = value
    table_last_update_time                              = STR     ; last update time for diagnostic data
    laser_temperature_media_hwarn{lane_num}             = BOOLEAN ; laser temperature high warning flag for media input
    esnr_media_input_hwarn{lane_num}                    = BOOLEAN ; eSNR high warning flag for media input
    esnr_host_input_hwarn{lane_num}                     = BOOLEAN ; eSNR high warning flag for host input
    pam4_level_transition_media_input_hwarn{lane_num}   = BOOLEAN ; PAM4 level transition high warning flag for media input
    pam4_level_transition_host_input_hwarn{lane_num}    = BOOLEAN ; PAM4 level transition high warning flag for host input
    prefec_ber_min_media_input_hwarn{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high warning flag for media input
    prefec_ber_max_media_input_hwarn{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high warning flag for media input
    prefec_ber_avg_media_input_hwarn{lane_num}          = BOOLEAN ; Pre-FEC BER average high warning flag for media input
    prefec_ber_curr_media_input_hwarn{lane_num}         = BOOLEAN ; Pre-FEC BER current high warning flag for media input
    prefec_ber_min_host_input_hwarn{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high warning flag for host input
    prefec_ber_max_host_input_hwarn{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high warning flag for host input
    prefec_ber_avg_host_input_hwarn{lane_num}           = BOOLEAN ; Pre-FEC BER average high warning flag for host input
    prefec_ber_curr_host_input_hwarn{lane_num}          = BOOLEAN ; Pre-FEC BER current high warning flag for host input
    errored_frames_min_media_input_hwarn{lane_num}      = BOOLEAN ; Errored frames minimum high warning flag for media input
    errored_frames_max_media_input_hwarn{lane_num}      = BOOLEAN ; Errored frames maximum high warning flag for media input
    errored_frames_avg_media_input_hwarn{lane_num}      = BOOLEAN ; Errored frames average high warning flag for media input
    errored_frames_curr_media_input_hwarn{lane_num}     = BOOLEAN ; Errored frames current high warning flag for media input
    errored_frames_min_host_input_hwarn{lane_num}       = BOOLEAN ; Errored frames minimum high warning flag for host input
    errored_frames_max_host_input_hwarn{lane_num}       = BOOLEAN ; Errored frames maximum high warning flag for host input
    errored_frames_avg_host_input_hwarn{lane_num}       = BOOLEAN ; Errored frames average high warning flag for host input
    errored_frames_curr_host_input_hwarn{lane_num}      = BOOLEAN ; Errored frames current high warning flag for host input

    ;C-CMIS specific fields
    biasxi_hwarn{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (high warning flag)
    biasxq_hwarn{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (high warning flag)
    biasxp_hwarn{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (high warning flag)
    biasyi_hwarn{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (high warning flag)
    biasyq_hwarn{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high warning flag)
    biasyp_hwarn{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (high warning flag)
    cdshort_hwarn{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (high warning flag)
    cdlong_hwarn{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (high warning flag)
    dgd_hwarn{lane_num}                                 = BOOLEAN ; differential group delay in ps (high warning flag)
    sopmd_hwarn{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (high warning flag)
    soproc_hwarn{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (high warning flag)
    pdl_hwarn{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (high warning flag)
    osnr_hwarn{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (high warning flag)
    esnr_hwarn{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (high warning flag)
    cfo_hwarn{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (high warning flag)
    txcurrpower_hwarn{lane_num}                         = BOOLEAN ; tx current output power in dbm (high warning flag)
    rxtotpower_hwarn{lane_num}                          = BOOLEAN ; rx total power in  dbm (high warning flag)
    rxsigpower_hwarn{lane_num}                          = BOOLEAN; rx signal power in dbm (high warning flag)
```

##### 2.2.3.4 Transceiver VDM low warning flag data

The `TRANSCEIVER_VDM_LWARN_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning flag for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG|ifname
    ; field                      = value
    table_last_update_time                              = STR     ; last update time for diagnostic data
    laser_temperature_media_lwarn{lane_num}             = BOOLEAN ; laser temperature low warning flag for media input
    esnr_media_input_lwarn{lane_num}                    = BOOLEAN ; eSNR low warning flag for media input
    esnr_host_input_lwarn{lane_num}                     = BOOLEAN ; eSNR low warning flag for host input
    pam4_level_transition_media_input_lwarn{lane_num}   = BOOLEAN ; PAM4 level transition low warning flag for media input
    pam4_level_transition_host_input_lwarn{lane_num}    = BOOLEAN ; PAM4 level transition low warning flag for host input
    prefec_ber_min_media_input_lwarn{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low warning flag for media input
    prefec_ber_max_media_input_lwarn{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low warning flag for media input
    prefec_ber_avg_media_input_lwarn{lane_num}          = BOOLEAN ; Pre-FEC BER average low warning flag for media input
    prefec_ber_curr_media_input_lwarn{lane_num}         = BOOLEAN ; Pre-FEC BER current low warning flag for media input
    prefec_ber_min_host_input_lwarn{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low warning flag for host input
    prefec_ber_max_host_input_lwarn{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low warning flag for host input
    prefec_ber_avg_host_input_lwarn{lane_num}           = BOOLEAN ; Pre-FEC BER average low warning flag for host input
    prefec_ber_curr_host_input_lwarn{lane_num}          = BOOLEAN ; Pre-FEC BER current low warning flag for host input
    errored_frames_min_media_input_lwarn{lane_num}      = BOOLEAN ; Errored frames minimum low warning flag for media input
    errored_frames_max_media_input_lwarn{lane_num}      = BOOLEAN ; Errored frames maximum low warning flag for media input
    errored_frames_avg_media_input_lwarn{lane_num}      = BOOLEAN ; Errored frames average low warning flag for media input
    errored_frames_curr_media_input_lwarn{lane_num}     = BOOLEAN ; Errored frames current low warning flag for media input
    errored_frames_min_host_input_lwarn{lane_num}       = BOOLEAN ; Errored frames minimum low warning flag for host input
    errored_frames_max_host_input_lwarn{lane_num}       = BOOLEAN ; Errored frames maximum low warning flag for host input
    errored_frames_avg_host_input_lwarn{lane_num}       = BOOLEAN ; Errored frames average low warning flag for host input
    errored_frames_curr_host_input_lwarn{lane_num}      = BOOLEAN ; Errored frames current low warning flag for host input

    ;C-CMIS specific fields
    biasxi_lwarn{lane_num}                              = BOOLEAN ; modulator bias xi in percentage (low warning flag)
    biasxq_lwarn{lane_num}                              = BOOLEAN ; modulator bias xq in percentage (low warning flag)
    biasxp_lwarn{lane_num}                              = BOOLEAN ; modulator bias xp in percentage (low warning flag)
    biasyi_lwarn{lane_num}                              = BOOLEAN ; modulator bias yi in percentage (low warning flag)
    biasyq_lwarn{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low warning flag)
    biasyp_lwarn{lane_num}                              = BOOLEAN ; modulator bias yq in percentage (low warning flag)
    cdshort_lwarn{lane_num}                             = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (low warning flag)
    cdlong_lwarn{lane_num}                              = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (low warning flag)
    dgd_lwarn{lane_num}                                 = BOOLEAN ; differential group delay in ps (low warning flag)
    sopmd_lwarn{lane_num}                               = BOOLEAN ; second order polarization mode dispersion in ps^2 (low warning flag)
    soproc_lwarn{lane_num}                              = BOOLEAN ; state of polarization rate of change in krad/s (low warning flag)
    pdl_lwarn{lane_num}                                 = BOOLEAN ; polarization dependent loss in db (low warning flag)
    osnr_lwarn{lane_num}                                = BOOLEAN ; optical signal to noise ratio in db (low warning flag)
    esnr_lwarn{lane_num}                                = BOOLEAN ; electrical signal to noise ratio in db (low warning flag)
    cfo_lwarn{lane_num}                                 = BOOLEAN ; carrier frequency offset in Hz (low warning flag)
    txcurrpower_lwarn{lane_num}                         = BOOLEAN ; tx current output power in dbm (low warning flag)
    rxtotpower_lwarn{lane_num}                          = BOOLEAN ; rx total power in  dbm (low warning flag)
    rxsigpower_lwarn{lane_num}                          = BOOLEAN; rx signal power in dbm (low warning flag)
```

#### 2.2.4 Transceiver VDM flag change count data

##### 2.2.4.1 Transceiver VDM high alarm flag change count data

The `TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT` table stores the flag change count for high alarm flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm flag change count for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_halarm{lane_num}             = INTEGER ; laser temperature high alarm flag change count for media input
    esnr_media_input_halarm{lane_num}                    = INTEGER ; eSNR high alarm flag change count for media input
    esnr_host_input_halarm{lane_num}                     = INTEGER ; eSNR high alarm flag change count for host input
    pam4_level_transition_media_input_halarm{lane_num}   = INTEGER ; PAM4 level transition high alarm flag change count for media input
    pam4_level_transition_host_input_halarm{lane_num}    = INTEGER ; PAM4 level transition high alarm flag change count for host input
    prefec_ber_min_media_input_halarm{lane_num}          = INTEGER ; Pre-FEC BER minimum high alarm flag change count for media input
    prefec_ber_max_media_input_halarm{lane_num}          = INTEGER ; Pre-FEC BER maximum high alarm flag change count for media input
    prefec_ber_avg_media_input_halarm{lane_num}          = INTEGER ; Pre-FEC BER average high alarm flag change count for media input
    prefec_ber_curr_media_input_halarm{lane_num}         = INTEGER ; Pre-FEC BER current high alarm flag change count for media input
    prefec_ber_min_host_input_halarm{lane_num}           = INTEGER ; Pre-FEC BER minimum high alarm flag change count for host input
    prefec_ber_max_host_input_halarm{lane_num}           = INTEGER ; Pre-FEC BER maximum high alarm flag change count for host input
    prefec_ber_avg_host_input_halarm{lane_num}           = INTEGER ; Pre-FEC BER average high alarm flag change count for host input
    prefec_ber_curr_host_input_halarm{lane_num}          = INTEGER ; Pre-FEC BER current high alarm flag change count for host input
    errored_frames_min_media_input_halarm{lane_num}      = INTEGER ; Errored frames minimum high alarm flag change count for media input
    errored_frames_max_media_input_halarm{lane_num}      = INTEGER ; Errored frames maximum high alarm flag change count for media input
    errored_frames_avg_media_input_halarm{lane_num}      = INTEGER ; Errored frames average high alarm flag change count for media input
    errored_frames_curr_media_input_halarm{lane_num}     = INTEGER ; Errored frames current high alarm flag change count for media input
    errored_frames_min_host_input_halarm{lane_num}       = INTEGER ; Errored frames minimum high alarm flag change count for host input
    errored_frames_max_host_input_halarm{lane_num}       = INTEGER ; Errored frames maximum high alarm flag change count for host input
    errored_frames_avg_host_input_halarm{lane_num}       = INTEGER ; Errored frames average high alarm flag change count for host input
    errored_frames_curr_host_input_halarm{lane_num}      = INTEGER ; Errored frames current high alarm flag change count for host input

    ;C-CMIS specific fields
    biasxi_halarm{lane_num}                              = INTEGER ; modulator bias xi in percentage (high alarm flag change count)
    biasxq_halarm{lane_num}                              = INTEGER ; modulator bias xq in percentage (high alarm flag change count)
    biasxp_halarm{lane_num}                              = INTEGER ; modulator bias xp in percentage (high alarm flag change count)
    biasyi_halarm{lane_num}                              = INTEGER ; modulator bias yi in percentage (high alarm flag change count)
    biasyq_halarm{lane_num}                              = INTEGER ; modulator bias yq in percentage (high alarm flag change count)
    biasyp_halarm{lane_num}                              = INTEGER ; modulator bias yq in percentage (high alarm flag change count)
    cdshort_halarm{lane_num}                             = INTEGER ; chromatic dispersion, high granularity, short link in ps/nm (high alarm flag change count)
    cdlong_halarm{lane_num}                              = INTEGER ; chromatic dispersion, high granularity, long link in ps/nm (high alarm flag change count)
    dgd_halarm{lane_num}                                 = INTEGER ; differential group delay in ps (high alarm flag change count)
    sopmd_halarm{lane_num}                               = INTEGER ; second order polarization mode dispersion in ps^2 (high alarm flag change count)
    soproc_halarm{lane_num}                              = INTEGER ; state of polarization rate of change in krad/s (high alarm flag change count)
    pdl_halarm{lane_num}                                 = INTEGER ; polarization dependent loss in db (high alarm flag change count)
    osnr_halarm{lane_num}                                = INTEGER ; optical signal to noise ratio in db (high alarm flag change count)
    esnr_halarm{lane_num}                                = INTEGER ; electrical signal to noise ratio in db (high alarm flag change count)
    cfo_halarm{lane_num}                                 = INTEGER ; carrier frequency offset in Hz (high alarm flag change count)
    txcurrpower_halarm{lane_num}                         = INTEGER ; tx current output power in dbm (high alarm flag change count)
    rxtotpower_halarm{lane_num}                          = INTEGER ; rx total power in  dbm (high alarm flag change count)
    rxsigpower_halarm{lane_num}                          = INTEGER; rx signal power in dbm (high alarm flag change count)
```

##### 2.2.4.2 Transceiver VDM low alarm flag change count data

The `TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT` table stores the flag change count for low alarm flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm flag change count for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_lalarm{lane_num}             = INTEGER ; laser temperature low alarm flag change count for media input
    esnr_media_input_lalarm{lane_num}                    = INTEGER ; eSNR low alarm flag change count for media input
    esnr_host_input_lalarm{lane_num}                     = INTEGER ; eSNR low alarm flag change count for host input
    pam4_level_transition_media_input_lalarm{lane_num}   = INTEGER ; PAM4 level transition low alarm flag change count for media input
    pam4_level_transition_host_input_lalarm{lane_num}    = INTEGER ; PAM4 level transition low alarm flag change count for host input
    prefec_ber_min_media_input_lalarm{lane_num}          = INTEGER ; Pre-FEC BER minimum low alarm flag change count for media input
    prefec_ber_max_media_input_lalarm{lane_num}          = INTEGER ; Pre-FEC BER maximum low alarm flag change count for media input
    prefec_ber_avg_media_input_lalarm{lane_num}          = INTEGER ; Pre-FEC BER average low alarm flag change count for media input
    prefec_ber_curr_media_input_lalarm{lane_num}         = INTEGER ; Pre-FEC BER current low alarm flag change count for media input
    prefec_ber_min_host_input_lalarm{lane_num}           = INTEGER ; Pre-FEC BER minimum low alarm flag change count for host input
    prefec_ber_max_host_input_lalarm{lane_num}           = INTEGER ; Pre-FEC BER maximum low alarm flag change count for host input
    prefec_ber_avg_host_input_lalarm{lane_num}           = INTEGER ; Pre-FEC BER average low alarm flag change count for host input
    prefec_ber_curr_host_input_lalarm{lane_num}          = INTEGER ; Pre-FEC BER current low alarm flag change count for host input
    errored_frames_min_media_input_lalarm{lane_num}      = INTEGER ; Errored frames minimum low alarm flag change count for media input
    errored_frames_max_media_input_lalarm{lane_num}      = INTEGER ; Errored frames maximum low alarm flag change count for media input
    errored_frames_avg_media_input_lalarm{lane_num}      = INTEGER ; Errored frames average low alarm flag change count for media input
    errored_frames_curr_media_input_lalarm{lane_num}     = INTEGER ; Errored frames current low alarm flag change count for media input
    errored_frames_min_host_input_lalarm{lane_num}       = INTEGER ; Errored frames minimum low alarm flag change count for host input
    errored_frames_max_host_input_lalarm{lane_num}       = INTEGER ; Errored frames maximum low alarm flag change count for host input
    errored_frames_avg_host_input_lalarm{lane_num}       = INTEGER ; Errored frames average low alarm flag change count for host input
    errored_frames_curr_host_input_lalarm{lane_num}      = INTEGER ; Errored frames current low alarm flag change count for host input

    ;C-CMIS specific fields
    biasxi_lalarm{lane_num}                              = INTEGER ; modulator bias xi in percentage (low alarm flag change count)
    biasxq_lalarm{lane_num}                              = INTEGER ; modulator bias xq in percentage (low alarm flag change count)
    biasxp_lalarm{lane_num}                              = INTEGER ; modulator bias xp in percentage (low alarm flag change count)
    biasyi_lalarm{lane_num}                              = INTEGER ; modulator bias yi in percentage (low alarm flag change count)
    biasyq_lalarm{lane_num}                              = INTEGER ; modulator bias yq in percentage (low alarm flag change count)
    biasyp_lalarm{lane_num}                              = INTEGER ; modulator bias yq in percentage (low alarm flag change count)
    cdshort_lalarm{lane_num}                             = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (low alarm flag change count)
    cdlong_lalarm{lane_num}                              = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (low alarm flag change count)
    dgd_lalarm{lane_num}                                 = INTEGER ; differential group delay in ps (low alarm flag change count)
    sopmd_lalarm{lane_num}                               = INTEGER ; second order polarization mode dispersion in ps^2 (low alarm flag change count)
    soproc_lalarm{lane_num}                              = INTEGER ; state of polarization rate of change in krad/s (low alarm flag change count)
    pdl_lalarm{lane_num}                                 = INTEGER ; polarization dependent loss in db (low alarm flag change count)
    osnr_lalarm{lane_num}                                = INTEGER ; optical signal to noise ratio in db (low alarm flag change count)
    esnr_lalarm{lane_num}                                = INTEGER ; electrical signal to noise ratio in db (low alarm flag change count)
    cfo_lalarm{lane_num}                                 = INTEGER ; carrier frequency offset in Hz (low alarm flag change count)
    txcurrpower_lalarm{lane_num}                         = INTEGER ; tx current output power in dbm (low alarm flag change count)
    rxtotpower_lalarm{lane_num}                          = INTEGER ; rx total power in  dbm (low alarm flag change count)
    rxsigpower_lalarm{lane_num}                          = INTEGER; rx signal power in dbm (low alarm flag change count)
```

##### 2.2.4.3 Transceiver VDM high warning flag change count data

The `TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT` table stores the flag change count for high warning flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning flag change count for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_hwarn{lane_num}             = INTEGER ; laser temperature high warning flag change count for media input
    esnr_media_input_hwarn{lane_num}                    = INTEGER ; eSNR high warning flag change count for media input
    esnr_host_input_hwarn{lane_num}                     = INTEGER ; eSNR high warning flag change count for host input
    pam4_level_transition_media_input_hwarn{lane_num}   = INTEGER ; PAM4 level transition high warning flag change count for media input
    pam4_level_transition_host_input_hwarn{lane_num}    = INTEGER ; PAM4 level transition high warning flag change count for host input
    prefec_ber_min_media_input_hwarn{lane_num}          = INTEGER ; Pre-FEC BER minimum high warning flag change count for media input
    prefec_ber_max_media_input_hwarn{lane_num}          = INTEGER ; Pre-FEC BER maximum high warning flag change count for media input
    prefec_ber_avg_media_input_hwarn{lane_num}          = INTEGER ; Pre-FEC BER average high warning flag change count for media input
    prefec_ber_curr_media_input_hwarn{lane_num}         = INTEGER ; Pre-FEC BER current high warning flag change count for media input
    prefec_ber_min_host_input_hwarn{lane_num}           = INTEGER ; Pre-FEC BER minimum high warning flag change count for host input
    prefec_ber_max_host_input_hwarn{lane_num}           = INTEGER ; Pre-FEC BER maximum high warning flag change count for host input
    prefec_ber_avg_host_input_hwarn{lane_num}           = INTEGER ; Pre-FEC BER average high warning flag change count for host input
    prefec_ber_curr_host_input_hwarn{lane_num}          = INTEGER ; Pre-FEC BER current high warning flag change count for host input
    errored_frames_min_media_input_hwarn{lane_num}      = INTEGER ; Errored frames minimum high warning flag change count for media input
    errored_frames_max_media_input_hwarn{lane_num}      = INTEGER ; Errored frames maximum high warning flag change count for media input
    errored_frames_avg_media_input_hwarn{lane_num}      = INTEGER ; Errored frames average high warning flag change count for media input
    errored_frames_curr_media_input_hwarn{lane_num}     = INTEGER ; Errored frames current high warning flag change count for media input
    errored_frames_min_host_input_hwarn{lane_num}       = INTEGER ; Errored frames minimum high warning flag change count for host input
    errored_frames_max_host_input_hwarn{lane_num}       = INTEGER ; Errored frames maximum high warning flag change count for host input
    errored_frames_avg_host_input_hwarn{lane_num}       = INTEGER ; Errored frames average high warning flag change count for host input
    errored_frames_curr_host_input_hwarn{lane_num}      = INTEGER ; Errored frames current high warning flag change count for host input

    ;C-CMIS specific fields
    biasxi_hwarn                                        = INTEGER ; modulator bias xi in percentage (high warning flag change count)
    biasxq_hwarn                                        = INTEGER ; modulator bias xq in percentage (high warning flag change count)
    biasxp_hwarn                                        = INTEGER ; modulator bias xp in percentage (high warning flag change count)
    biasyi_hwarn                                        = INTEGER ; modulator bias yi in percentage (high warning flag change count)
    biasyq_hwarn                                        = INTEGER ; modulator bias yq in percentage (high warning flag change count)
    biasyp_hwarn                                        = INTEGER ; modulator bias yq in percentage (high warning flag change count)
    cdshort_hwarn                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (high warning flag change count)
    cdlong_hwarn                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (high warning flag change count)
    dgd_hwarn                                           = INTEGER ; differential group delay in ps (high warning flag change count)
    sopmd_hwarn                                         = INTEGER ; second order polarization mode dispersion in ps^2 (high warning flag change count)
    soproc_hwarn                                        = INTEGER ; state of polarization rate of change in krad/s (high warning flag change count)
    pdl_hwarn                                           = INTEGER ; polarization dependent loss in db (high warning flag change count)
    osnr_hwarn                                          = INTEGER ; optical signal to noise ratio in db (high warning flag change count)
    esnr_hwarn                                          = INTEGER ; electrical signal to noise ratio in db (high warning flag change count)
    cfo_hwarn                                           = INTEGER ; carrier frequency offset in Hz (high warning flag change count)
    txcurrpower_hwarn                                   = INTEGER ; tx current output power in dbm (high warning flag change count)
    rxtotpower_hwarn                                    = INTEGER ; rx total power in  dbm (high warning flag change count)
    rxsigpower_hwarn                                    = INTEGER; rx signal power in dbm (high warning flag change count)
```

##### 2.2.4.4 Transceiver VDM low warning flag change count data

The `TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT` table stores the flag change count for low warning flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning flag change count for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_lwarn{lane_num}             = INTEGER ; laser temperature low warning flag change count for media input
    esnr_media_input_lwarn{lane_num}                    = INTEGER ; eSNR low warning flag change count for media input
    esnr_host_input_lwarn{lane_num}                     = INTEGER ; eSNR low warning flag change count for host input
    pam4_level_transition_media_input_lwarn{lane_num}   = INTEGER ; PAM4 level transition low warning flag change count for media input
    pam4_level_transition_host_input_lwarn{lane_num}    = INTEGER ; PAM4 level transition low warning flag change count for host input
    prefec_ber_min_media_input_lwarn{lane_num}          = INTEGER ; Pre-FEC BER minimum low warning flag change count for media input
    prefec_ber_max_media_input_lwarn{lane_num}          = INTEGER ; Pre-FEC BER maximum low warning flag change count for media input
    prefec_ber_avg_media_input_lwarn{lane_num}          = INTEGER ; Pre-FEC BER average low warning flag change count for media input
    prefec_ber_curr_media_input_lwarn{lane_num}         = INTEGER ; Pre-FEC BER current low warning flag change count for media input
    prefec_ber_min_host_input_lwarn{lane_num}           = INTEGER ; Pre-FEC BER minimum low warning flag change count for host input
    prefec_ber_max_host_input_lwarn{lane_num}           = INTEGER ; Pre-FEC BER maximum low warning flag change count for host input
    prefec_ber_avg_host_input_lwarn{lane_num}           = INTEGER ; Pre-FEC BER average low warning flag change count for host input
    prefec_ber_curr_host_input_lwarn{lane_num}          = INTEGER ; Pre-FEC BER current low warning flag change count for host input
    errored_frames_min_media_input_lwarn{lane_num}      = INTEGER ; Errored frames minimum low warning flag change count for media input
    errored_frames_max_media_input_lwarn{lane_num}      = INTEGER ; Errored frames maximum low warning flag change count for media input
    errored_frames_avg_media_input_lwarn{lane_num}      = INTEGER ; Errored frames average low warning flag change count for media input
    errored_frames_curr_media_input_lwarn{lane_num}     = INTEGER ; Errored frames current low warning flag change count for media input
    errored_frames_min_host_input_lwarn{lane_num}       = INTEGER ; Errored frames minimum low warning flag change count for host input
    errored_frames_max_host_input_lwarn{lane_num}       = INTEGER ; Errored frames maximum low warning flag change count for host input
    errored_frames_avg_host_input_lwarn{lane_num}       = INTEGER ; Errored frames average low warning flag change count for host input
    errored_frames_curr_host_input_lwarn{lane_num}      = INTEGER ; Errored frames current low warning flag change count for host input

    ;C-CMIS specific fields
    biasxi_lwarn                                        = INTEGER ; modulator bias xi in percentage (low warning flag change count)
    biasxq_lwarn                                        = INTEGER ; modulator bias xq in percentage (low warning flag change count)
    biasxp_lwarn                                        = INTEGER ; modulator bias xp in percentage (low warning flag change count)
    biasyi_lwarn                                        = INTEGER ; modulator bias yi in percentage (low warning flag change count)
    biasyq_lwarn                                        = INTEGER ; modulator bias yq in percentage (low warning flag change count)
    biasyp_lwarn                                        = INTEGER ; modulator bias yq in percentage (low warning flag change count)
    cdshort_lwarn                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (low warning flag change count)
    cdlong_lwarn                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (low warning flag change count)
    dgd_lwarn                                           = INTEGER ; differential group delay in ps (low warning flag change count)
    sopmd_lwarn                                         = INTEGER ; second order polarization mode dispersion in ps^2 (low warning flag change count)
    soproc_lwarn                                        = INTEGER ; state of polarization rate of change in krad/s (low warning flag change count)
    pdl_lwarn                                           = INTEGER ; polarization dependent loss in db (low warning flag change count)
    osnr_lwarn                                          = INTEGER ; optical signal to noise ratio in db (low warning flag change count)
    esnr_lwarn                                          = INTEGER ; electrical signal to noise ratio in db (low warning flag change count)
    cfo_lwarn                                           = INTEGER ; carrier frequency offset in Hz (low warning flag change count)
    txcurrpower_lwarn                                   = INTEGER ; tx current output power in dbm (low warning flag change count)
    rxtotpower_lwarn                                    = INTEGER ; rx total power in  dbm (low warning flag change count)
    rxsigpower_lwarn                                    = INTEGER; rx signal power in dbm (low warning flag change count)
```

#### 2.2.5 Transceiver VDM flag time set data

##### 2.2.5.1 Transceiver VDM high alarm flag time set data

The `TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME` table stores the last set time for the VDM high alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm last set time for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_halarm{lane_num}             = STR ; laser temperature high alarm last set time for media input
    esnr_media_input_halarm{lane_num}                    = STR ; eSNR high alarm last set time for media input
    esnr_host_input_halarm{lane_num}                     = STR ; eSNR high alarm last set time for host input
    pam4_level_transition_media_input_halarm{lane_num}   = STR ; PAM4 level transition high alarm last set time for media input
    pam4_level_transition_host_input_halarm{lane_num}    = STR ; PAM4 level transition high alarm last set time for host input
    prefec_ber_min_media_input_halarm{lane_num}          = STR ; Pre-FEC BER minimum high alarm last set time for media input
    prefec_ber_max_media_input_halarm{lane_num}          = STR ; Pre-FEC BER maximum high alarm last set time for media input
    prefec_ber_avg_media_input_halarm{lane_num}          = STR ; Pre-FEC BER average high alarm last set time for media input
    prefec_ber_curr_media_input_halarm{lane_num}         = STR ; Pre-FEC BER current high alarm last set time for media input
    prefec_ber_min_host_input_halarm{lane_num}           = STR ; Pre-FEC BER minimum high alarm last set time for host input
    prefec_ber_max_host_input_halarm{lane_num}           = STR ; Pre-FEC BER maximum high alarm last set time for host input
    prefec_ber_avg_host_input_halarm{lane_num}           = STR ; Pre-FEC BER average high alarm last set time for host input
    prefec_ber_curr_host_input_halarm{lane_num}          = STR ; Pre-FEC BER current high alarm last set time for host input
    errored_frames_min_media_input_halarm{lane_num}      = STR ; Errored frames minimum high alarm last set time for media input
    errored_frames_max_media_input_halarm{lane_num}      = STR ; Errored frames maximum high alarm last set time for media input
    errored_frames_avg_media_input_halarm{lane_num}      = STR ; Errored frames average high alarm last set time for media input
    errored_frames_curr_media_input_halarm{lane_num}     = STR ; Errored frames current high alarm last set time for media input
    errored_frames_min_host_input_halarm{lane_num}       = STR ; Errored frames minimum high alarm last set time for host input
    errored_frames_max_host_input_halarm{lane_num}       = STR ; Errored frames maximum high alarm last set time for host input
    errored_frames_avg_host_input_halarm{lane_num}       = STR ; Errored frames average high alarm last set time for host input
    errored_frames_curr_host_input_halarm{lane_num}      = STR ; Errored frames current high alarm last set time for host input

    ;C-CMIS specific fields
    biasxi_halarm{lane_num}                              = STR ; modulator bias xi in percentage (high alarm last set time)
    biasxq_halarm{lane_num}                              = STR ; modulator bias xq in percentage (high alarm last set time)
    biasxp_halarm{lane_num}                              = STR ; modulator bias xp in percentage (high alarm last set time)
    biasyi_halarm{lane_num}                              = STR ; modulator bias yi in percentage (high alarm last set time)
    biasyq_halarm{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last set time)
    biasyp_halarm{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last set time)
    cdshort_halarm{lane_num}                             = STR ; chromatic dispersion, high granularity, short link in ps/nm (high alarm last set time)
    cdlong_halarm{lane_num}                              = STR ; chromatic dispersion, high granularity, long link in ps/nm (high alarm last set time)
    dgd_halarm{lane_num}                                 = STR ; differential group delay in ps (high alarm last set time)
    sopmd_halarm{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (high alarm last set time)
    soproc_halarm{lane_num}                              = STR ; state of polarization rate of change in krad/s (high alarm last set time)
    pdl_halarm{lane_num}                                 = STR ; polarization dependent loss in db (high alarm last set time)
    osnr_halarm{lane_num}                                = STR ; optical signal to noise ratio in db (high alarm last set time)
    esnr_halarm{lane_num}                                = STR ; electrical signal to noise ratio in db (high alarm last set time)
    cfo_halarm{lane_num}                                 = STR ; carrier frequency offset in Hz (high alarm last set time)
    txcurrpower_halarm{lane_num}                         = STR ; tx current output power in dbm (high alarm last set time)
    rxtotpower_halarm{lane_num}                          = STR ; rx total power in  dbm (high alarm last set time)
    rxsigpower_halarm{lane_num}                          = STR; rx signal power in dbm (high alarm last set time)
```

##### 2.2.5.2 Transceiver VDM low alarm flag time set data

The `TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME` table stores the last set time for the VDM low alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm last set time for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_lalarm{lane_num}             = STR ; laser temperature low alarm last set time for media input
    esnr_media_input_lalarm{lane_num}                    = STR ; eSNR low alarm last set time for media input
    esnr_host_input_lalarm{lane_num}                     = STR ; eSNR low alarm last set time for host input
    pam4_level_transition_media_input_lalarm{lane_num}   = STR ; PAM4 level transition low alarm last set time for media input
    pam4_level_transition_host_input_lalarm{lane_num}    = STR ; PAM4 level transition low alarm last set time for host input
    prefec_ber_min_media_input_lalarm{lane_num}          = STR ; Pre-FEC BER minimum low alarm last set time for media input
    prefec_ber_max_media_input_lalarm{lane_num}          = STR ; Pre-FEC BER maximum low alarm last set time for media input
    prefec_ber_avg_media_input_lalarm{lane_num}          = STR ; Pre-FEC BER average low alarm last set time for media input
    prefec_ber_curr_media_input_lalarm{lane_num}         = STR ; Pre-FEC BER current low alarm last set time for media input
    prefec_ber_min_host_input_lalarm{lane_num}           = STR ; Pre-FEC BER minimum low alarm last set time for host input
    prefec_ber_max_host_input_lalarm{lane_num}           = STR ; Pre-FEC BER maximum low alarm last set time for host input
    prefec_ber_avg_host_input_lalarm{lane_num}           = STR ; Pre-FEC BER average low alarm last set time for host input
    prefec_ber_curr_host_input_lalarm{lane_num}          = STR ; Pre-FEC BER current low alarm last set time for host input
    errored_frames_min_media_input_lalarm{lane_num}      = STR ; Errored frames minimum low alarm last set time for media input
    errored_frames_max_media_input_lalarm{lane_num}      = STR ; Errored frames maximum low alarm last set time for media input
    errored_frames_avg_media_input_lalarm{lane_num}      = STR ; Errored frames average low alarm last set time for media input
    errored_frames_curr_media_input_lalarm{lane_num}     = STR ; Errored frames current low alarm last set time for media input
    errored_frames_min_host_input_lalarm{lane_num}       = STR ; Errored frames minimum low alarm last set time for host input
    errored_frames_max_host_input_lalarm{lane_num}       = STR ; Errored frames maximum low alarm last set time for host input
    errored_frames_avg_host_input_lalarm{lane_num}       = STR ; Errored frames average low alarm last set time for host input
    errored_frames_curr_host_input_lalarm{lane_num}      = STR ; Errored frames current low alarm last set time for host input

    ;C-CMIS specific fields
    biasxi_lalarm{lane_num}                              = STR ; modulator bias xi in percentage (low alarm last set time)
    biasxq_lalarm{lane_num}                              = STR ; modulator bias xq in percentage (low alarm last set time)
    biasxp_lalarm{lane_num}                              = STR ; modulator bias xp in percentage (low alarm last set time)
    biasyi_lalarm{lane_num}                              = STR ; modulator bias yi in percentage (low alarm last set time)
    biasyq_lalarm{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last set time)
    biasyp_lalarm{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last set time)
    cdshort_lalarm{lane_num}                             = STR ; chromatic dispersion, low granularity, short link in ps/nm (low alarm last set time)
    cdlong_lalarm{lane_num}                              = STR ; chromatic dispersion, low granularity, long link in ps/nm (low alarm last set time)
    dgd_lalarm{lane_num}                                 = STR ; differential group delay in ps (low alarm last set time)
    sopmd_lalarm{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (low alarm last set time)
    soproc_lalarm{lane_num}                              = STR ; state of polarization rate of change in krad/s (low alarm last set time)
    pdl_lalarm{lane_num}                                 = STR ; polarization dependent loss in db (low alarm last set time)
    osnr_lalarm{lane_num}                                = STR ; optical signal to noise ratio in db (low alarm last set time)
    esnr_lalarm{lane_num}                                = STR ; electrical signal to noise ratio in db (low alarm last set time)
    cfo_lalarm{lane_num}                                 = STR ; carrier frequency offset in Hz (low alarm last set time)
    txcurrpower_lalarm{lane_num}                         = STR ; tx current output power in dbm (low alarm last set time)
    rxtotpower_lalarm{lane_num}                          = STR ; rx total power in  dbm (low alarm last set time)
    rxsigpower_lalarm{lane_num}                          = STR; rx signal power in dbm (low alarm last set time)
```

##### 2.2.5.3 Transceiver VDM high warning flag time set data

The `TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME` table stores the last set time for the VDM high warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning last set time for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_hwarn{lane_num}             = STR ; laser temperature high warning last set time for media input
    esnr_media_input_hwarn{lane_num}                    = STR ; eSNR high warning last set time for media input
    esnr_host_input_hwarn{lane_num}                     = STR ; eSNR high warning last set time for host input
    pam4_level_transition_media_input_hwarn{lane_num}   = STR ; PAM4 level transition high warning last set time for media input
    pam4_level_transition_host_input_hwarn{lane_num}    = STR ; PAM4 level transition high warning last set time for host input
    prefec_ber_min_media_input_hwarn{lane_num}          = STR ; Pre-FEC BER minimum high warning last set time for media input
    prefec_ber_max_media_input_hwarn{lane_num}          = STR ; Pre-FEC BER maximum high warning last set time for media input
    prefec_ber_avg_media_input_hwarn{lane_num}          = STR ; Pre-FEC BER average high warning last set time for media input
    prefec_ber_curr_media_input_hwarn{lane_num}         = STR ; Pre-FEC BER current high warning last set time for media input
    prefec_ber_min_host_input_hwarn{lane_num}           = STR ; Pre-FEC BER minimum high warning last set time for host input
    prefec_ber_max_host_input_hwarn{lane_num}           = STR ; Pre-FEC BER maximum high warning last set time for host input
    prefec_ber_avg_host_input_hwarn{lane_num}           = STR ; Pre-FEC BER average high warning last set time for host input
    prefec_ber_curr_host_input_hwarn{lane_num}          = STR ; Pre-FEC BER current high warning last set time for host input
    errored_frames_min_media_input_hwarn{lane_num}      = STR ; Errored frames minimum high warning last set time for media input
    errored_frames_max_media_input_hwarn{lane_num}      = STR ; Errored frames maximum high warning last set time for media input
    errored_frames_avg_media_input_hwarn{lane_num}      = STR ; Errored frames average high warning last set time for media input
    errored_frames_curr_media_input_hwarn{lane_num}     = STR ; Errored frames current high warning last set time for media input
    errored_frames_min_host_input_hwarn{lane_num}       = STR ; Errored frames minimum high warning last set time for host input
    errored_frames_max_host_input_hwarn{lane_num}       = STR ; Errored frames maximum high warning last set time for host input
    errored_frames_avg_host_input_hwarn{lane_num}       = STR ; Errored frames average high warning last set time for host input
    errored_frames_curr_host_input_hwarn{lane_num}      = STR ; Errored frames current high warning last set time for host input

    ;C-CMIS specific fields
    biasxi_hwarn                                        = STR ; modulator bias xi in percentage (high warning last set time)
    biasxq_hwarn                                        = STR ; modulator bias xq in percentage (high warning last set time)
    biasxp_hwarn                                        = STR ; modulator bias xp in percentage (high warning last set time)
    biasyi_hwarn                                        = STR ; modulator bias yi in percentage (high warning last set time)
    biasyq_hwarn                                        = STR ; modulator bias yq in percentage (high warning last set time)
    biasyp_hwarn                                        = STR ; modulator bias yq in percentage (high warning last set time)
    cdshort_hwarn                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (high warning last set time)
    cdlong_hwarn                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (high warning last set time)
    dgd_hwarn                                           = STR ; differential group delay in ps (high warning last set time)
    sopmd_hwarn                                         = STR ; second order polarization mode dispersion in ps^2 (high warning last set time)
    soproc_hwarn                                        = STR ; state of polarization rate of change in krad/s (high warning last set time)
    pdl_hwarn                                           = STR ; polarization dependent loss in db (high warning last set time)
    osnr_hwarn                                          = STR ; optical signal to noise ratio in db (high warning last set time)
    esnr_hwarn                                          = STR ; electrical signal to noise ratio in db (high warning last set time)
    cfo_hwarn                                           = STR ; carrier frequency offset in Hz (high warning last set time)
    txcurrpower_hwarn                                   = STR ; tx current output power in dbm (high warning last set time)
    rxtotpower_hwarn                                    = STR ; rx total power in  dbm (high warning last set time)
    rxsigpower_hwarn                                    = STR; rx signal power in dbm (high warning last set time)
```

##### 2.2.5.4 Transceiver VDM low warning flag time set data

The `TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME` table stores the last set time for the VDM low warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning last set time for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_lwarn{lane_num}             = STR ; laser temperature low warning last set time for media input
    esnr_media_input_lwarn{lane_num}                    = STR ; eSNR low warning last set time for media input
    esnr_host_input_lwarn{lane_num}                     = STR ; eSNR low warning last set time for host input
    pam4_level_transition_media_input_lwarn{lane_num}   = STR ; PAM4 level transition low warning last set time for media input
    pam4_level_transition_host_input_lwarn{lane_num}    = STR ; PAM4 level transition low warning last set time for host input
    prefec_ber_min_media_input_lwarn{lane_num}          = STR ; Pre-FEC BER minimum low warning last set time for media input
    prefec_ber_max_media_input_lwarn{lane_num}          = STR ; Pre-FEC BER maximum low warning last set time for media input
    prefec_ber_avg_media_input_lwarn{lane_num}          = STR ; Pre-FEC BER average low warning last set time for media input
    prefec_ber_curr_media_input_lwarn{lane_num}         = STR ; Pre-FEC BER current low warning last set time for media input
    prefec_ber_min_host_input_lwarn{lane_num}           = STR ; Pre-FEC BER minimum low warning last set time for host input
    prefec_ber_max_host_input_lwarn{lane_num}           = STR ; Pre-FEC BER maximum low warning last set time for host input
    prefec_ber_avg_host_input_lwarn{lane_num}           = STR ; Pre-FEC BER average low warning last set time for host input
    prefec_ber_curr_host_input_lwarn{lane_num}          = STR ; Pre-FEC BER current low warning last set time for host input
    errored_frames_min_media_input_lwarn{lane_num}      = STR ; Errored frames minimum low warning last set time for media input
    errored_frames_max_media_input_lwarn{lane_num}      = STR ; Errored frames maximum low warning last set time for media input
    errored_frames_avg_media_input_lwarn{lane_num}      = STR ; Errored frames average low warning last set time for media input
    errored_frames_curr_media_input_lwarn{lane_num}     = STR ; Errored frames current low warning last set time for media input
    errored_frames_min_host_input_lwarn{lane_num}       = STR ; Errored frames minimum low warning last set time for host input
    errored_frames_max_host_input_lwarn{lane_num}       = STR ; Errored frames maximum low warning last set time for host input
    errored_frames_avg_host_input_lwarn{lane_num}       = STR ; Errored frames average low warning last set time for host input
    errored_frames_curr_host_input_lwarn{lane_num}      = STR ; Errored frames current low warning last set time for host input

    ;C-CMIS specific fields
    biasxi_lwarn                                        = STR ; modulator bias xi in percentage (low warning last set time)
    biasxq_lwarn                                        = STR ; modulator bias xq in percentage (low warning last set time)
    biasxp_lwarn                                        = STR ; modulator bias xp in percentage (low warning last set time)
    biasyi_lwarn                                        = STR ; modulator bias yi in percentage (low warning last set time)
    biasyq_lwarn                                        = STR ; modulator bias yq in percentage (low warning last set time)
    biasyp_lwarn                                        = STR ; modulator bias yq in percentage (low warning last set time)
    cdshort_lwarn                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low warning last set time)
    cdlong_lwarn                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low warning last set time)
    dgd_lwarn                                           = STR ; differential group delay in ps (low warning last set time)
    sopmd_lwarn                                         = STR ; second order polarization mode dispersion in ps^2 (low warning last set time)
    soproc_lwarn                                        = STR ; state of polarization rate of change in krad/s (low warning last set time)
    pdl_lwarn                                           = STR ; polarization dependent loss in db (low warning last set time)
    osnr_lwarn                                          = STR ; optical signal to noise ratio in db (low warning last set time)
    esnr_lwarn                                          = STR ; electrical signal to noise ratio in db (low warning last set time)
    cfo_lwarn                                           = STR ; carrier frequency offset in Hz (low warning last set time)
    txcurrpower_lwarn                                   = STR ; tx current output power in dbm (low warning last set time)
    rxtotpower_lwarn                                    = STR ; rx total power in  dbm (low warning last set time)
    rxsigpower_lwarn                                    = STR; rx signal power in dbm (low warning last set time)
```

#### 2.2.6 Transceiver VDM flag time clear data

##### 2.2.6.1 Transceiver VDM high alarm flag time clear data

The `TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME` table stores the last clear time for the VDM high alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm last clear time for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_halarm{lane_num}             = STR ; laser temperature high alarm last clear time for media input
    esnr_media_input_halarm{lane_num}                    = STR ; eSNR high alarm last clear time for media input
    esnr_host_input_halarm{lane_num}                     = STR ; eSNR high alarm last clear time for host input
    pam4_level_transition_media_input_halarm{lane_num}   = STR ; PAM4 level transition high alarm last clear time for media input
    pam4_level_transition_host_input_halarm{lane_num}    = STR ; PAM4 level transition high alarm last clear time for host input
    prefec_ber_min_media_input_halarm{lane_num}          = STR ; Pre-FEC BER minimum high alarm last clear time for media input
    prefec_ber_max_media_input_halarm{lane_num}          = STR ; Pre-FEC BER maximum high alarm last clear time for media input
    prefec_ber_avg_media_input_halarm{lane_num}          = STR ; Pre-FEC BER average high alarm last clear time for media input
    prefec_ber_curr_media_input_halarm{lane_num}         = STR ; Pre-FEC BER current high alarm last clear time for media input
    prefec_ber_min_host_input_halarm{lane_num}           = STR ; Pre-FEC BER minimum high alarm last clear time for host input
    prefec_ber_max_host_input_halarm{lane_num}           = STR ; Pre-FEC BER maximum high alarm last clear time for host input
    prefec_ber_avg_host_input_halarm{lane_num}           = STR ; Pre-FEC BER average high alarm last clear time for host input
    prefec_ber_curr_host_input_halarm{lane_num}          = STR ; Pre-FEC BER current high alarm last clear time for host input
    errored_frames_min_media_input_halarm{lane_num}      = STR ; Errored frames minimum high alarm last clear time for media input
    errored_frames_max_media_input_halarm{lane_num}      = STR ; Errored frames maximum high alarm last clear time for media input
    errored_frames_avg_media_input_halarm{lane_num}      = STR ; Errored frames average high alarm last clear time for media input
    errored_frames_curr_media_input_halarm{lane_num}     = STR ; Errored frames current high alarm last clear time for media input
    errored_frames_min_host_input_halarm{lane_num}       = STR ; Errored frames minimum high alarm last clear time for host input
    errored_frames_max_host_input_halarm{lane_num}       = STR ; Errored frames maximum high alarm last clear time for host input
    errored_frames_avg_host_input_halarm{lane_num}       = STR ; Errored frames average high alarm last clear time for host input
    errored_frames_curr_host_input_halarm{lane_num}      = STR ; Errored frames current high alarm last clear time for host input

    ;C-CMIS specific fields
    biasxi_halarm{lane_num}                              = STR ; modulator bias xi in percentage (high alarm last clear time)
    biasxq_halarm{lane_num}                              = STR ; modulator bias xq in percentage (high alarm last clear time)
    biasxp_halarm{lane_num}                              = STR ; modulator bias xp in percentage (high alarm last clear time)
    biasyi_halarm{lane_num}                              = STR ; modulator bias yi in percentage (high alarm last clear time)
    biasyq_halarm{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last clear time)
    biasyp_halarm{lane_num}                              = STR ; modulator bias yq in percentage (high alarm last clear time)
    cdshort_halarm{lane_num}                             = STR ; chromatic dispersion, high granularity, short link in ps/nm (high alarm last clear time)
    cdlong_halarm{lane_num}                              = STR ; chromatic dispersion, high granularity, long link in ps/nm (high alarm last clear time)
    dgd_halarm{lane_num}                                 = STR ; differential group delay in ps (high alarm last clear time)
    sopmd_halarm{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (high alarm last clear time)
    soproc_halarm{lane_num}                              = STR ; state of polarization rate of change in krad/s (high alarm last clear time)
    pdl_halarm{lane_num}                                 = STR ; polarization dependent loss in db (high alarm last clear time)
    osnr_halarm{lane_num}                                = STR ; optical signal to noise ratio in db (high alarm last clear time)
    esnr_halarm{lane_num}                                = STR ; electrical signal to noise ratio in db (high alarm last clear time)
    cfo_halarm{lane_num}                                 = STR ; carrier frequency offset in Hz (high alarm last clear time)
    txcurrpower_halarm{lane_num}                         = STR ; tx current output power in dbm (high alarm last clear time)
    rxtotpower_halarm{lane_num}                          = STR ; rx total power in  dbm (high alarm last clear time)
    rxsigpower_halarm{lane_num}                          = STR; rx signal power in dbm (high alarm last clear time)
```

##### 2.2.6.2 Transceiver VDM low alarm flag time clear data

The `TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME` table stores the last clear time for the VDM low alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm last clear time for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_lalarm{lane_num}             = STR ; laser temperature low alarm last clear time for media input
    esnr_media_input_lalarm{lane_num}                    = STR ; eSNR low alarm last clear time for media input
    esnr_host_input_lalarm{lane_num}                     = STR ; eSNR low alarm last clear time for host input
    pam4_level_transition_media_input_lalarm{lane_num}   = STR ; PAM4 level transition low alarm last clear time for media input
    pam4_level_transition_host_input_lalarm{lane_num}    = STR ; PAM4 level transition low alarm last clear time for host input
    prefec_ber_min_media_input_lalarm{lane_num}          = STR ; Pre-FEC BER minimum low alarm last clear time for media input
    prefec_ber_max_media_input_lalarm{lane_num}          = STR ; Pre-FEC BER maximum low alarm last clear time for media input
    prefec_ber_avg_media_input_lalarm{lane_num}          = STR ; Pre-FEC BER average low alarm last clear time for media input
    prefec_ber_curr_media_input_lalarm{lane_num}         = STR ; Pre-FEC BER current low alarm last clear time for media input
    prefec_ber_min_host_input_lalarm{lane_num}           = STR ; Pre-FEC BER minimum low alarm last clear time for host input
    prefec_ber_max_host_input_lalarm{lane_num}           = STR ; Pre-FEC BER maximum low alarm last clear time for host input
    prefec_ber_avg_host_input_lalarm{lane_num}           = STR ; Pre-FEC BER average low alarm last clear time for host input
    prefec_ber_curr_host_input_lalarm{lane_num}          = STR ; Pre-FEC BER current low alarm last clear time for host input
    errored_frames_min_media_input_lalarm{lane_num}      = STR ; Errored frames minimum low alarm last clear time for media input
    errored_frames_max_media_input_lalarm{lane_num}      = STR ; Errored frames maximum low alarm last clear time for media input
    errored_frames_avg_media_input_lalarm{lane_num}      = STR ; Errored frames average low alarm last clear time for media input
    errored_frames_curr_media_input_lalarm{lane_num}     = STR ; Errored frames current low alarm last clear time for media input
    errored_frames_min_host_input_lalarm{lane_num}       = STR ; Errored frames minimum low alarm last clear time for host input
    errored_frames_max_host_input_lalarm{lane_num}       = STR ; Errored frames maximum low alarm last clear time for host input
    errored_frames_avg_host_input_lalarm{lane_num}       = STR ; Errored frames average low alarm last clear time for host input
    errored_frames_curr_host_input_lalarm{lane_num}      = STR ; Errored frames current low alarm last clear time for host input

    ;C-CMIS specific fields
    biasxi_lalarm{lane_num}                              = STR ; modulator bias xi in percentage (low alarm last clear time)
    biasxq_lalarm{lane_num}                              = STR ; modulator bias xq in percentage (low alarm last clear time)
    biasxp_lalarm{lane_num}                              = STR ; modulator bias xp in percentage (low alarm last clear time)
    biasyi_lalarm{lane_num}                              = STR ; modulator bias yi in percentage (low alarm last clear time)
    biasyq_lalarm{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last clear time)
    biasyp_lalarm{lane_num}                              = STR ; modulator bias yq in percentage (low alarm last clear time)
    cdshort_lalarm{lane_num}                             = STR ; chromatic dispersion, low granularity, short link in ps/nm (low alarm last clear time)
    cdlong_lalarm{lane_num}                              = STR ; chromatic dispersion, low granularity, long link in ps/nm (low alarm last clear time)
    dgd_lalarm{lane_num}                                 = STR ; differential group delay in ps (low alarm last clear time)
    sopmd_lalarm{lane_num}                               = STR ; second order polarization mode dispersion in ps^2 (low alarm last clear time)
    soproc_lalarm{lane_num}                              = STR ; state of polarization rate of change in krad/s (low alarm last clear time)
    pdl_lalarm{lane_num}                                 = STR ; polarization dependent loss in db (low alarm last clear time)
    osnr_lalarm{lane_num}                                = STR ; optical signal to noise ratio in db (low alarm last clear time)
    esnr_lalarm{lane_num}                                = STR ; electrical signal to noise ratio in db (low alarm last clear time)
    cfo_lalarm{lane_num}                                 = STR ; carrier frequency offset in Hz (low alarm last clear time)
    txcurrpower_lalarm{lane_num}                         = STR ; tx current output power in dbm (low alarm last clear time)
    rxtotpower_lalarm{lane_num}                          = STR ; rx total power in  dbm (low alarm last clear time)
    rxsigpower_lalarm{lane_num}                          = STR; rx signal power in dbm (low alarm last clear time)
```

##### 2.2.6.3 Transceiver VDM high warning flag time clear data

The `TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME` table stores the last clear time for the VDM high warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning last clear time for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_hwarn{lane_num}             = STR ; laser temperature high warning last clear time for media input
    esnr_media_input_hwarn{lane_num}                    = STR ; eSNR high warning last clear time for media input
    esnr_host_input_hwarn{lane_num}                     = STR ; eSNR high warning last clear time for host input
    pam4_level_transition_media_input_hwarn{lane_num}   = STR ; PAM4 level transition high warning last clear time for media input
    pam4_level_transition_host_input_hwarn{lane_num}    = STR ; PAM4 level transition high warning last clear time for host input
    prefec_ber_min_media_input_hwarn{lane_num}          = STR ; Pre-FEC BER minimum high warning last clear time for media input
    prefec_ber_max_media_input_hwarn{lane_num}          = STR ; Pre-FEC BER maximum high warning last clear time for media input
    prefec_ber_avg_media_input_hwarn{lane_num}          = STR ; Pre-FEC BER average high warning last clear time for media input
    prefec_ber_curr_media_input_hwarn{lane_num}         = STR ; Pre-FEC BER current high warning last clear time for media input
    prefec_ber_min_host_input_hwarn{lane_num}           = STR ; Pre-FEC BER minimum high warning last clear time for host input
    prefec_ber_max_host_input_hwarn{lane_num}           = STR ; Pre-FEC BER maximum high warning last clear time for host input
    prefec_ber_avg_host_input_hwarn{lane_num}           = STR ; Pre-FEC BER average high warning last clear time for host input
    prefec_ber_curr_host_input_hwarn{lane_num}          = STR ; Pre-FEC BER current high warning last clear time for host input
    errored_frames_min_media_input_hwarn{lane_num}      = STR ; Errored frames minimum high warning last clear time for media input
    errored_frames_max_media_input_hwarn{lane_num}      = STR ; Errored frames maximum high warning last clear time for media input
    errored_frames_avg_media_input_hwarn{lane_num}      = STR ; Errored frames average high warning last clear time for media input
    errored_frames_curr_media_input_hwarn{lane_num}     = STR ; Errored frames current high warning last clear time for media input
    errored_frames_min_host_input_hwarn{lane_num}       = STR ; Errored frames minimum high warning last clear time for host input
    errored_frames_max_host_input_hwarn{lane_num}       = STR ; Errored frames maximum high warning last clear time for host input
    errored_frames_avg_host_input_hwarn{lane_num}       = STR ; Errored frames average high warning last clear time for host input
    errored_frames_curr_host_input_hwarn{lane_num}      = STR ; Errored frames current high warning last clear time for host input

    ;C-CMIS specific fields
    biasxi_hwarn                                        = STR ; modulator bias xi in percentage (high warning last clear time)
    biasxq_hwarn                                        = STR ; modulator bias xq in percentage (high warning last clear time)
    biasxp_hwarn                                        = STR ; modulator bias xp in percentage (high warning last clear time)
    biasyi_hwarn                                        = STR ; modulator bias yi in percentage (high warning last clear time)
    biasyq_hwarn                                        = STR ; modulator bias yq in percentage (high warning last clear time)
    biasyp_hwarn                                        = STR ; modulator bias yq in percentage (high warning last clear time)
    cdshort_hwarn                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (high warning last clear time)
    cdlong_hwarn                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (high warning last clear time)
    dgd_hwarn                                           = STR ; differential group delay in ps (high warning last clear time)
    sopmd_hwarn                                         = STR ; second order polarization mode dispersion in ps^2 (high warning last clear time)
    soproc_hwarn                                        = STR ; state of polarization rate of change in krad/s (high warning last clear time)
    pdl_hwarn                                           = STR ; polarization dependent loss in db (high warning last clear time)
    osnr_hwarn                                          = STR ; optical signal to noise ratio in db (high warning last clear time)
    esnr_hwarn                                          = STR ; electrical signal to noise ratio in db (high warning last clear time)
    cfo_hwarn                                           = STR ; carrier frequency offset in Hz (high warning last clear time)
    txcurrpower_hwarn                                   = STR ; tx current output power in dbm (high warning last clear time)
    rxtotpower_hwarn                                    = STR ; rx total power in  dbm (high warning last clear time)
    rxsigpower_hwarn                                    = STR; rx signal power in dbm (high warning last clear time)
```

##### 2.2.6.4 Transceiver VDM low warning flag time clear data

The `TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME` table stores the last clear time for the VDM low warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning last clear time for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_lwarn{lane_num}             = STR ; laser temperature low warning last clear time for media input
    esnr_media_input_lwarn{lane_num}                    = STR ; eSNR low warning last clear time for media input
    esnr_host_input_lwarn{lane_num}                     = STR ; eSNR low warning last clear time for host input
    pam4_level_transition_media_input_lwarn{lane_num}   = STR ; PAM4 level transition low warning last clear time for media input
    pam4_level_transition_host_input_lwarn{lane_num}    = STR ; PAM4 level transition low warning last clear time for host input
    prefec_ber_min_media_input_lwarn{lane_num}          = STR ; Pre-FEC BER minimum low warning last clear time for media input
    prefec_ber_max_media_input_lwarn{lane_num}          = STR ; Pre-FEC BER maximum low warning last clear time for media input
    prefec_ber_avg_media_input_lwarn{lane_num}          = STR ; Pre-FEC BER average low warning last clear time for media input
    prefec_ber_curr_media_input_lwarn{lane_num}         = STR ; Pre-FEC BER current low warning last clear time for media input
    prefec_ber_min_host_input_lwarn{lane_num}           = STR ; Pre-FEC BER minimum low warning last clear time for host input
    prefec_ber_max_host_input_lwarn{lane_num}           = STR ; Pre-FEC BER maximum low warning last clear time for host input
    prefec_ber_avg_host_input_lwarn{lane_num}           = STR ; Pre-FEC BER average low warning last clear time for host input
    prefec_ber_curr_host_input_lwarn{lane_num}          = STR ; Pre-FEC BER current low warning last clear time for host input
    errored_frames_min_media_input_lwarn{lane_num}      = STR ; Errored frames minimum low warning last clear time for media input
    errored_frames_max_media_input_lwarn{lane_num}      = STR ; Errored frames maximum low warning last clear time for media input
    errored_frames_avg_media_input_lwarn{lane_num}      = STR ; Errored frames average low warning last clear time for media input
    errored_frames_curr_media_input_lwarn{lane_num}     = STR ; Errored frames current low warning last clear time for media input
    errored_frames_min_host_input_lwarn{lane_num}       = STR ; Errored frames minimum low warning last clear time for host input
    errored_frames_max_host_input_lwarn{lane_num}       = STR ; Errored frames maximum low warning last clear time for host input
    errored_frames_avg_host_input_lwarn{lane_num}       = STR ; Errored frames average low warning last clear time for host input
    errored_frames_curr_host_input_lwarn{lane_num}      = STR ; Errored frames current low warning last clear time for host input

    ;C-CMIS specific fields
    biasxi_lwarn                                        = STR ; modulator bias xi in percentage (low warning last clear time)
    biasxq_lwarn                                        = STR ; modulator bias xq in percentage (low warning last clear time)
    biasxp_lwarn                                        = STR ; modulator bias xp in percentage (low warning last clear time)
    biasyi_lwarn                                        = STR ; modulator bias yi in percentage (low warning last clear time)
    biasyq_lwarn                                        = STR ; modulator bias yq in percentage (low warning last clear time)
    biasyp_lwarn                                        = STR ; modulator bias yq in percentage (low warning last clear time)
    cdshort_lwarn                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low warning last clear time)
    cdlong_lwarn                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low warning last clear time)
    dgd_lwarn                                           = STR ; differential group delay in ps (low warning last clear time)
    sopmd_lwarn                                         = STR ; second order polarization mode dispersion in ps^2 (low warning last clear time)
    soproc_lwarn                                        = STR ; state of polarization rate of change in krad/s (low warning last clear time)
    pdl_lwarn                                           = STR ; polarization dependent loss in db (low warning last clear time)
    osnr_lwarn                                          = STR ; optical signal to noise ratio in db (low warning last clear time)
    esnr_lwarn                                          = STR ; electrical signal to noise ratio in db (low warning last clear time)
    cfo_lwarn                                           = STR ; carrier frequency offset in Hz (low warning last clear time)
    txcurrpower_lwarn                                   = STR ; tx current output power in dbm (low warning last clear time)
    rxtotpower_lwarn                                    = STR ; rx total power in  dbm (low warning last clear time)
    rxsigpower_lwarn                                    = STR; rx signal power in dbm (low warning last clear time)
```

### 2.3 Transceiver status data

#### 2.3.1 Transceiver status data to store module and data path status

The `TRANSCEIVER_STATUS` table stores the status of the transceiver.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS|ifname        ; Error information for module on port
    ; field                                 = value
    cmis_state                              = 1*255VCHAR        ; Software CMIS state of the module
    status                                  = 1*255VCHAR        ; code of the module status (plug in, plug out)
    error                                   = 1*255VCHAR        ; module error (N/A or a string consisting of error descriptions joined by "|", like "error1 | error2" )
    diagnostics_update_interval             = INTEGER           ; DOM thread update interval in seconds
    table_last_update_time                  = STR               ; last update time for diagnostic data
    module_state                            = 1*255VCHAR        ; current module state (ModuleLowPwr, ModulePwrUp, ModuleReady, ModulePwrDn, Fault)
    module_fault_cause                      = 1*255VCHAR        ; reason of entering the module fault state
    DP{lane_num}State                       = 1*255VCHAR        ; data path state indicator on host lane {lane_num}
    txoutput_status{lane_num}               = BOOLEAN           ; tx output status on media lane {lane_num}
    rxoutput_status_hostlane{lane_num}      = BOOLEAN           ; rx output status on host lane {lane_num}
    tx{lane_num}disable                     = BOOLEAN           ; TX disable state on media lane {lane_num}
    tx_disabled_channel                     = INTEGER           ; TX disable field
    config_state_hostlane{lane_num}         = 1*255VCHAR        ; configuration status for the data path of host line {lane_num}
    dpdeinit_hostlane{lane_num}             = BOOLEAN           ; data path deinitialized status on host lane {lane_num}
    dpinit_pending_hostlane{lane_num}       = BOOLEAN           ; data path configuration updated on host lane {lane_num}
    tuning_in_progress                      = BOOLEAN           ; tuning in progress status
    wavelength_unlock_status                = BOOLEAN           ; laser unlocked status
```

#### 2.3.2 Transceiver status data to store module and data path flag status

The `TRANSCEIVER_STATUS_FLAG` table stores the status of the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS_FLAG|ifname        ; Flag information for module on port
    ; field                                 = value
    table_last_update_time                  = STR               ; last update time for diagnostic data
    datapath_firmware_fault                 = BOOLEAN           ; datapath (DSP) firmware fault
    module_firmware_fault                   = BOOLEAN           ; module firmware fault
    module_state_changed                    = BOOLEAN           ; module state changed
    txfault{lane_num}                       = BOOLEAN           ; tx fault flag on media lane {lane_num}
    txlos_hostlane{lane_num}                = BOOLEAN           ; tx loss of signal flag on host lane {lane_num}
    txcdrlol_hostlane{lane_num}             = BOOLEAN           ; tx clock and data recovery loss of lock flag on host lane {lane_num}
    tx_eq_fault{lane_num}                   = BOOLEAN           ; tx equalization fault flag on host lane {lane_num}
    rxlos{lane_num}                         = BOOLEAN           ; rx loss of signal flag on media lane {lane_num}
    rxcdrlol{lane_num}                      = BOOLEAN           ; rx clock and data recovery loss of lock flag on media lane {lane_num}
    target_output_power_oor                 = BOOLEAN           ; target output power out of range flag
    fine_tuning_oor                         = BOOLEAN           ; fine tuning  out of range flag
    tuning_not_accepted                     = BOOLEAN           ; tuning not accepted flag
    invalid_channel_num                     = BOOLEAN           ; invalid channel number flag
    tuning_complete                         = BOOLEAN           ; tuning complete flag
```

#### 2.3.3 Transceiver status data to store module and data path change count

The `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` table stores the change count for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                     = TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT|ifname        ; Flag information for module on port
    ; field                                 = value
    datapath_firmware_fault           = INTEGER           ; datapath (DSP) firmware fault change count
    module_firmware_fault             = INTEGER           ; module firmware fault change count
    module_state_changed              = INTEGER           ; module state changed change count
    txfault{lane_num}                 = INTEGER           ; tx fault flag on media lane {lane_num} change count
    txlos_hostlane{lane_num}          = INTEGER           ; tx loss of signal flag on host lane {lane_num} change count
    txcdrlol_hostlane{lane_num}       = INTEGER           ; tx clock and data recovery loss of lock flag on host lane {lane_num} change count
    tx_eq_fault{lane_num}             = INTEGER           ; tx equalization fault flag on host lane {lane_num} change count
    rxlos{lane_num}                   = INTEGER           ; rx loss of signal flag on media lane {lane_num} change count
    rxcdrlol{lane_num}                = INTEGER           ; rx clock and data recovery loss of lock flag on media lane {lane_num} change count
    target_output_power_oor           = INTEGER           ; target output power out of range flag change count
    fine_tuning_oor                   = INTEGER           ; fine tuning  out of range flag change count
    tuning_not_accepted               = INTEGER           ; tuning not accepted flag change count
    invalid_channel_num               = INTEGER           ; invalid channel number flag change count
    tuning_complete                   = INTEGER           ; tuning complete flag change count
```

#### 2.3.4 Transceiver status data to store module and data path flag set time

The `TRANSCEIVER_STATUS_FLAG_SET_TIME` table stores the last set time for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                        = TRANSCEIVER_STATUS_FLAG_SET_TIME|ifname        ; Flag information for module on port
    ; field                                    = value
    datapath_firmware_fault      = STR           ; datapath (DSP) firmware fault set time
    module_firmware_fault        = STR           ; module firmware fault set time
    module_state_changed         = STR           ; module state changed set time
    txfault{lane_num}            = STR           ; tx fault flag on media lane {lane_num} set time
    txlos_hostlane{lane_num}     = STR           ; tx loss of signal flag on host lane {lane_num} set time
    txcdrlol_hostlane{lane_num}  = STR           ; tx clock and data recovery loss of lock flag on host lane {lane_num} set time
    tx_eq_fault{lane_num}        = STR           ; tx equalization fault flag on host lane {lane_num} set time
    rxlos{lane_num}              = STR           ; rx loss of signal flag on media lane {lane_num} set time
    rxcdrlol{lane_num}           = STR           ; rx clock and data recovery loss of lock flag on media lane {lane_num} set time
    target_output_power_oor      = STR           ; target output power out of range flag set time
    fine_tuning_oor              = STR           ; fine tuning  out of range flag set time
    tuning_not_accepted          = STR           ; tuning not accepted flag set time
    invalid_channel_num          = STR           ; invalid channel number flag set time
    tuning_complete              = STR           ; tuning complete flag set time
```

#### 2.3.5 Transceiver status data to store module and data path flag clear time

The `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` table stores the last clear time for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                        = TRANSCEIVER_STATUS_FLAG_CLEAR_TIME|ifname        ; Flag information for module on port
    ; field                                    = value
    datapath_firmware_fault           = STR           ; datapath (DSP) firmware fault clear time
    module_firmware_fault             = STR           ; module firmware fault clear time
    module_state_changed              = STR           ; module state changed clear time
    txfault{lane_num}                 = STR           ; tx fault flag on media lane {lane_num} clear time
    txlos_hostlane{lane_num}          = STR           ; tx loss of signal flag on host lane {lane_num} clear time
    txcdrlol_hostlane{lane_num}       = STR           ; tx clock and data recovery loss of lock flag on host lane {lane_num} clear time
    tx_eq_fault{lane_num}             = STR           ; tx equalization fault flag on host lane {lane_num} clear time
    rxlos{lane_num}                   = STR           ; rx loss of signal flag on media lane {lane_num} clear time
    rxcdrlol{lane_num}                = STR           ; rx clock and data recovery loss of lock flag on media lane {lane_num} clear time
    target_output_power_last_oor_clear_time           = STR           ; target output power out of range flag clear time
    fine_tuning_oor                   = STR           ; fine tuning  out of range flag clear time
    tuning_not_accepted               = STR           ; tuning not accepted flag clear time
    invalid_channel_num               = STR           ; invalid channel number flag clear time
    tuning_complete                   = STR           ; tuning complete flag clear time
```

### 2.4 Transceiver PM data

The `TRANSCEIVER_PM` table stores the performance monitoring data of the transceiver. This table is exists only for C-CMIS transceivers.

```plaintext
    ; Defines Transceiver PM information for a port
    key                          = TRANSCEIVER_PM|ifname            ; information of PM on port
    ; field                      = value 
    table_last_update_time       = STR                              ; last update time for diagnostic data
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

For devices with breakout ports, the CLI handler will always fetch diagnostic monitoring data from the first port of the breakout group.

### 3.1 CLI Commands for DOM Monitoring

#### 3.1.1 `show interfaces transceiver dom PORT`

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

#### 3.1.2 `show interfaces transceiver dom flag PORT`

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

### 3.2 CLI Commands for VDM Monitoring

#### 3.2.1 `show interfaces transceiver vdm PORT`

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

#### 3.2.2 `show interfaces transceiver vdm flag PORT`

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

##### 3.2.2.1 VDM flags dump using the `--detail` option

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

### 3.3 CLI Commands for transceiver status monitoring

#### 3.3.1 `show interfaces transceiver status PORT`

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
```

#### 3.3.2 `show interfaces transceiver status flag PORT`

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

## 4. SONiC CMIS diagnostic monitoring workflow

### 4.1 Static Diagnostic Information

The `SfpStateUpdateTask` thread is responsible for updating the static diagnostic information for all the transceivers in the system. The static diagnostic information, such as threshold values for DOM, VDM and PM, are read from the transceiver and updated in the `redis-db` during `xcvrd` boot-up and during transceiver removal and insertion.

The following tables are updated by the `SfpStateUpdateTask` thread:

1. `TRANSCEIVER_DOM_THRESHOLD`
2. `TRANSCEIVER_VDM_XXX_THRESHOLD` where `XXX` is the threshold type (`highalarm`, `highwarning`, `lowwarning`, `lowalarm`)

### 4.2 Dynamic Diagnostic Information

The `DomInfoUpdateTask` thread is responsible for updating the dynamic diagnostic information for all the transceivers in the system. The following events drive the dynamic update of the diagnostic information:

1. **Periodic update of the diagnostic information:**
    - The `DomInfoUpdateTask` thread periodically updates the diagnostic information for all the ports.
    - The update period interval can be retrieved by reading the `dom_info_update_periodic_secs` field from the `/usr/share/sonic/device/{platform}/{hwsku}/pmon_daemon_control.json` file.
    - If this field or the file is absent, the default timer value is 0 seconds.

2. **Link change event:**
    - Only the **flag-related diagnostic information** is updated for a port when a link change event is detected by the `DomInfoUpdateTask` thread. Further details on the tables updated during a link change event are provided in the `Diagnostic Information Update During Link Change Event` section.
    - This ensures that the flag change time is updated during a link change event, as the periodic update through the `DomInfoUpdateTask` thread can take more time to update the diagnostic information since it reads the diagnostic information for all the ports in a sequential manner.

#### 4.2.1 High-Level Steps for Updating Dynamic Diagnostic Information

1. The `DomInfoUpdateTask` thread is created by the `xcvrd` process.
2. The `dom_info_update_periodic_secs` value is retrieved from the `pmon_daemon_control.json` file to determine the interval for updating the diagnostic information for all the ports. If the `dom_info_update_periodic_secs` field is absent or set to 0, the diagnostic information will be updated continuously without any delay between updates.
3. The `DomInfoUpdateTask` thread starts polling for the diagnostic information of the ports in a sequential manner:
    - It first checks if the `dom_info_update_periodic_secs` value is set. If not, it defaults to 0 seconds.
    - The thread then enters a loop that continues until the `task_stopping_event` is set.
    - Within the loop, it checks if the current time has exceeded the `expired_time`. If so, it sets a flag to update all diagnostic information in the database.
    - It iterates over all physical ports, handling any port update events for ports that have undergone a link change and updating the flag-related tables accordingly.
    - If the flag to update all diagnostic information is set, it reads the diagnostic information for the current port.
    - After processing all ports, it resets the flag and updates the `expired_time` to the current time plus the `dom_info_update_periodic_secs` interval.

The following steps are performed to update all diagnostic information for a port:

1. Ensure DOM monitoring is enabled for the port. If DOM monitoring is disabled, skip updating the diagnostic information for the port.
2. If the current port is the first port from its breakout port group to be polled, clear the cached diagnostic information. For all subsequent ports in the breakout port group, use the cached diagnostic information to update the `redis-db`.
3. Read the transceiver firmware information from the module and update the `TRANSCEIVER_FIRMWARE_INFO` table.
4. Read the transceiver DOM sensor data from the module and update the `TRANSCEIVER_DOM_SENSOR` table.
5. Read the transceiver DOM flag data from the module, record the timestamp, and update the `TRANSCEIVER_DOM_FLAG` table (update the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables as well).
6. Read the transceiver status data from the module and update the `TRANSCEIVER_STATUS` table.
7. Read the transceiver status flag data from the module, record the timestamp, and update the `TRANSCEIVER_STATUS_FLAG` table (update the `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT`, `TRANSCEIVER_STATUS_FLAG_SET_TIME`, and `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` tables as well).
8. If the transceiver supports VDM monitoring, perform the following steps:
    1. Freeze the statistics by calling the CMIS API (`freeze_vdm_stats`) and wait for `FreezeDone` by calling `get_vdm_freeze_status`.
    2. Once the statistics are frozen, read the VDM real values, flags, and PM data from the module and update the `TRANSCEIVER_VDM_REAL_VALUE`, `TRANSCEIVER_VDM_FLAG`, and `TRANSCEIVER_PM` tables respectively.
    3. Update the VDM flag, change count, and time-related tables by comparing the current data with the previous data.
    4. Unfreeze the statistics by calling the CMIS API (`unfreeze_vdm_stats`).

Pseudo code:

```python
# Retrieve the update period interval
dom_info_update_periodic_secs = parse_field_from_pmon_daemon_control('dom_info_update_periodic_secs')
if dom_info_update_periodic_secs is None:
    dom_info_update_periodic_secs = 0

expired_time = time.time()

while not dom_mgr.task_stopping_event.is_set():
    if expired_time <= time.time():
        update_all_diagnostic_info_in_db = True
    
    for current_pport in range(1, last_physical_port + 1):
        if handle_port_update_event_for_all_link_changed_ports():
            update_flag_related_tables(ports_going_through_link_change)
        
        if update_all_diagnostic_info_in_db:
            read_diagnostic_info(current_pport)
    
    update_all_diagnostic_info_in_db = False
    expired_time = time.time() + dom_info_update_periodic_secs
```

#### 4.2.2 Diagnostic Information Update During Link Change Event

The following tables are updated during a link change event:

##### 4.2.2.1 DOM Related Fields

The DOM flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link change event:

- `temperature`
- `voltage`
- `tx{lane_num}power`
- `rx{lane_num}power`
- `tx{lane_num}bias`
- `laser_temperature`

Example

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

##### 4.2.2.2 VDM Related Fields

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

Example

The following fields related to `esnr_media_input` are updated in the `redis-db` during a link change event:

- `esnr_media_input_halarm{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG` table
- `esnr_media_input_lalarm{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG` table
- `esnr_media_input_hwarn{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG` table
- `esnr_media_input_lwarn{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG` table
- `esnr_media_input_halarm{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT` table
- `esnr_media_input_lalarm{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT` table
- `esnr_media_input_hwarn{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT` table
- `esnr_media_input_lwarn{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT` tables
- `esnr_media_input_halarm{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG_SET_TIME` table
- `esnr_media_input_lalarm{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG_SET_TIME` table
- `esnr_media_input_hwarn{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG_SET_TIME` table
- `esnr_media_input_lwarn{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG_SET_TIME` table
- `esnr_media_input_halarm{lane_num}` in `TRANSCEIVER_VDM_HALARM_FLAG_CLEAR_TIME` table
- `esnr_media_input_lalarm{lane_num}` in `TRANSCEIVER_VDM_LALARM_FLAG_CLEAR_TIME` table
- `esnr_media_input_hwarn{lane_num}` in `TRANSCEIVER_VDM_HWARN_FLAG_CLEAR_TIME` table
- `esnr_media_input_lwarn{lane_num}` in `TRANSCEIVER_VDM_LWARN_FLAG_CLEAR_TIME` table

##### 4.2.2.3 Transceiver Status Related Fields

The following fields of the `TRANSCEIVER_STATUS` table are updated in the `redis-db` during a link change event:

- `tx_disabled_channel`
- `module_state`
- `module_fault_cause`
- `DP{lane_num}State`
- `txoutput_status{lane_num}`
- `rxoutput_status_hostlane{lane_num}`
- `config_state_hostlane{lane_num}`
- `dpdeinit_hostlane{lane_num}`

The transceive status flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link change event:

- `datapath_firmware_fault`
- `module_firmware_fault`
- `module_state_changed`
- `txfault{lane_num}`
- `rxlos{lane_num}`
- `txlos_hostlane{lane_num}`
- `txcdrlol_hostlane{lane_num}`
- `tx_eq_fault{lane_num}`
- `rxcdrlol{lane_num}`

Example

The following fields related to `datapath_firmware_fault` are updated in the `redis-db` during a link change event:

- `datapath_firmware_fault` in `TRANSCEIVER_STATUS` table
- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` table
- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG_SET_TIME` table
- `datapath_firmware_fault` in `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` table

#### 4.2.3 Details of Flag Analysis of Tables

**Note**: For simplicity, this section uses DOM as an example. However, the same analysis is applicable for VDM and Status related flags as well.

**Purpose of Flag Analysis:**

The purpose of flag analysis is to track the status of various parameters and to count the number of times each DOM flag has changed. It also records the timestamp when each DOM flag was set and cleared.

**Tables Used for Flag Analysis:**

- `TRANSCEIVER_DOM_FLAG`: This table stores flags indicating the status of various DOM parameters.
- `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`: This table keeps a count of how many times each DOM flag has changed. Upon initialization, the count is set to 0.
- `TRANSCEIVER_DOM_FLAG_SET_TIME`: This table records the timestamp (in local timezone) when each DOM flag was set. The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`. During initialization, the timestamp is set to `never` if the flag is not set. Since SONiC does not support flag-based interrupt handling, the timestamp refers to either:
  - The timestamp at which the link status was changed, or
  - The polling event timestamp if the flag was set during the routine polling by the `DomInfoUpdateTask` thread.
- `TRANSCEIVER_DOM_FLAG_CLEAR_TIME`: This table records the timestamp (in local timezone) when each DOM flag was cleared. The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`. During initialization, the timestamp is set to `never` if the flag is set. Since SONiC does not support flag-based interrupt handling, the timestamp refers to either:
  - The timestamp at which the link status was changed, or
  - The polling event timestamp if the flag was cleared during the routine polling by the `DomInfoUpdateTask` thread.

**Example of Table Updates:**

- **TRANSCEIVER_DOM_FLAG_CHANGE_COUNT:**
  - Each time a flag in the `TRANSCEIVER_DOM_FLAG` table changes (either set or cleared), the corresponding count in this table is incremented.
- **TRANSCEIVER_DOM_FLAG_SET_TIME:**
  - When a flag is set in the `TRANSCEIVER_DOM_FLAG` table, the current timestamp (in local timezone) is recorded in this table.
- **TRANSCEIVER_DOM_FLAG_CLEAR_TIME:**
  - When a flag is cleared in the `TRANSCEIVER_DOM_FLAG` table, the current timestamp (in local timezone) is recorded in this table.

##### 4.2.3.1 Flag Change Count and Time Set/Clear Behavior During `xcvrd` Restart

During `xcvrd` stop, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are deleted by the `xcvrd` process. When `xcvrd` is restarted, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are recreated and the flag change count and set/clear time are updated based on the current flag status (i.e. the value of these fields are not cached between `xcvrd` restarts).

##### 4.2.3.2 Flag Change Count and Time Set/Clear Behavior During Transceiver Removal and Insertion

When a transceiver is removed, `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are deleted by the `SfpStateUpdateTask` thread.

When the transceiver is inserted back, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are recreated through the periodic polling routine of `DomInfoUpdateTask` and the flag change count and set/clear time are updated based on the current flag status.

#### 4.2.4 Diagnostic Information Last Update Timestamp and Interval Period by `DomInfoUpdateTask`

All the diagnostic tables (except for the metadata tables storing change count and last set/clear time) contain the `table_last_update_time` field to capture the last update timestamp.
Specifically, the `TRANSCEIVER_STATUS` table contains the `diagnostics_update_interval` field to capture the interval period at which the diagnostic information is updated by the `DomInfoUpdateTask` thread for a port. This field is not present in the other diagnostic tables since the diagnostic information is updated for all ports in a sequential manner.

1. **`table_last_update_time`**:
   - This field records the timestamp (in local timezone) at which the corresponding diagnostic information was last updated by the `DomInfoUpdateTask` thread for a port.
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

#### Calculation of `diagnostics_update_interval` Using EWMA

The Exponentially Weighted Moving Average (EWMA) is used to calculate the `diagnostics_update_interval`, providing a smooth and responsive average of the update intervals. An alpha value of 0.1 is used for the EWMA calculation to give more weight to historical intervals.

**Formula:**

$
\text{EWMA}_t = \alpha \cdot x_t + (1 - \alpha) \cdot \text{EWMA}_{t-1}
$

Where:

- $\text{EWMA}_t$ is the current `diagnostics_update_interval`.
- $x_t$ is the current update interval (time taken to read the diagnostic information).
- $\text{EWMA}_{t-1}$ is the previous `diagnostics_update_interval`.
- $\alpha$ is the smoothing factor (0 < α ≤ 1).

**Steps:**

1. **Initial Update**: The `diagnostics_update_interval` is initially set to `0` during table creation.
2. **Subsequent Updates**: After the second diagnostic information update for a port, the `diagnostics_update_interval` is updated using the EWMA formula.
