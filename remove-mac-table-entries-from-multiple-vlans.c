#include   "cps_api_object.h"
#include   "dell-base-l2-mac.h"
#include   "cps_class_map.h"
#include   "cps_api_object_key.h"


#include   <stdint.h>
#include   <net/if.h>


bool   cps_flush_mac(){

  // Create   and initialize   the   transaction   object
  cps_api_transaction_params_t   tran;
  if (cps_api_transaction_init(&tran)   !=   cps_api_ret_code_OK   ){
    return   false;
  }

  // Create   and initialize   the   key
  cps_api_key_t   key;
  cps_api_key_from_attr_with_qual(&key,   BASE_MAC_FLUSH_OBJ,   cps_api_qualifier_TARGET);


  // Create   the   object
  cps_api_object_t   obj   =  cps_api_object_create(); 


  if(obj   ==   NULL ){
    cps_api_transaction_close(&tran);
    return   false;
  }

  // Set   the   key for   the   obejct
  cps_api_object_set_key(obj,&key);

  // Add   attributes   to   Flush   MAC   entries
  cps_api_attr_id_t   ids[3]   =  {BASE_MAC_FLUSH_INPUT_FILTER,0,   BASE_MAC_FLUSH_INPUT_FILTER_VLAN   };
  const   int   ids_len   =  sizeof(ids)/sizeof(ids[0]);


  uint16_t   vlan_list[3]={1,2,3};
  for(unsigned   int   ix=0;   ix<sizeof(vlan_list)/sizeof(vlan_list[0]);   ++ix) {
    ids[1]=ix;
    cps_api_object_e_add(obj,ids,ids_len,cps_api_object_ATTR_T_U16,&(vlan_list[ix]),sizeof(vlan_list[ix]));
  }


  unsigned   int   ifindex_list[]   =  { if_nametoindex("e101-001-0"),if_nametoindex("e101-002-0"), if_nametoindex("e101-003-0")};
  ids[2]=BASE_MAC_FLUSH_INPUT_FILTER_IFINDEX;
  
  for(unsigned   int   ix=0; ix<sizeof(ifindex_list)/sizeof(ifindex_list[0]); ++ix){
    ids[1]=ix;

    cps_api_object_e_add(obj,ids,ids_len,cps_api_object_ATTR_T_U16,&ifindex_list[ix],sizeof(ifindex_list[ix]));
  }


  // Add   the   object   along   with   the   operation   to   transaction
  if(cps_api_action(&tran,obj)   !=   cps_api_ret_code_OK   ){
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

