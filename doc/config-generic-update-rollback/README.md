# Guide to reading the design documents
The document is divided into 3 parts, please read them in order:
1. [SONiC Generic Configuration Update and Rollback - HLD](SONiC_Generic_Config_Update_and_Rollback_Design.md)
2. [Json_Change_Application_Design](Json_Change_Application_Design.md) 
3. [Json_Patch_Ordering_using_YANG_Models_Design](Json_Patch_Ordering_using_YANG_Models_Design.md) 

# Plan of implementation
The implementation is going to be divided into the following steps:
1. Implementing [SONiC Generic Configuration Update and Rollback - HLD](SONiC_Generic_Config_Update_and_Rollback_Design.md)
2. Implementing [Json_Change_Application_Design](Json_Change_Application_Design.md)
3. Implementing [Json_Patch_Ordering_using_YANG_Models_Design](Json_Patch_Ordering_using_YANG_Models_Design.md)
4. Improving logging by making sure all the steps are logged to syslog as well as systemd journal
