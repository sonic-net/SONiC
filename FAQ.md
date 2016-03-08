# Software for Open Networking in the Cloud 
# FAQ

The purpose of this FAQ is to provide an introduction to Software for Open Networking In the Cloud (SONiC) and answer common questions.

###SCOPE
Q. Is SONiC a Linux distribution?

A. No, SONiC is a collection of networking software components required to have a fully functional L3 device that can be agnostic of any particular Linux distribution. Today SONiC runs on Debian 

Q. Does SONiC have any hardware?
A. No SONiC is purely a software offering.

Q. Is Microsoft going to sell SONiC?
A. No, Microsoft has no plans to sell SONiC to customers or provide any network engineering or development support.

Q. Where is Microsoft planning on deploying SONiC?
A. The scope of SONiC is limited to the Azure Public Cloud to be run as T0 and T1 switches in the datacenter infrastructure.

###UNIQUENESS
Q. Is SONiC what was formerly the Azure Cloud Switch (ACS)?
A. Mostly.   ACS builds on top of SONiC with internal cloud management applications. 

Q. How is SONiC different from FBOSS?
A. Today, FBOSS only supports Broadcom. SONiC works on top of SAI and can support multiple chipsets. FBOSS as released today only contains a router agent which is similar to the syncd component inside SONiC both of which sync information to a network switch ASIC.  SONiC includes this functionality, adds a switch state service and includes a curated set of open source software which delivers full L3 router functionality.

Q. What is ONL and how is SONiC different from it?
A. ONL is intended to provide a basic Linux environment for white box switches.  
SONiC also works in a Linux environment, but includes the switch state service and a curated set of open source software to provide full L3 router functionality.  

Q. Will ONL and SONiC compete at the OCP?
A. No.  In fact, ONL and SONiC maintainers will work together to integrate SONiC on top of ONL to achieve broad support for OCP switches.

Q. HP recently announced openswitch.net. Why do we need yet another open sourced software switch?
A. Open Switch currently only supports Accton hardware via EdgeCore and HP switch brands. It also only supports the Broadcom chipset via OpenNSL. Additionally, it has not been adopted by operational networks. 
OCP Ecosystem

Q. Where is SONiC being contributed?
A. SONiC is being contributed to the Open Compute Project for consideration to be accepted as an OCP.

Q. Why OCP and not some other consortium?
A. We believe after OCP HW and SAI, SONiC is the next holistic step to grow under the OCP Umbrella. SONiC via SAI can be ported onto multiple chipsets. SONiC via future collaborations with ONL can be ported to OCP HW. 

Q. Who are your co-contributors?
A. Our initial co-contributors are Dell, Mellanox, Arista, Broadcom, and Canonical. 

Q. What is the open source license?
A. Most of the code that is unique to SONiC is Apache 2.0. However, some packages are other licenses including GPL.  

###DEPLOYMENT
Q. Is SONiC deployed in Microsoft datacenters today?
A. Yes, SONiC is deployed in Microsoft production datacenters.

Q. How many devices are SONiC based?
A. The deployment is currently small but growing.  We plan to rapidly expand SONiC deployment over the coming months. 

Q. Which hardware platforms and ASIC chipset are you running SONiC on?
A. From our demo in the Microsoft booth you can see switches and chipsets that SONiC is running on.   We can’t comment on the hardware deployed in our production network.  

Q.  Is the same version on GitHub running in deployment today (March 9th, 2016)?
A. No.  As of March 9th, 2016, we are running SONiC v1 in the Microsoft production network.  The open source release of SONiC is v2 and represents many improvements over v1.    We will be working hard to deploy SONiC v2 into production in the coming weeks.PRODUCT/ENVIRONMENT

Q. Does the SONiC offer hardware options, and/or can it be customized?
A. The list of compatible hardware and ASIC vendors are on our GitHub.   SONiC and ONL plan to work together to greatly expand switch support for the community. 

Q. Does the SONiC offer Linux options, and/or can it be customized?
A. Today (March 9, 2016) SONiC requires Linux kernel 3.16.  We built and tested on Debian Linux, but theoretically any distribution could be supported.  It is fully open sourced and can be customized by users.  A contributor’s guide is posted to cover how to add documentation, code and report and fix bugs. 

Q. Will SONiC have binaries?
A. We will build some binaries, use binaries from existing Linux distribtutions and in some cases just release source code.  The getting started guide covers how to build, install and configure SONiC . 

Q. Where can I download SONiC?
A.  Please head to our landing page for all details regarding SONiC: http://azure.github.io/SONiC/

Q. Can a consumer add 3rd party components to SONiC?
A. The community can run whatever applications they like in their deployment. To add or change the core SONiC code, see the contributors guide.

Q. Are there sample SONiC configurations?
A.  Yes, the getting started guide provides links to example configurations. 

Q. Is SONiC a supported product?
A. SONiC is a community supported product.  Microsoft is interested in keeping SONiC relevant, reliable and stable.  We run it in our own network.
 
###LICENSE

Q. What license does Software for Open Networking In the Cloud (SONiC) allow?
A. The unique components of SONiC are licensed as Apache 2.0. However, SONiC selects many other open source packages which each have their own licenses.  
GOVERNANCE
Q. What is the governance model for SONiC?
A. Details are in the governance documentation at the landing page.

###CONTRIBUTING
Q. Can anyone contribute to SONiC?
A. Yes, SONiC collaborates and welcome open community involvement. Please check the contributors guide for details. 
