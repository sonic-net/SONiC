# CMIS Diagnostic Monitoring Overview in SONiC

## 1. Overview

The CMIS (Common Management Interface Specification) diagnostic monitoring feature is a standard for monitoring the performance of optical transceivers. It provides a way to monitor the performance of optical transceivers in real time. SONiC periodically reads the diagnostic monitoring data from the optical transceivers and stores the data in the database. The data can be retrieved using the SONiC CLI or by querying the database directly.

The current scope of the CMIS diagnostic monitoring feature in SONiC includes the following parameters:

- **DOM (Digital Optical Monitoring) data:** Provides real-time monitoring of optical transceiver parameters such as temperature, voltage, and optical power.
- **VDM (Versatile Diagnostics Monitoring) data:** Offers versatile diagnostic information for enhanced monitoring and troubleshooting.
- **PM (Performance Monitoring) data:** Applicable only for C-CMIS transceivers, this includes performance metrics such as error counts and signal quality indicators.

## 2. STATE_DB Schema for CMIS Diagnostic Monitoring

The CMIS diagnostic monitoring data is stored in the `STATE_DB` database. The `STATE_DB` schema for the CMIS diagnostic monitoring feature includes the following tables:

- `TRANSCEIVER_DOM_SENSOR`: Stores real-time DOM data for the optical transceivers.
- `TRANSCEIVER_DOM_THRESHOLD`: Contains threshold values for DOM parameters.
- `TRANSCEIVER_DOM_FLAG`: Stores flags indicating the status of various DOM parameters.
- `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`: Keeps a count of how many times each DOM flag has changed.
- `TRANSCEIVER_DOM_FLAG_SET_TIME`: Records the timestamp when each DOM flag was set.
- `TRANSCEIVER_DOM_FLAG_CLEAR_TIME`: Records the timestamp when each DOM flag was cleared.
- `TRANSCEIVER_VDM_CURRENT_SAMPLE`: Stores VDM sample data.
- `TRANSCEIVER_VDM_THRESHOLD`: Contains threshold values for VDM parameters.
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
- `TRANSCEIVER_VDM_HALARM_SET_TIME`: Records the timestamp when each VDM high alarm flag was set.
- `TRANSCEIVER_VDM_LALARM_SET_TIME`: Records the timestamp when each VDM low alarm flag was set.
- `TRANSCEIVER_VDM_HWARN_SET_TIME`: Records the timestamp when each VDM high warning flag was set.
- `TRANSCEIVER_VDM_LWARN_SET_TIME`: Records the timestamp when each VDM low warning flag was set.
- `TRANSCEIVER_VDM_HALARM_CLEAR_TIME`: Records the timestamp when each VDM high alarm flag was cleared.
- `TRANSCEIVER_VDM_LALARM_CLEAR_TIME`: Records the timestamp when each VDM low alarm flag was cleared.
- `TRANSCEIVER_VDM_HWARN_CLEAR_TIME`: Records the timestamp when each VDM high warning flag was cleared.
- `TRANSCEIVER_VDM_LWARN_CLEAR_TIME`: Records the timestamp when each VDM low warning flag was cleared.
- `TRANSCEIVER_STATUS`: Stores the module and datapath state data along with various flags related to it. Also stores various Tx and Rx related flags.
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
```

#### 2.1.4 Transceiver DOM flag change count data

The `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` table stores the flag change count for the DOM flags.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag change count for a port
    key                              = TRANSCEIVER_DOM_FLAG_CHANGE|ifname   ; information module DOM flags change count on port
    ; field                          = value
    temphighalarm_chg_cnt                 = INTEGER           ; temperature high alarm change count
    temphighwarning_chg_cnt               = INTEGER           ; temperature high warning change count
    templowalarm_chg_cnt                  = INTEGER           ; temperature low alarm change count
    templowwarning_chg_cnt                = INTEGER           ; temperature low warning change count
    vcchighalarm_chg_cnt                  = INTEGER           ; vcc high alarm change count
    vcchighwarning_chg_cnt                = INTEGER           ; vcc high warning change count
    vcclowalarm_chg_cnt                   = INTEGER           ; vcc low alarm change count
    vcclowwarning_chg_cnt                 = INTEGER           ; vcc low warning change count
    txpowerhighalarm_chg_cnt{lane_num}    = INTEGER           ; tx power high alarm change count
    txpowerlowalarm_chg_cnt{lane_num}     = INTEGER           ; tx power low alarm change count
    txpowerhighwarning_chg_cnt{lane_num}  = INTEGER           ; tx power high warning change count
    txpowerlowwarning_chg_cnt{lane_num}   = INTEGER           ; tx power low alarm change count
    rxpowerhighalarm_chg_cnt{lane_num}    = INTEGER           ; rx power high alarm change count
    rxpowerlowalarm_chg_cnt{lane_num}     = INTEGER           ; rx power low alarm change count
    rxpowerhighwarning_chg_cnt{lane_num}  = INTEGER           ; rx power high warning change count
    rxpowerlowwarning_chg_cnt{lane_num}   = INTEGER           ; rx power low warning change count
    txbiashighalarm_chg_cnt{lane_num}     = INTEGER           ; tx bias high alarm change count
    txbiaslowalarm_chg_cnt{lane_num}      = INTEGER           ; tx bias low alarm change count
    txbiashighwarning_chg_cnt{lane_num}   = INTEGER           ; tx bias high warning change count
    txbiaslowwarning_chg_cnt{lane_num}    = INTEGER           ; tx bias low warning change count
    lasertemphighalarm_chg_cnt            = INTEGER           ; laser temperature high alarm change count
    lasertemplowalarm_chg_cnt             = INTEGER           ; laser temperature low alarm change count
    lasertemphighwarning_chg_cnt          = INTEGER           ; laser temperature high warning change count
    lasertemplowwarning_chg_cnt           = INTEGER           ; laser temperature low warning change count
```

#### 2.1.5 Transceiver DOM flag time set data

The `TRANSCEIVER_DOM_FLAG_SET_TIME` table stores the last set time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time set for a port
    key                          = TRANSCEIVER_DOM_FLAG_SET_TIME|ifname   ; information module DOM flag time set on port
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
```

#### 2.1.6 Transceiver DOM flag time clear data

The `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` table stores the last clear time for the corresponding DOM flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver DOM flag time clear for a port
    key                          = TRANSCEIVER_DOM_FLAG_CLEAR_TIME|ifname  ; information module DOM flag time clear on port
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
```

### 2.2 Transceiver VDM

#### 2.2.1 Transceiver VDM sample data

The `TRANSCEIVER_VDM_CURRENT_SAMPLE` table stores the real time VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM sample for a port
    key                                            = TRANSCEIVER_VDM_CURRENT_SAMPLE|ifname    ; information module VDM sample on port
    ; field                                        = value
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
    biasxi                                         = FLOAT                  ; modulator bias xi in percentage
    biasxq                                         = FLOAT                  ; modulator bias xq in percentage
    biasxp                                         = FLOAT                  ; modulator bias xp in percentage
    biasyi                                         = FLOAT                  ; modulator bias yi in percentage
    biasyq                                         = FLOAT                  ; modulator bias yq in percentage
    biasyp                                         = FLOAT                  ; modulator bias yq in percentage
    cdshort                                        = FLOAT                  ; chromatic dispersion, high granularity, short link in ps/nm
    cdlong                                         = FLOAT                  ; chromatic dispersion, high granularity, long link in ps/nm  
    dgd                                            = FLOAT                  ; differential group delay in ps
    sopmd                                          = FLOAT                  ; second order polarization mode dispersion in ps^2
    soproc                                         = FLOAT                  ; state of polarization rate of change in krad/s
    pdl                                            = FLOAT                  ; polarization dependent loss in db
    osnr                                           = FLOAT                  ; optical signal to noise ratio in db
    esnr                                           = FLOAT                  ; electrical signal to noise ratio in db
    cfo                                            = FLOAT                  ; carrier frequency offset in Hz
    txcurrpower                                    = FLOAT                  ; tx current output power in dbm
    rxtotpower                                     = FLOAT                  ; rx total power in  dbm
    rxsigpower                                     = FLOAT                  ; rx signal power in dbm
```

#### 2.2.2 Transceiver VDM threshold data

##### 2.2.2.1 Transceiver VDM high alarm threshold data

The `TRANSCEIVER_VDM_HALARM_THRESHOLD` table stores the high alarm threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm threshold for a port
    key                                            = TRANSCEIVER_VDM_HALARM_THRESHOLD|ifname    ; information module VDM high alarm threshold on port
    ; field                                        = value
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
    biasxi_halarm                                       = FLOAT         ; modulator bias xi in percentage (high alarm)
    biasxq_halarm                                       = FLOAT         ; modulator bias xq in percentage (high alarm)
    biasxp_halarm                                       = FLOAT         ; modulator bias xp in percentage (high alarm)
    biasyi_halarm                                       = FLOAT         ; modulator bias yi in percentage (high alarm)
    biasyq_halarm                                       = FLOAT         ; modulator bias yq in percentage (high alarm)
    biasyp_halarm                                       = FLOAT         ; modulator bias yq in percentage (high alarm)
    cdshort_halarm                                      = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (high alarm)
    cdlong_halarm                                       = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (high alarm)
    dgd_halarm                                          = FLOAT         ; differential group delay in ps (high alarm)
    sopmd_halarm                                        = FLOAT         ; second order polarization mode dispersion in ps^2 (high alarm)
    soproc_halarm                                       = FLOAT         ; state of polarization rate of change in krad/s (high alarm)
    pdl_halarm                                          = FLOAT         ; polarization dependent loss in db (high alarm)
    osnr_halarm                                         = FLOAT         ; optical signal to noise ratio in db (high alarm)
    esnr_halarm                                         = FLOAT         ; electrical signal to noise ratio in db (high alarm)
    cfo_halarm                                          = FLOAT         ; carrier frequency offset in Hz (high alarm)
    txcurrpower_halarm                                  = FLOAT         ; tx current output power in dbm (high alarm)
    rxtotpower_halarm                                   = FLOAT         ; rx total power in  dbm (high alarm)
    rxsigpower_halarm                                   = FLOAT         ; rx signal power in dbm (high alarm)
```

##### 2.2.2.2 Transceiver VDM low alarm threshold data

The `TRANSCEIVER_VDM_LALARM_THRESHOLD` table stores the low alarm threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm threshold for a port
    key                                            = TRANSCEIVER_VDM_LALARM_THRESHOLD|ifname    ; information module VDM low alarm threshold on port
    ; field                                        = value
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
    biasxi_lalarm                                       = FLOAT         ; modulator bias xi in percentage (low alarm)
    biasxq_lalarm                                       = FLOAT         ; modulator bias xq in percentage (low alarm)
    biasxp_lalarm                                       = FLOAT         ; modulator bias xp in percentage (low alarm)
    biasyi_lalarm                                       = FLOAT         ; modulator bias yi in percentage (low alarm)
    biasyq_lalarm                                       = FLOAT         ; modulator bias yq in percentage (low alarm)
    biasyp_lalarm                                       = FLOAT         ; modulator bias yq in percentage (low alarm)
    cdshort_lalarm                                      = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (low alarm)
    cdlong_lalarm                                       = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (low alarm)
    dgd_lalarm                                          = FLOAT         ; differential group delay in ps (low alarm)
    sopmd_lalarm                                        = FLOAT         ; second order polarization mode dispersion in ps^2 (low alarm)
    soproc_lalarm                                       = FLOAT         ; state of polarization rate of change in krad/s (low alarm)
    pdl_lalarm                                          = FLOAT         ; polarization dependent loss in db (low alarm)
    osnr_lalarm                                         = FLOAT         ; optical signal to noise ratio in db (low alarm)
    esnr_lalarm                                         = FLOAT         ; electrical signal to noise ratio in db (low alarm)
    cfo_lalarm                                          = FLOAT         ; carrier frequency offset in Hz (low alarm)
    txcurrpower_lalarm                                  = FLOAT         ; tx current output power in dbm (low alarm)
    rxtotpower_lalarm                                   = FLOAT         ; rx total power in  dbm (low alarm)
    rxsigpower_lalarm                                   = FLOAT         ; rx signal power in dbm (low alarm)
```

##### 2.2.2.3 Transceiver VDM high warning threshold data

The `TRANSCEIVER_VDM_HWARN_THRESHOLD` table stores the high warning threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning threshold for a port
    key                                            = TRANSCEIVER_VDM_HWARN_THRESHOLD|ifname    ; information module VDM high warning threshold on port
    ; field                                        = value
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
    biasxi_hwarn                                       = FLOAT         ; modulator bias xi in percentage (high warning)
    biasxq_hwarn                                       = FLOAT         ; modulator bias xq in percentage (high warning)
    biasxp_hwarn                                       = FLOAT         ; modulator bias xp in percentage (high warning)
    biasyi_hwarn                                       = FLOAT         ; modulator bias yi in percentage (high warning)
    biasyq_hwarn                                       = FLOAT         ; modulator bias yq in percentage (high warning)
    biasyp_hwarn                                       = FLOAT         ; modulator bias yq in percentage (high warning)
    cdshort_hwarn                                      = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (high warning)
    cdlong_hwarn                                       = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (high warning)
    dgd_hwarn                                          = FLOAT         ; differential group delay in ps (high warning)
    sopmd_hwarn                                        = FLOAT         ; second order polarization mode dispersion in ps^2 (high warning)
    soproc_hwarn                                       = FLOAT         ; state of polarization rate of change in krad/s (high warning)
    pdl_hwarn                                          = FLOAT         ; polarization dependent loss in db (high warning)
    osnr_hwarn                                         = FLOAT         ; optical signal to noise ratio in db (high warning)
    esnr_hwarn                                         = FLOAT         ; electrical signal to noise ratio in db (high warning)
    cfo_hwarn                                          = FLOAT         ; carrier frequency offset in Hz (high warning)
    txcurrpower_hwarn                                  = FLOAT         ; tx current output power in dbm (high warning)
    rxtotpower_hwarn                                   = FLOAT         ; rx total power in  dbm (high warning)
    rxsigpower_hwarn                                   = FLOAT         ; rx signal power in dbm (high warning)
```

