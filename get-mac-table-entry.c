#include   "cps_api_object.h"
#include   "dell-base-l2-mac.h"
#include   "cps_class_map.h"
#include   "cps_api_object_key.h"


#include   <stdio.h>


bool   cps_get_mac(){


  // Create   and initialize   the   Get   object
  cps_api_get_params_t   gp; cps_api_get_request_init(&gp);

  // Create   a new   object   and append it to   get   request's   filter   object   list
  cps_api_object_t   obj   =  cps_api_object_list_create_obj_and_append(gp.filters);
  if(obj   ==   NULL){
    cps_api_get_request_close(&gp);
    return   false;
  } 



  // Create,   initialize   and set   the   key for   object
  cps_api_key_t   key;
  cps_api_key_from_attr_with_qual(&key,   BASE_MAC_QUERY_OBJ,   cps_api_qualifier_TARGET);
  cps_api_object_set_key(obj,&key);


  //Perform   a get   request bool   rc=false;
  if (cps_api_get(&gp)==cps_api_ret_code_OK)   {
    rc =  true;
    size_t   mx   =  cps_api_object_list_size(gp.list);
    for   (size_t   ix   =  0  ; ix   <  mx   ; ++ix   ) {
      cps_api_object_t   obj   =  cps_api_object_list_get(gp.list,ix);
      cps_api_object_attr_t   vlan_id   =  cps_api_object_attr_get(obj,BASE_MAC_QUERY_VLAN);
      cps_api_object_attr_t   ifindex   =  cps_api_object_attr_get(obj,BASE_MAC_QUERY_IFINDEX);
      cps_api_object_attr_t   mac_addr   =  cps_api_object_attr_get(obj,BASE_MAC_QUERY_MAC_ADDRESS);

      printf("VLAN ID %d\n",cps_api_object_attr_data_u16(vlan_id));
      printf("Ifindex %d\n",cps_api_object_attr_data_u32(ifindex));
      char   mt[6];
      char   mac_string[20];
      memcpy(mt,   cps_api_object_attr_data_bin(mac_addr),   6);
      sprintf(mac_string,   "%x:%x:%x:%x:%x:%x",   mt[0],   mt[1],   mt[2],   mt[3],   mt[4],   mt[5]);
      printf("MAC   Address   %s\n",mac_string);
    }
  }

  // Close   the   get   the   request
  cps_api_get_request_close(&gp);
  return   rc;
}


