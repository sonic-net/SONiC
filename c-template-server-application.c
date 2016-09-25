/******************************************************************
Template CPS API object server read handler function
This function is invoked by the CPS API service when a GET request
is placed for a registered CPS API object.  The binding of CPS
API object key to the read handler function is done below.
*******************************************************************/

cps_api_return_code_t xyz_read(
   void                 *context,
   cps_api_get_params_t *param,
   size_t               key_idx
   )
{
   /* Allocate a response object, and add to response */
   cps_api_object_t response_obj;
   response_obj = cps_api_object_list_create_obj_and_append(
                      param->list
                      );

   if (response_obj == CPS_API_OBJECT_NULL) {
       /* Failed to allocate response object
          => Indicate an error
       */
       return (cps_api_ret_code_ERR);
   }

   /* Fill in response object */
   cps_api_key_from_attr_with_qual(cps_api_object_key(response_obj),
                                   ...                                  
   );

   cps_api_set_key_data(response_obj, ...);
   ...      cps_api_set_key_data(response_obj, ...);

     cps_api_object_attr_add_...(response_obj, ...);

   ...      cps_api_object_attr_add_...(response_obj, ...);

   /* Indicate GET response successful */
   return (cps_api_ret_code_OK);}

/******************************************************************
Template CPS API object server write handler function
This function is invoked by the CPS API service when a SET request
is placed for a registered CPS API object.  The binding of CPS
API object key to the write handler function is done below.
*******************************************************************/

cps_api_return_code_t xyz_write(
   void                         *context,
   cps_api_transaction_params_t *param,
   size_t                       index_of_element_being_updated
   )

{
   /* Extract the object given in the request */
   cps_api_object_t request_obj;
   request_obj = cps_api_object_list_get(
                     param->change_list,
                     index_of_element_being_updated
                     );

   if (request_obj == CPS_API_OBJECT_NULL) {
       /* Failed to extract request object
          => Indicate error
       */
       return (cps_api_ret_code_ERR);
   }

   /* Assume error response */
   cps_api_return_code_t result = cps_api_ret_code_ERR;

   /* Determine the type of write operation */
   switch (cps_api_object_type_operation(
               cps_api_object_key(request_obj)
               )
           ) {

   case cps_api_oper_SET:

       /* SET operation requested */
       /* Create the rollback object, i.e. an object to return
          containing the old values for any attributes set, and
          add to transaction
       */

       cps_api_object_t rollback_obj;
       rollback_obj = cps_api_object_list_create_obj_and_append(
                          param->prev
                          );

       if (rollback_obj == CPS_API_OBJECT_NULL) {
           /* Failed to create rollback object */
           break;

       }

       /* Assume SET successful */
       result = cps_api_ret_code_OK;

       /* For each attribute given in the request,   */
       cps_api_object_it_t attr_iter;

       cps_api_object_it_begin(request_obj, &attr_iter);
       while (cps_api_object_it_valid(&attr_iter)) {

           /* Get the attribute id from the attribute iterator */
           cps_api_attr_id_t attr_id;

           attr_id = cps_api_object_attr_id(attr_iter.attr);

           /* Update the rollback object with the old value
              of the attribute
           */

           cps_api_object_attr_add_...(rollback_obj,
                                       attr_id,
                                        
                                       );

           /* Extract the attribute from the request object */
           cps_api_object_attr_t attr;

           attr = cps_api_object_attr_get(request_obj, attr_id);

           if (attr == CPS_API_ATTR_NULL)) {
               /* Failed to extract attribute
                  => Indicate error
               */
               result = cps_api_ret_code_ERR;
               continue;
           }

           /* Extract the value of the attribute in the request
              object
           */
           value = cps_api_object_attr_data_....(attr);

           /* Validate the requested attribute value, its
              consistency with other attributes and/or existing
              configuration, etc.
           */

       }

       /* If the whole request has been validated, do something with
          the extracted values   program hardware,
          take some action, etc.
       */
       break;

   case cps_api_oper_CREATE:
       /* CREATE operation requested */
       break;

   case cps_api_oper_DELETE:
       /* DELETE operation requested */
       break;

   case cps_api_oper_ACTION:
       /* ACTION operation requested */
       break;

   default:
       /* Invalid SET request type */
       break;
   }

   return (result);

}

/**********************************************************
Template CPS API object server rollback handler function
*******************************************************************/
cps_api_return_code_t xyz_rollback(
   void                         *context,
   cps_api_transaction_params_t *param,
   size_t                       index_of_element_being_updated
   )
{
   /* Extract object to be rolled back */
   cps_api_object_t rollback_obj;
   rollback_obj = cps_api_object_list_get(
                      param->prev,
                      index_of_element_being_updated
                      );

   if (rollback_obj == CPS_API_OBJECT_NULL) {
       /* Failed to extract rollback object
          => Indicate failure
       */

       return (cps_api_ret_code_ERR);

   }

   /* For each attribute to be rolled back,   */
   cps_api_object_it_t attr_iter;

   cps_api_object_it_begin(rollback_obj, &attr_iter);
   while (cps_api_object_it_valid(&attr_iter)) {

       /* Get the attribute id from the attribute iterator */
       cps_api_attr_id_t attr_id;

       attr_id = cps_api_object_attr_id(attr_iter.attr);
       /* Extract the attribute from the rollback object */

       cps_api_object_attr_t attr;

       attr = cps_api_object_attr_get(rollback_obj, attr_id);

       if (attr == CPS_API_ATTR_NULL)) {

           /* Failed to extract attribute
              => Indicate error
           */

           result = cps_api_ret_code_ERR;
           continue;

       }

       /* Extract the value of the attribute in the rollback
          object
       */
       value = cps_api_object_attr_data_....(attr);

       /* Apply attribute value */

   }

   return (result);
}

/******************************************************************
Template mainline function for a CPS API object server
This function registers with the CPS API service, and registers handler
functions to be invoked by the CPS API service when CPS API requests
are made for certain CPS API objects.
*******************************************************************/

cps_api_return_code_t init(void)
{      /* Obtain a handle for the CPS API service */

   cps_api_operation_handle_t cps_hdl;

   if (cps_api_operation_subsystem_init(&cps_hdl, 1) !=
           cps_api_ret_code_OK
      ) {

       /* Failed to obtain handle for CPS API service
          => Indicate an error
       */
       return (cps_api_ret_code_ERR);
   }

   /* Allocate a CPS API object registration structure */
   cps_api_registration_functions_t reg;

   /* Assign the key of the CPS API object to be registered */
   cps_api_key_init(&reg.key,  );

   /* Assign the handler functions to be invoked for this object */
   reg._read_function     = xyz_read;
   reg._write_function    = xyz_write;
   reg._rollback_function = xyz_rollback;

   /* Use obtained handle for CPS API service */
   reg.handle = cps_hdl;

   /* Perform the object registration */
   if (cps_api_register(&reg) != cps_api_ret_code_OK) {

       /* Failed to register handler function with CPS API service
          => Indicate an error
       */
       return (cps_api_ret_code_ERR);
   }

   /* All done */
   return (cps_api_ret_code_OK);
}