##### 2.2.2.4 Transceiver VDM low warning threshold data

The `TRANSCEIVER_VDM_LWARN_THRESHOLD` table stores the low warning threshold values for the VDM data

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning threshold for a port
    key                                            = TRANSCEIVER_VDM_LWARN_THRESHOLD|ifname    ; information module VDM low warning threshold on port
    ; field                                        = value
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
    biasxi_lwarn                                       = FLOAT         ; modulator bias xi in percentage (low warning)
    biasxq_lwarn                                       = FLOAT         ; modulator bias xq in percentage (low warning)
    biasxp_lwarn                                       = FLOAT         ; modulator bias xp in percentage (low warning)
    biasyi_lwarn                                       = FLOAT         ; modulator bias yi in percentage (low warning)
    biasyq_lwarn                                       = FLOAT         ; modulator bias yq in percentage (low warning)
    biasyp_lwarn                                       = FLOAT         ; modulator bias yq in percentage (low warning)
    cdshort_lwarn                                      = FLOAT         ; chromatic dispersion, high granularity, short link in ps/nm (low warning)
    cdlong_lwarn                                       = FLOAT         ; chromatic dispersion, high granularity, long link in ps/nm (low warning)
    dgd_lwarn                                          = FLOAT         ; differential group delay in ps (low warning)
    sopmd_lwarn                                        = FLOAT         ; second order polarization mode dispersion in ps^2 (low warning)
    soproc_lwarn                                       = FLOAT         ; state of polarization rate of change in krad/s (low warning)
    pdl_lwarn                                          = FLOAT         ; polarization dependent loss in db (low warning)
    osnr_lwarn                                         = FLOAT         ; optical signal to noise ratio in db (low warning)
    esnr_lwarn                                         = FLOAT         ; electrical signal to noise ratio in db (low warning)
    cfo_lwarn                                          = FLOAT         ; carrier frequency offset in Hz (low warning)
    txcurrpower_lwarn                                  = FLOAT         ; tx current output power in dbm (low warning)
    rxtotpower_lwarn                                   = FLOAT         ; rx total power in  dbm (low warning)
    rxsigpower_lwarn                                   = FLOAT         ; rx signal power in dbm (low warning)
```

#### 2.2.3 Transceiver VDM flag data

##### 2.2.3.1 Transceiver VDM high alarm flag data

The `TRANSCEIVER_VDM_HALARM_FLAG` table stores the flag status for the VDM data.

```plaintext
    ;Defines Transceiver VDM high alarm flag for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG|ifname
    ; field                      = value
    laser_temperature_media_halarm_flag{lane_num}             = BOOLEAN ; laser temperature high alarm flag for media input
    esnr_media_input_halarm_flag{lane_num}                    = BOOLEAN ; eSNR high alarm flag for media input
    esnr_host_input_halarm_flag{lane_num}                     = BOOLEAN ; eSNR high alarm flag for host input
    pam4_level_transition_media_input_halarm_flag{lane_num}   = BOOLEAN ; PAM4 level transition high alarm flag for media input
    pam4_level_transition_host_input_halarm_flag{lane_num}    = BOOLEAN ; PAM4 level transition high alarm flag for host input
    prefec_ber_min_media_input_halarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high alarm flag for media input
    prefec_ber_max_media_input_halarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high alarm flag for media input
    prefec_ber_avg_media_input_halarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER average high alarm flag for media input
    prefec_ber_curr_media_input_halarm_flag{lane_num}         = BOOLEAN ; Pre-FEC BER current high alarm flag for media input
    prefec_ber_min_host_input_halarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high alarm flag for host input
    prefec_ber_max_host_input_halarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high alarm flag for host input
    prefec_ber_avg_host_input_halarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER average high alarm flag for host input
    prefec_ber_curr_host_input_halarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER current high alarm flag for host input
    errored_frames_min_media_input_halarm_flag{lane_num}      = BOOLEAN ; Errored frames minimum high alarm flag for media input
    errored_frames_max_media_input_halarm_flag{lane_num}      = BOOLEAN ; Errored frames maximum high alarm flag for media input
    errored_frames_avg_media_input_halarm_flag{lane_num}      = BOOLEAN ; Errored frames average high alarm flag for media input
    errored_frames_curr_media_input_halarm_flag{lane_num}     = BOOLEAN ; Errored frames current high alarm flag for media input
    errored_frames_min_host_input_halarm_flag{lane_num}       = BOOLEAN ; Errored frames minimum high alarm flag for host input
    errored_frames_max_host_input_halarm_flag{lane_num}       = BOOLEAN ; Errored frames maximum high alarm flag for host input
    errored_frames_avg_host_input_halarm_flag{lane_num}       = BOOLEAN ; Errored frames average high alarm flag for host input
    errored_frames_curr_host_input_halarm_flag{lane_num}      = BOOLEAN ; Errored frames current high alarm flag for host input

    ;C-CMIS specific fields
    biasxi_halarm_flag                                        = BOOLEAN ; modulator bias xi in percentage (high alarm flag)
    biasxq_halarm_flag                                        = BOOLEAN ; modulator bias xq in percentage (high alarm flag)
    biasxp_halarm_flag                                        = BOOLEAN ; modulator bias xp in percentage (high alarm flag)
    biasyi_halarm_flag                                        = BOOLEAN ; modulator bias yi in percentage (high alarm flag)
    biasyq_halarm_flag                                        = BOOLEAN ; modulator bias yq in percentage (high alarm flag)
    biasyp_halarm_flag                                        = BOOLEAN ; modulator bias yq in percentage (high alarm flag)
    cdshort_halarm_flag                                       = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (high alarm flag)
    cdlong_halarm_flag                                        = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (high alarm flag)
    dgd_halarm_flag                                           = BOOLEAN ; differential group delay in ps (high alarm flag)
    sopmd_halarm_flag                                         = BOOLEAN ; second order polarization mode dispersion in ps^2 (high alarm flag)
    soproc_halarm_flag                                        = BOOLEAN ; state of polarization rate of change in krad/s (high alarm flag)
    pdl_halarm_flag                                           = BOOLEAN ; polarization dependent loss in db (high alarm flag)
    osnr_halarm_flag                                          = BOOLEAN ; optical signal to noise ratio in db (high alarm flag)
    esnr_halarm_flag                                          = BOOLEAN ; electrical signal to noise ratio in db (high alarm flag)
    cfo_halarm_flag                                           = BOOLEAN ; carrier frequency offset in Hz (high alarm flag)
    txcurrpower_halarm_flag                                   = BOOLEAN ; tx current output power in dbm (high alarm flag)
    rxtotpower_halarm_flag                                    = BOOLEAN ; rx total power in  dbm (high alarm flag)
    rxsigpower_halarm_flag                                    = BOOLEAN; rx signal power in dbm (high alarm flag)
```

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

##### 2.2.3.2 Transceiver VDM low alarm flag data

The `TRANSCEIVER_VDM_LALARM_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm flag for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG|ifname
    ; field                      = value
    laser_temperature_media_lalarm_flag{lane_num}             = BOOLEAN ; laser temperature low alarm flag for media input
    esnr_media_input_lalarm_flag{lane_num}                    = BOOLEAN ; eSNR low alarm flag for media input
    esnr_host_input_lalarm_flag{lane_num}                     = BOOLEAN ; eSNR low alarm flag for host input
    pam4_level_transition_media_input_lalarm_flag{lane_num}   = BOOLEAN ; PAM4 level transition low alarm flag for media input
    pam4_level_transition_host_input_lalarm_flag{lane_num}    = BOOLEAN ; PAM4 level transition low alarm flag for host input
    prefec_ber_min_media_input_lalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low alarm flag for media input
    prefec_ber_max_media_input_lalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low alarm flag for media input
    prefec_ber_avg_media_input_lalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER average low alarm flag for media input
    prefec_ber_curr_media_input_lalarm_flag{lane_num}         = BOOLEAN ; Pre-FEC BER current low alarm flag for media input
    prefec_ber_min_host_input_lalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low alarm flag for host input
    prefec_ber_max_host_input_lalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low alarm flag for host input
    prefec_ber_avg_host_input_lalarm_flag{lane_num}           = BOOLEAN ; Pre-FEC BER average low alarm flag for host input
    prefec_ber_curr_host_input_lalarm_flag{lane_num}          = BOOLEAN ; Pre-FEC BER current low alarm flag for host input
    errored_frames_min_media_input_lalarm_flag{lane_num}      = BOOLEAN ; Errored frames minimum low alarm flag for media input
    errored_frames_max_media_input_lalarm_flag{lane_num}      = BOOLEAN ; Errored frames maximum low alarm flag for media input
    errored_frames_avg_media_input_lalarm_flag{lane_num}      = BOOLEAN ; Errored frames average low alarm flag for media input
    errored_frames_curr_media_input_lalarm_flag{lane_num}     = BOOLEAN ; Errored frames current low alarm flag for media input
    errored_frames_min_host_input_lalarm_flag{lane_num}       = BOOLEAN ; Errored frames minimum low alarm flag for host input
    errored_frames_max_host_input_lalarm_flag{lane_num}       = BOOLEAN ; Errored frames maximum low alarm flag for host input
    errored_frames_avg_host_input_lalarm_flag{lane_num}       = BOOLEAN ; Errored frames average low alarm flag for host input
    errored_frames_curr_host_input_lalarm_flag{lane_num}      = BOOLEAN ; Errored frames current low alarm flag for host input

    ;C-CMIS specific fields
    biasxi_lalarm_flag                                        = BOOLEAN ; modulator bias xi in percentage (low alarm flag)
    biasxq_lalarm_flag                                        = BOOLEAN ; modulator bias xq in percentage (low alarm flag)
    biasxp_lalarm_flag                                        = BOOLEAN ; modulator bias xp in percentage (low alarm flag)
    biasyi_lalarm_flag                                        = BOOLEAN ; modulator bias yi in percentage (low alarm flag)
    biasyq_lalarm_flag                                        = BOOLEAN ; modulator bias yq in percentage (low alarm flag)
    biasyp_lalarm_flag                                        = BOOLEAN ; modulator bias yq in percentage (low alarm flag)
    cdshort_lalarm_flag                                       = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (low alarm flag)
    cdlong_lalarm_flag                                        = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (low alarm flag)
    dgd_lalarm_flag                                           = BOOLEAN ; differential group delay in ps (low alarm flag)
    sopmd_lalarm_flag                                         = BOOLEAN ; second order polarization mode dispersion in ps^2 (low alarm flag)
    soproc_lalarm_flag                                        = BOOLEAN ; state of polarization rate of change in krad/s (low alarm flag)
    pdl_lalarm_flag                                           = BOOLEAN ; polarization dependent loss in db (low alarm flag)
    osnr_lalarm_flag                                          = BOOLEAN ; optical signal to noise ratio in db (low alarm flag)
    esnr_lalarm_flag                                          = BOOLEAN ; electrical signal to noise ratio in db (low alarm flag)
    cfo_lalarm_flag                                           = BOOLEAN ; carrier frequency offset in Hz (low alarm flag)
    txcurrpower_lalarm_flag                                   = BOOLEAN ; tx current output power in dbm (low alarm flag)
    rxtotpower_lalarm_flag                                    = BOOLEAN ; rx total power in  dbm (low alarm flag)
    rxsigpower_lalarm_flag                                    = BOOLEAN; rx signal power in dbm (low alarm flag)
