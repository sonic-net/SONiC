/****************************************************************** 
Template   to   perform   a CPS   API   GET  request.
*******************************************************************/
cps_api_return_code_t   do_get_request()
{
  /*   Allocate   and initialize   the   get   request   structure   */
  cps_api_get_params_t   get_req;

  if (cps_api_get_request_init(&get_req)   !=   cps_api_ret_code_OK)   {
    /*   Failed   to   initialize   get   request
	 =>   Indicate   error
    */

    return   (cps_api_ret_code_ERR);
  }

  /*   Assume   failure   response   */
  cps_api_return_code_t   result   =  cps_api_ret_code_ERR;
  do {
    /*   Allocate   the   request   object   and add it to   the   get request
     */
    cps_api_object_t   request_obj;
    request_obj   =  cps_api_object_list_create_obj_and_append(
							       get_req.filters
							       );
    if (request_obj   ==   CPS_API_OBJECT_NULL)   {
      /*   Failed   to   allocate   response   object   and add it to get   request
       */ 
      break;
    }

    /*   Set   the   key and key attributes   for   the   request   object. 
         The   actual   object   key and key attribute   ids,   types   and values   
         will   of   course   depend  on which   object   is being requested;   
         such dependent   values   are indicated   by  ellipses ... below.     
         Consult   the   data   model   for   the   desired   object.
    */


    cps_api_key_from_attr_with_qual(cps_api_object_key(
						       request_obj
						       ),
				    ...
				    );


    cps_api_set_key_data(request_obj,   ...);
    ...          cps_api_set_key_data(request_obj,   ...);


    cps_api_object_attr_add_...(request_obj,   ...);
    ...          cps_api_object_attr_add_...(request_obj,   ...);


    /*   Do  the   GET  request   */
    if (cps_api_get(&get_req)   !=   cps_api_ret_code_OK)   {
      /*   GET  request   failed   */
      break;
    }

    /*   Extract   the   response   object   */
    cps_api_object_t   response_obj;

    response_obj   =  cps_api_object_list_get(get_req.list,   0);
    if (response_obj   ==   CPS_API_OBJECT_NULL)   {
      /*   Failed   to   extract   the   response   object   */
      break;
    }

    /*   Extract   the   desired   object   attributes   from   the response   object.     
         (The   actual   object   attributes will   depend  on the   nature   of   the   response   object; 
         such dependent   values   are indicated   by  ellipses below.     
         Consult   the   appropriate   data   model   for details.)
    */ 

    cps_api_object_attr_t   attr;
    attr   =  cps_api_object_attr_get(response_obj,    );
    if (attr   ==   CPS_API_ATTR_NULL)   {
      /*   Failed   to   extract   expected   attribute   */
      break;
    }

    /*   Get   the   value   for   the   attribute   */
         =  cps_api_object_attr_data_...(attr);


    /*   Do  something   with   the   extracted   value   */

    /*   Indicate   success */
    result   =  cps_api_ret_code_OK;
  } while   (0);


  cps_api_get_request_close(&get_req);
  return   (result);
}




/****************************************************************** 
 Template   to   perform   a CPS   API   SET
*******************************************************************/


cps_api_return_code_t   do_set_request()
{
  cps_api_transaction_params_t   xact   ;
  if (cps_api_transaction_init(&xact)   !=   cps_api_ret_code_OK)   {
    return   (cps_api_ret_code_ERR);
  }


  cps_api_return_code_t   result   =  cps_api_ret_code_ERR;
  do {
    cps_api_object_t   request_obj;

    request_obj   =  cps_api_object_create()   ; 
    if (request_obj   ==   CPS_API_OBJECT_NULL)   {
      break;
    }


    /*   Set   key and attributes   in   request   object   */
    cps_api_key_from_attr_with_qual(cps_api_object_key(
						       request_obj
						       ),
				     
				    );


    cps_api_set_key_data(request_obj,   ...);
    ...          cps_api_set_key_data(request_obj,   ...);


    cps_api_object_attr_add_...(request_obj,   ...);
    ...          cps_api_object_attr_add_...(request_obj,   ...);


    if (cps_api_set(&xact,   request_obj)   !=   cps_api_ret_code_OK)   {
      cps_api_object_delete(request_obj);

      break;
    }

    result   =  cps_api_commit(&xact);
  } while   (0);


  cps_api_transaction_close(&xact);

  return   (result);
}
