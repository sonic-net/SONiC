#include   "cps_api_object.h"
#include   "dell-base-l2-mac.h"
#include   "cps_class_map.h"
#include   "cps_api_object_key.h"


#include   <stdint.h>
#include   <net/if.h>


bool   cps_create_mac(){


  // Create   and initialize   the   transaction   object
  cps_api_transaction_params_t   tran;

  if (cps_api_transaction_init(&tran)   !=   cps_api_ret_code_OK   ){
    return   false;
  }


  // Create   and initialize   the   key cps_api_key_t   key;
  cps_api_key_from_attr_with_qual(&key,   BASE_MAC_TABLE_OBJ,   cps_api_qualifier_TARGET);


  // Create   the   object
  cps_api_object_t   obj   =  cps_api_object_create();

  if(obj   ==   NULL ){
    cps_api_transaction_close(&tran);
    return   false;
  }


  // Set   the   key for   the   obejct
  cps_api_object_set_key(obj,&key);

  // Add   attributes   mandatory   to   create   MAC   address   entry
  uint8_t   mac_addr[6]   =  {0x0,0xa,0xb,0xc,0xd,0xe}; uint16_t   vlan_id   =  100;

  cps_api_object_attr_add(obj,BASE_MAC_TABLE_MAC_ADDRESS,   mac_addr,   sizeof(hal_mac_addr_t));
  cps_api_object_attr_add_u32(obj,BASE_MAC_TABLE_IFINDEX,if_nametoindex("e101-001-0")   ); 



  cps_api_object_attr_add_u16(obj,BASE_MAC_TABLE_VLAN,vlan_id);


  // Add   the   object   along   with   the   operation   to   transaction
  if(cps_api_create(&tran,obj)   !=   cps_api_ret_code_OK   ){
    cps_api_object_delete(obj);
    return   false;
  }


  // Commit   the   transaction
  if(cps_api_commit(&tran)   !=   cps_api_ret_code_OK   ) {
    cps_api_transaction_close(&tran);
    return   false;
  }

  // Cleanup   the   Transaction
  cps_api_transaction_close(&tran);

  return   true;
}