```

##### 2.2.3.3 Transceiver VDM high warning flag data

The `TRANSCEIVER_VDM_HWARN_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning flag for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG|ifname
    ; field                      = value
    laser_temperature_media_hwarn_flag{lane_num}             = BOOLEAN ; laser temperature high warning flag for media input
    esnr_media_input_hwarn_flag{lane_num}                    = BOOLEAN ; eSNR high warning flag for media input
    esnr_host_input_hwarn_flag{lane_num}                     = BOOLEAN ; eSNR high warning flag for host input
    pam4_level_transition_media_input_hwarn_flag{lane_num}   = BOOLEAN ; PAM4 level transition high warning flag for media input
    pam4_level_transition_host_input_hwarn_flag{lane_num}    = BOOLEAN ; PAM4 level transition high warning flag for host input
    prefec_ber_min_media_input_hwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER minimum high warning flag for media input
    prefec_ber_max_media_input_hwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER maximum high warning flag for media input
    prefec_ber_avg_media_input_hwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER average high warning flag for media input
    prefec_ber_curr_media_input_hwarn_flag{lane_num}         = BOOLEAN ; Pre-FEC BER current high warning flag for media input
    prefec_ber_min_host_input_hwarn_flag{lane_num}           = BOOLEAN ; Pre-FEC BER minimum high warning flag for host input
    prefec_ber_max_host_input_hwarn_flag{lane_num}           = BOOLEAN ; Pre-FEC BER maximum high warning flag for host input
    prefec_ber_avg_host_input_hwarn_flag{lane_num}           = BOOLEAN ; Pre-FEC BER average high warning flag for host input
    prefec_ber_curr_host_input_hwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER current high warning flag for host input
    errored_frames_min_media_input_hwarn_flag{lane_num}      = BOOLEAN ; Errored frames minimum high warning flag for media input
    errored_frames_max_media_input_hwarn_flag{lane_num}      = BOOLEAN ; Errored frames maximum high warning flag for media input
    errored_frames_avg_media_input_hwarn_flag{lane_num}      = BOOLEAN ; Errored frames average high warning flag for media input
    errored_frames_curr_media_input_hwarn_flag{lane_num}     = BOOLEAN ; Errored frames current high warning flag for media input
    errored_frames_min_host_input_hwarn_flag{lane_num}       = BOOLEAN ; Errored frames minimum high warning flag for host input
    errored_frames_max_host_input_hwarn_flag{lane_num}       = BOOLEAN ; Errored frames maximum high warning flag for host input
    errored_frames_avg_host_input_hwarn_flag{lane_num}       = BOOLEAN ; Errored frames average high warning flag for host input
    errored_frames_curr_host_input_hwarn_flag{lane_num}      = BOOLEAN ; Errored frames current high warning flag for host input

    ;C-CMIS specific fields
    biasxi_hwarn_flag                                        = BOOLEAN ; modulator bias xi in percentage (high warning flag)
    biasxq_hwarn_flag                                        = BOOLEAN ; modulator bias xq in percentage (high warning flag)
    biasxp_hwarn_flag                                        = BOOLEAN ; modulator bias xp in percentage (high warning flag)
    biasyi_hwarn_flag                                        = BOOLEAN ; modulator bias yi in percentage (high warning flag)
    biasyq_hwarn_flag                                        = BOOLEAN ; modulator bias yq in percentage (high warning flag)
    biasyp_hwarn_flag                                        = BOOLEAN ; modulator bias yq in percentage (high warning flag)
    cdshort_hwarn_flag                                       = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (high warning flag)
    cdlong_hwarn_flag                                        = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (high warning flag)
    dgd_hwarn_flag                                           = BOOLEAN ; differential group delay in ps (high warning flag)
    sopmd_hwarn_flag                                         = BOOLEAN ; second order polarization mode dispersion in ps^2 (high warning flag)
    soproc_hwarn_flag                                        = BOOLEAN ; state of polarization rate of change in krad/s (high warning flag)
    pdl_hwarn_flag                                           = BOOLEAN ; polarization dependent loss in db (high warning flag)
    osnr_hwarn_flag                                          = BOOLEAN ; optical signal to noise ratio in db (high warning flag)
    esnr_hwarn_flag                                          = BOOLEAN ; electrical signal to noise ratio in db (high warning flag)
    cfo_hwarn_flag                                           = BOOLEAN ; carrier frequency offset in Hz (high warning flag)
    txcurrpower_hwarn_flag                                   = BOOLEAN ; tx current output power in dbm (high warning flag)
    rxtotpower_hwarn_flag                                    = BOOLEAN ; rx total power in  dbm (high warning flag)
    rxsigpower_hwarn_flag                                    = BOOLEAN; rx signal power in dbm (high warning flag)
```

##### 2.2.3.4 Transceiver VDM low warning flag data

The `TRANSCEIVER_VDM_LWARN_FLAG` table stores the flag status for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning flag for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG|ifname
    ; field                      = value
    laser_temperature_media_lwarn_flag{lane_num}             = BOOLEAN ; laser temperature low warning flag for media input
    esnr_media_input_lwarn_flag{lane_num}                    = BOOLEAN ; eSNR low warning flag for media input
    esnr_host_input_lwarn_flag{lane_num}                     = BOOLEAN ; eSNR low warning flag for host input
    pam4_level_transition_media_input_lwarn_flag{lane_num}   = BOOLEAN ; PAM4 level transition low warning flag for media input
    pam4_level_transition_host_input_lwarn_flag{lane_num}    = BOOLEAN ; PAM4 level transition low warning flag for host input
    prefec_ber_min_media_input_lwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER minimum low warning flag for media input
    prefec_ber_max_media_input_lwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER maximum low warning flag for media input
    prefec_ber_avg_media_input_lwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER average low warning flag for media input
    prefec_ber_curr_media_input_lwarn_flag{lane_num}         = BOOLEAN ; Pre-FEC BER current low warning flag for media input
    prefec_ber_min_host_input_lwarn_flag{lane_num}           = BOOLEAN ; Pre-FEC BER minimum low warning flag for host input
    prefec_ber_max_host_input_lwarn_flag{lane_num}           = BOOLEAN ; Pre-FEC BER maximum low warning flag for host input
    prefec_ber_avg_host_input_lwarn_flag{lane_num}           = BOOLEAN ; Pre-FEC BER average low warning flag for host input
    prefec_ber_curr_host_input_lwarn_flag{lane_num}          = BOOLEAN ; Pre-FEC BER current low warning flag for host input
    errored_frames_min_media_input_lwarn_flag{lane_num}      = BOOLEAN ; Errored frames minimum low warning flag for media input
    errored_frames_max_media_input_lwarn_flag{lane_num}      = BOOLEAN ; Errored frames maximum low warning flag for media input
    errored_frames_avg_media_input_lwarn_flag{lane_num}      = BOOLEAN ; Errored frames average low warning flag for media input
    errored_frames_curr_media_input_lwarn_flag{lane_num}     = BOOLEAN ; Errored frames current low warning flag for media input
    errored_frames_min_host_input_lwarn_flag{lane_num}       = BOOLEAN ; Errored frames minimum low warning flag for host input
    errored_frames_max_host_input_lwarn_flag{lane_num}       = BOOLEAN ; Errored frames maximum low warning flag for host input
    errored_frames_avg_host_input_lwarn_flag{lane_num}       = BOOLEAN ; Errored frames average low warning flag for host input
    errored_frames_curr_host_input_lwarn_flag{lane_num}      = BOOLEAN ; Errored frames current low warning flag for host input

    ;C-CMIS specific fields
    biasxi_lwarn_flag                                        = BOOLEAN ; modulator bias xi in percentage (low warning flag)
    biasxq_lwarn_flag                                        = BOOLEAN ; modulator bias xq in percentage (low warning flag)
    biasxp_lwarn_flag                                        = BOOLEAN ; modulator bias xp in percentage (low warning flag)
    biasyi_lwarn_flag                                        = BOOLEAN ; modulator bias yi in percentage (low warning flag)
    biasyq_lwarn_flag                                        = BOOLEAN ; modulator bias yq in percentage (low warning flag)
    biasyp_lwarn_flag                                        = BOOLEAN ; modulator bias yq in percentage (low warning flag)
    cdshort_lwarn_flag                                       = BOOLEAN ; chromatic dispersion, high granularity, short link in ps/nm (low warning flag)
    cdlong_lwarn_flag                                        = BOOLEAN ; chromatic dispersion, high granularity, long link in ps/nm (low warning flag)
    dgd_lwarn_flag                                           = BOOLEAN ; differential group delay in ps (low warning flag)
    sopmd_lwarn_flag                                         = BOOLEAN ; second order polarization mode dispersion in ps^2 (low warning flag)
    soproc_lwarn_flag                                        = BOOLEAN ; state of polarization rate of change in krad/s (low warning flag)
    pdl_lwarn_flag                                           = BOOLEAN ; polarization dependent loss in db (low warning flag)
    osnr_lwarn_flag                                          = BOOLEAN ; optical signal to noise ratio in db (low warning flag)
    esnr_lwarn_flag                                          = BOOLEAN ; electrical signal to noise ratio in db (low warning flag)
    cfo_lwarn_flag                                           = BOOLEAN ; carrier frequency offset in Hz (low warning flag)
    txcurrpower_lwarn_flag                                   = BOOLEAN ; tx current output power in dbm (low warning flag)
    rxtotpower_lwarn_flag                                    = BOOLEAN ; rx total power in  dbm (low warning flag)
    rxsigpower_lwarn_flag                                    = BOOLEAN; rx signal power in dbm (low warning flag)
```

#### 2.2.4 Transceiver VDM flag change count data

##### 2.2.4.1 Transceiver VDM high alarm flag change count data

The `TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT` table stores the flag change count for high alarm flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm flag change count for a port
    key                          = TRANSCEIVER_VDM_HALARM_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_halarm_chg_cnt{lane_num}             = INTEGER ; laser temperature high alarm flag change count for media input
    esnr_media_input_halarm_chg_cnt{lane_num}                    = INTEGER ; eSNR high alarm flag change count for media input
    esnr_host_input_halarm_chg_cnt{lane_num}                     = INTEGER ; eSNR high alarm flag change count for host input
    pam4_level_transition_media_input_halarm_chg_cnt{lane_num}   = INTEGER ; PAM4 level transition high alarm flag change count for media input
    pam4_level_transition_host_input_halarm_chg_cnt{lane_num}    = INTEGER ; PAM4 level transition high alarm flag change count for host input
    prefec_ber_min_media_input_halarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER minimum high alarm flag change count for media input
    prefec_ber_max_media_input_halarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER maximum high alarm flag change count for media input
    prefec_ber_avg_media_input_halarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER average high alarm flag change count for media input
    prefec_ber_curr_media_input_halarm_chg_cnt{lane_num}         = INTEGER ; Pre-FEC BER current high alarm flag change count for media input
    prefec_ber_min_host_input_halarm_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER minimum high alarm flag change count for host input
    prefec_ber_max_host_input_halarm_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER maximum high alarm flag change count for host input
    prefec_ber_avg_host_input_halarm_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER average high alarm flag change count for host input
    prefec_ber_curr_host_input_halarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER current high alarm flag change count for host input
    errored_frames_min_media_input_halarm_chg_cnt{lane_num}      = INTEGER ; Errored frames minimum high alarm flag change count for media input
    errored_frames_max_media_input_halarm_chg_cnt{lane_num}      = INTEGER ; Errored frames maximum high alarm flag change count for media input
    errored_frames_avg_media_input_halarm_chg_cnt{lane_num}      = INTEGER ; Errored frames average high alarm flag change count for media input
    errored_frames_curr_media_input_halarm_chg_cnt{lane_num}     = INTEGER ; Errored frames current high alarm flag change count for media input
    errored_frames_min_host_input_halarm_chg_cnt{lane_num}       = INTEGER ; Errored frames minimum high alarm flag change count for host input
    errored_frames_max_host_input_halarm_chg_cnt{lane_num}       = INTEGER ; Errored frames maximum high alarm flag change count for host input
    errored_frames_avg_host_input_halarm_chg_cnt{lane_num}       = INTEGER ; Errored frames average high alarm flag change count for host input
    errored_frames_curr_host_input_halarm_chg_cnt{lane_num}      = INTEGER ; Errored frames current high alarm flag change count for host input

    ;C-CMIS specific fields
    biasxi_halarm_chg_cnt                                        = INTEGER ; modulator bias xi in percentage (high alarm flag change count)
    biasxq_halarm_chg_cnt                                        = INTEGER ; modulator bias xq in percentage (high alarm flag change count)
    biasxp_halarm_chg_cnt                                        = INTEGER ; modulator bias xp in percentage (high alarm flag change count)
    biasyi_halarm_chg_cnt                                        = INTEGER ; modulator bias yi in percentage (high alarm flag change count)
    biasyq_halarm_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (high alarm flag change count)
    biasyp_halarm_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (high alarm flag change count)
    cdshort_halarm_chg_cnt                                       = INTEGER ; chromatic dispersion, high granularity, short link in ps/nm (high alarm flag change count)
    cdlong_halarm_chg_cnt                                        = INTEGER ; chromatic dispersion, high granularity, long link in ps/nm (high alarm flag change count)
    dgd_halarm_chg_cnt                                           = INTEGER ; differential group delay in ps (high alarm flag change count)
    sopmd_halarm_chg_cnt                                         = INTEGER ; second order polarization mode dispersion in ps^2 (high alarm flag change count)
    soproc_halarm_chg_cnt                                        = INTEGER ; state of polarization rate of change in krad/s (high alarm flag change count)
    pdl_halarm_chg_cnt                                           = INTEGER ; polarization dependent loss in db (high alarm flag change count)
    osnr_halarm_chg_cnt                                          = INTEGER ; optical signal to noise ratio in db (high alarm flag change count)
    esnr_halarm_chg_cnt                                          = INTEGER ; electrical signal to noise ratio in db (high alarm flag change count)
    cfo_halarm_chg_cnt                                           = INTEGER ; carrier frequency offset in Hz (high alarm flag change count)
    txcurrpower_halarm_chg_cnt                                   = INTEGER ; tx current output power in dbm (high alarm flag change count)
    rxtotpower_halarm_chg_cnt                                    = INTEGER ; rx total power in  dbm (high alarm flag change count)
    rxsigpower_halarm_chg_cnt                                    = INTEGER; rx signal power in dbm (high alarm flag change count)
