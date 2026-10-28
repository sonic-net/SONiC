# Software for Open Networking in the Cloud (SONiC)

This repository contains documentation, Wiki, master project management, and website for the Software for Open Networking in the Cloud (SONiC).

Documentation covers project wide concerns such as the getting started guide, faq,  general requirements for 
contribution, developer's guide, governance, architecture, and so on.  It also contains links to download and install SONiC
and links to all the source. See [SONiC Wiki](https://github.com/sonic-net/sonic/wiki) for complete information.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Build Status](https://dev.azure.com/mssonic/build/_apis/build/status/sonic-buildimage-official-vs?branchName=master)](https://dev.azure.com/mssonic/build/_build/latest?definitionId=138&branchName=master)

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Community](#community)
- [License](#license)

## Overview

SONiC (Software for Open Networking in the Cloud) is a free and open-source network operating system based on Linux that runs on switches from multiple vendors and ASICs. SONiC offers a full-suite of network functionality, like BGP and RDMA, that has been production-hardened in the data centers of some of the largest cloud-service providers.

This repository contains documentation, Wiki, master project management, and website for the SONiC project.

## Key Features

- **Multi-vendor support** - Runs on switches from various hardware vendors
- **Container-based architecture** - Modular design with Docker containers
- **Standard interfaces** - Uses standard Linux interfaces and tools
- **Production-ready** - Battle-tested in large-scale cloud environments
- **Open source** - Fully open-source with active community development
- **Programmable** - Supports modern network programming paradigms

## Architecture

SONiC is built on a modular architecture where each network function runs in its own Docker container. This design provides:
- Better fault isolation
- Easier debugging and troubleshooting
- Simplified upgrades and maintenance
- Enhanced scalability

## Getting Started

### Prerequisites
- Compatible network switch hardware
- Basic understanding of Linux networking
- Docker knowledge (recommended)

### Quick Start
1. Check hardware compatibility
2. Download the appropriate SONiC image
3. Install SONiC on your switch
4. Configure basic network settings
5. Start using SONiC features

## Installation

### Supported Platforms
SONiC supports a wide range of network switches. Check the [supported devices list](https://github.com/sonic-net/sonic/wiki/Supported-Devices-and-Platforms) for compatibility.

### Installation Methods
- **ONIE Installation** - Recommended for most deployments
- **Docker Installation** - For development and testing
- **Virtual Machine** - For learning and development

For detailed installation instructions, visit the [Installation Guide](https://github.com/sonic-net/sonic/wiki/Installation).

## Usage

### Basic Commands
```bash
# Show system status
show system status

# Display interface information
show interfaces status

# View routing table
show ip route

# Check BGP status
show bgp summary
```

### Configuration
SONiC uses JSON-based configuration files and supports both CLI and programmatic configuration methods.

## Documentation

Comprehensive documentation covers project-wide concerns including:
- Getting started guide
- FAQ
- Contribution requirements
- Developer's guide
- Governance
- Architecture details
- API documentation

Visit the [SONiC Wiki](https://github.com/sonic-net/sonic/wiki) for complete information.

### Additional Resources
- [Developer Guide](https://github.com/sonic-net/sonic/wiki/Developer-Guide)
- [User Manual](https://github.com/sonic-net/sonic/wiki/User-Manual)
- [Troubleshooting Guide](https://github.com/sonic-net/sonic/wiki/Troubleshooting)

## Contributing

We welcome contributions from the community! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Development Setup
- Follow the [Developer Guide](https://github.com/sonic-net/sonic/wiki/Developer-Guide)
- Set up your development environment
- Run tests before submitting changes

### Code of Conduct
Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Community

- **Mailing Lists**: [sonic-dev](https://groups.google.com/g/sonic-dev)
- **Slack**: [SONiC Community Slack](https://sonic-net.slack.com/)
- **Meetings**: Weekly community meetings (check Wiki for schedule)
- **Issues**: Report bugs and request features via GitHub Issues

## License

SONiC is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for more details.

---

**Note**: This is the master repository for SONiC project coordination. For source code, please visit the individual component repositories listed in the [SONiC Wiki](https://github.com/sonic-net/sonic/wiki).
