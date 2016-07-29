/****************************************************************** 
Template   to   perform   a CPS   API   SET

This   function   is a sample   of   how   to   compose   a CPS   API   get   request object,   
and how   to   extract   data   from   the   GET  response.

*******************************************************************/

cps_api_return_code_t   event_publish(cps_api_object_t   event_obj)
{
  static   bool                                                                    init_flag   =  false;
  static   cps_api_event_service_handle_t   handle;


  if (!init_flag)   {
    /*   Not   initialized
	 =>   Connect   to   CPS   event   subsystem
    */


    if (cps_api_event_service_init()   !=   cps_api_ret_code_OK)   {
      return   (cps_api_ret_code_ERR);
    }


    if (cps_api_event_client_connect(&handle)   !=
	cps_api_ret_code_OK
	) {
      return   (cps_api_ret_code_ERR);
    }

    /*   Mark   as initialized   */

    init_flag   =  true;
  }

  cps_api_return_code_t   result; 




  /*   Publish   the   given   object   */


  result   =  cps_api_event_publish(handle,   event_obj);


  /*   Consume   the   given   object   */


  cps_api_object_delete(event_obj);

  return   (result);
}




Python Template: CPS Event Publisher Application


import   cps
import   cps_utils


handle   =  cps.event_connect()


  obj   =  cps_utils.CPSObject('base-port/interface',qual='observed', data=   {"ifindex":23})

  cps.event_send(handle,   obj.get())




  C Template: Event Subscriber Application

  This section describes the structure of a CPS event subscriber implemented in C. It illustrates the initialization of the event service and event processing thread, registration of the event handler function and event processing callback. The key list specified in the registration is used to determine the events that are delivered to this application (in this case, the list contains a single element).


  bool   event_handler(cps_api_object_t   object,   void   *context)
{           /*   Extract   key and attributes   of   received   object   */

  /*   Do  something   with   that   information   */
}
  

cps_api_return_code_t   event_subscribe()
{           /*   Connect   to   the   CPS   API   event   service   */


    if (cps_api_event_service_init()   !=   cps_api_ret_code_OK)   {
      return   (cps_api_ret_code_ERR);
    } 




    if (cps_api_event_thread_init()   !=   cps_api_ret_code_OK)   {
      return   (cps_api_ret_code_ERR);
    }


    /*   Register   the   event   handler   function   */
    cps_api_key_t   key; cps_api_key_init(&key,    ); cps_api_event_reg_t   reg; reg.objects                            =  key;
    reg.number_of_objects   =  1;


    if (cps_api_event_thread_reg(&reg,   event_handler,   0)
	!=   cps_api_ret_code_OK
	) {
      /*   Failed   to   register   handler   */

      return   (cps_api_ret_code_ERR);
    }

    /*   Indicate   success */

    return   (cps_api_reg_code_OK);
}