```

##### 2.2.4.2 Transceiver VDM low alarm flag change count data

The `TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT` table stores the flag change count for low alarm flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm flag change count for a port
    key                          = TRANSCEIVER_VDM_LALARM_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_lalarm_chg_cnt{lane_num}             = INTEGER ; laser temperature low alarm flag change count for media input
    esnr_media_input_lalarm_chg_cnt{lane_num}                    = INTEGER ; eSNR low alarm flag change count for media input
    esnr_host_input_lalarm_chg_cnt{lane_num}                     = INTEGER ; eSNR low alarm flag change count for host input
    pam4_level_transition_media_input_lalarm_chg_cnt{lane_num}   = INTEGER ; PAM4 level transition low alarm flag change count for media input
    pam4_level_transition_host_input_lalarm_chg_cnt{lane_num}    = INTEGER ; PAM4 level transition low alarm flag change count for host input
    prefec_ber_min_media_input_lalarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER minimum low alarm flag change count for media input
    prefec_ber_max_media_input_lalarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER maximum low alarm flag change count for media input
    prefec_ber_avg_media_input_lalarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER average low alarm flag change count for media input
    prefec_ber_curr_media_input_lalarm_chg_cnt{lane_num}         = INTEGER ; Pre-FEC BER current low alarm flag change count for media input
    prefec_ber_min_host_input_lalarm_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER minimum low alarm flag change count for host input
    prefec_ber_max_host_input_lalarm_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER maximum low alarm flag change count for host input
    prefec_ber_avg_host_input_lalarm_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER average low alarm flag change count for host input
    prefec_ber_curr_host_input_lalarm_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER current low alarm flag change count for host input
    errored_frames_min_media_input_lalarm_chg_cnt{lane_num}      = INTEGER ; Errored frames minimum low alarm flag change count for media input
    errored_frames_max_media_input_lalarm_chg_cnt{lane_num}      = INTEGER ; Errored frames maximum low alarm flag change count for media input
    errored_frames_avg_media_input_lalarm_chg_cnt{lane_num}      = INTEGER ; Errored frames average low alarm flag change count for media input
    errored_frames_curr_media_input_lalarm_chg_cnt{lane_num}     = INTEGER ; Errored frames current low alarm flag change count for media input
    errored_frames_min_host_input_lalarm_chg_cnt{lane_num}       = INTEGER ; Errored frames minimum low alarm flag change count for host input
    errored_frames_max_host_input_lalarm_chg_cnt{lane_num}       = INTEGER ; Errored frames maximum low alarm flag change count for host input
    errored_frames_avg_host_input_lalarm_chg_cnt{lane_num}       = INTEGER ; Errored frames average low alarm flag change count for host input
    errored_frames_curr_host_input_lalarm_chg_cnt{lane_num}      = INTEGER ; Errored frames current low alarm flag change count for host input

    ;C-CMIS specific fields
    biasxi_lalarm_chg_cnt                                        = INTEGER ; modulator bias xi in percentage (low alarm flag change count)
    biasxq_lalarm_chg_cnt                                        = INTEGER ; modulator bias xq in percentage (low alarm flag change count)
    biasxp_lalarm_chg_cnt                                        = INTEGER ; modulator bias xp in percentage (low alarm flag change count)
    biasyi_lalarm_chg_cnt                                        = INTEGER ; modulator bias yi in percentage (low alarm flag change count)
    biasyq_lalarm_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (low alarm flag change count)
    biasyp_lalarm_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (low alarm flag change count)
    cdshort_lalarm_chg_cnt                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (low alarm flag change count)
    cdlong_lalarm_chg_cnt                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (low alarm flag change count)
    dgd_lalarm_chg_cnt                                           = INTEGER ; differential group delay in ps (low alarm flag change count)
    sopmd_lalarm_chg_cnt                                         = INTEGER ; second order polarization mode dispersion in ps^2 (low alarm flag change count)
    soproc_lalarm_chg_cnt                                        = INTEGER ; state of polarization rate of change in krad/s (low alarm flag change count)
    pdl_lalarm_chg_cnt                                           = INTEGER ; polarization dependent loss in db (low alarm flag change count)
    osnr_lalarm_chg_cnt                                          = INTEGER ; optical signal to noise ratio in db (low alarm flag change count)
    esnr_lalarm_chg_cnt                                          = INTEGER ; electrical signal to noise ratio in db (low alarm flag change count)
    cfo_lalarm_chg_cnt                                           = INTEGER ; carrier frequency offset in Hz (low alarm flag change count)
    txcurrpower_lalarm_chg_cnt                                   = INTEGER ; tx current output power in dbm (low alarm flag change count)
    rxtotpower_lalarm_chg_cnt                                    = INTEGER ; rx total power in  dbm (low alarm flag change count)
    rxsigpower_lalarm_chg_cnt                                    = INTEGER; rx signal power in dbm (low alarm flag change count)
```

##### 2.2.4.3 Transceiver VDM high warning flag change count data

The `TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT` table stores the flag change count for high warning flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning flag change count for a port
    key                          = TRANSCEIVER_VDM_HWARN_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_hwarn_chg_cnt{lane_num}             = INTEGER ; laser temperature high warning flag change count for media input
    esnr_media_input_hwarn_chg_cnt{lane_num}                    = INTEGER ; eSNR high warning flag change count for media input
    esnr_host_input_hwarn_chg_cnt{lane_num}                     = INTEGER ; eSNR high warning flag change count for host input
    pam4_level_transition_media_input_hwarn_chg_cnt{lane_num}   = INTEGER ; PAM4 level transition high warning flag change count for media input
    pam4_level_transition_host_input_hwarn_chg_cnt{lane_num}    = INTEGER ; PAM4 level transition high warning flag change count for host input
    prefec_ber_min_media_input_hwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER minimum high warning flag change count for media input
    prefec_ber_max_media_input_hwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER maximum high warning flag change count for media input
    prefec_ber_avg_media_input_hwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER average high warning flag change count for media input
    prefec_ber_curr_media_input_hwarn_chg_cnt{lane_num}         = INTEGER ; Pre-FEC BER current high warning flag change count for media input
    prefec_ber_min_host_input_hwarn_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER minimum high warning flag change count for host input
    prefec_ber_max_host_input_hwarn_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER maximum high warning flag change count for host input
    prefec_ber_avg_host_input_hwarn_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER average high warning flag change count for host input
    prefec_ber_curr_host_input_hwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER current high warning flag change count for host input
    errored_frames_min_media_input_hwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames minimum high warning flag change count for media input
    errored_frames_max_media_input_hwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames maximum high warning flag change count for media input
    errored_frames_avg_media_input_hwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames average high warning flag change count for media input
    errored_frames_curr_media_input_hwarn_chg_cnt{lane_num}     = INTEGER ; Errored frames current high warning flag change count for media input
    errored_frames_min_host_input_hwarn_chg_cnt{lane_num}       = INTEGER ; Errored frames minimum high warning flag change count for host input
    errored_frames_max_host_input_hwarn_chg_cnt{lane_num}       = INTEGER ; Errored frames maximum high warning flag change count for host input
    errored_frames_avg_host_input_hwarn_chg_cnt{lane_num}       = INTEGER ; Errored frames average high warning flag change count for host input
    errored_frames_curr_host_input_hwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames current high warning flag change count for host input

    ;C-CMIS specific fields
    biasxi_hwarn_chg_cnt                                        = INTEGER ; modulator bias xi in percentage (high warning flag change count)
    biasxq_hwarn_chg_cnt                                        = INTEGER ; modulator bias xq in percentage (high warning flag change count)
    biasxp_hwarn_chg_cnt                                        = INTEGER ; modulator bias xp in percentage (high warning flag change count)
    biasyi_hwarn_chg_cnt                                        = INTEGER ; modulator bias yi in percentage (high warning flag change count)
    biasyq_hwarn_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (high warning flag change count)
    biasyp_hwarn_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (high warning flag change count)
    cdshort_hwarn_chg_cnt                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (high warning flag change count)
    cdlong_hwarn_chg_cnt                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (high warning flag change count)
    dgd_hwarn_chg_cnt                                           = INTEGER ; differential group delay in ps (high warning flag change count)
    sopmd_hwarn_chg_cnt                                         = INTEGER ; second order polarization mode dispersion in ps^2 (high warning flag change count)
    soproc_hwarn_chg_cnt                                        = INTEGER ; state of polarization rate of change in krad/s (high warning flag change count)
    pdl_hwarn_chg_cnt                                           = INTEGER ; polarization dependent loss in db (high warning flag change count)
    osnr_hwarn_chg_cnt                                          = INTEGER ; optical signal to noise ratio in db (high warning flag change count)
    esnr_hwarn_chg_cnt                                          = INTEGER ; electrical signal to noise ratio in db (high warning flag change count)
    cfo_hwarn_chg_cnt                                           = INTEGER ; carrier frequency offset in Hz (high warning flag change count)
    txcurrpower_hwarn_chg_cnt                                   = INTEGER ; tx current output power in dbm (high warning flag change count)
    rxtotpower_hwarn_chg_cnt                                    = INTEGER ; rx total power in  dbm (high warning flag change count)
    rxsigpower_hwarn_chg_cnt                                    = INTEGER; rx signal power in dbm (high warning flag change count)
```

##### 2.2.4.4 Transceiver VDM low warning flag change count data

The `TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT` table stores the flag change count for low warning flag for the VDM data.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning flag change count for a port
    key                          = TRANSCEIVER_VDM_LWARN_FLAG_CHANGE_COUNT|ifname
    ; field                      = value
    laser_temperature_media_lwarn_chg_cnt{lane_num}             = INTEGER ; laser temperature low warning flag change count for media input
    esnr_media_input_lwarn_chg_cnt{lane_num}                    = INTEGER ; eSNR low warning flag change count for media input
    esnr_host_input_lwarn_chg_cnt{lane_num}                     = INTEGER ; eSNR low warning flag change count for host input
    pam4_level_transition_media_input_lwarn_chg_cnt{lane_num}   = INTEGER ; PAM4 level transition low warning flag change count for media input
    pam4_level_transition_host_input_lwarn_chg_cnt{lane_num}    = INTEGER ; PAM4 level transition low warning flag change count for host input
    prefec_ber_min_media_input_lwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER minimum low warning flag change count for media input
    prefec_ber_max_media_input_lwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER maximum low warning flag change count for media input
    prefec_ber_avg_media_input_lwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER average low warning flag change count for media input
    prefec_ber_curr_media_input_lwarn_chg_cnt{lane_num}         = INTEGER ; Pre-FEC BER current low warning flag change count for media input
    prefec_ber_min_host_input_lwarn_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER minimum low warning flag change count for host input
    prefec_ber_max_host_input_lwarn_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER maximum low warning flag change count for host input
    prefec_ber_avg_host_input_lwarn_chg_cnt{lane_num}           = INTEGER ; Pre-FEC BER average low warning flag change count for host input
    prefec_ber_curr_host_input_lwarn_chg_cnt{lane_num}          = INTEGER ; Pre-FEC BER current low warning flag change count for host input
    errored_frames_min_media_input_lwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames minimum low warning flag change count for media input
    errored_frames_max_media_input_lwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames maximum low warning flag change count for media input
    errored_frames_avg_media_input_lwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames average low warning flag change count for media input
    errored_frames_curr_media_input_lwarn_chg_cnt{lane_num}     = INTEGER ; Errored frames current low warning flag change count for media input
    errored_frames_min_host_input_lwarn_chg_cnt{lane_num}       = INTEGER ; Errored frames minimum low warning flag change count for host input
    errored_frames_max_host_input_lwarn_chg_cnt{lane_num}       = INTEGER ; Errored frames maximum low warning flag change count for host input
    errored_frames_avg_host_input_lwarn_chg_cnt{lane_num}       = INTEGER ; Errored frames average low warning flag change count for host input
    errored_frames_curr_host_input_lwarn_chg_cnt{lane_num}      = INTEGER ; Errored frames current low warning flag change count for host input

    ;C-CMIS specific fields
    biasxi_lwarn_chg_cnt                                        = INTEGER ; modulator bias xi in percentage (low warning flag change count)
    biasxq_lwarn_chg_cnt                                        = INTEGER ; modulator bias xq in percentage (low warning flag change count)
    biasxp_lwarn_chg_cnt                                        = INTEGER ; modulator bias xp in percentage (low warning flag change count)
    biasyi_lwarn_chg_cnt                                        = INTEGER ; modulator bias yi in percentage (low warning flag change count)
    biasyq_lwarn_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (low warning flag change count)
    biasyp_lwarn_chg_cnt                                        = INTEGER ; modulator bias yq in percentage (low warning flag change count)
    cdshort_lwarn_chg_cnt                                       = INTEGER ; chromatic dispersion, low granularity, short link in ps/nm (low warning flag change count)
    cdlong_lwarn_chg_cnt                                        = INTEGER ; chromatic dispersion, low granularity, long link in ps/nm (low warning flag change count)
    dgd_lwarn_chg_cnt                                           = INTEGER ; differential group delay in ps (low warning flag change count)
    sopmd_lwarn_chg_cnt                                         = INTEGER ; second order polarization mode dispersion in ps^2 (low warning flag change count)
    soproc_lwarn_chg_cnt                                        = INTEGER ; state of polarization rate of change in krad/s (low warning flag change count)
    pdl_lwarn_chg_cnt                                           = INTEGER ; polarization dependent loss in db (low warning flag change count)
    osnr_lwarn_chg_cnt                                          = INTEGER ; optical signal to noise ratio in db (low warning flag change count)
    esnr_lwarn_chg_cnt                                          = INTEGER ; electrical signal to noise ratio in db (low warning flag change count)
    cfo_lwarn_chg_cnt                                           = INTEGER ; carrier frequency offset in Hz (low warning flag change count)
    txcurrpower_lwarn_chg_cnt                                   = INTEGER ; tx current output power in dbm (low warning flag change count)
    rxtotpower_lwarn_chg_cnt                                    = INTEGER ; rx total power in  dbm (low warning flag change count)
    rxsigpower_lwarn_chg_cnt                                    = INTEGER; rx signal power in dbm (low warning flag change count)
```

#### 2.2.5 Transceiver VDM flag time set data

##### 2.2.5.1 Transceiver VDM high alarm flag time set data

