## CMIS and C-CMIS support for ZR on SONiC

### 1. Overview
Common Management Interface Specification (CMIS) is defined for pluggables or on-board modules to communicate with the registers [CMIS v5.0](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf). With a clear difinition of these registers, modules can set the configurations or get the status, to achieve the basic level of monitor and control. 

CMIS is widely used on modules based on a Two-Wire-Interface (TWI), including QSFP-DD, OSFP, COBO and QSFP modules. However, new requirements emerge with the introduction of coherent optical modules, such as 400G ZR. 400G ZR is the first type of modules to require definitions on coherent optical specifications, a field CMIS does not touch on. The development of C(coherent)-CMIS aims to solve this issue [C-CMIS v1.1](https://www.oiforum.com/wp-content/uploads/OIF-C-CMIS-01.1.pdf). It is based on CMIS but incroporates more definitions on registers in the extended space, regarding the emerging demands on coherent optics specifications.

The scope of this work is to develop APIs for both CMIS and C-CMIS to support 400G ZR modules on SONiC.

#### 1.1 Diagram - from CLI, State_DB, Config_DB, xcvrd to module registers

The following diagram shows how the CLI interfaces with the module registers through config_DB and state_DB and xcvrd platform. 

```
               ---------------------------
              |           CLIs            |
               ---------------------------
               ||                       /\
               \/                       ||
          ---------                    --------
        | Config_DB |                | State_DB |
          ---------                    --------
            ||                              /\
            \/                              ||
 -------------------------       ---------------------------------
|lpmode|freq|TXPow|looback|     |xcvr_info|xcvr_dom|xcvr_status|PM|
 -------------------------       --------------------------------- 
            ||                              /\
            \/                              ||
       ---------------------------------------------
      |                   xcvrd                     |
       ---------------------------------------------
                    ||            /\
                    \/            ||
              ---------------------------
             |    High level functions   |
              ---------------------------
                    ||            /\
                    \/            ||
                 ---------------------
                | Encode        Decode |
                 ---------------------
                    ||            /\
                    \/            ||
                ------------------------
               | write_reg     read_reg |
                ------------------------               
                    ||            /\
                    \/            ||
                 ---------------------
                |   Module registers  |
                 ---------------------
```      

##### 1.1.1 Upon plug-in of a module 
When there is plug-in event of a module on a port, the xcvrd detects the presence state changes from "absent" to "present" on that port. xcvrd reacts to this event by pushing the config_DB on that port to the module. More specifically for ZR module, the low power mode (lpmode), the configured frequency, the configured TX power and the loopback mode are the four most important settings to decide whether the module will be turned up, and with what settings if the module is to be turned up. xcvrd also constantly polls the state of the module and update its memory. When a CLI show command queries the module state or other features, the state_DB will be updated with the information in xcvrd.

##### 1.1.2 Issuing a show CLI command
When a user issues a show CLI command, state_DB will read from xcvrd and update its fields with information from xcvrd.

##### 1.1.3 Issuing a config CLI command
When a user issues a config CLI command, config_DB will be updated, and send new settings to xcvrd. xcvrd will further push the settings into the module registers. 

### 2. State_DB, Config_DB, show/config transceiver CLI definitions:

#### 2.1 State_DB Schema ####

New Transceiver info table and transceiver DOM sensor table adapted to 400G-ZR modules.

##### 2.1.1 Transceiver info Table #####

    ; Defines Transceiver information for a port
    key                          = TRANSCEIVER_INFO|ifname          ; information for module on port
    ; field                      = value
    type                         = 1*255VCHAR                       ; module type full name(QSFP-DD, OSFP, etc)
    host_electrical_interface    = 1*255VCHAR                       ; host electrical interface ID
    media_interface_code         = 1*255VCHAR                       ; media interface code
    host_lane_count              = INTEGER                          ; host lane count
    media_lane_count             = INTEGER                          ; media lane count
    host_lane_assignment_option  = INTEGER                          ; permissible first host lane number for application
    media_lane_assignment_option = INTEGER                          ; permissible first media lane number for application
    active_apsel_hostlane1       = INTEGER                          ; active application selected code assigned to host lane 1
    active_apsel_hostlane2       = INTEGER                          ; active application selected code assigned to host lane 2
    active_apsel_hostlane3       = INTEGER                          ; active application selected code assigned to host lane 3
    active_apsel_hostlane4       = INTEGER                          ; active application selected code assigned to host lane 4
    active_apsel_hostlane5       = INTEGER                          ; active application selected code assigned to host lane 5
    active_apsel_hostlane6       = INTEGER                          ; active application selected code assigned to host lane 6
    active_apsel_hostlane7       = INTEGER                          ; active application selected code assigned to host lane 7
    active_apsel_hostlane8       = INTEGER                          ; active application selected code assigned to host lane 8
    media_interface_technology   = 1*255VCHAR                       ; media interface technology
    hardware_rev                 = 1*255VCHAR                       ; module hardware revision 
    serial                       = 1*255VCHAR                       ; module serial number 
    manufacturer                 = 1*255VCHAR                       ; module venndor name
    model                        = 1*255VCHAR                       ; module part number
    vendor_rev                   = 1*255VCHAR                       ; module vendor revision
    vendor_oui                   = 1*255VCHAR                       ; vendor organizationally unique identifier
    vendor_date                  = 1*255VCHAR                       ; module manufacture date
    connector                    = 1*255VCHAR                       ; connector type
    encoding                     = 1*255VCHAR                       ; N/A
    specification_compliance     = 1*255VCHAR                       ; module media type
    application_advertisement    = 1*255VCHAR                       ; N/A
    cmis_rev                     = 1*255VCHAR                       ; CMIS revision that the module complies to
    active_firmware              = 1*255VCHAR                       ; active firmware
    inactive_firmware            = 1*255VCHAR                       ; inactive firmware
    supported_max_tx_power       = FLOAT                            ; support maximum tx power
    supported_min_tx_power       = FLOAT                            ; support minimum tx power
    supported_max_laser_freq     = FLOAT                            ; support maximum laser frequency
    supported_min_laser_freq     = FLOAT                            ; support minimum laser frequency

##### 2.1.2 Transceiver DOM sensor Table #####

    ; Defines Transceiver DOM sensor information for a port
    key                          = TRANSCEIVER_DOM_SENSOR|ifname    ; information module DOM sensors on port
    ; field                      = value
    temperature                  = FLOAT                            ; temperature value in Celsius
    voltage                      = FLOAT                            ; voltage value in V
    tx1power                     = FLOAT                            ; tx 1 power in dBm
    tx2power                     = FLOAT                            ; tx 2 power in dBm
    tx3power                     = FLOAT                            ; tx 3 power in dBm
    tx4power                     = FLOAT                            ; tx 4 power in dBm
    tx5power                     = FLOAT                            ; tx 5 power in dBm
    tx6power                     = FLOAT                            ; tx 6 power in dBm
    tx7power                     = FLOAT                            ; tx 7 power in dBm
    tx8power                     = FLOAT                            ; tx 8 power in dBm
    rx1power                     = FLOAT                            ; rx 1 power in dBm
    rx2power                     = FLOAT                            ; rx 2 power in dBm
    rx3power                     = FLOAT                            ; rx 3 power in dBm
    rx4power                     = FLOAT                            ; rx 4 power in dBm
    rx5power                     = FLOAT                            ; rx 5 power in dBm
    rx6power                     = FLOAT                            ; rx 6 power in dBm
    rx7power                     = FLOAT                            ; rx 7 power in dBm
    rx8power                     = FLOAT                            ; rx 8 power in dBm
    tx1bias                      = FLOAT                            ; tx 1 bias in mA
    tx2bias                      = FLOAT                            ; tx 2 bias in mA
    tx3bias                      = FLOAT                            ; tx 3 bias in mA
    tx4bias                      = FLOAT                            ; tx 4 bias in mA
    tx5bias                      = FLOAT                            ; tx 5 bias in mA
    tx6bias                      = FLOAT                            ; tx 6 bias in mA
    tx7bias                      = FLOAT                            ; tx 7 bias in mA
    tx8bias                      = FLOAT                            ; tx 8 bias in mA
    laser_temperature	         = FLOAT                            ; laser temperature value in Celsius
    prefec_ber                   = FLOAT                            ; prefec ber
    postfec_ber                  = FLOAT                            ; postfec ber
    cd_shortlink                 = FLOAT                            ; chromatic dispersion, high granularity, short link in ps/nm
    cd_longlink                  = FLOAT                            ; chromatic dispersion, low granularity, long link in ps/nm
    dgd                          = FLOAT                            ; differential group delay in ps
    sopmd                        = FLOAT                            ; second order polarization mode dispersion in ps^2
    pdl                          = FLOAT                            ; polarization dependent loss in db
    osnr                         = FLOAT                            ; optical signal to noise ratio in db
    esnr                         = FLOAT                            ; electrical signal to noise ratio in db
    cfo                          = FLOAT                            ; carrier frequency offset in MHz
    soproc                       = FLOAT                            ; state of polarization rate of change in krad/s
    laser_config_freq            = FLOAT                            ; laser configured frequency in MHz
    laser_curr_freq              = FLOAT                            ; laser current frequency in MHz
    tx_config_power              = FLOAT                            ; configured tx output power in dbm
    tx_curr_power                = FLOAT                            ; tx current output power in dbm
    rx_tot_power                 = FLOAT                            ; rx total power in  dbm
    rx_sig_power                 = FLOAT                            ; rx signal power in dbm
    bias_xi                      = FLOAT                            ; modulator bias xi in percentage
    bias_xq                      = FLOAT                            ; modulator bias xq in percentage
    bias_xp                      = FLOAT                            ; modulator bias xp in percentage
    bias_yi                      = FLOAT                            ; modulator bias yi in percentage
    bias_yq                      = FLOAT                            ; modulator bias yq in percentage
    bias_yp                      = FLOAT                            ; modulator bias yp in percentage

##### 2.1.3 Transceiver DOM Threshold Table #####

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
    prefecberhighalarm           = FLOAT                            ; prefec ber high alarm threshold
    prefecberlowalarm            = FLOAT                            ; prefec ber low alarm threshold
    prefecberhighwarning         = FLOAT                            ; prefec ber high warning threshold
    prefecberlowwarning          = FLOAT                            ; prefec ber low warning threshold
    postfecberhighalarm          = FLOAT                            ; postfec ber high alarm threshold
    postfecberlowalarm           = FLOAT                            ; postfec ber low alarm threshold
    postfecberhighwarning        = FLOAT                            ; postfec ber high warning threshold
    postfecberlowwarning         = FLOAT                            ; postfec ber low warning threshold
    biasxihighalarm              = FLOAT                            ; bias xi high alarm threshold in percent
    biasxilowalarm               = FLOAT                            ; bias xi low alarm threshold in percent
    biasxihighwarning            = FLOAT                            ; bias xi high warning threshold in percent
    biasxilowwarning             = FLOAT                            ; bias xi low warning threshold in percent
    biasxqhighalarm              = FLOAT                            ; bias xq high alarm threshold in percent
    biasxqlowalarm               = FLOAT                            ; bias xq low alarm threshold in percent
    biasxqhighwarning            = FLOAT                            ; bias xq high warning threshold in percent
    biasxqlowwarning             = FLOAT                            ; bias xq low warning threshold in percent
    biasxphighalarm              = FLOAT                            ; bias xp high alarm threshold in percent
    biasxplowalarm               = FLOAT                            ; bias xp low alarm threshold in percent
    biasxphighwarning            = FLOAT                            ; bias xp high warning threshold in percent
    biasxplowwarning             = FLOAT                            ; bias xp low warning threshold in percent
    biasyihighalarm              = FLOAT                            ; bias yi high alarm threshold in percent
    biasyilowalarm               = FLOAT                            ; bias yi low alarm threshold in percent
    biasyihighwarning            = FLOAT                            ; bias yi high warning threshold in percent
    biasyilowwarning             = FLOAT                            ; bias yi low warning threshold in percent
    biasyqhighalarm              = FLOAT                            ; bias yq high alarm threshold in percent
    biasyqlowalarm               = FLOAT                            ; bias yq low alarm threshold in percent
    biasyqhighwarning            = FLOAT                            ; bias yq high warning threshold in percent
    biasyqlowwarning             = FLOAT                            ; bias yq low warning threshold in percent
    biasyphighalarm              = FLOAT                            ; bias yp high alarm threshold in percent
    biasyplowalarm               = FLOAT                            ; bias yp low alarm threshold in percent
    biasyphighwarning            = FLOAT                            ; bias yp high warning threshold in percent
    biasyplowwarning             = FLOAT                            ; bias yp low warning threshold in percent
    cdshorthighalarm             = FLOAT                            ; cd short high alarm threshold in ps/nm
    cdshortlowalarm              = FLOAT                            ; cd short low alarm threshold in ps/nm
    cdshorthighwarning           = FLOAT                            ; cd short high warning threshold in ps/nm
    cdshortlowwarning            = FLOAT                            ; cd short low warning threshold in ps/nm
    cdlonghighalarm              = FLOAT                            ; cd long high alarm threshold in ps/nm
    cdlonglowalarm               = FLOAT                            ; cd long low alarm threshold in ps/nm
    cdlonghighwarning            = FLOAT                            ; cd long high warning threshold in ps/nm
    cdlonglowwarning             = FLOAT                            ; cd long low warning threshold in ps/nm
    dgdhighalarm                 = FLOAT                            ; dgd high alarm threshold in ps
    dgdlowalarm                  = FLOAT                            ; dgd low alarm threshold in ps
    dgdhighwarning               = FLOAT                            ; dgd high warning threshold in ps
    dgdlowwarning                = FLOAT                            ; dgd low warning threshold in ps
    sopmdhighalarm               = FLOAT                            ; sopmd high alarm threshold in ps^2
    sopmdlowalarm                = FLOAT                            ; sopmd low alarm threshold in ps^2
    sopmdhighwarning             = FLOAT                            ; sopmd high warning threshold in ps^2
    sopmdlowwarning              = FLOAT                            ; sopmd low warning threshold in ps^2
    pdlhighalarm                 = FLOAT                            ; pdl high alarm threshold in db
    pdllowalarm                  = FLOAT                            ; pdl low alarm threshold in db
    pdlhighwarning               = FLOAT                            ; pdl high warning threshold in db
    pdllowwarning                = FLOAT                            ; pdl low warning threshold in db
    osnrhighalarm                = FLOAT                            ; osnr high alarm threshold in db
    osnrlowalarm                 = FLOAT                            ; osnr low alarm threshold in db
    osnrhighwarning              = FLOAT                            ; osnr high warning threshold in db
    osnrlowwarning               = FLOAT                            ; osnr low warning threshold in db
    esnrhighalarm                = FLOAT                            ; esnr high alarm threshold in db
    esnrlowalarm                 = FLOAT                            ; esnr low alarm threshold in db
    esnrhighwarning              = FLOAT                            ; esnr high warning threshold in db
    esnrlowwarning               = FLOAT                            ; esnr low warning threshold in db
    cfohighalarm                 = FLOAT                            ; cfo high alarm threshold in MHz
    cfolowalarm                  = FLOAT                            ; cfo low alarm threshold in MHz
    cfohighwarning               = FLOAT                            ; cfo high warning threshold in MHz
    cfolowwarning                = FLOAT                            ; cfo low warning threshold in MHz
    txcurrpowerhighalarm         = FLOAT                            ; txcurrpower high alarm threshold in dbm
    txcurrpowerlowalarm          = FLOAT                            ; txcurrpower low alarm threshold in dbm
    txcurrpowerhighwarning       = FLOAT                            ; txcurrpower high warning threshold in dbm
    txcurrpowerlowwarning        = FLOAT                            ; txcurrpower low warning threshold in dbm
    rxtotpowerhighalarm          = FLOAT                            ; rxtotpower high alarm threshold in dbm
    rxtotpowerlowalarm           = FLOAT                            ; rxtotpower low alarm threshold in dbm
    rxtotpowerhighwarning        = FLOAT                            ; rxtotpower high warning threshold in dbm
    rxtotpowerlowwarning         = FLOAT                            ; rxtotpower low warning threshold in dbm
    rxsigpowerhighalarm          = FLOAT                            ; rxsigpower high alarm threshold in dbm
    rxsigpowerlowalarm           = FLOAT                            ; rxsigpower low alarm threshold in dbm
    rxsigpowerhighwarning        = FLOAT                            ; rxsigpower high warning threshold in dbm
    rxsigpowerlowwarning         = FLOAT                            ; rxsigpower low warning threshold in dbm


##### 2.1.4 Transceiver Status Table #####

    ; Defines Transceiver Status info for a port
    key                          = TRANSCEIVER_STATUS|ifname        ; Error information for module on port
    ; field                      = value
    status                       = 1*255VCHAR                       ; code of the module status (plug in, plug out)
    error                        = 1*255VCHAR                       ; module error (N/A or a string consisting of error descriptions joined by "|", like "error1 | error2" )
    module_state                 = 1*255VCHAR                       ; current module state (ModuleLowPwr, ModulePwrUp, ModuleReady, ModulePwrDn, Fault)
    module_fault_cause           = 1*255VCHAR                       ; reason of entering the module fault state
    datapath_firmware_fault      = BOOLEAN                          ; datapath (DSP) firmware fault
    module_firmware_fault        = BOOLEAN                          ; module firmware fault
    module_state_changed         = BOOLEAN                          ; module state changed
    DP1State                     = 1*255VCHAR                       ; data path state indicator on host lane 1
    DP2State                     = 1*255VCHAR                       ; data path state indicator on host lane 2
    DP3State                     = 1*255VCHAR                       ; data path state indicator on host lane 3
    DP4State                     = 1*255VCHAR                       ; data path state indicator on host lane 4
    DP5State                     = 1*255VCHAR                       ; data path state indicator on host lane 5
    DP6State                     = 1*255VCHAR                       ; data path state indicator on host lane 6
    DP7State                     = 1*255VCHAR                       ; data path state indicator on host lane 7
    DP8State                     = 1*255VCHAR                       ; data path state indicator on host lane 8
    txoutput_status              = BOOLEAN                          ; tx output status on media lane
    rxoutput_status_hostlane1    = BOOLEAN                          ; rx output status on host lane 1
    rxoutput_status_hostlane2    = BOOLEAN                          ; rx output status on host lane 2
    rxoutput_status_hostlane3    = BOOLEAN                          ; rx output status on host lane 3
    rxoutput_status_hostlane4    = BOOLEAN                          ; rx output status on host lane 4
    rxoutput_status_hostlane5    = BOOLEAN                          ; rx output status on host lane 5
    rxoutput_status_hostlane6    = BOOLEAN                          ; rx output status on host lane 6
    rxoutput_status_hostlane7    = BOOLEAN                          ; rx output status on host lane 7
    rxoutput_status_hostlane8    = BOOLEAN                          ; rx output status on host lane 8
    tx_disable                   = BOOLEAN                          ; TX disable state
    tx_disabled_channel          = INTEGER                          ; TX disable field
    txfault                      = BOOLEAN                          ; tx fault flag on media lane
    txlos_hostlane1              = BOOLEAN                          ; tx loss of signal flag on host lane 1
    txlos_hostlane2              = BOOLEAN                          ; tx loss of signal flag on host lane 2
    txlos_hostlane3              = BOOLEAN                          ; tx loss of signal flag on host lane 3
    txlos_hostlane4              = BOOLEAN                          ; tx loss of signal flag on host lane 4
    txlos_hostlane5              = BOOLEAN                          ; tx loss of signal flag on host lane 5
    txlos_hostlane6              = BOOLEAN                          ; tx loss of signal flag on host lane 6
    txlos_hostlane7              = BOOLEAN                          ; tx loss of signal flag on host lane 7
    txlos_hostlane8              = BOOLEAN                          ; tx loss of signal flag on host lane 8
    txcdrlol_hostlane1           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 1
    txcdrlol_hostlane2           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 2
    txcdrlol_hostlane3           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 3
    txcdrlol_hostlane4           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 4
    txcdrlol_hostlane5           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 5
    txcdrlol_hostlane6           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 6
    txcdrlol_hostlane7           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 7
    txcdrlol_hostlane8           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 8
    rxlos                        = BOOLEAN                          ; rx loss of signal flag on media lane
    rxcdrlol                     = BOOLEAN                          ; rx clock and data recovery loss of lock on media lane
    config_state_hostlane1       = 1*255VCHAR                       ; configuration status for the data path of host line 1
    config_state_hostlane2       = 1*255VCHAR                       ; configuration status for the data path of host line 2
    config_state_hostlane3       = 1*255VCHAR                       ; configuration status for the data path of host line 3
    config_state_hostlane4       = 1*255VCHAR                       ; configuration status for the data path of host line 4
    config_state_hostlane5       = 1*255VCHAR                       ; configuration status for the data path of host line 5
    config_state_hostlane6       = 1*255VCHAR                       ; configuration status for the data path of host line 6
    config_state_hostlane7       = 1*255VCHAR                       ; configuration status for the data path of host line 7
    config_state_hostlane8       = 1*255VCHAR                       ; configuration status for the data path of host line 8
    dpinit_pending_hostlane1     = BOOLEAN                          ; data path configuration updated on host lane 1 
    dpinit_pending_hostlane2     = BOOLEAN                          ; data path configuration updated on host lane 2
    dpinit_pending_hostlane3     = BOOLEAN                          ; data path configuration updated on host lane 3
    dpinit_pending_hostlane4     = BOOLEAN                          ; data path configuration updated on host lane 4
    dpinit_pending_hostlane5     = BOOLEAN                          ; data path configuration updated on host lane 5
    dpinit_pending_hostlane6     = BOOLEAN                          ; data path configuration updated on host lane 6
    dpinit_pending_hostlane7     = BOOLEAN                          ; data path configuration updated on host lane 7
    dpinit_pending_hostlane8     = BOOLEAN                          ; data path configuration updated on host lane 8
    tuning_in_progress           = BOOLEAN                          ; tuning in progress status
    wavelength_unlock_status     = BOOLEAN                          ; laser unlocked status
    target_output_power_oor      = BOOLEAN                          ; target output power out of range flag
    fine_tuning_oor              = BOOLEAN                          ; fine tuning  out of range flag
    tuning_not_accepted          = BOOLEAN                          ; tuning not accepted flag
    invalid_channel_num          = BOOLEAN                          ; invalid channel number flag
    tuning_complete              = BOOLEAN                          ; tuning complete flag
    temphighalarm_flag           = BOOLEAN                          ; temperature high alarm flag 
    temphighwarning_flag         = BOOLEAN                          ; temperature high warning flag
    templowalarm_flag            = BOOLEAN                          ; temperature low alarm flag
    templowwarning_flag          = BOOLEAN                          ; temperature low warning flag
    vcchighalarm_flag            = BOOLEAN                          ; vcc high alarm flag
    vcchighwarning_flag          = BOOLEAN                          ; vcc high warning flag
    vcclowalarm_flag             = BOOLEAN                          ; vcc low alarm flag
    vcclowwarning_flag           = BOOLEAN                          ; vcc low warning flag
    txpowerhighalarm_flag        = BOOLEAN                          ; tx power high alarm flag
    txpowerlowalarm_flag         = BOOLEAN                          ; tx power low alarm flag
    txpowerhighwarning_flag      = BOOLEAN                          ; tx power high warning flag
    txpowerlowwarning_flag       = BOOLEAN                          ; tx power low alarm flag
    rxpowerhighalarm_flag        = BOOLEAN                          ; rx power high alarm flag
    rxpowerlowalarm_flag         = BOOLEAN                          ; rx power low alarm flag
    rxpowerhighwarning_flag      = BOOLEAN                          ; rx power high warning flag
    rxpowerlowwarning_flag       = BOOLEAN                          ; rx power low warning flag
    txbiashighalarm_flag         = BOOLEAN                          ; tx bias high alarm flag
    txbiaslowalarm_flag          = BOOLEAN                          ; tx bias low alarm flag
    txbiashighwarning_flag       = BOOLEAN                          ; tx bias high warning flag
    txbiaslowwarning_flag        = BOOLEAN                          ; tx bias low warning flag
    lasertemphighalarm_flag      = BOOLEAN                          ; laser temperature high alarm flag
    lasertemplowalarm_flag       = BOOLEAN                          ; laser temperature low alarm flag
    lasertemphighwarning_flag    = BOOLEAN                          ; laser temperature high warning flag
    lasertemplowwarning_flag     = BOOLEAN                          ; laser temperature low warning flag
    prefecberhighalarm_flag      = BOOLEAN                          ; prefec ber high alarm flag
    prefecberlowalarm_flag       = BOOLEAN                          ; prefec ber low alarm flag
    prefecberhighwarning_flag    = BOOLEAN                          ; prefec ber high warning flag
    prefecberlowwarning_flag     = BOOLEAN                          ; prefec ber low warning flag
    postfecberhighalarm_flag     = BOOLEAN                          ; postfec ber high alarm flag
    postfecberlowalarm_flag      = BOOLEAN                          ; postfec ber low alarm flag
    postfecberhighwarning_flag   = BOOLEAN                          ; postfec ber high warning flag
    postfecberlowwarning_flag    = BOOLEAN                          ; postfec ber low warning flag
    biasxihighalarm_flag         = BOOLEAN                          ; bias xi high alarm flag
    biasxilowalarm_flag          = BOOLEAN                          ; bias xi low alarm flag
    biasxihighwarning_flag       = BOOLEAN                          ; bias xi high warning flag
    biasxilowwarning_flag        = BOOLEAN                          ; bias xi low warning flag
    biasxqhighalarm_flag         = BOOLEAN                          ; bias xq high alarm flag
    biasxqlowalarm_flag          = BOOLEAN                          ; bias xq low alarm flag
    biasxqhighwarning_flag       = BOOLEAN                          ; bias xq high warning flag
    biasxqlowwarning_flag        = BOOLEAN                          ; bias xq low warning flag
    biasxphighalarm_flag         = BOOLEAN                          ; bias xp high alarm flag
    biasxplowalarm_flag          = BOOLEAN                          ; bias xp low alarm flag
    biasxphighwarning_flag       = BOOLEAN                          ; bias xp high warning flag
    biasxplowwarning_flag        = BOOLEAN                          ; bias xp low warning flag
    biasyihighalarm_flag         = BOOLEAN                          ; bias yi high alarm flag
    biasyilowalarm_flag          = BOOLEAN                          ; bias yi low alarm flag
    biasyihighwarning_flag       = BOOLEAN                          ; bias yi high warning flag
    biasyilowwarning_flag        = BOOLEAN                          ; bias yi low warning flag
    biasyqhighalarm_flag         = BOOLEAN                          ; bias yq high alarm flag
    biasyqlowalarm_flag          = BOOLEAN                          ; bias yq low alarm flag
    biasyqhighwarning_flag       = BOOLEAN                          ; bias yq high warning flag
    biasyqlowwarning_flag        = BOOLEAN                          ; bias yq low warning flag
    biasyphighalarm_flag         = BOOLEAN                          ; bias yp high alarm flag
    biasyplowalarm_flag          = BOOLEAN                          ; bias yp low alarm flag
    biasyphighwarning_flag       = BOOLEAN                          ; bias yp high warning flag
    biasyplowwarning_flag        = BOOLEAN                          ; bias yp low warning flag
    cdshorthighalarm_flag        = BOOLEAN                          ; cd short high alarm flag
    cdshortlowalarm_flag         = BOOLEAN                          ; cd short low alarm flag
    cdshorthighwarning_flag      = BOOLEAN                          ; cd short high warning flag
    cdshortlowwarning_flag       = BOOLEAN                          ; cd short low warning flag
    cdlonghighalarm_flag         = BOOLEAN                          ; cd long high alarm flag
    cdlonglowalarm_flag          = BOOLEAN                          ; cd long low alarm flag
    cdlonghighwarning_flag       = BOOLEAN                          ; cd long high warning flag
    cdlonglowwarning_flag        = BOOLEAN                          ; cd long low warning flag
    dgdhighalarm_flag            = BOOLEAN                          ; dgd high alarm flag
    dgdlowalarm_flag             = BOOLEAN                          ; dgd low alarm flag
    dgdhighwarning_flag          = BOOLEAN                          ; dgd high warning flag
    dgdlowwarning_flag           = BOOLEAN                          ; dgd low warning flag
    sopmdhighalarm_flag          = BOOLEAN                          ; sopmd high alarm flag
    sopmdlowalarm_flag           = BOOLEAN                          ; sopmd low alarm flag
    sopmdhighwarning_flag        = BOOLEAN                          ; sopmd high warning flag
    sopmdlowwarning_flag         = BOOLEAN                          ; sopmd low warning flag
    pdlhighalarm_flag            = BOOLEAN                          ; pdl high alarm flag
    pdllowalarm_flag             = BOOLEAN                          ; pdl low alarm flag
    pdlhighwarning_flag          = BOOLEAN                          ; pdl high warning flag
    pdllowwarning_flag           = BOOLEAN                          ; pdl low warning flag
    osnrhighalarm_flag           = BOOLEAN                          ; osnr high alarm flag
    osnrlowalarm_flag            = BOOLEAN                          ; osnr low alarm flag
    osnrhighwarning_flag         = BOOLEAN                          ; osnr high warning flag
    osnrlowwarning_flag          = BOOLEAN                          ; osnr low warning flag
    esnrhighalarm_flag           = BOOLEAN                          ; esnr high alarm flag
    esnrlowalarm_flag            = BOOLEAN                          ; esnr low alarm flag
    esnrhighwarning_flag         = BOOLEAN                          ; esnr high warning flag
    esnrlowwarning_flag          = BOOLEAN                          ; esnr low warning flag
    cfohighalarm_flag            = BOOLEAN                          ; cfo high alarm flag
    cfolowalarm_flag             = BOOLEAN                          ; cfo low alarm flag
    cfohighwarning_flag          = BOOLEAN                          ; cfo high warning flag
    cfolowwarning_flag           = BOOLEAN                          ; cfo low warning flag
    txcurrpowerhighalarm_flag    = BOOLEAN                          ; txcurrpower high alarm flag
    txcurrpowerlowalarm_flag     = BOOLEAN                          ; txcurrpower low alarm flag
    txcurrpowerhighwarning_flag  = BOOLEAN                          ; txcurrpower high warning flag
    txcurrpowerlowwarning_flag   = BOOLEAN                          ; txcurrpower low warning flag
    rxtotpowerhighalarm_flag     = BOOLEAN                          ; rxtotpower high alarm flag
    rxtotpowerlowalarm_flag      = BOOLEAN                          ; rxtotpower low alarm flag
    rxtotpowerhighwarning_flag   = BOOLEAN                          ; rxtotpower high warning flag
    rxtotpowerlowwarning_flag    = BOOLEAN                          ; rxtotpower low warning flag
    rxsigpowerhighalarm_flag     = BOOLEAN                          ; rxsigpower high alarm flag
    rxsigpowerlowalarm_flag      = BOOLEAN                          ; rxsigpower low alarm flag
    rxsigpowerhighwarning_flag   = BOOLEAN                          ; rxsigpower high warning flag
    rxsigpowerlowwarning_flag    = BOOLEAN                          ; rxsigpower low warning flag
    
##### 2.1.5 Transceiver PM Table #####

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

##### 2.1.6 Transceiver Loopback Table #####

    ; Defines Transceiver loopback information for a port
    key                                         = TRANSCEIVER_LOOPBACK|ifname      ; information of loopback on port
    ; field                                     = value 
    simultaneous_host_media_loopback_supported  = BOOLEAN                          ; simultaneous host and media loopback support
    per_lane_media_loopback_supported           = BOOLEAN                          ; per lane media loopback support
    per_lane_host_loopback_supported            = BOOLEAN                          ; per lane host loopback support
    host_side_input_loopback_supported          = BOOLEAN                          ; host input loopback support
    host_side_output_loopback_supported         = BOOLEAN                          ; host output loopback support
    media_side_input_loopback_supported         = BOOLEAN                          ; media input loopback support
    media_side_output_loopback_supported        = BOOLEAN                          ; media output loopback support
    media_output_loopback                       = BOOLEAN                          ; media side output loopback enable
    media_input_loopback                        = BOOLEAN                          ; media side input loopback enable
    host_output_loopback_lane1                  = BOOLEAN                          ; host side output loopback enable lane1
    host_output_loopback_lane2                  = BOOLEAN                          ; host side output loopback enable lane2
    host_output_loopback_lane3                  = BOOLEAN                          ; host side output loopback enable lane3
    host_output_loopback_lane4                  = BOOLEAN                          ; host side output loopback enable lane4
    host_output_loopback_lane5                  = BOOLEAN                          ; host side output loopback enable lane5
    host_output_loopback_lane6                  = BOOLEAN                          ; host side output loopback enable lane6
    host_output_loopback_lane7                  = BOOLEAN                          ; host side output loopback enable lane7
    host_output_loopback_lane8                  = BOOLEAN                          ; host side output loopback enable lane8
    host_input_loopback_lane1                   = BOOLEAN                          ; host side input loopback enable lane1
    host_input_loopback_lane2                   = BOOLEAN                          ; host side input loopback enable lane2
    host_input_loopback_lane3                   = BOOLEAN                          ; host side input loopback enable lane3
    host_input_loopback_lane4                   = BOOLEAN                          ; host side input loopback enable lane4
    host_input_loopback_lane5                   = BOOLEAN                          ; host side input loopback enable lane5
    host_input_loopback_lane6                   = BOOLEAN                          ; host side input loopback enable lane6
    host_input_loopback_lane7                   = BOOLEAN                          ; host side input loopback enable lane7
    host_input_loopback_lane8                   = BOOLEAN                          ; host side input loopback enable lane8


#### 2.2 Show interfaces transceiver CLI
Displays diagnostic monitoring information of the transceivers

**show interfaces transceiver**

This command displays information for all the interfaces for the transceiver requested or a specific interface if the optional "interface_name" is specified.

- Usage:
  ```
  show interfaces transceiver (eeprom [-d|--dom] | presence | error-status | status | pm | loopback) [<interface_name>]
  ```

- Example (Decode and display module and dom information of the transceiver connected to Ethernet0):
  ```
  admin@sonic:~$ show interfaces transceive eeprom --dom Ethernet0
  Ethernet0: SFP EEPROM detected
          Application Advertisement: {1: {'host_electrical_interface_id': '400GAUI-8 C2M (Annex 120E)', 'module_media_interface_id': '400ZR, DWDM, amplified', 'media_lane_count': 1, 'host_lane_count': 8, 'host_lane_assignment_options': 1}, 2: {'host_electrical_interface_id': '400GAUI-8 C2M (Annex 120E)', 'module_media_interface_id': '400ZR, Single Wavelength, Unamplified', 'media_lane_count': 1, 'host_lane_count': 8, 'host_lane_assignment_options': 1}, 3: {'host_electrical_interface_id': '100GAUI-2 C2M (Annex 135G)', 'module_media_interface_id': '400ZR, DWDM, amplified', 'media_lane_count': 1, 'host_lane_count': 2, 'host_lane_assignment_options': 85}}
          Connector: LC
          Encoding: N/A
          Extended Identifier: Power Class 8 (20.0W Max)
          Extended RateSelect Compliance: N/A
          Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
          Length Cable Assembly(m): 0.0
          Nominal Bit Rate(100Mbs): 0
          Specification compliance: sm_media_interface
          Vendor Date Code(YYYY-MM-DD Lot): 2020-01-01
          Vendor Name: XXXX
          Vendor OUI: xx-xx-xx
          Vendor PN: XXX
          Vendor Rev: XXX
          Vendor SN: 0123456789
          ChannelMonitorValues:
                  RX1Power: -infdBm
                  RX2Power: -infdBm
                  RX3Power: -infdBm
                  RX4Power: -infdBm
                  RX5Power: -infdBm
                  RX6Power: -infdBm
                  RX7Power: -infdBm
                  RX8Power: -infdBm
                  TX1Bias: 0.0mA
                  TX1Power: -10.0dBm
                  TX2Bias: 0.0mA
                  TX2Power: -infdBm
                  TX3Bias: 0.0mA
                  TX3Power: -infdBm
                  TX4Bias: 0.0mA
                  TX4Power: -infdBm
                  TX5Bias: 0.0mA
                  TX5Power: -infdBm
                  TX6Bias: 0.0mA
                  TX6Power: -infdBm
                  TX7Bias: 0.0mA
                  TX7Power: -infdBm
                  TX8Bias: 0.0mA
                  TX8Power: -infdBm
          ChannelThresholdValues:
                  RxPowerHighAlarm  : 2.0dBm
                  RxPowerHighWarning: 0.0dBm
                  RxPowerLowAlarm   : -20.01dBm
                  RxPowerLowWarning : -20.0dBm
                  TxBiasHighAlarm   : 0.0mA
                  TxBiasHighWarning : 0.0mA
                  TxBiasLowAlarm    : 0.0mA
                  TxBiasLowWarning  : 0.0mA
                  TxPowerHighAlarm  : 0.0dBm
                  TxPowerHighWarning: -2.0dBm
                  TxPowerLowAlarm   : -18.013dBm
                  TxPowerLowWarning : -16.003dBm
          ModuleMonitorValues:
                  Temperature: 57.0C
                  Vcc: 3.329Volts
          ModuleThresholdValues:
                  TempHighAlarm  : 80.0C
                  TempHighWarning: 75.0C
                  TempLowAlarm   : -5.0C
                  TempLowWarning : 15.0C
                  VccHighAlarm   : 3.465Volts
                  VccHighWarning : 3.432Volts
                  VccLowAlarm    : 3.135Volts
                  VccLowWarning  : 3.168Volts
  ```

- Example (Display presence of SFP transceiver connected to Ethernet0):
  ```
  admin@sonic:~$ show interfaces transceiver presence Ethernet0
  Port       Presence
  ---------  ----------
  Ethernet0  Present
  ```

- Example (Decode and display error-status of the transceiver connected to Ethernet0):
  ```
  admin@sonic:~$ show interfaces transceiver error-status Ethernet0
  Port       Error Status
  ---------  --------------
  Ethernet0  OK
  ```

- Example (Display status of transceiver connected to Ethernet0):
  ```
  admin@sonic:~$ show interfaces transceiver status Ethernet0
  Ethernet0:
  Module State : Ready
  Module Fault Cause : No Fault detected
  Datapath Firmware Fault : False
  Module Firmware Fault : False
  Module State Changed : False
  Datapath Host Lane 1: Activated
  Datapath Host Lane 2: Activated
  Datapath Host Lane 3: Activated
  Datapath Host Lane 4: Activated
  Datapath Host Lane 5: Activated
  Datapath Host Lane 6: Activated
  Datapath Host Lane 7: Activated
  Datapath Host Lane 8: Activated
  Tx Output Status : Valid
  Rx Output Status : Valid  
  Tx Fault : False
  Tx Los : False
  Tx Cdr Lol: False
  Rx Los : False
  Rx Cdr Lol : False
  Configuration State Host Lane 1: Config Success
  Configuration State Host Lane 2: Config Success
  Configuration State Host Lane 3: Config Success
  Configuration State Host Lane 4: Config Success
  Configuration State Host Lane 5: Config Success
  Configuration State Host Lane 6: Config Success
  Configuration State Host Lane 7: Config Success
  Configuration State Host Lane 8: Config Success
  Datapath Init Pending Host Lane 1: False
  Datapath Init Pending Host Lane 2: False
  Datapath Init Pending Host Lane 3: False
  Datapath Init Pending Host Lane 4: False
  Datapath Init Pending Host Lane 5: False
  Datapath Init Pending Host Lane 6: False
  Datapath Init Pending Host Lane 7: False
  Datapath Init Pending Host Lane 8: False
  Tuning In Progress: False
  Wavelegnth Unlock Status : False
  Target Output Power Out Of Range : False
  Fine Tuning Out Of Range : False
  Tuning Not Accepted : False
  Invalid Channel Number : False
  Tuning Complete : True
  Temperature High Alarm : False
  Temperature High Warning : False
  Temperature Low Alarm : False
  Temperature Low Warning : False
  Vcc High Alarm : False
  Vcc High Warning : False
  Vcc Low Alarm : False
  Vcc Low Warning : False
  Tx Power High Alarm : False
  Tx Power High Warning : False
  Tx Power Low Alarm : False
  Tx Power Low Warning : False
  Rx Power High Alarm : False
  Rx Power High Warning : False
  Rx Power Low Alarm : False
  Rx Power Low Warning : False  
  Tx Bias High Alarm : False
  Tx Bias High Warning : False
  Tx Bias Low Alarm : False
  Tx Bias Low Warning : False  
  Laser Temperature High Alarm : False
  Laser Temperature High Warning : False
  Laser Temperature Low Alarm : False
  Laser Temperature Low Warning : False
  ```
- Example (Display pm status of transceiver connected to Ethernet0):
  ```
  admin@sonic:~$ show interfaces transceiver pm Ethernet0
  Ethernet0:
  prefec_ber_avg : 1.00E-3
  prefec_ber_min : 1.00E-3
  prefec_ber_max : 1.00E-3
  uncorr_frames_avg : 0.00E0
  uncorr_frames_min : 0.00E0
  uncorr_frames_max : 0.00E0
  cd_avg : 0 ps/ns
  cd_min : 0 ps/ns
  cd_max : 0 ps/ns
  dgd_avg : 1.0 ps
  dgd_min : 1.0 ps
  dgd_max : 1.0 ps
  sopmd_avg : 1 ps^2
  sopmd_min : 1 ps^2
  sopmd_max : 1 ps^2
  pdl_avg  : 1.0 dB
  pdl_min  : 1.0 dB
  pdl_max  : 1.0 dB
  osnr_avg : 28.0 dB
  osnr_min : 28.0 dB
  osnr_max : 28.0 dB
  esnr_avg : 15.0 dB
  esnr_min : 15.0 dB
  esnr_max : 15.0 dB
  cfo_avg  : 500 MHz
  cfo_min  : 500 MHz
  cfo_max  : 500 MHz
  soproc_avg : 1 krad/s
  soproc_min : 1 krad/s
  soproc_max : 1 krad/s
  tx_power_avg : -10.00 dBm
  tx_power_min : -10.00 dBm
  tx_power_max : -10.00 dBm
  rx_tot_power_avg : -8.00 dBm
  rx_tot_power_min : -8.00 dBm
  rx_tot_power_max : -8.00 dBm
  rx_sig_power_avg : -8.00 dBm
  rx_sig_power_min : -8.00 dBm
  rx_sig_power_max : -8.00 dBm
  ```

- Example (Display loopback status of transceiver connected to Ethernet0):
  ```
  admin@sonic:~$ show interfaces transceiver loopback Ethernet0
  Ethernet0:
  Media Output Loopback : False
  Media Input Loopback : False
  Host Output Loopback : False
  Host Input Loopback : False
  ```

- **show interfaces transceiver dom**

    Expected output for "show interfaces transceiver dom \<port\>" CLI.

    Please note that in the below o/p, the line starting with "Section" will not be printed with CLI o/p. It is currently present just for information purpose only.

    **Laser config frequency, Laser current frequency and Tx config power** will show value as N/A for non C_CMIS transveivers and threshold values
    ```
                                  Live          High Alarm  High Warn   Low Warn    Low Alarm
    Sensor Type                   Measurement   Threshold   Threshold   Threshold   Threshold
    -------                       ------------  ----------  ----------  ----------  ----------
    Section 1 - Common fields for all types (CCMIS, CMIS, SFF8636 (QSFP28), SFF8436 (QSFP+), SFF8472 (QSFP+))
    Laser config frequency [GHz]
    Laser current frequency [GHz]
    Tx config power [dBm]
    Case Temperature [C]
    Voltage [V]
    Tx Bias [mA]                  [Val1, .. Valn]
    Tx Power [dBm]                [Val1, .. Valn]
    Rx Power [dBm]                [Val1, .. Valn]

    Section 2 - Fields specific for CMIS + CCMIS
    Laser Temperatue [C]
    Post-FEC BER
    Pre-FEC BER

    Section 3 - Fields specific for CCMIS
    Bias X/I [%]
    Bias X_Phase [%]
    Bias X/Q [%]
    Bias Y/I [%]
    Bias Y_Phase [%]
    Bias Y/Q [%]
    SOP ROC [krad/s]
    CD – Long Link [Ps/nm]
    CD – Short Link [Ps/nm]
    CFO [MHz]
    DGD [Ps]
    eSNR [dB]
    OSNR [dB]
    PDL [dB]
    Rx signal power[dBm]
    Rx total power[dBm]
    SOPMD [Ps^2]
    ```

#### 2.3 Config_DB Schema ####
##### 2.3.1 Transceiver Config Table #####
Stores information for physical switch ports managed by the switch chip. Ports to the CPU (ie: management port) and logical ports (loopback) are not declared in the PORT_TABLE. See INTF_TABLE.

    ;Defines layer 2 ports
    ;In SONiC, Data is loaded from configuration file by portsyncd
    key                 = PORT_TABLE:ifname     ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
    admin_status        = "down" / "up"         ; admin status
    oper_status         = "down" / "up"         ; oper status
    lanes               = list of lanes         ; (need format spec???)
    mac                 = 12HEXDIG              ;
    alias               = 1*64VCHAR             ; alias name of the port used by LLDP and SNMP, must be unique
    description         = 1*64VCHAR             ; port description
    speed               = 1*6DIGIT              ; port line speed in Mbps
    mtu                 = 1*4DIGIT              ; port MTU
    fec                 = 1*64VCHAR             ; port fec mode
    lpmode              = "enable" / "disable"  ; port low power mode
    configured_freq     = 1*9DIGIT              ; configured frequency
    configured_TX_power = FLOAT                 ; configured TX output power 
    loopback            = "media output" / "media input" / "host output" / "host input" / "none" ; loopback mode
    
    
#### 2.4 Configure interface transceiver CLI ####
configure privisioning settings of the transceivers

- Usage:
    ```
    config interface transceiver (lpmode | frequency | tx_power | loopback) [<interface_name>]
    ```

- Example (bring module up from low power mode, or bring down module to low power mode):
    ```
    admin@sonic:~# config interface transceiver lpmode Ethernet0 enable
    Enabling low-power mode for port Ethernet0 ... OK

    admin@sonic:~# config interface transceiver lpmode Ethernet0 disable
    Disabling low-power mode for port Ethernet0 ... OK
    ```

- Example (config the privisioning frequency):
    ```
    admin@sonic:~# config interface transceiver frequency Ethernet0 196025
    Setting laser frequency to 196025 GHz on port Ethernet0
    ```

- Example (config the privisioning TX power):
The "--" is needed here because the provisioned value is negative.
    ```
    admin@sonic:~# config interface transceiver tx_power Ethernet0 -- -10.0
    Setting target Tx output power to -10.0 dBm on port Ethernet0
    ```

- Example (config the loopback mode):
    ```
    admin@sonic:~$ config interface transceiver loopback Ethernet0 none
    Setting loopback mode to none
    ```
    
#### 2.5 Module firmware CLI ####

- Usage:
    ```
    show interfaces transceiver (firmware version) [<interface_name>]
    configure interfaces transceiver (firmware download <bin_file> | firmware commit | firmware run | firmware upgrade <bin_file> | firmware switch) [<interface_name>]
    ```

- Example (show module firmware version):
    ```
    admin@sonic:~$ show interfaces transceiver firmware version Ethernet0 
    Ethernet0:
    Get module FW info
    Image A Version: xxx.xxx.xxx
    Image B Version: xxx.xxx.xxx
    Running Image: A; Committed Image: A
    Get module FW info time: 0.15 s
    ```
    
- Example (configure module firmware download):
    ```
    admin@sonic:~$ configure interfaces transceiver firmware download qsfp_dd_ver_xx_xx_xx.bin Ethernet0
    Start FW downloading
    Start module FW download: Success
    Start module FW download time: 0.10 s
    Total size: 1234567 start bytes: 67 remaining: 1234500
    Module FW download complete: Success
    Complete module FW download time: 500.00 s
    ```
    
- Example (configure module firmware run):
    ```
    admin@sonic:~$ configure interfaces transceiver firmware run Ethernet0
    Module FW run: Success
    Module FW run time: 2.00 s
    ```
    
- Example (configure module firmware commit):
    ```
    admin@sonic:~$ configure interfaces transceiver firmware commit Ethernet0
    Module FW commit: Success
    Module FW commit time: 2.00 s
    ```

- Example (configure module firmware upgrade, which combines the show FW version, configure download, show download status, configure commit and run and show version in the end):
    ```
    admin@sonic:~$ configure interfaces transceiver firmware upgrade qsfp_dd_ver_xx_xx_xx.bin Ethernet0
    Ethernet0:
    Start FW downloading
    Start module FW download: Success
    Start module FW download time: 0.10 s
    Total size: 1234567 start bytes: 67 remaining: 1234500
    Module FW download complete: Success
    Complete module FW download time: 500.00 s
    
    Module FW run: Success
    Module FW run time: 2.00 s
    
    Module FW commit: Success
    Module FW commit time: 2.00 s
  
    Before switch Image A: xxx.xxx.xxx; Run: 1 Commit: 1, Valid: 0
    Before switch Image B: xxx.xxx.xxx; Run: 0 Commit: 0, Valid: 0
    Image A: xxx.xxx.xxx; Run: 0 Commit: 0, Valid: 0
    Image B: xxx.xxx.xxx; Run: 1 Commit: 1, Valid: 0
    ```

- Example (configure module firmware switch):
    ```
    admin@sonic:~$ configure interfaces transceiver firmware switch Ethernet0
    Module FW run: Success
    Module FW run time: 2.00 s
    
    Module FW commit: Success
    Module FW commit time: 2.00 s
  
    Before switch Image A: xxx.xxx.xxx; Run: 1 Commit: 1, Valid: 0
    Before switch Image B: xxx.xxx.xxx; Run: 0 Commit: 0, Valid: 0
    Image A: xxx.xxx.xxx; Run: 0 Commit: 0, Valid: 0
    Image B: xxx.xxx.xxx; Run: 1 Commit: 1, Valid: 0
    ```

### 3. High level functions

#### 3.1 Get module basic information
- get_module_type

```
def get_module_type(port):
    module_type = read_reg_from_dict(port, Page00h_Lower.SFF8024_IDENTIFIER)
    # 400ZR specific: 18h, QSFP-DD
    return Data_Type_Dict.MODULE_TYPE_DICT[module_type]
```

- get_module_status

```
def get_module_status(port):
    # Bit 3-1:      Module state. 
    # 000b          -
    # 001b          ModuleLowPwr
    # 010b          ModulePwrUp
    # 011b          ModuleReady This is the only state reported by flat memory modules
    # 100b          ModulePwrDn
    # 101b          Fault
    # 110b          -
    # 111b          -
    # Bit 0: Interrupt status. Status of Interrupt output (inverted logic hardware signal)
    # 0b: Interrupt asserted
    # 1b: Interrupt not asserted (default)
    module_status_raw = read_reg_from_dict(port, Page00h_Lower.MODULE_STATE)
    module_status = (module_status_raw>>1) & 0x7
    return Data_Type_Dict.MODULE_STATUS_DICT[module_status]
```

- get_module_vendor

```
def get_module_vendor(port):
    module_vendor = read_reg_from_dict(port, Page00h_Upper.VENDOR_NAME)
    return module_vendor
```
- get_module_part_number

```
def get_module_part_number(port):
    module_part_number = read_reg_from_dict(port, Page00h_Upper.VENDOR_PN)
    return module_part_number
```
- get_module_serial_number

```
def get_module_serial_nubmer(port):
    module_serial_number = read_reg_from_dict(port, Page00h_Upper.VENDOR_SN)
    return module_serial_number
```
- get_datapath_lane_status

```
def get_datapath_lane_status(port):
    LANE_NUMBER = 8
    datapath_lane_status = [0] * LANE_NUMBER
    # Bit 7-4: DataPathStateHostLane2 Data Path State Indicator, as observed on host lane 2
    # Bit 3-0: DataPathStateHostLane1 Data Path State Indicator, as observed on host lane 1
    # Bit 7-4: DataPathStateHostLane4 Data Path State Indicator, as observed on host lane 4
    # Bit 3-0: DataPathStateHostLane3 Data Path State Indicator, as observed on host lane 3
    # Bit 7-4: DataPathStateHostLane6 Data Path State Indicator, as observed on host lane 6
    # Bit 3-0: DataPathStateHostLane5 Data Path State Indicator, as observed on host lane 5
    # Bit 7-4: DataPathStateHostLane8 Data Path State Indicator, as observed on host lane 8
    # Bit 3-0: DataPathStateHostLane7 Data Path State Indicator, as observed on host lane 7
    datapath_state_1 = read_reg_from_dict(port, Page11h.DATA_PATH_STATE_HOST_1)
    datapath_state_2 = read_reg_from_dict(port, Page11h.DATA_PATH_STATE_HOST_2)
    datapath_state_3 = read_reg_from_dict(port, Page11h.DATA_PATH_STATE_HOST_3)
    datapath_state_4 = read_reg_from_dict(port, Page11h.DATA_PATH_STATE_HOST_4)
    # Data path state
    # Encoding      State
    # 0h            Reserved
    # 1h            DataPathDeactivated
    # 2h            DataPathInit
    # 3h            DataPathDeinit
    # 4h            DataPathActivated
    # 5h            DataPathTxTurnOn
    # 6h            DataPathTxTurnOff
    # 7h            DataPathInitialized
    # 8h-Fh         Reserved
    datapath_lane_status[0] = datapath_state_1 & 0xF
    datapath_lane_status[1] = (datapath_state_1>>4) & 0xF
    datapath_lane_status[2] = datapath_state_2 & 0xF
    datapath_lane_status[3] = (datapath_state_2>>4) & 0xF
    datapath_lane_status[4] = datapath_state_3 & 0xF
    datapath_lane_status[5] = (datapath_state_3>>4) & 0xF
    datapath_lane_status[6] = datapath_state_4 & 0xF
    datapath_lane_status[7] = (datapath_state_4>>4) & 0xF
    return Data_Type_Dict.DATA_PATH_STATUS_DICT[datapath_lane_status[0]]
```
- get_module_case_temp

```
def get_module_case_temp(port):
    # Scaled with 1/256 degree Celsius increments. Unit in deg C
    MODULE_CASE_TEMP_SCALE = 1.0/256
    module_case_temp = read_reg_from_dict(port, Page00h_Lower.MODULE_CASE_TEMP) * MODULE_CASE_TEMP_SCALE
    return module_case_temp
```
- get_supply_3v3

```
def get_supply_3v3(port):
    # Scaled with 100 uV increments. Unit converted to Volt
    SUPPLY_3V3_SCALE = 0.0001
    supply_3v3 = read_reg_from_dict(port, Page00h_Lower.SUPPLY_3V3) * SUPPLY_3V3_SCALE
    return supply_3v3
```
- get_laser_temp

```
def get_laser_temp(port):
    aux_monitor_ad = read_reg_from_dict(port, Page01h.MODULE_CHARACTERISTICS_MISC_1)
    # Bit 1: Aux2MonitorType
    # 0b: Aux 2 monitor monitors Laser Temperature
    # 1b: Aux 2 monitor monitors TEC current    
    Aux2MonitorType = (aux_monitor_ad>>1) & 0x1
    # Bit 2: Aux3MonitorType
    # 0b: Aux 3 monitor monitors Laser Temperature
    # 1b: Aux 3 monitor monitors Vcc2
    Aux3MonitorType = (aux_monitor_ad>>2) & 0x1
    # laser temp scaled with 1/256 degree Celsius increments. Unit in deg C
    # laser temp from Aux3
    LASER_TEMP_SCALE = 1.0/256
    if Aux2MonitorType and not Aux3MonitorType: 
        laser_temp = read_reg_from_dict(port, Page00h_Lower.AUX3MONITOR) * LASER_TEMP_SCALE
    # laser temp from Aux2
    elif not Aux2MonitorType and Aux3MonitorType: 
        laser_temp = read_reg_from_dict(port, Page00h_Lower.AUX2MONITOR) * LASER_TEMP_SCALE
    # laser temp monitor not supported
    else:
        laser_temp = None
    return laser_temp
```
- get_tuning_status

```
def get_tuning_status(port):
    tuning_status = read_reg_from_dict(port, Page12h.TX_TUNING_STATUS_LANE_1) & 0x3
    return Data_Type_Dict.LASER_TUNING_STATUS_DICT[tuning_status]
```
- get_laser_freq

```
def get_laser_freq(port):
    # Unit in MHz
    laser_freq = read_reg_from_dict(port, Page12h.TX_CURRENT_LASER_FREQUENCY_LANE_1)
    return laser_freq
```
- get_TX_configured_power

```
def get_TX_configured_power(port):
    # configured TX power value
    # Scaled with 0.01 dBm. Unit in dBm
    TX_POWER_SCALE = 0.01
    tx_configured_power = read_reg_from_dict(port, Page12h.TX_TARGET_OUTPUT_POWER_LANE_1) * TX_POWER_SCALE
```

#### 3.2 Get VDM related information

The table below specifies the threshold for important optics and DSP performance metrics:


|PM|	Min|	Max|
|--|--|--|
|PreFEC BER|0|	1.25E-2|
|PostFEC BER|	|0|
|Tx Power (dBm)|		| | 
|Rx Power (dBm)|		| | 
|OSNR (dB/0.1nm)|26| |
|SNR (dB)|13.6| |
|CD (ps/nm)|	0|	2400|
|Frequency Offset (GHz)|-3.6|3.6|
|peak DGD (ps)|	0|	28|
|peak PDL (dB)|	0| 3.5|
|SOP (krad/s)|	0|	50|
|Case Temperature ($^{o}$C)	|	|75 |
|Laser Temperature ($^{o}$C)|	|75 |
| EVM| | |



- get_VDM

```get_VDM_page``` function uses ```VDM_TYPE``` dictionary above. It parses all the VDM items defined in the dictionary within a certain VDM page and returns both VDM monitor values and four threshold values related to this VDM item. ```get_VDM``` function combines VDM items from all VDM pages.
```
PAGE_SIZE = 128
PAGE_OFFSET = 128
THRSH_SPACING = 8
VDM_SIZE = 2

def get_F16(value):
    scale_exponent = (value >> 11) & 0x1f
    mantissa = value & 0x7ff
    result = mantissa*10**(scale_exponent-24)
    return result

def get_VDM_page(port, page):
    if page not in [0x20, 0x21, 0x22, 0x23]:
        raise ValueError('Page not in VDM Descriptor range!')
    VDM_descriptor = struct.unpack(f'{PAGE_SIZE}B', read_reg(port, page, PAGE_OFFSET, PAGE_SIZE))
    # Odd Adress VDM observable type ID, real-time monitored value in Page + 4
    VDM_typeID = VDM_descriptor[1::2]
    # Even Address
    # Bit 7-4: Threshold set ID in Page + 8, in group of 8 bytes, 16 sets/page
    # Bit 3-0: n. Monitored lane n+1 
    VDM_lane = [(elem & 0xf) for elem in VDM_descriptor[0::2]]
    VDM_thresholdID = [(elem>>4) for elem in VDM_descriptor[0::2]]
    VDM_valuePage = page+4
    VDM_thrshPage = page+8
    VDM_Page_data = {}
    for index, typeID in enumerate(VDM_typeID):
        if typeID not in Data_Type_Dict.VDM_TYPE:
            continue
        else:
            vdm_info_dict = Data_Type_Dict.VDM_TYPE[typeID]
            scale = vdm_info_dict[2]
            thrshID = VDM_thresholdID[index]
            vdm_value_raw = read_reg(port, VDM_valuePage, PAGE_OFFSET+VDM_SIZE*index, VDM_SIZE)
            vdm_thrsh_high_alarm_raw = read_reg(port, VDM_thrshPage, PAGE_OFFSET + THRSH_SPACING * thrshID, VDM_SIZE)
            vdm_thrsh_low_alarm_raw = read_reg(port, VDM_thrshPage, PAGE_OFFSET + THRSH_SPACING * thrshID + 2, VDM_SIZE)
            vdm_thrsh_high_warn_raw = read_reg(port, VDM_thrshPage, PAGE_OFFSET + THRSH_SPACING * thrshID + 4, VDM_SIZE)
            vdm_thrsh_low_warn_raw = read_reg(port, VDM_thrshPage, PAGE_OFFSET + THRSH_SPACING * thrshID + 6, VDM_SIZE)
            if vdm_info_dict[1] == 'S16':
                vdm_value = struct.unpack('>h',vdm_value_raw)[0] * scale
                vdm_thrsh_high_alarm = struct.unpack('>h', vdm_thrsh_high_alarm_raw)[0] * scale
                vdm_thrsh_low_alarm = struct.unpack('>h', vdm_thrsh_low_alarm_raw)[0] * scale
                vdm_thrsh_high_warn = struct.unpack('>h', vdm_thrsh_high_warn_raw)[0] * scale
                vdm_thrsh_low_warn = struct.unpack('>h', vdm_thrsh_low_warn_raw)[0] * scale
            elif vdm_info_dict[1] == 'U16':
                vdm_value = struct.unpack('>H',vdm_value_raw)[0] * scale
                vdm_thrsh_high_alarm = struct.unpack('>H', vdm_thrsh_high_alarm_raw)[0] * scale
                vdm_thrsh_low_alarm = struct.unpack('>H', vdm_thrsh_low_alarm_raw)[0] * scale
                vdm_thrsh_high_warn = struct.unpack('>H', vdm_thrsh_high_warn_raw)[0] * scale
                vdm_thrsh_low_warn = struct.unpack('>H', vdm_thrsh_low_warn_raw)[0] * scale
            elif vdm_info_dict[1] == 'F16':
                vdm_value_int = struct.unpack('>H',vdm_value_raw)[0]
                vdm_value = get_F16(vdm_value_int)
                vdm_thrsh_high_alarm_int = struct.unpack('>H', vdm_thrsh_high_alarm_raw)[0]
                vdm_thrsh_low_alarm_int = struct.unpack('>H', vdm_thrsh_low_alarm_raw)[0]
                vdm_thrsh_high_warn_int = struct.unpack('>H', vdm_thrsh_high_warn_raw)[0]
                vdm_thrsh_low_warn_int = struct.unpack('>H', vdm_thrsh_low_warn_raw)[0]
                vdm_thrsh_high_alarm = get_F16(vdm_thrsh_high_alarm_int)
                vdm_thrsh_low_alarm = get_F16(vdm_thrsh_low_alarm_int)
                vdm_thrsh_high_warn = get_F16(vdm_thrsh_high_warn_int)
                vdm_thrsh_low_warn = get_F16(vdm_thrsh_low_warn_int)
            else:
                continue

        if vdm_info_dict[0] not in VDM_Page_data:
            VDM_Page_data[vdm_info_dict[0]] = {VDM_lane[index]+1: [vdm_value,
                                                                   vdm_thrsh_high_alarm,
                                                                   vdm_thrsh_low_alarm,
                                                                   vdm_thrsh_high_warn,
                                                                   vdm_thrsh_low_warn]}
        else:
            VDM_Page_data[vdm_info_dict[0]][VDM_lane[index]+1] = [vdm_value,
                                                                  vdm_thrsh_high_alarm,
                                                                  vdm_thrsh_low_alarm,
                                                                  vdm_thrsh_high_warn,
                                                                  vdm_thrsh_low_warn]
    return VDM_Page_data

def get_VDM(port):
    vdm_page_supported_raw = read_reg_from_dict(port, Page2Fh.VDM_SUPPORT) & 0x3
    vdm_page_supported = Data_Type_Dict.VDM_SUPPORTED_PAGE[vdm_page_supported_raw]
    VDM = {}
    # Bit 7, freeze all PMs for reporting
    write_reg_from_dict(port, Page2Fh.FREEZE_REQUEST, 128)
    time.sleep(1)
    for page in vdm_page_supported:
        VDM_current_page = get_VDM_page(port, page)
        VDM.update(VDM_current_page)
    write_reg_from_dict(port, Page2Fh.FREEZE_REQUEST, 0)
    return VDM
```
#### 3.3 Get C-CMIS PM
- get_PM
Sample code to read C-CMIS defined PMs:
```
def get_PM(port):

    write_reg_from_dict(port, Page2Fh.FREEZE_REQUEST, 128)
    time.sleep(1)

    PM_dict = {}
    rx_bits_pm = read_reg_from_dict(port, Page34h.RX_BITS_PM)
    rx_bits_subint_pm = read_reg_from_dict(port, Page34h.RX_BITS_SUB_INTERVAL_PM)
    rx_corr_bits_pm = read_reg_from_dict(port, Page34h.RX_CORR_BITS_PM)
    rx_min_corr_bits_subint_pm = read_reg_from_dict(port, Page34h.RX_MIN_CORR_BITS_SUB_INTERVAL_PM)
    rx_max_corr_bits_subint_pm = read_reg_from_dict(port, Page34h.RX_MAX_CORR_BITS_SUB_INTERVAL_PM)

    if (rx_bits_subint_pm != 0) and (rx_bits_pm != 0):
        PM_dict['preFEC_BER_cur'] = rx_corr_bits_pm*1.0/rx_bits_pm
        PM_dict['preFEC_BER_min'] = rx_min_corr_bits_subint_pm*1.0/rx_bits_subint_pm
        PM_dict['preFEC_BER_max'] = rx_max_corr_bits_subint_pm*1.0/rx_bits_subint_pm

    rx_frames_pm = read_reg_from_dict(port, Page34h.RX_FRAMES_PM)
    rx_frames_subint_pm = read_reg_from_dict(port, Page34h.RX_FRAMES_SUB_INTERVAL_PM)
    rx_frames_uncorr_err_pm = read_reg_from_dict(port, Page34h.RX_FRAMES_UNCORR_ERR_PM)
    rx_min_frames_uncorr_err_subint_pm = read_reg_from_dict(port, Page34h.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM)
    rx_max_frames_uncorr_err_subint_pm = read_reg_from_dict(port, Page34h.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM)

    if (rx_frames_subint_pm != 0) and (rx_frames_pm != 0):
        PM_dict['preFEC_uncorr_frame_ratio_cur'] = rx_frames_uncorr_err_pm*1.0/rx_frames_subint_pm
        PM_dict['preFEC_uncorr_frame_ratio_min'] = rx_min_frames_uncorr_err_subint_pm*1.0/rx_frames_subint_pm
        PM_dict['preFEC_uncorr_frame_ratio_max'] = rx_max_frames_uncorr_err_subint_pm*1.0/rx_frames_subint_pm


    PM_dict['rx_cd_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_CD_PM)
    PM_dict['rx_cd_min'] = read_reg_from_dict(port, Page35h.RX_MIN_CD_PM)
    PM_dict['rx_cd_max'] = read_reg_from_dict(port, Page35h.RX_MAX_CD_PM)

    PM_dict['rx_dgd_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_DGD_PM)*Data_Type_Dict.PM_SCALE['RX_DGD_SCALE_PS']
    PM_dict['rx_dgd_min'] = read_reg_from_dict(port, Page35h.RX_MIN_DGD_PM)*Data_Type_Dict.PM_SCALE['RX_DGD_SCALE_PS']
    PM_dict['rx_dgd_max'] = read_reg_from_dict(port, Page35h.RX_MAX_DGD_PM)*Data_Type_Dict.PM_SCALE['RX_DGD_SCALE_PS']

    PM_dict['rx_sopmd_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_SOPMD_PM)*Data_Type_Dict.PM_SCALE['RX_SOPMD_SCALE_PS2']
    PM_dict['rx_sopmd_min'] = read_reg_from_dict(port, Page35h.RX_MIN_SOPMD_PM)*Data_Type_Dict.PM_SCALE['RX_SOPMD_SCALE_PS2']
    PM_dict['rx_sopmd_max'] = read_reg_from_dict(port, Page35h.RX_MAX_SOPMD_PM)*Data_Type_Dict.PM_SCALE['RX_SOPMD_SCALE_PS2']

    PM_dict['rx_pdl_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_PDL_PM)*Data_Type_Dict.PM_SCALE['RX_PDL_SCALE_DB']
    PM_dict['rx_pdl_min'] = read_reg_from_dict(port, Page35h.RX_MIN_PDL_PM)*Data_Type_Dict.PM_SCALE['RX_PDL_SCALE_DB']
    PM_dict['rx_pdl_max'] = read_reg_from_dict(port, Page35h.RX_MAX_PDL_PM)*Data_Type_Dict.PM_SCALE['RX_PDL_SCALE_DB']

    PM_dict['rx_osnr_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_OSNR_PM)*Data_Type_Dict.PM_SCALE['OSNR_SCALE_DB']
    PM_dict['rx_osnr_min'] = read_reg_from_dict(port, Page35h.RX_MIN_OSNR_PM)*Data_Type_Dict.PM_SCALE['OSNR_SCALE_DB']
    PM_dict['rx_osnr_max'] = read_reg_from_dict(port, Page35h.RX_MAX_OSNR_PM)*Data_Type_Dict.PM_SCALE['OSNR_SCALE_DB']

    PM_dict['rx_esnr_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_ESNR_PM)*Data_Type_Dict.PM_SCALE['ESNR_SCALE_DB']
    PM_dict['rx_esnr_min'] = read_reg_from_dict(port, Page35h.RX_MIN_ESNR_PM)*Data_Type_Dict.PM_SCALE['ESNR_SCALE_DB']
    PM_dict['rx_esnr_max'] = read_reg_from_dict(port, Page35h.RX_MAX_ESNR_PM)*Data_Type_Dict.PM_SCALE['ESNR_SCALE_DB']

    PM_dict['rx_cfo_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_CFO_PM)
    PM_dict['rx_cfo_min'] = read_reg_from_dict(port, Page35h.RX_MIN_CFO_PM)
    PM_dict['rx_cfo_max'] = read_reg_from_dict(port, Page35h.RX_MAX_CFO_PM)

    PM_dict['rx_evm_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_EVM_PM)*Data_Type_Dict.PM_SCALE['EVM_SCALE']
    PM_dict['rx_evm_min'] = read_reg_from_dict(port, Page35h.RX_MIN_EVM_PM)*Data_Type_Dict.PM_SCALE['EVM_SCALE']
    PM_dict['rx_evm_max'] = read_reg_from_dict(port, Page35h.RX_MAX_EVM_PM)*Data_Type_Dict.PM_SCALE['EVM_SCALE']

    PM_dict['tx_power_avg'] = read_reg_from_dict(port, Page35h.TX_AVG_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']
    PM_dict['tx_power_min'] = read_reg_from_dict(port, Page35h.TX_MIN_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']
    PM_dict['tx_power_max'] = read_reg_from_dict(port, Page35h.TX_MAX_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']

    PM_dict['rx_power_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']
    PM_dict['rx_power_min'] = read_reg_from_dict(port, Page35h.RX_MIN_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']
    PM_dict['rx_power_max'] = read_reg_from_dict(port, Page35h.RX_MAX_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']

    PM_dict['rx_sigpwr_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_SIG_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']
    PM_dict['rx_sigpwr_min'] = read_reg_from_dict(port, Page35h.RX_MIN_SIG_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']
    PM_dict['rx_sigpwr_max'] = read_reg_from_dict(port, Page35h.RX_MAX_SIG_POWER_PM)*Data_Type_Dict.PM_SCALE['POWER_SCALE_DBM']

    PM_dict['rx_soproc_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_SIG_SOPROC_PM)
    PM_dict['rx_soproc_min'] = read_reg_from_dict(port, Page35h.RX_MIN_SIG_SOPROC_PM)
    PM_dict['rx_soproc_max'] = read_reg_from_dict(port, Page35h.RX_MAX_SIG_SOPROC_PM)

    PM_dict['rx_mer_avg'] = read_reg_from_dict(port, Page35h.RX_AVG_MER_PM)*Data_Type_Dict.PM_SCALE['MER_SCALE_DB']
    PM_dict['rx_mer_min'] = read_reg_from_dict(port, Page35h.RX_MIN_MER_PM)*Data_Type_Dict.PM_SCALE['MER_SCALE_DB']
    PM_dict['rx_mer_max'] = read_reg_from_dict(port, Page35h.RX_MAX_MER_PM)*Data_Type_Dict.PM_SCALE['MER_SCALE_DB']

    write_reg_from_dict(port, Page2Fh.FREEZE_REQUEST, 0)
    return PM_dict
```
#### 3.4 Set module configuration, turn up
- set_low_power
```
def set_low_power(port, AssertLowPower):
    module_control = AssertLowPower << 6    
    write_reg_from_dict(port, Page00h_Lower.MODULE_LEVEL_CONTROL, module_control)
```
- set_TX_power
```
def set_TX_power(port, TX_power):
    
    # Target programmable output power increments of 0.01 dBm.
    TX_POWER_SCALE = 0.01
    TX_power_buffer = round(TX_power / TX_POWER_SCALE)
    write_reg_from_dict(port, Page12h.TX_TARGET_OUTPUT_POWER_LANE_1,TX_power_buffer)

    # Keep reading tuning in progress bit until it completes. TX_TUNING_STATUS_LANE_1
    # Bit 1: 0b, TX tuning not in progress; 1b, TX tuning in progress (both freq and power)
    # Bit 0: TX wavelength unlocked real-time status. 0b, wavelength locked; 1b, wavelength unlocked
    WAIT_TIME = 30 # wait for 30 seconds
    counter = 0
    while counter < WAIT_TIME:
        tuning_status = read_reg_from_dict(port, Page12h.TX_TUNING_STATUS_LANE_1) & 0x3
        if (tuning_status == 0):
            break
        time.sleep(1)
        counter += 1

    tuning_status = read_reg_from_dict(port, Page12h.TX_TUNING_STATUS_LANE_1) & 0x3
    if (tuning_status == 0):  # Tuning complete
        print('Success! Tuning completes!')
    else:
        print('Error! Tuning failed!')
```
- set_laser_freq
```
def set_laser_freq(port, freq):
    # Note the input argument freq must be in THz
    set_low_power(port, True)
    time.sleep(5)
    # Set selected grid spacing in Page 12h to 75 GHz
    # Bit 7-4: TX lane {n} selected grid spacing RW
    # Selected grid spacing of lane n=1-8.
    # 0000b: 3.125 GHz
    # 0001b: 6.25 GHz
    # 0010b: 12.5 GHz
    # 0011b: 25 GHz
    # 0100b: 50 GHz
    # 0101b: 100 GHz
    # 0110b: 33 GHz
    # 0111: 75 GHz
    # 8-14: Reserved
    # 1111b: Not available

    # Bit 0: TX lane {n} fine tuning enable RW
    # Bool fine-tuning enabled for lane n=1-8.
    # 0b: Fine-tuning disabled
    # 1b: Fine-tuning enabled.
    freq_grid = 0x70
    write_reg_from_dict(port, Page12h.TX_TUNING_SETTING_LANE_1, freq_grid)

    # Channel number n for 75 GHz grid spacing
    # Frequency (THz) = 193.1 + n * 0.025, where n must be divisible by 3.
    channel_number = int(round((freq - 193.1)/0.025))
    if channel_number % 3 is not 0:
        print('Error! Frequency has to be in 75 GHz grid!')
        return
    write_reg_from_dict(port, Page12h.TX_CHANNEL_NUM_LANE_1, channel_number)

    # Deassert low power mode
    set_low_power(port, False)
    
    # Keep reading tuning in progress bit until it completes. TX_TUNING_STATUS_LANE_1
    # Bit 1: 0b, TX tuning not in progress; 1b, TX tuning in progress (both freq and power)
    # Bit 0: TX wavelength unlocked real-time status. 0b, wavelength locked; 1b, wavelength unlocked
    WAIT_TIME = 30 # wait for 30 seconds
    counter = 0
    while counter < WAIT_TIME:
        tuning_status = read_reg_from_dict(port, Page12h.TX_TUNING_STATUS_LANE_1) & 0x3
        if (tuning_status == 0):
            break
        time.sleep(1)
        counter += 1

    tuning_status = read_reg_from_dict(port, Page12h.TX_TUNING_STATUS_LANE_1) & 0x3
    if (tuning_status == 0):  # Tuning complete
        print('Success! Tuning completes!')
    else:
        print('Error! Tuning failed!')
```                
### 4. Method to read from and write to registers
#### 4.1 Read and write registers
- read_reg
- write_reg
Read and write registers use vendor provided functions to access the bottom layer registers with dictionaries defined Sample code to read and write registers with vendor provided functoins. As mentioned above, the address of a byte with *page* and *offset* is *page* * 128 + *offset*. Below is sample code to read and write registers.
```
import sonic_platform.platform
import sonic_platform_base.sonic_sfp.sfputilhelper
platform_chassis = sonic_platform.platform.Platform().get_chassis()
PAGE_SIZE = 128

def read_reg(port, page, offset, size):
    return platform_chassis.get_sfp(port).read_eeprom(page*PAGE_SIZE + offset,size)

def write_reg(port, page, offset, size, write_raw):
    platform_chassis.get_sfp(port).write_eeprom(page*PAGE_SIZE + offset,size,write_raw)
```
#### 4.2 Encoding and decoding raw data
- read_reg_from_dict
- write_reg_from_dict
Read and write registers from dictionary use dictionaries defined [here](#definition-on-cmis-and-c-cmis-registers) and calls read and write register function [here](#read-and-write-registers). We use Python built-in library ```struct``` to encode and decode the raw data in bytearray form to meaningful values. Sample code to decode and encode from/to rawdata in registers:
```
def read_reg_from_dict(port, Dict): 
    read_raw = read_reg(port, page = Dict['PAGE'], offset = Dict['OFFSET'], size = Dict['SIZE'])
    read_buffer = struct.unpack(Dict['TYPE'], read_raw)
    if len(read_buffer) == 1:
        return read_buffer[0]
    else:
        return read_buffer

def write_reg_from_dict(port, Dict, write_buffer):
    write_raw = struct.pack(Dict['TYPE'], write_buffer)
    write_reg(port, page = Dict['PAGE'], offset = Dict['OFFSET'], size = Dict['SIZE'], write_raw = write_raw)
```
### 5. Definition on CMIS and C-CMIS registers
-  Memory structure and mapping
The host addressable memory starts with a lower memory of 128 bytes that occupy address byte 0-127. 
Then it starts from Page 0. Each page has 128 bytes and the first byte of each page starts with an offset of 128.
Therefore, the address of a byte with *page* and *offset* is *page* * 128 + *offset*.
-  Module general information pages (Page 0h - 1Fh, CMIS). See Figure 8-1 and Figure 8-2 in [CMIS](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf)
Important pages containing module general information:
|Address|Page Description|Type|
|-------|----------------|----|
|00h|Administrative Information|RO|
|01h|Advertising|RO|
|02h|Threshold Information|RO|
|04h|Laser Capabilities Advertising|RO|
|10h|Lane and Datapath Configuration|RW|
|11h|Lane and Datapath Status|RO|
|12h|Tunable Laser Control and Status|mixed|
Sample code to define registers with module general information:
```
SFF8024_IDENTIFIER = {
          'PAGE': 0x00,
          'OFFSET': 0,
          'SIZE': 1,
          'TYPE': 'B'
}
```
-  Versatile Diagnostics Monitor (VDM) pages (Page 20h - 2Fh, CMIS and C-CMIS)
VDM Pages. See Table 8-119 in [CMIS](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf)
|Address|Page Description|Type|
|-------|----------------|----|
|20h|VDM Observable Descriptors 1| RO|
|21h|VDM Observable Descriptors 2| RO|
|22h|VDM Observable Descriptors 3| RO|
|23h|VDM Observable Descriptors 4| RO|
|24h|VDM Samples 1| RO|
|25h|VDM Samples 2| RO|
|26h|VDM Samples 3| RO|
|27h|VDM Samples 4| RO|
|28h|VDM Thresholds 1| RO|
|29h|VDM Thresholds 2| RO|
|2Ah|VDM Thresholds 3| RO|
|2Bh|VDM Thresholds 4| RO|
|2Ch|VDM Flags|RO/COR|
|2Dh|VDM Masks|RW|
Note that VDM ID 1-24 are defined in CMIS. VDM ID starting from 128 are defined in C-CMIS. Below is sample code to define registers with VDM information. 
We use ```get_VDM``` function to get VDM items and their thresholds, which will be introduced later in this document [here](#get-vdm-related-information).
```
VDM_TYPE = {
          # VDM_ID: [VDM_NAME, DATA_TYPE, SCALE]
          1: ['Laser Age [%]', 'U16', 1],
          2: ['TEC Current [%]', 'S16', 100.0/32767],
          3: ['Laser Frequency Error [MHz]', 'S16', 10],
          4: ['Laser Temperature [C]', 'S16', 1.0/256],
          5: ['eSNR Media Input [dB]', 'U16', 1.0/256],
          6: ['eSNR Host Input [dB]', 'U16', 1.0/256],
          7: ['PAM4 Level Transition Parameter Media Input [dB]', 'U16', 1.0/256],
          8: ['PAM4 Level Transition Parameter Host Input [dB]', 'U16', 1.0/256],
          9: ['Pre-FEC BER Minimum Media Input', 'F16', 1], 
          10: ['Pre-FEC BER Minimum Host Input', 'F16', 1], 
          11: ['Pre-FEC BER Maximum Media Input', 'F16', 1], 
          12: ['Pre-FEC BER Maximum Host Input', 'F16', 1], 
          13: ['Pre-FEC BER Average Media Input', 'F16', 1], 
          14: ['Pre-FEC BER Average Host Input', 'F16', 1], 
          15: ['Pre-FEC BER Current Value Media Input', 'F16', 1],
          16: ['Pre-FEC BER Current Value Host Input', 'F16', 1],
          17: ['Errored Frames Minimum Media Input', 'F16', 1], 
          18: ['Errored Frames Minimum Host Input', 'F16', 1], 
          19: ['Errored Frames Maximum Media Input', 'F16', 1], 
          20: ['Errored Frames Minimum Host Input', 'F16', 1], 
          21: ['Errored Frames Average Media Input', 'F16', 1], 
          22: ['Errored Frames Average Host Input', 'F16', 1], 
          23: ['Errored Frames Current Value Media Input', 'F16', 1], 
          24: ['Errored Frames Current Value Host Input', 'F16', 1],
          128: ['Modulator Bias X/I [%]', 'U16', 100.0/65535],
          129: ['Modulator Bias X/Q [%]', 'U16', 100.0/65535],
          130: ['Modulator Bias Y/I [%]', 'U16', 100.0/65535],
          131: ['Modulator Bias Y/Q [%]', 'U16', 100.0/65535],
          132: ['Modulator Bias X_Phase [%]', 'U16', 100.0/65535],
          133: ['Modulator Bias Y_Phase [%]', 'U16', 100.0/65535],
          134: ['CD high granularity, short link [ps/nm]', 'S16', 1], 
          135: ['CD low granularity, long link [ps/nm]', 'S16', 20],
          136: ['DGD [ps]', 'U16', 0.01],
          137: ['SOPMD [ps^2]', 'U16', 0.01],
          138: ['PDL [dB]', 'U16', 0.1],
          139: ['OSNR [dB]', 'U16', 0.1],
          140: ['eSNR [dB]', 'U16', 0.1],
          141: ['CFO [MHz]', 'S16', 1],
          142: ['EVM_modem [%]', 'U16', 100.0/65535],
          143: ['Tx Power [dBm]', 'S16', 0.01],
          144: ['Rx Total Power [dBm]', 'S16', 0.01],
          145: ['Rx Signal Power [dBm]', 'S16', 0.01],
          146: ['SOP ROC [krad/s]', 'U16', 1],
          147: ['MER [dB]', 'U16', 0.1]
}
```
-  C-CMIS related pages (Page 30h - 4Fh, C-CMIS)
See [C-CMIS v1.1](https://www.oiforum.com/wp-content/uploads/OIF-C-CMIS-01.1.pdf)
|Address|Page Description|Type|
|-------|----------------|----|
|30h|Media Lane Configurable Thresholds|RW|
|31h|Media Lane Provisioning|RW|
|32h|Media Lane Masks|RW|
|33h|Media Lane Flags|RO/COR|
|34h|Media Lane FEC PM|RO|
|35h|Media Lane Link PM|RO|
|38h|Host Interface Configuration|RW|
|3Ah|Host Interface PM|RO|
|3Bh|Host Interface Flags and Masks|mixed|
|41h|RX Power Advertisement and Configurable Thresholds|RO|
|42h|PM Advertisement|RO|
|43h|Media Lane Provisioning Advertisement|RO|
### 6. Module firmware upgrade using command data block (CDB)
This section discusses the details of implementing firmware upgrade using CDB message communication. Figure 7-4 in [CMIS](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf) defines the flowchart for upgrading the module firmware. 
The first step is to obtain CDB features supported by the module from CDB command 0041h, such as start header size, maximum block size, whether extended payload messaging (page 0xA0 - 0xAF) or only local payload is supported. These features are important because the following upgrade with depend on these parameters. 
The second step is to start CDB download by writing the header of start header size from the designated firmware file to the local payload page 0x9F, with CDB command 0101h. 
The third step is to repeatedly read from the given firmware file and write to the payload space advertised from the first step. We use CDB command 0103h to write to the local payload; we use CDB command 0104h to write to the extended paylaod. This step repeats until it reaches end of the firmware file, or the CDB status failed.
The last step is to complete the firmware upgrade with CDB command 0107h. 
Note that if the download process fails anywhere in the middle, we need to run CDB command 0102h to abort the upgrade before we restart another upgrade process. 
After the firmware download finishes. The firmware will be run and committed with CDB command 0109h and 010Ah. We also check the currently running and committed firmware iamge version by CDB command 0100h before and after the entire firmware upgrade process to confirm the module switched to the updated firmware. 
A CDB command is triggered when byte 0x9F: 129 is written. This requires we break a CDB command into two written pieces:
1. write bytes from 0x9F: 130 till the message ends.
2. write bytes 0x9F: 128-129.
A single write command from 0x9F: 128 until the message ends should be avoided. 
Sample code to run firmware upgrade from high level functions:
```
import CDB_operations as cdb_oper

def module_firmware_upgrade(port, filepath):
    cdb_oper.get_module_FW_info(port)
    startLPLsize, maxblocksize, lplonly_flag = cdb_oper.get_module_FW_upgrade_features(port)
    cdb_oper.module_FW_download(port, startLPLsize, maxblocksize, lplonly_flag, filepath)
    cdb_oper.module_FW_run(port)
    time.sleep(60)
    cdb_oper.module_FW_commit(port)
    cdb_oper.get_module_FW_info(port)
```
Sample *CDB_operations* code (partial) to get module firmware information:
```
import cmisCDB as cdb

def get_module_FW_info(port):
    # get fw info (CMD 0100h)
    starttime = time.time()
    print('Get module FW info')
    rlplen, rlp_chkcode, rlp = cdb.cmd0100h(port)
    if cdb.cdb_chkcode(rlp) == rlp_chkcode:
        # Regiter 9Fh:136
        fwStatus = rlp[0]
        # Registers 9Fh:138,139; 140,141
        print('Image A Version: %d.%d; BuildNum: %d' %(rlp[2], rlp[3], ((rlp[4]<< 8) | rlp[5])))
        # Registers 9Fh:174,175; 176.177
        print('Image B Version: %d.%d; BuildNum: %d' %(rlp[38], rlp[39], ((rlp[40]<< 8) | rlp[41])))

        ImageARunning = (fwStatus & 0x01) # bit 0 - image A is running
        ImageACommitted = ((fwStatus >> 1) & 0x01) # bit 1 - image A is committed
        ImageBRunning = ((fwStatus >> 4) & 0x01) # bit 4 - image B is running
        ImageBCommitted = ((fwStatus >> 5) & 0x01)  # bit 5 - image B is committed

        if ImageARunning == 1: 
            RunningImage = 'A'
        elif ImageBRunning == 1:
            RunningImage = 'B'
        if ImageACommitted == 1:
            CommittedImage = 'A'
        elif ImageBCommitted == 1:
            CommittedImage = 'B'
        print('Running Image: %s; Committed Image: %s' %(RunningImage, CommittedImage))
    else:
        raise ValueError, 'Reply payload check code error'
    elapsedtime = time.time()-starttime
    print('Get module FW info time: %.2f s' %elapsedtime) 
```
The output of *get_module_FW_info* function:
```
>>> get_module_FW_info(port)
Get module FW info
Image A Version: 1.1; BuildNum: 4
Image B Version: 0.11; BuildNum: 127
Running Image: A; Committed Image: A
```
Sample code in *cmisCDB* to support *get_module_FW_info* function:
```
LPLPAGE = 0x9f
INIT_OFFSET = 128
CMDLEN = 2
# Get FW info
def cmd0100h(port):
    cmd = bytearray(b'\x01\x00\x00\x00\x00\x00\x00\x00')
    cmd[133-INIT_OFFSET] = cdb_chkcode(cmd)
    write_cdb(port,cmd)
    while cdb1_chkstatus(port):
        time.sleep(0.1)
    return read_cdb(port)
    
def cdb_chkcode(cmd):
    checksum = 0
    for byte in cmd:
        checksum += byte   
    return 0xff - (checksum & 0xff)

def cdb1_chkstatus(port):
    status = read_reg_from_dict(port, Page00h_Lower.CDB1_STATUS)
    return bool(status & 0x80)

def write_cdb(port,cmd):
    write_reg(port, LPLPAGE, INIT_OFFSET+CMDLEN, len(cmd)-CMDLEN, cmd[CMDLEN:])
    write_reg(port, LPLPAGE, INIT_OFFSET, CMDLEN, cmd[:CMDLEN])
```
