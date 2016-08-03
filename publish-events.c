#include   "cps_api_events.h"
#include   "cps_api_object.h"
#include   "dell-base-phy-interface.h"
#include   "cps_class_map.h"
#include   "cps_api_object_key.h"


#include   <stdio.h>
#include   <net/if.h>


bool   cps_pub_intf_event()   {


  static   cps_api_event_service_handle_t   handle;
  if (cps_api_event_service_init()   !=   cps_api_ret_code_OK)   {
    return   false;
  }
  if (cps_api_event_client_connect(&handle)   !=   cps_api_ret_code_OK)   {
    return   false;
  }


  //Create   and intialize   the   key
  cps_api_key_t   key;
  cps_api_key_from_attr_with_qual(&key,   BASE_PORT_INTERFACE_OBJ, cps_api_qualifier_OBSERVED);

  // Create   the   object
  cps_api_object_t   obj   =  cps_api_object_create();


  if(obj   ==   NULL){
    return   false;
  }


  // Add   attributes   to   the   object
  cps_api_object_attr_add_u32(obj,BASE_PORT_INTERFACE_IFINDEX, if_nametoindex("e101-001-0"));


  //Set   the   Key   to   the   object
  cps_api_object_set_key(obj,&key);

  //Publish   the   object
  if(cps_api_event_publish(handle,obj)!=   cps_api_ret_code_OK){
    cps_api_object_delete(obj);
    return   false;
  }
  // Delete   the   object
  cps_api_object_delete(obj);
  return   true;

} 