The `TRANSCEIVER_VDM_HALARM_SET_TIME` table stores the flag time set for the VDM high alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm last set time for a port
    key                          = TRANSCEIVER_VDM_HALARM_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_halarm_last_set_time{lane_num}             = STR ; laser temperature high alarm last set time for media input
    esnr_media_input_halarm_last_set_time{lane_num}                    = STR ; eSNR high alarm last set time for media input
    esnr_host_input_halarm_last_set_time{lane_num}                     = STR ; eSNR high alarm last set time for host input
    pam4_level_transition_media_input_halarm_last_set_time{lane_num}   = STR ; PAM4 level transition high alarm last set time for media input
    pam4_level_transition_host_input_halarm_last_set_time{lane_num}    = STR ; PAM4 level transition high alarm last set time for host input
    prefec_ber_min_media_input_halarm_last_set_time{lane_num}          = STR ; Pre-FEC BER minimum high alarm last set time for media input
    prefec_ber_max_media_input_halarm_last_set_time{lane_num}          = STR ; Pre-FEC BER maximum high alarm last set time for media input
    prefec_ber_avg_media_input_halarm_last_set_time{lane_num}          = STR ; Pre-FEC BER average high alarm last set time for media input
    prefec_ber_curr_media_input_halarm_last_set_time{lane_num}         = STR ; Pre-FEC BER current high alarm last set time for media input
    prefec_ber_min_host_input_halarm_last_set_time{lane_num}           = STR ; Pre-FEC BER minimum high alarm last set time for host input
    prefec_ber_max_host_input_halarm_last_set_time{lane_num}           = STR ; Pre-FEC BER maximum high alarm last set time for host input
    prefec_ber_avg_host_input_halarm_last_set_time{lane_num}           = STR ; Pre-FEC BER average high alarm last set time for host input
    prefec_ber_curr_host_input_halarm_last_set_time{lane_num}          = STR ; Pre-FEC BER current high alarm last set time for host input
    errored_frames_min_media_input_halarm_last_set_time{lane_num}      = STR ; Errored frames minimum high alarm last set time for media input
    errored_frames_max_media_input_halarm_last_set_time{lane_num}      = STR ; Errored frames maximum high alarm last set time for media input
    errored_frames_avg_media_input_halarm_last_set_time{lane_num}      = STR ; Errored frames average high alarm last set time for media input
    errored_frames_curr_media_input_halarm_last_set_time{lane_num}     = STR ; Errored frames current high alarm last set time for media input
    errored_frames_min_host_input_halarm_last_set_time{lane_num}       = STR ; Errored frames minimum high alarm last set time for host input
    errored_frames_max_host_input_halarm_last_set_time{lane_num}       = STR ; Errored frames maximum high alarm last set time for host input
    errored_frames_avg_host_input_halarm_last_set_time{lane_num}       = STR ; Errored frames average high alarm last set time for host input
    errored_frames_curr_host_input_halarm_last_set_time{lane_num}      = STR ; Errored frames current high alarm last set time for host input

    ;C-CMIS specific fields
    biasxi_halarm_last_set_time                                        = STR ; modulator bias xi in percentage (high alarm last set time)
    biasxq_halarm_last_set_time                                        = STR ; modulator bias xq in percentage (high alarm last set time)
    biasxp_halarm_last_set_time                                        = STR ; modulator bias xp in percentage (high alarm last set time)
    biasyi_halarm_last_set_time                                        = STR ; modulator bias yi in percentage (high alarm last set time)
    biasyq_halarm_last_set_time                                        = STR ; modulator bias yq in percentage (high alarm last set time)
    biasyp_halarm_last_set_time                                        = STR ; modulator bias yq in percentage (high alarm last set time)
    cdshort_halarm_last_set_time                                       = STR ; chromatic dispersion, high granularity, short link in ps/nm (high alarm last set time)
    cdlong_halarm_last_set_time                                        = STR ; chromatic dispersion, high granularity, long link in ps/nm (high alarm last set time)
    dgd_halarm_last_set_time                                           = STR ; differential group delay in ps (high alarm last set time)
    sopmd_halarm_last_set_time                                         = STR ; second order polarization mode dispersion in ps^2 (high alarm last set time)
    soproc_halarm_last_set_time                                        = STR ; state of polarization rate of change in krad/s (high alarm last set time)
    pdl_halarm_last_set_time                                           = STR ; polarization dependent loss in db (high alarm last set time)
    osnr_halarm_last_set_time                                          = STR ; optical signal to noise ratio in db (high alarm last set time)
    esnr_halarm_last_set_time                                          = STR ; electrical signal to noise ratio in db (high alarm last set time)
    cfo_halarm_last_set_time                                           = STR ; carrier frequency offset in Hz (high alarm last set time)
    txcurrpower_halarm_last_set_time                                   = STR ; tx current output power in dbm (high alarm last set time)
    rxtotpower_halarm_last_set_time                                    = STR ; rx total power in  dbm (high alarm last set time)
    rxsigpower_halarm_last_set_time                                    = STR; rx signal power in dbm (high alarm last set time)
```

##### 2.2.5.2 Transceiver VDM low alarm flag time set data

The `TRANSCEIVER_VDM_LALARM_SET_TIME` table stores the flag time set for the VDM low alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm last set time for a port
    key                          = TRANSCEIVER_VDM_LALARM_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_lalarm_last_set_time{lane_num}             = STR ; laser temperature low alarm last set time for media input
    esnr_media_input_lalarm_last_set_time{lane_num}                    = STR ; eSNR low alarm last set time for media input
    esnr_host_input_lalarm_last_set_time{lane_num}                     = STR ; eSNR low alarm last set time for host input
    pam4_level_transition_media_input_lalarm_last_set_time{lane_num}   = STR ; PAM4 level transition low alarm last set time for media input
    pam4_level_transition_host_input_lalarm_last_set_time{lane_num}    = STR ; PAM4 level transition low alarm last set time for host input
    prefec_ber_min_media_input_lalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER minimum low alarm last set time for media input
    prefec_ber_max_media_input_lalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER maximum low alarm last set time for media input
    prefec_ber_avg_media_input_lalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER average low alarm last set time for media input
    prefec_ber_curr_media_input_lalarm_last_set_time{lane_num}         = STR ; Pre-FEC BER current low alarm last set time for media input
    prefec_ber_min_host_input_lalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER minimum low alarm last set time for host input
    prefec_ber_max_host_input_lalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER maximum low alarm last set time for host input
    prefec_ber_avg_host_input_lalarm_last_set_time{lane_num}           = STR ; Pre-FEC BER average low alarm last set time for host input
    prefec_ber_curr_host_input_lalarm_last_set_time{lane_num}          = STR ; Pre-FEC BER current low alarm last set time for host input
    errored_frames_min_media_input_lalarm_last_set_time{lane_num}      = STR ; Errored frames minimum low alarm last set time for media input
    errored_frames_max_media_input_lalarm_last_set_time{lane_num}      = STR ; Errored frames maximum low alarm last set time for media input
    errored_frames_avg_media_input_lalarm_last_set_time{lane_num}      = STR ; Errored frames average low alarm last set time for media input
    errored_frames_curr_media_input_lalarm_last_set_time{lane_num}     = STR ; Errored frames current low alarm last set time for media input
    errored_frames_min_host_input_lalarm_last_set_time{lane_num}       = STR ; Errored frames minimum low alarm last set time for host input
    errored_frames_max_host_input_lalarm_last_set_time{lane_num}       = STR ; Errored frames maximum low alarm last set time for host input
    errored_frames_avg_host_input_lalarm_last_set_time{lane_num}       = STR ; Errored frames average low alarm last set time for host input
    errored_frames_curr_host_input_lalarm_last_set_time{lane_num}      = STR ; Errored frames current low alarm last set time for host input

    ;C-CMIS specific fields
    biasxi_lalarm_last_set_time                                        = STR ; modulator bias xi in percentage (low alarm last set time)
    biasxq_lalarm_last_set_time                                        = STR ; modulator bias xq in percentage (low alarm last set time)
    biasxp_lalarm_last_set_time                                        = STR ; modulator bias xp in percentage (low alarm last set time)
    biasyi_lalarm_last_set_time                                        = STR ; modulator bias yi in percentage (low alarm last set time)
    biasyq_lalarm_last_set_time                                        = STR ; modulator bias yq in percentage (low alarm last set time)
    biasyp_lalarm_last_set_time                                        = STR ; modulator bias yq in percentage (low alarm last set time)
    cdshort_lalarm_last_set_time                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low alarm last set time)
    cdlong_lalarm_last_set_time                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low alarm last set time)
    dgd_lalarm_last_set_time                                           = STR ; differential group delay in ps (low alarm last set time)
    sopmd_lalarm_last_set_time                                         = STR ; second order polarization mode dispersion in ps^2 (low alarm last set time)
    soproc_lalarm_last_set_time                                        = STR ; state of polarization rate of change in krad/s (low alarm last set time)
    pdl_lalarm_last_set_time                                           = STR ; polarization dependent loss in db (low alarm last set time)
    osnr_lalarm_last_set_time                                          = STR ; optical signal to noise ratio in db (low alarm last set time)
    esnr_lalarm_last_set_time                                          = STR ; electrical signal to noise ratio in db (low alarm last set time)
    cfo_lalarm_last_set_time                                           = STR ; carrier frequency offset in Hz (low alarm last set time)
    txcurrpower_lalarm_last_set_time                                   = STR ; tx current output power in dbm (low alarm last set time)
    rxtotpower_lalarm_last_set_time                                    = STR ; rx total power in  dbm (low alarm last set time)
    rxsigpower_lalarm_last_set_time                                    = STR; rx signal power in dbm (low alarm last set time)
```

##### 2.2.5.3 Transceiver VDM high warning flag time set data

The `TRANSCEIVER_VDM_HWARN_SET_TIME` table stores the flag time set for the VDM high warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning last set time for a port
    key                          = TRANSCEIVER_VDM_HWARN_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_hwarn_last_set_time{lane_num}             = STR ; laser temperature high warning last set time for media input
    esnr_media_input_hwarn_last_set_time{lane_num}                    = STR ; eSNR high warning last set time for media input
    esnr_host_input_hwarn_last_set_time{lane_num}                     = STR ; eSNR high warning last set time for host input
    pam4_level_transition_media_input_hwarn_last_set_time{lane_num}   = STR ; PAM4 level transition high warning last set time for media input
    pam4_level_transition_host_input_hwarn_last_set_time{lane_num}    = STR ; PAM4 level transition high warning last set time for host input
    prefec_ber_min_media_input_hwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER minimum high warning last set time for media input
    prefec_ber_max_media_input_hwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER maximum high warning last set time for media input
    prefec_ber_avg_media_input_hwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER average high warning last set time for media input
    prefec_ber_curr_media_input_hwarn_last_set_time{lane_num}         = STR ; Pre-FEC BER current high warning last set time for media input
    prefec_ber_min_host_input_hwarn_last_set_time{lane_num}           = STR ; Pre-FEC BER minimum high warning last set time for host input
    prefec_ber_max_host_input_hwarn_last_set_time{lane_num}           = STR ; Pre-FEC BER maximum high warning last set time for host input
    prefec_ber_avg_host_input_hwarn_last_set_time{lane_num}           = STR ; Pre-FEC BER average high warning last set time for host input
    prefec_ber_curr_host_input_hwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER current high warning last set time for host input
    errored_frames_min_media_input_hwarn_last_set_time{lane_num}      = STR ; Errored frames minimum high warning last set time for media input
    errored_frames_max_media_input_hwarn_last_set_time{lane_num}      = STR ; Errored frames maximum high warning last set time for media input
    errored_frames_avg_media_input_hwarn_last_set_time{lane_num}      = STR ; Errored frames average high warning last set time for media input
    errored_frames_curr_media_input_hwarn_last_set_time{lane_num}     = STR ; Errored frames current high warning last set time for media input
    errored_frames_min_host_input_hwarn_last_set_time{lane_num}       = STR ; Errored frames minimum high warning last set time for host input
    errored_frames_max_host_input_hwarn_last_set_time{lane_num}       = STR ; Errored frames maximum high warning last set time for host input
    errored_frames_avg_host_input_hwarn_last_set_time{lane_num}       = STR ; Errored frames average high warning last set time for host input
    errored_frames_curr_host_input_hwarn_last_set_time{lane_num}      = STR ; Errored frames current high warning last set time for host input

    ;C-CMIS specific fields
    biasxi_hwarn_last_set_time                                        = STR ; modulator bias xi in percentage (high warning last set time)
    biasxq_hwarn_last_set_time                                        = STR ; modulator bias xq in percentage (high warning last set time)
    biasxp_hwarn_last_set_time                                        = STR ; modulator bias xp in percentage (high warning last set time)
    biasyi_hwarn_last_set_time                                        = STR ; modulator bias yi in percentage (high warning last set time)
    biasyq_hwarn_last_set_time                                        = STR ; modulator bias yq in percentage (high warning last set time)
    biasyp_hwarn_last_set_time                                        = STR ; modulator bias yq in percentage (high warning last set time)
    cdshort_hwarn_last_set_time                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (high warning last set time)
    cdlong_hwarn_last_set_time                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (high warning last set time)
    dgd_hwarn_last_set_time                                           = STR ; differential group delay in ps (high warning last set time)
    sopmd_hwarn_last_set_time                                         = STR ; second order polarization mode dispersion in ps^2 (high warning last set time)
    soproc_hwarn_last_set_time                                        = STR ; state of polarization rate of change in krad/s (high warning last set time)
    pdl_hwarn_last_set_time                                           = STR ; polarization dependent loss in db (high warning last set time)
    osnr_hwarn_last_set_time                                          = STR ; optical signal to noise ratio in db (high warning last set time)
    esnr_hwarn_last_set_time                                          = STR ; electrical signal to noise ratio in db (high warning last set time)
    cfo_hwarn_last_set_time                                           = STR ; carrier frequency offset in Hz (high warning last set time)
    txcurrpower_hwarn_last_set_time                                   = STR ; tx current output power in dbm (high warning last set time)
    rxtotpower_hwarn_last_set_time                                    = STR ; rx total power in  dbm (high warning last set time)
    rxsigpower_hwarn_last_set_time                                    = STR; rx signal power in dbm (high warning last set time)
