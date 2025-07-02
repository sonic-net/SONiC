# SONiC 200G SerDes/1.6T Support

## Table of Content

### 1\. Revision

| Rev | Date | Author | Change Description |
| :---- | :---- | :---- | :---- |
| 1.0 | 2024-01-25 | bobby-nexthop | Initial Version |

### 2\. Scope
This document describes the following enhancements to the SONiC OS:

- Changes required to support 1.6T operation and speeds utilizing 200G SerDes rates.
- Support for new transceiver types.
- Updates to utilities and show commands.

### 3\. Definitions/Abbreviations

| Term | Definition | 
| :---- | :---- |
| SFF | Small Form Factor |
| SerDes | Serializer/Deserializer |
| PAM4 | Pulse Amplitude Modulation 4-level |
| MMF | Multi-Mode Fiber |
| SMF | Single-Mode Fiber |
| GBd | Gigabaud (billion symbols per second) |
| Gb/s | Gigabits per second |
| FLR | Frame Loss Ratio |

### 4\. Overview

The IEEE P802.3dj taskforce is working on finalizing the amendment to the 802.3 spec. This amendment includes Media Access Control parameters for 1.6 Tb/s and Physical Layers and management parameters for 200 Gb/s, 400 Gb/s, 800 Gb/s, and 1.6 Tb/s operation. 

### 5\. High-Level Enchancements

#### 5.1. SFF-8024 Additions

Changes need to be made to the SFF Api to support the required host electrical interface IDs, MMF media interface IDs, and SMF media interface IDs.

##### 5.1.1. Host Electrical Interface

| |  |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ID** | **Host Electrical Interface (Specification Reference)** | **Application Bit Rate (Gb/s)** | **Lane Count** | **Lane Signaling Rate (GBd)** | **Modulation** |
| 30 | 200GBASE-CR1 (Clause179) | 212.5 | 1 | 106.25 | PAM4 |
| 31 | 400GBASE-CR2 (Clause179) | 425 | 2 | 106.25 | PAM4 |
| 87 | 800GBASE-CR4 (Clause179) | 850 | 4 | 106.25 | PAM4 |
| 88 | 1.6TBASE-CR8 (Clause179) | 1700 | 8 | 106.25 | PAM4 |
| 128 | 200GAUI-1 (Annex176E) | 212.5 | 1 | 106.25 | PAM4 |
| 129 | 400GAUI-2 (Annex176E) | 425 | 2 | 106.25 | PAM4 |
| 130 | 800GAUI-4 (Annex176E) | 850 | 4 | 106.25 | PAM4 |
| 131 | 1.6TAUI-8 (Annex176E) | 1700 | 8 | 106.25 | PAM4 |

##### 5.1.2. MMF Media Interface
| |  |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ID** | **MM Media Interface (Specification Reference)** | **Application Rate** | **Lane Count** | **Lane Signaling Rate (GBd)** | **Modulation** |
| 33 | 800G-VR4.2 | 850 | 8 | 53.125 | PAM4 |
| 34 | 800G-SR4.2 | 850 | 8 | 53.125 | PAM4 |

##### 5.1.3. SMF Media Interface
| |  |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ID** | **SM Media Interface (Specification Reference)** | **Application Bit Rate (Gb/s)** | **Lane Count** | **Lane Signaling Rate (GBd)** | **Modulation** |
| 115 | 200GBASE-DR1 (Clause 180\) | 212.5 | 1 | 106.25 | PAM4 |
| 116 | 200GBASE-DR1-2 (Clause 181\) | 212.5 | 1 | 113.4375 | PAM4 |
| 117 | 400GBASE-DR2 (Clause 180\) | 425 | 2 | 106.25 | PAM4 |
| 118 | 400GBASE-DR2-2 (Clause 181\) | 425 | 2 | 113.4375 | PAM4 |
| 119 | 800GBASE-DR4 (Clause 180\) | 850 | 4 | 106.25 | PAM4 |
| 120 | 800GBASE-DR4-2 (Clause 181\) | 850 | 4 | 113.4375 | PAM4 |
| 121 | 800GBASE-FR4-500 (Clause 183\) | 850 | 4 | 106.25 | PAM4 |
| 122 | 800GBASE-FR4 (Clause 183\) | 850 | 4 | 113.4375 | PAM4 |
| 123 | 800GBASE-LR4 (Clause 183\) | 850 | 4 | 113.4375 | PAM4 |
| 127 | 1.6TBASE-DR8 (Clause 180\) | 1700 | 8 | 106.25 | PAM4 |
| 128 | 1.6TBASE-DR8-2 (Clause 181\) | 1700 | 8 | 113.4375 | PAM4 |

#### 5.2. sonic-platform-daemons Support
sonic-platform-daemons will need to add 1.6T speed support to xcvrd.

#### 5.3. sonic-utilities Support
- show interfaces status and other related commands would need to be updated to recognize and correctly display 1.6
- The config interface speed command would need to be updated to accept 1.6T as a valid speed.

#### 5.4. sonic-swss Support
Orchagent will need to update the FLR calculation to support SerDes rates of 212.50.

### 6\. Restrictions/Limitations
The hardware does not exist yet. This is a list of anticipated changes that will need to be made. It is possible that the final implementation and areas needed to be changedmay differ.
