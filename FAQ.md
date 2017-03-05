# Software for Open Networking in the Cloud (SONiC)
# FAQ


###SCOPE
Q. Is SONiC a Linux distribution?

A. No, SONiC is a collection of networking software components required to have a fully functional L3 device that can be agnostic of any particular Linux distribution. Today SONiC runs on Debian. SONiC on Ubuntu is coming very soon. 

----------

Q. Does SONiC have any hardware?

A. No SONiC is purely a software offering.

----------

Q. Is Microsoft going to sell SONiC?

A. No, Microsoft has no plans to sell SONiC to customers or provide any network engineering or development support.

----------

Q. Where is Microsoft planning on deploying SONiC?

A. SONiC is deployed in Microsoft cloud data center infrastructure.  

----------

Q. Is SONiC what was formerly the Azure Cloud Switch (ACS)?

A. Mostly. ACS builds on top of SONiC with internal cloud management applications. 

----------

Q. Is SONiC deployed in Microsoft datacenters today?

A. Yes, SONiC is deployed in Microsoft production datacenters.

----------

Q. How many devices are SONiC based?

A. The deployment is growing from one datacetner to cross regions.  We plan to rapidly expand SONiC deployment over the coming months. 

----------

Q. Which hardware platforms and ASIC chipset are you running SONiC on?

A. From our demo in the Microsoft booth you can see switches and chipsets that SONiC is running on.   We can’t comment on the hardware deployed in our production network.  

----------

Q.  Is the same version on GitHub running in deployment today (March 9th, 2016)?

A. No.  As of March 9th, 2016, we are running SONiC v1 in the Microsoft production network.  The open source release of SONiC is v2 and represents many improvements over v1.    We will be working hard to deploy SONiC v2 into production in the coming weeks.

----------

Q. Does the SONiC offer Linux options, and/or can it be customized?

A. Today (March 9, 2016) SONiC requires Linux kernel 3.16.  We built and tested on Debian Linux, but theoretically any distribution could be supported.  It is fully open sourced and can be customized by users.  A contributor’s guide is posted to cover how to add documentation, code and report and fix bugs. 

----------

Q. Will SONiC have binaries?

A. We will build some binaries, use binaries from existing Linux distributions and in some cases just release source code.  The getting started guide covers how to build, install and configure SONiC . 

----------

Q. Where can I download SONiC?

A.  Please head to our landing page for all details regarding SONiC: http://azure.github.io/SONiC/

----------

Q. Is SONiC a supported product?

A. SONiC is a community supported product.  Microsoft is interested in keeping SONiC relevant, reliable and stable.  We run it in our own network.
 
----------
###CONTRIBUTING
Q. Can anyone contribute to SONiC?

A. Yes, SONiC collaborates and welcome open community involvement. Please check the contributors guide for details. 