```

##### 2.2.5.4 Transceiver VDM low warning flag time set data

The `TRANSCEIVER_VDM_LWARN_SET_TIME` table stores the flag time set for the VDM low warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning last set time for a port
    key                          = TRANSCEIVER_VDM_LWARN_SET_TIME|ifname
    ; field                      = value
    laser_temperature_media_lwarn_last_set_time{lane_num}             = STR ; laser temperature low warning last set time for media input
    esnr_media_input_lwarn_last_set_time{lane_num}                    = STR ; eSNR low warning last set time for media input
    esnr_host_input_lwarn_last_set_time{lane_num}                     = STR ; eSNR low warning last set time for host input
    pam4_level_transition_media_input_lwarn_last_set_time{lane_num}   = STR ; PAM4 level transition low warning last set time for media input
    pam4_level_transition_host_input_lwarn_last_set_time{lane_num}    = STR ; PAM4 level transition low warning last set time for host input
    prefec_ber_min_media_input_lwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER minimum low warning last set time for media input
    prefec_ber_max_media_input_lwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER maximum low warning last set time for media input
    prefec_ber_avg_media_input_lwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER average low warning last set time for media input
    prefec_ber_curr_media_input_lwarn_last_set_time{lane_num}         = STR ; Pre-FEC BER current low warning last set time for media input
    prefec_ber_min_host_input_lwarn_last_set_time{lane_num}           = STR ; Pre-FEC BER minimum low warning last set time for host input
    prefec_ber_max_host_input_lwarn_last_set_time{lane_num}           = STR ; Pre-FEC BER maximum low warning last set time for host input
    prefec_ber_avg_host_input_lwarn_last_set_time{lane_num}           = STR ; Pre-FEC BER average low warning last set time for host input
    prefec_ber_curr_host_input_lwarn_last_set_time{lane_num}          = STR ; Pre-FEC BER current low warning last set time for host input
    errored_frames_min_media_input_lwarn_last_set_time{lane_num}      = STR ; Errored frames minimum low warning last set time for media input
    errored_frames_max_media_input_lwarn_last_set_time{lane_num}      = STR ; Errored frames maximum low warning last set time for media input
    errored_frames_avg_media_input_lwarn_last_set_time{lane_num}      = STR ; Errored frames average low warning last set time for media input
    errored_frames_curr_media_input_lwarn_last_set_time{lane_num}     = STR ; Errored frames current low warning last set time for media input
    errored_frames_min_host_input_lwarn_last_set_time{lane_num}       = STR ; Errored frames minimum low warning last set time for host input
    errored_frames_max_host_input_lwarn_last_set_time{lane_num}       = STR ; Errored frames maximum low warning last set time for host input
    errored_frames_avg_host_input_lwarn_last_set_time{lane_num}       = STR ; Errored frames average low warning last set time for host input
    errored_frames_curr_host_input_lwarn_last_set_time{lane_num}      = STR ; Errored frames current low warning last set time for host input

    ;C-CMIS specific fields
    biasxi_lwarn_last_set_time                                        = STR ; modulator bias xi in percentage (low warning last set time)
    biasxq_lwarn_last_set_time                                        = STR ; modulator bias xq in percentage (low warning last set time)
    biasxp_lwarn_last_set_time                                        = STR ; modulator bias xp in percentage (low warning last set time)
    biasyi_lwarn_last_set_time                                        = STR ; modulator bias yi in percentage (low warning last set time)
    biasyq_lwarn_last_set_time                                        = STR ; modulator bias yq in percentage (low warning last set time)
    biasyp_lwarn_last_set_time                                        = STR ; modulator bias yq in percentage (low warning last set time)
    cdshort_lwarn_last_set_time                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low warning last set time)
    cdlong_lwarn_last_set_time                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low warning last set time)
    dgd_lwarn_last_set_time                                           = STR ; differential group delay in ps (low warning last set time)
    sopmd_lwarn_last_set_time                                         = STR ; second order polarization mode dispersion in ps^2 (low warning last set time)
    soproc_lwarn_last_set_time                                        = STR ; state of polarization rate of change in krad/s (low warning last set time)
    pdl_lwarn_last_set_time                                           = STR ; polarization dependent loss in db (low warning last set time)
    osnr_lwarn_last_set_time                                          = STR ; optical signal to noise ratio in db (low warning last set time)
    esnr_lwarn_last_set_time                                          = STR ; electrical signal to noise ratio in db (low warning last set time)
    cfo_lwarn_last_set_time                                           = STR ; carrier frequency offset in Hz (low warning last set time)
    txcurrpower_lwarn_last_set_time                                   = STR ; tx current output power in dbm (low warning last set time)
    rxtotpower_lwarn_last_set_time                                    = STR ; rx total power in  dbm (low warning last set time)
    rxsigpower_lwarn_last_set_time                                    = STR; rx signal power in dbm (low warning last set time)
```

#### 2.2.6 Transceiver VDM flag time clear data

##### 2.2.6.1 Transceiver VDM high alarm flag time clear data

The `TRANSCEIVER_VDM_HALARM_CLEAR_TIME` table stores the flag time clear for the VDM high alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high alarm last clear time for a port
    key                          = TRANSCEIVER_VDM_HALARM_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_halarm_last_clear_time{lane_num}             = STR ; laser temperature high alarm last clear time for media input
    esnr_media_input_halarm_last_clear_time{lane_num}                    = STR ; eSNR high alarm last clear time for media input
    esnr_host_input_halarm_last_clear_time{lane_num}                     = STR ; eSNR high alarm last clear time for host input
    pam4_level_transition_media_input_halarm_last_clear_time{lane_num}   = STR ; PAM4 level transition high alarm last clear time for media input
    pam4_level_transition_host_input_halarm_last_clear_time{lane_num}    = STR ; PAM4 level transition high alarm last clear time for host input
    prefec_ber_min_media_input_halarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER minimum high alarm last clear time for media input
    prefec_ber_max_media_input_halarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER maximum high alarm last clear time for media input
    prefec_ber_avg_media_input_halarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER average high alarm last clear time for media input
    prefec_ber_curr_media_input_halarm_last_clear_time{lane_num}         = STR ; Pre-FEC BER current high alarm last clear time for media input
    prefec_ber_min_host_input_halarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER minimum high alarm last clear time for host input
    prefec_ber_max_host_input_halarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER maximum high alarm last clear time for host input
    prefec_ber_avg_host_input_halarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER average high alarm last clear time for host input
    prefec_ber_curr_host_input_halarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER current high alarm last clear time for host input
    errored_frames_min_media_input_halarm_last_clear_time{lane_num}      = STR ; Errored frames minimum high alarm last clear time for media input
    errored_frames_max_media_input_halarm_last_clear_time{lane_num}      = STR ; Errored frames maximum high alarm last clear time for media input
    errored_frames_avg_media_input_halarm_last_clear_time{lane_num}      = STR ; Errored frames average high alarm last clear time for media input
    errored_frames_curr_media_input_halarm_last_clear_time{lane_num}     = STR ; Errored frames current high alarm last clear time for media input
    errored_frames_min_host_input_halarm_last_clear_time{lane_num}       = STR ; Errored frames minimum high alarm last clear time for host input
    errored_frames_max_host_input_halarm_last_clear_time{lane_num}       = STR ; Errored frames maximum high alarm last clear time for host input
    errored_frames_avg_host_input_halarm_last_clear_time{lane_num}       = STR ; Errored frames average high alarm last clear time for host input
    errored_frames_curr_host_input_halarm_last_clear_time{lane_num}      = STR ; Errored frames current high alarm last clear time for host input

    ;C-CMIS specific fields
    biasxi_halarm_last_clear_time                                        = STR ; modulator bias xi in percentage (high alarm last clear time)
    biasxq_halarm_last_clear_time                                        = STR ; modulator bias xq in percentage (high alarm last clear time)
    biasxp_halarm_last_clear_time                                        = STR ; modulator bias xp in percentage (high alarm last clear time)
    biasyi_halarm_last_clear_time                                        = STR ; modulator bias yi in percentage (high alarm last clear time)
    biasyq_halarm_last_clear_time                                        = STR ; modulator bias yq in percentage (high alarm last clear time)
    biasyp_halarm_last_clear_time                                        = STR ; modulator bias yq in percentage (high alarm last clear time)
    cdshort_halarm_last_clear_time                                       = STR ; chromatic dispersion, high granularity, short link in ps/nm (high alarm last clear time)
    cdlong_halarm_last_clear_time                                        = STR ; chromatic dispersion, high granularity, long link in ps/nm (high alarm last clear time)
    dgd_halarm_last_clear_time                                           = STR ; differential group delay in ps (high alarm last clear time)
    sopmd_halarm_last_clear_time                                         = STR ; second order polarization mode dispersion in ps^2 (high alarm last clear time)
    soproc_halarm_last_clear_time                                        = STR ; state of polarization rate of change in krad/s (high alarm last clear time)
    pdl_halarm_last_clear_time                                           = STR ; polarization dependent loss in db (high alarm last clear time)
    osnr_halarm_last_clear_time                                          = STR ; optical signal to noise ratio in db (high alarm last clear time)
    esnr_halarm_last_clear_time                                          = STR ; electrical signal to noise ratio in db (high alarm last clear time)
    cfo_halarm_last_clear_time                                           = STR ; carrier frequency offset in Hz (high alarm last clear time)
    txcurrpower_halarm_last_clear_time                                   = STR ; tx current output power in dbm (high alarm last clear time)
    rxtotpower_halarm_last_clear_time                                    = STR ; rx total power in  dbm (high alarm last clear time)
    rxsigpower_halarm_last_clear_time                                    = STR; rx signal power in dbm (high alarm last clear time)
```

##### 2.2.6.2 Transceiver VDM low alarm flag time clear data

The `TRANSCEIVER_VDM_LALARM_CLEAR_TIME` table stores the flag time clear for the VDM low alarm flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low alarm last clear time for a port
    key                          = TRANSCEIVER_VDM_LALARM_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_lalarm_last_clear_time{lane_num}             = STR ; laser temperature low alarm last clear time for media input
    esnr_media_input_lalarm_last_clear_time{lane_num}                    = STR ; eSNR low alarm last clear time for media input
    esnr_host_input_lalarm_last_clear_time{lane_num}                     = STR ; eSNR low alarm last clear time for host input
    pam4_level_transition_media_input_lalarm_last_clear_time{lane_num}   = STR ; PAM4 level transition low alarm last clear time for media input
    pam4_level_transition_host_input_lalarm_last_clear_time{lane_num}    = STR ; PAM4 level transition low alarm last clear time for host input
    prefec_ber_min_media_input_lalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER minimum low alarm last clear time for media input
    prefec_ber_max_media_input_lalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER maximum low alarm last clear time for media input
    prefec_ber_avg_media_input_lalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER average low alarm last clear time for media input
    prefec_ber_curr_media_input_lalarm_last_clear_time{lane_num}         = STR ; Pre-FEC BER current low alarm last clear time for media input
    prefec_ber_min_host_input_lalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER minimum low alarm last clear time for host input
    prefec_ber_max_host_input_lalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER maximum low alarm last clear time for host input
    prefec_ber_avg_host_input_lalarm_last_clear_time{lane_num}           = STR ; Pre-FEC BER average low alarm last clear time for host input
    prefec_ber_curr_host_input_lalarm_last_clear_time{lane_num}          = STR ; Pre-FEC BER current low alarm last clear time for host input
    errored_frames_min_media_input_lalarm_last_clear_time{lane_num}      = STR ; Errored frames minimum low alarm last clear time for media input
    errored_frames_max_media_input_lalarm_last_clear_time{lane_num}      = STR ; Errored frames maximum low alarm last clear time for media input
    errored_frames_avg_media_input_lalarm_last_clear_time{lane_num}      = STR ; Errored frames average low alarm last clear time for media input
    errored_frames_curr_media_input_lalarm_last_clear_time{lane_num}     = STR ; Errored frames current low alarm last clear time for media input
    errored_frames_min_host_input_lalarm_last_clear_time{lane_num}       = STR ; Errored frames minimum low alarm last clear time for host input
    errored_frames_max_host_input_lalarm_last_clear_time{lane_num}       = STR ; Errored frames maximum low alarm last clear time for host input
    errored_frames_avg_host_input_lalarm_last_clear_time{lane_num}       = STR ; Errored frames average low alarm last clear time for host input
    errored_frames_curr_host_input_lalarm_last_clear_time{lane_num}      = STR ; Errored frames current low alarm last clear time for host input

    ;C-CMIS specific fields
    biasxi_lalarm_last_clear_time                                        = STR ; modulator bias xi in percentage (low alarm last clear time)
    biasxq_lalarm_last_clear_time                                        = STR ; modulator bias xq in percentage (low alarm last clear time)
    biasxp_lalarm_last_clear_time                                        = STR ; modulator bias xp in percentage (low alarm last clear time)
    biasyi_lalarm_last_clear_time                                        = STR ; modulator bias yi in percentage (low alarm last clear time)
    biasyq_lalarm_last_clear_time                                        = STR ; modulator bias yq in percentage (low alarm last clear time)
    biasyp_lalarm_last_clear_time                                        = STR ; modulator bias yq in percentage (low alarm last clear time)
    cdshort_lalarm_last_clear_time                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low alarm last clear time)
    cdlong_lalarm_last_clear_time                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low alarm last clear time)
    dgd_lalarm_last_clear_time                                           = STR ; differential group delay in ps (low alarm last clear time)
    sopmd_lalarm_last_clear_time                                         = STR ; second order polarization mode dispersion in ps^2 (low alarm last clear time)
    soproc_lalarm_last_clear_time                                        = STR ; state of polarization rate of change in krad/s (low alarm last clear time)
    pdl_lalarm_last_clear_time                                           = STR ; polarization dependent loss in db (low alarm last clear time)
    osnr_lalarm_last_clear_time                                          = STR ; optical signal to noise ratio in db (low alarm last clear time)
    esnr_lalarm_last_clear_time                                          = STR ; electrical signal to noise ratio in db (low alarm last clear time)
    cfo_lalarm_last_clear_time                                           = STR ; carrier frequency offset in Hz (low alarm last clear time)
    txcurrpower_lalarm_last_clear_time                                   = STR ; tx current output power in dbm (low alarm last clear time)
    rxtotpower_lalarm_last_clear_time                                    = STR ; rx total power in  dbm (low alarm last clear time)
    rxsigpower_lalarm_last_clear_time                                    = STR; rx signal power in dbm (low alarm last clear time)
```

