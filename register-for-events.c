#include   "cps_api_events.h"
#include   "cps_api_object.h"
#include   "dell-base-phy-interface.h"
#include   "cps_class_map.h"
#include   "cps_api_object_key.h"


#include   <stdlib.h> 
#include   <stdio.h>
#include   <unistd.h>


//Callback   for   the   interface   event   handling
static   bool   cps_if_event_cb(cps_api_object_t   obj,   void   *param){

  char   buf[1024];
  cps_api_object_to_string(obj,buf,sizeof(buf));
  printf("Object   Received   %s   \n",buf);
  return   true;
}

bool   cps_reg_intf_events(){


  // Initialize   the   event   service
  if (cps_api_event_service_init()   !=   cps_api_ret_code_OK)   {
    return   false;
  }
  // Initialize   the   event   handling   thread
  if (cps_api_event_thread_init()   !=   cps_api_ret_code_OK)   {
    return   false;
  }


  //Create   and initialize   the   key
  cps_api_key_t   key;
  cps_api_key_from_attr_with_qual(&key,   BASE_PORT_INTERFACE_OBJ, cps_api_qualifier_OBSERVED);

  //Create   the   registration   object
  cps_api_event_reg_t   reg;
  memset(&reg,0,sizeof(reg));

  reg.number_of_objects   =  1;
  reg.objects   =  &key;


  // Register   to   receive   events   for   key created   above
  if (cps_api_event_thread_reg(&reg,   cps_if_event_cb,NULL)!=cps_api_ret_code_OK)   {
    return   false;
  }


  //Wait   for   the   events
  while(1){
    sleep(1);
  }

  return   true;

} 
