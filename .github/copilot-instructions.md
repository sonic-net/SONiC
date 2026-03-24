# Copilot Instructions for SONiC

## Project Overview

This is the main SONiC (Software for Open Networking in the Cloud) repository — the central hub for project documentation, architecture designs, High Level Design (HLD) documents, roadmaps, governance, and community information. It serves as the landing page and design authority for the entire SONiC ecosystem.

## Architecture

```
SONiC/
├── doc/                        # Core documentation
│   ├── aaa/                    # Authentication/Authorization/Accounting
│   ├── acl/                    # Access Control Lists
│   ├── bgp/                    # BGP-related designs
│   ├── buffer/                 # Buffer management
│   ├── chassis/                # Chassis/modular platform designs
│   ├── crm/                    # Critical Resource Monitoring
│   ├── dash/                   # DASH (SmartNIC/DPU) designs
│   ├── dpu/                    # Data Processing Unit designs
│   ├── ecmp/                   # ECMP designs
│   ├── event-alarm/            # Event and alarm framework
│   ├── nat/                    # NAT designs
│   ├── pins/                   # PINS (P4 Integrated Network Stack)
│   ├── platform/               # Platform abstraction designs
│   ├── qos/                    # Quality of Service
│   ├── smart-switch/           # Smart Switch designs
│   ├── stp/                    # Spanning Tree Protocol
│   ├── warm-reboot/            # Warm reboot/restart
│   ├── xrcvd/                  # Transceiver daemon
│   └── ...                     # Many more feature areas
├── tsc/                        # Technical Steering Committee
│   ├── TSC_Election.md         # TSC election process
│   └── meetings/               # TSC meeting notes
├── Governance.md               # Project governance model
├── CONTRIBUTING.md             # Contribution guidelines
├── README.md                   # Project landing page
└── .github/                    # GitHub configuration
```

### Key Concepts
- **HLD (High Level Design)**: The primary design document format for SONiC features
- **Design review**: New features require HLD submission and community review
- **TSC (Technical Steering Committee)**: Governs the SONiC project
- **Feature areas**: Documentation organized by networking feature domain
- **Community meetings**: Regular community meetings and sub-group meetings

## HLD Document Format

Every new SONiC feature requires an HLD document. Follow this structure:

1. **Title and revision history**
2. **Scope**: What the document covers
3. **Definitions/Abbreviations**: Key terms
4. **Overview**: Feature description and motivation
5. **Requirements**: Functional and non-functional requirements
6. **Architecture Design**: How it fits into SONiC architecture
7. **High-Level Design**: Detailed design including:
   - DB schema changes (CONFIG_DB, APPL_DB, STATE_DB, etc.)
   - SAI API usage
   - CLI commands
   - YANG models
8. **SAI API**: Required SAI changes
9. **Configuration and management**: CLI, YANG, REST API
10. **Warm boot support**: How the feature handles warm restart
11. **Testing**: Test plan overview
12. **References**: Related documents and specifications

## Language & Style

- **Documentation**: Markdown (`.md` files)
- **Diagrams**: Embedded images or Mermaid diagrams
- **Tables**: Use Markdown tables for DB schema, CLI commands, etc.
- **Naming**: Follow SONiC naming conventions (CONFIG_DB, APPL_DB, orchagent, syncd, etc.)
- **File organization**: Place HLDs in the appropriate `doc/<feature>/` subdirectory

## PR Guidelines

- **Signed-off-by**: Required on all commits
- **CLA**: Sign Linux Foundation EasyCLA
- **HLD review**: Design documents require community review before merge
- **Feature proposals**: Discuss in SONiC community meetings before submitting HLD
- **Formatting**: Use consistent Markdown formatting — check rendering before submitting
- **Images**: Include architecture diagrams to illustrate designs
- **Cross-references**: Link to related HLDs and implementation PRs

## Gotchas

- **Documentation-only repo**: This repo contains no source code — only documentation and governance
- **HLD before code**: The SONiC process expects HLD approval before implementation PRs
- **Community process**: Major features should be presented at community meetings
- **DB schema coordination**: HLD DB schema changes must be coordinated across repos
- **Backward compatibility**: Design for backward compatibility with existing SONiC releases
- **Multi-repo impact**: A single HLD may require changes across sonic-swss, sonic-sairedis, sonic-utilities, etc.
- **Release branches**: HLDs target specific SONiC releases — note the target release