##### 2.2.6.3 Transceiver VDM high warning flag time clear data

The `TRANSCEIVER_VDM_HWARN_CLEAR_TIME` table stores the flag time clear for the VDM high warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM high warning last clear time for a port
    key                          = TRANSCEIVER_VDM_HWARN_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_hwarn_last_clear_time{lane_num}             = STR ; laser temperature high warning last clear time for media input
    esnr_media_input_hwarn_last_clear_time{lane_num}                    = STR ; eSNR high warning last clear time for media input
    esnr_host_input_hwarn_last_clear_time{lane_num}                     = STR ; eSNR high warning last clear time for host input
    pam4_level_transition_media_input_hwarn_last_clear_time{lane_num}   = STR ; PAM4 level transition high warning last clear time for media input
    pam4_level_transition_host_input_hwarn_last_clear_time{lane_num}    = STR ; PAM4 level transition high warning last clear time for host input
    prefec_ber_min_media_input_hwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER minimum high warning last clear time for media input
    prefec_ber_max_media_input_hwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER maximum high warning last clear time for media input
    prefec_ber_avg_media_input_hwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER average high warning last clear time for media input
    prefec_ber_curr_media_input_hwarn_last_clear_time{lane_num}         = STR ; Pre-FEC BER current high warning last clear time for media input
    prefec_ber_min_host_input_hwarn_last_clear_time{lane_num}           = STR ; Pre-FEC BER minimum high warning last clear time for host input
    prefec_ber_max_host_input_hwarn_last_clear_time{lane_num}           = STR ; Pre-FEC BER maximum high warning last clear time for host input
    prefec_ber_avg_host_input_hwarn_last_clear_time{lane_num}           = STR ; Pre-FEC BER average high warning last clear time for host input
    prefec_ber_curr_host_input_hwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER current high warning last clear time for host input
    errored_frames_min_media_input_hwarn_last_clear_time{lane_num}      = STR ; Errored frames minimum high warning last clear time for media input
    errored_frames_max_media_input_hwarn_last_clear_time{lane_num}      = STR ; Errored frames maximum high warning last clear time for media input
    errored_frames_avg_media_input_hwarn_last_clear_time{lane_num}      = STR ; Errored frames average high warning last clear time for media input
    errored_frames_curr_media_input_hwarn_last_clear_time{lane_num}     = STR ; Errored frames current high warning last clear time for media input
    errored_frames_min_host_input_hwarn_last_clear_time{lane_num}       = STR ; Errored frames minimum high warning last clear time for host input
    errored_frames_max_host_input_hwarn_last_clear_time{lane_num}       = STR ; Errored frames maximum high warning last clear time for host input
    errored_frames_avg_host_input_hwarn_last_clear_time{lane_num}       = STR ; Errored frames average high warning last clear time for host input
    errored_frames_curr_host_input_hwarn_last_clear_time{lane_num}      = STR ; Errored frames current high warning last clear time for host input

    ;C-CMIS specific fields
    biasxi_hwarn_last_clear_time                                        = STR ; modulator bias xi in percentage (high warning last clear time)
    biasxq_hwarn_last_clear_time                                        = STR ; modulator bias xq in percentage (high warning last clear time)
    biasxp_hwarn_last_clear_time                                        = STR ; modulator bias xp in percentage (high warning last clear time)
    biasyi_hwarn_last_clear_time                                        = STR ; modulator bias yi in percentage (high warning last clear time)
    biasyq_hwarn_last_clear_time                                        = STR ; modulator bias yq in percentage (high warning last clear time)
    biasyp_hwarn_last_clear_time                                        = STR ; modulator bias yq in percentage (high warning last clear time)
    cdshort_hwarn_last_clear_time                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (high warning last clear time)
    cdlong_hwarn_last_clear_time                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (high warning last clear time)
    dgd_hwarn_last_clear_time                                           = STR ; differential group delay in ps (high warning last clear time)
    sopmd_hwarn_last_clear_time                                         = STR ; second order polarization mode dispersion in ps^2 (high warning last clear time)
    soproc_hwarn_last_clear_time                                        = STR ; state of polarization rate of change in krad/s (high warning last clear time)
    pdl_hwarn_last_clear_time                                           = STR ; polarization dependent loss in db (high warning last clear time)
    osnr_hwarn_last_clear_time                                          = STR ; optical signal to noise ratio in db (high warning last clear time)
    esnr_hwarn_last_clear_time                                          = STR ; electrical signal to noise ratio in db (high warning last clear time)
    cfo_hwarn_last_clear_time                                           = STR ; carrier frequency offset in Hz (high warning last clear time)
    txcurrpower_hwarn_last_clear_time                                   = STR ; tx current output power in dbm (high warning last clear time)
    rxtotpower_hwarn_last_clear_time                                    = STR ; rx total power in  dbm (high warning last clear time)
    rxsigpower_hwarn_last_clear_time                                    = STR; rx signal power in dbm (high warning last clear time)
```

##### 2.2.6.4 Transceiver VDM low warning flag time clear data

The `TRANSCEIVER_VDM_LWARN_CLEAR_TIME` table stores the flag time clear for the VDM low warning flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ;Defines Transceiver VDM low warning last clear time for a port
    key                          = TRANSCEIVER_VDM_LWARN_CLEAR_TIME|ifname
    ; field                      = value
    laser_temperature_media_lwarn_last_clear_time{lane_num}             = STR ; laser temperature low warning last clear time for media input
    esnr_media_input_lwarn_last_clear_time{lane_num}                    = STR ; eSNR low warning last clear time for media input
    esnr_host_input_lwarn_last_clear_time{lane_num}                     = STR ; eSNR low warning last clear time for host input
    pam4_level_transition_media_input_lwarn_last_clear_time{lane_num}   = STR ; PAM4 level transition low warning last clear time for media input
    pam4_level_transition_host_input_lwarn_last_clear_time{lane_num}    = STR ; PAM4 level transition low warning last clear time for host input
    prefec_ber_min_media_input_lwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER minimum low warning last clear time for media input
    prefec_ber_max_media_input_lwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER maximum low warning last clear time for media input
    prefec_ber_avg_media_input_lwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER average low warning last clear time for media input
    prefec_ber_curr_media_input_lwarn_last_clear_time{lane_num}         = STR ; Pre-FEC BER current low warning last clear time for media input
    prefec_ber_min_host_input_lwarn_last_clear_time{lane_num}           = STR ; Pre-FEC BER minimum low warning last clear time for host input
    prefec_ber_max_host_input_lwarn_last_clear_time{lane_num}           = STR ; Pre-FEC BER maximum low warning last clear time for host input
    prefec_ber_avg_host_input_lwarn_last_clear_time{lane_num}           = STR ; Pre-FEC BER average low warning last clear time for host input
    prefec_ber_curr_host_input_lwarn_last_clear_time{lane_num}          = STR ; Pre-FEC BER current low warning last clear time for host input
    errored_frames_min_media_input_lwarn_last_clear_time{lane_num}      = STR ; Errored frames minimum low warning last clear time for media input
    errored_frames_max_media_input_lwarn_last_clear_time{lane_num}      = STR ; Errored frames maximum low warning last clear time for media input
    errored_frames_avg_media_input_lwarn_last_clear_time{lane_num}      = STR ; Errored frames average low warning last clear time for media input
    errored_frames_curr_media_input_lwarn_last_clear_time{lane_num}     = STR ; Errored frames current low warning last clear time for media input
    errored_frames_min_host_input_lwarn_last_clear_time{lane_num}       = STR ; Errored frames minimum low warning last clear time for host input
    errored_frames_max_host_input_lwarn_last_clear_time{lane_num}       = STR ; Errored frames maximum low warning last clear time for host input
    errored_frames_avg_host_input_lwarn_last_clear_time{lane_num}       = STR ; Errored frames average low warning last clear time for host input
    errored_frames_curr_host_input_lwarn_last_clear_time{lane_num}      = STR ; Errored frames current low warning last clear time for host input

    ;C-CMIS specific fields
    biasxi_lwarn_last_clear_time                                        = STR ; modulator bias xi in percentage (low warning last clear time)
    biasxq_lwarn_last_clear_time                                        = STR ; modulator bias xq in percentage (low warning last clear time)
    biasxp_lwarn_last_clear_time                                        = STR ; modulator bias xp in percentage (low warning last clear time)
    biasyi_lwarn_last_clear_time                                        = STR ; modulator bias yi in percentage (low warning last clear time)
    biasyq_lwarn_last_clear_time                                        = STR ; modulator bias yq in percentage (low warning last clear time)
    biasyp_lwarn_last_clear_time                                        = STR ; modulator bias yq in percentage (low warning last clear time)
    cdshort_lwarn_last_clear_time                                       = STR ; chromatic dispersion, low granularity, short link in ps/nm (low warning last clear time)
    cdlong_lwarn_last_clear_time                                        = STR ; chromatic dispersion, low granularity, long link in ps/nm (low warning last clear time)
    dgd_lwarn_last_clear_time                                           = STR ; differential group delay in ps (low warning last clear time)
    sopmd_lwarn_last_clear_time                                         = STR ; second order polarization mode dispersion in ps^2 (low warning last clear time)
    soproc_lwarn_last_clear_time                                        = STR ; state of polarization rate of change in krad/s (low warning last clear time)
    pdl_lwarn_last_clear_time                                           = STR ; polarization dependent loss in db (low warning last clear time)
    osnr_lwarn_last_clear_time                                          = STR ; optical signal to noise ratio in db (low warning last clear time)
    esnr_lwarn_last_clear_time                                          = STR ; electrical signal to noise ratio in db (low warning last clear time)
    cfo_lwarn_last_clear_time                                           = STR ; carrier frequency offset in Hz (low warning last clear time)
    txcurrpower_lwarn_last_clear_time                                   = STR ; tx current output power in dbm (low warning last clear time)
    rxtotpower_lwarn_last_clear_time                                    = STR ; rx total power in  dbm (low warning last clear time)
    rxsigpower_lwarn_last_clear_time                                    = STR; rx signal power in dbm (low warning last clear time)
```

### 2.3 Transceiver status data

#### 2.3.1 Transceiver status data to store module and data path status

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
    DP{lane_num}State                       = 1*255VCHAR        ; data path state indicator on host lane {lane_num}
    txoutput_status{lane_num}               = BOOLEAN           ; tx output status on media lane {lane_num}
    rxoutput_status_hostlane{lane_num}      = BOOLEAN           ; rx output status on host lane {lane_num}
    tx{lane_num}disable                     = BOOLEAN           ; TX disable state on media lane {lane_num}
    tx_disabled_channel                     = INTEGER           ; TX disable field
    dpdeinit_hostlane{lane_num}             = BOOLEAN           ; data path deinitialized status on host lane {lane_num}
    config_state_hostlane{lane_num}         = 1*255VCHAR        ; configuration status for the data path of host line {lane_num}
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
    datapath_firmware_fault                 = BOOLEAN           ; datapath (DSP) firmware fault
    module_firmware_fault                   = BOOLEAN           ; module firmware fault
    module_state_changed                    = BOOLEAN           ; module state changed
    txfault{lane_num}                       = BOOLEAN            ; tx fault flag on media lane {lane_num}
    txlos_hostlane{lane_num}                = BOOLEAN            ; tx loss of signal flag on host lane {lane_num}
    txcdrlol_hostlane{lane_num}             = BOOLEAN            ; tx clock and data recovery loss of lock flag on host lane {lane_num}
    tx_eq_fault{lane_num}                   = BOOLEAN            ; tx equalization fault flag on host lane {lane_num}
    rxlos{lane_num}                         = BOOLEAN            ; rx loss of signal flag on media lane {lane_num}
    rxcdrlol{lane_num}                      = BOOLEAN            ; rx clock and data recovery loss of lock flag on media lane {lane_num}
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
    datapath_firmware_fault_chg_cnt           = INTEGER           ; datapath (DSP) firmware fault change count
    module_firmware_fault_chg_cnt             = INTEGER           ; module firmware fault change count
    module_state_changed_chg_cnt              = INTEGER           ; module state changed change count
    txfault{lane_num}_chg_cnt                 = INTEGER           ; tx fault flag on media lane {lane_num} change count
    txlos_hostlane{lane_num}_chg_cnt          = INTEGER           ; tx loss of signal flag on host lane {lane_num} change count
    txcdrlol_hostlane{lane_num}_chg_cnt       = INTEGER           ; tx clock and data recovery loss of lock flag on host lane {lane_num} change count
    tx_eq_fault{lane_num}_chg_cnt             = INTEGER           ; tx equalization fault flag on host lane {lane_num} change count
    rxlos{lane_num}_chg_cnt                   = INTEGER           ; rx loss of signal flag on media lane {lane_num} change count
    rxcdrlol{lane_num}_chg_cnt                = INTEGER           ; rx clock and data recovery loss of lock flag on media lane {lane_num} change count
    target_output_power_oor_chg_cnt           = INTEGER           ; target output power out of range flag change count
    fine_tuning_oor_chg_cnt                   = INTEGER           ; fine tuning  out of range flag change count
    tuning_not_accepted_chg_cnt               = INTEGER           ; tuning not accepted flag change count
    invalid_channel_num_chg_cnt               = INTEGER           ; invalid channel number flag change count
    tuning_complete_chg_cnt                   = INTEGER           ; tuning complete flag change count
```

#### 2.3.4 Transceiver status data to store module and data path flag set time

The `TRANSCEIVER_STATUS_FLAG_SET_TIME` table stores the set time for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                        = TRANSCEIVER_STATUS_FLAG_SET_TIME|ifname        ; Flag information for module on port
    ; field                                    = value
    datapath_firmware_fault_last_set_time      = STR           ; datapath (DSP) firmware fault set time
    module_firmware_fault_last_set_time        = STR           ; module firmware fault set time
    module_state_changed_last_set_time         = STR           ; module state changed set time
    txfault{lane_num}_last_set_time            = STR           ; tx fault flag on media lane {lane_num} set time
    txlos_hostlane{lane_num}_last_set_time     = STR           ; tx loss of signal flag on host lane {lane_num} set time
    txcdrlol_hostlane{lane_num}_last_set_time  = STR           ; tx clock and data recovery loss of lock flag on host lane {lane_num} set time
    tx_eq_fault{lane_num}_last_set_time        = STR           ; tx equalization fault flag on host lane {lane_num} set time
    rxlos{lane_num}_last_set_time              = STR           ; rx loss of signal flag on media lane {lane_num} set time
    rxcdrlol{lane_num}_last_set_time           = STR           ; rx clock and data recovery loss of lock flag on media lane {lane_num} set time
    target_output_power_oor_last_set_time      = STR           ; target output power out of range flag set time
    fine_tuning_oor_last_set_time              = STR           ; fine tuning  out of range flag set time
    tuning_not_accepted_last_set_time          = STR           ; tuning not accepted flag set time
    invalid_channel_num_last_set_time          = STR           ; invalid channel number flag set time
    tuning_complete_last_set_time              = STR           ; tuning complete flag set time
```

#### 2.3.5 Transceiver status data to store module and data path flag clear time

The `TRANSCEIVER_STATUS_FLAG_CLEAR_TIME` table stores the clear time for the transceiver flag.

lane_num: Represents lane number of the field. The lane number is an integer value that ranges from 1 to 8.

```plaintext
    ; Defines Transceiver Status info for a port
    key                                        = TRANSCEIVER_STATUS_FLAG_CLEAR_TIME|ifname        ; Flag information for module on port
    ; field                                    = value
    datapath_firmware_fault_last_clear_time           = STR           ; datapath (DSP) firmware fault clear time
    module_firmware_fault_last_clear_time             = STR           ; module firmware fault clear time
    module_state_changed_last_clear_time              = STR           ; module state changed clear time
    txfault{lane_num}_last_clear_time                 = STR           ; tx fault flag on media lane {lane_num} clear time
    txlos_hostlane{lane_num}_last_clear_time          = STR           ; tx loss of signal flag on host lane {lane_num} clear time
    txcdrlol_hostlane{lane_num}_last_clear_time       = STR           ; tx clock and data recovery loss of lock flag on host lane {lane_num} clear time
    tx_eq_fault{lane_num}_last_clear_time             = STR           ; tx equalization fault flag on host lane {lane_num} clear time
    rxlos{lane_num}_last_clear_time                   = STR           ; rx loss of signal flag on media lane {lane_num} clear time
    rxcdrlol{lane_num}_last_clear_time                = STR           ; rx clock and data recovery loss of lock flag on media lane {lane_num} clear time
    target_output_power_last_oor_clear_time           = STR           ; target output power out of range flag clear time
    fine_tuning_oor_last_clear_time                   = STR           ; fine tuning  out of range flag clear time
    tuning_not_accepted_last_clear_time               = STR           ; tuning not accepted flag clear time
    invalid_channel_num_last_clear_time               = STR           ; invalid channel number flag clear time
    tuning_complete_last_clear_time                   = STR           ; tuning complete flag clear time
```

### 2.4 Transceiver PM data

The `TRANSCEIVER_PM` table stores the performance monitoring data of the transceiver. This table is exists only for C-CMIS transceivers.

```plaintext
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
Current System Time: Day Mon DD HH:MM:SS YYYY
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Parameter_Name   Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  ---------------  ---------------  ---------------  ---------------

Example:
admin@sonic#show interfaces transceiver dom flag Ethernet1
Current System Time: Wed Oct 16 03:46:41 2024
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Parameter_Name   Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  -------------------------  -------------------------  -------------------------  -------------------------
Ethernet1    Temperature      True/                      False/                     False/                     False/
                              1/                         0/                         0/                         0/
                              Wed Oct 16 03:46:41 2024/  Never                      Never                      Never
                              Never                      Wed Oct 16 03:46:41 2024   Wed Oct 16 03:46:41 2024   Wed Oct 16 03:46:41 2024
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
Current System Time: Day Mon DD HH:MM:SS YYYY
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Parameter_Name   Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  ---------------  ---------------  ---------------  ---------------

Example:
admin@sonic#show interfaces transceiver vdm flag Ethernet1
Current System Time: Wed Oct 16 03:46:41 2024
                              High Alarm                 High Warning               Low Warning                Low Alarm
                              Flag/                      Flag/                      Flag/                      Flag/
                              Change Count/              Change Count/              Change Count/              Change Count/
                              Last Set Time/             Last Set Time/             Last Set Time/             Last Set Time/
Port         Parameter_Name   Last Clear Time            Last Clear Time            Last Clear Time            Last Clear Time
-----------  ---------------  -------------------------  -------------------------  -------------------------  -------------------------
Ethernet1    eSNR Media Input True/                      False/                     False/                     False/
                              1/                         0/                         0/                         0/
                              Wed Oct 16 03:46:41 2024/  Never                      Never                      Never
                              Never                      Wed Oct 16 03:46:41 2024   Wed Oct 16 03:46:41 2024   Wed Oct 16 03:46:41 2024
```

## 4. SONiC CMIS diagnostic monitoring workflow

### 4.1 Static Diagnostic Information

The `SfpStateUpdateTask` thread is responsible for updating the static diagnostic information for all the transceivers in the system. The static diagnostic information, such as threshold values for DOM, VDM and PM, are read from the transceiver and updated in the `redis-db` during `xcvrd` boot-up and during transceiver removal and insertion.

The following tables are updated by the `SfpStateUpdateTask` thread:

1. `TRANSCEIVER_DOM_THRESHOLD`
2. `TRANSCEIVER_VDM_THRESHOLD`

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
    6. Analyze the transceiver DOM flag data by comparing the current flag data with the previous flag data and update the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables.
    7. Read the transceiver status data from the module and update the `TRANSCEIVER_STATUS` table.
    8. If the transceiver supports VDM monitoring, perform the following steps:
        1. Freeze the statistics by calling the CMIS API (`freeze_vdm_stats`) and wait for `FreezeDone` by calling `get_vdm_freeze_status`. Once the statistics are frozen, record the timestamp and copy the supported VDM and PM data from the transceiver.
        2. Unfreeze the statistics by calling the CMIS API (`unfreeze_vdm_stats`).
        3. Update the `TRANSCEIVER_VDM_CURRENT_SAMPLE` and `TRANSCEIVER_PM` tables with both basic and statistic instance's data read for VDM and PM.
        4. Analyze the VDM flags by comparing the current data with the previous data and update the VDM flag, change count and time related tables.

#### 4.2.2 Diagnostic Information Update During Link Down Event

When a link down event is detected by the `DomInfoUpdateTask` thread, a specific subset of the diagnostic information fields are updated in the `redis-db`. This is done to ensure that the diagnostic information is up-to-date and accurate during a link down event since the periodic update through the `DomInfoUpdateTask` thread can take more than 60 seconds to update the diagnostic information.

The following tables are updated during a link down event:

##### 4.2.2.1 DOM Related Fields

The flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link down event:

- `temperature`
- `voltage`
- `tx{lane_num}power`
- `rx{lane_num}power`
- `tx{lane_num}bias`
- `laser_temperature`

Example

The following fields related to `temperature` are updated in the `redis-db` during a link down event:

- `temphighalarm_flag`
- `temphighwarning_flag`
- `templowwarning_flag`
- `templowalarm_flag`
- `temphighalarm_chg_cnt`
- `temphighwarning_chg_cnt`
- `templowwarning_chg_cnt`
- `templowalarm_chg_cnt`
- `temphighalarm_last_set_time`
- `temphighwarning_last_set_time`
- `templowwarning_last_set_time`
- `templowalarm_last_set_time`
- `temphighalarm_last_clear_time`
- `temphighwarning_last_clear_time`
- `templowwarning_last_clear_time`
- `templowalarm_last_clear_time`

##### 4.2.2.2 VDM Related Fields

The flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link down event:

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

The following fields related to `esnr_media_input` are updated in the `redis-db` during a link down event:

- `esnr_media_input_halarm_flag{lane_num}`
- `esnr_media_input_lalarm_flag{lane_num}`
- `esnr_media_input_hwarn_flag{lane_num}`
- `esnr_media_input_lwarn_flag{lane_num}`
- `esnr_media_input_halarm_chg_cnt{lane_num}`
- `esnr_media_input_lalarm_chg_cnt{lane_num}`
- `esnr_media_input_hwarn_chg_cnt{lane_num}`
- `esnr_media_input_lwarn_chg_cnt{lane_num}`
- `esnr_media_input_halarm_last_set_time{lane_num}`
- `esnr_media_input_lalarm_last_set_time{lane_num}`
- `esnr_media_input_hwarn_last_set_time{lane_num}`
- `esnr_media_input_lwarn_last_set_time{lane_num}`
- `esnr_media_input_halarm_last_clear_time{lane_num}`
- `esnr_media_input_lalarm_last_clear_time{lane_num}`
- `esnr_media_input_hwarn_last_clear_time{lane_num}`
- `esnr_media_input_lwarn_last_clear_time{lane_num}`

##### 4.2.2.3 Transceiver Status Related Fields

The following fields of the `TRANSCEIVER_STATUS` table are updated in the `redis-db` during a link down event:

- `tx_disabled_channel`
- `module_state`
- `module_fault_cause`
- `DP{lane_num}State`
- `txoutput_status{lane_num}`
- `rxoutput_status_hostlane{lane_num}`
- `config_state_hostlane{lane_num}`
- `dpdeinit_hostlane{lane_num}`

The flags, change count, and their set/clear time for the following fields are updated in the `redis-db` during a link down event:

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

The following fields related to `datapath_firmware_fault` are updated in the `redis-db` during a link down event:

- `datapath_firmware_fault`
- `datapath_firmware_fault_chg_cnt`
- `datapath_firmware_fault_last_set_time`
- `datapath_firmware_fault_last_clear_time`

#### 4.2.3 Details of Flag Analysis of Tables

**Note**: For simplicity, this section uses DOM as an example. However, the same analysis is applicable for VDM as well.

**Purpose of Flag Analysis:**

The purpose of flag analysis is to track the status of various parameters and to count the number of times each DOM flag has changed. It also records the timestamp when each DOM flag was set and cleared.

**Tables Used for Flag Analysis:**

- `TRANSCEIVER_DOM_FLAG`: This table stores flags indicating the status of various DOM parameters.
- `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`: This table keeps a count of how many times each DOM flag has changed. Upon initialization, the count is set to 0.
- `TRANSCEIVER_DOM_FLAG_SET_TIME`: This table records the timestamp (in local timezone) when each DOM flag was set. The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`. During initialization, the timestamp is set to `Never` if the flag is not set.
- `TRANSCEIVER_DOM_FLAG_CLEAR_TIME`: This table records the timestamp (in local timezone) when each DOM flag was cleared. The timestamp is recorded in the format `Day Mon DD HH:MM:SS YYYY`. During initialization, the timestamp is set to `Never` if the flag is set.

**Example of Table Updates:**

- **TRANSCEIVER_DOM_FLAG_CHANGE_COUNT:**
  - Each time a flag in the `TRANSCEIVER_DOM_FLAG` table changes (either set or cleared), the corresponding count in this table is incremented.
- **TRANSCEIVER_DOM_FLAG_SET_TIME:**
  - When a flag is set in the `TRANSCEIVER_DOM_FLAG` table, the current timestamp (based on local timezone) is recorded in this table.
- **TRANSCEIVER_DOM_FLAG_CLEAR_TIME:**
  - When a flag is cleared in the `TRANSCEIVER_DOM_FLAG` table, the current timestamp (based on local timezone) is recorded in this table.

#### 4.2.4 Flag Change Count and Time Set/Clear Behavior During `xcvrd` Restart

During `xcvrd` stop, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are deleted by the `xcvrd` process. When `xcvrd` is restarted, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are recreated and the flag change count and set/clear time are updated based on the current flag status (i.e. the value of these fields are not cached between `xcvrd` restarts).

#### 4.2.5 Flag Change Count and Time Set/Clear Behavior During Transceiver Removal and Insertion

When a transceiver is removed, `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are deleted by the `SfpStateUpdateTask` thread.

When the transceiver is inserted back, the `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT`, `TRANSCEIVER_DOM_FLAG_SET_TIME`, and `TRANSCEIVER_DOM_FLAG_CLEAR_TIME` tables are recreated through the periodic polling routine of `DomInfoUpdateTask` and the flag change count and set/clear time are updated based on the current flag status.
