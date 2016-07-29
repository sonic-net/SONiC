import   time import   cps
import   cps_utils


#  Define   the   get   callback   handler   function 
def   get_callback(methods,   params):

#  Append   an object   to   the   response,   echoing   back the   key
#  from   the   request,   and supplying   some   attributes


    params[ list ].append({ key :   params[ filter ][ key ],
                        data :   { attr_1 :    value_1 ,
                                    attr_n :    value_n 
                                 }
                      }
                     )

    return   True

#  Define   the   transaction   callback   handler   function
def   transaction_callback(methods,   params):
    if params[ operation ]   ==    set :
        #  Set   operation   requested
        #  Extract   the   attributes   from   the   request   object attr_1   =  params[ change ][ data ][ attr_1 ]
                                                 attr_n   =  params[ change ][ data ][ attr_n ]


        #  Do  something   with   them   -- program   hardware, 

        #  update   the   configuration,   etc.
        return   True
    if params[ operation ]   ==    create :
        return   True

    if params[ operation ]   ==    delete :
        return   True

    if params[ operation ]   ==    action :
        return   True
    
    return   False

# Obtain   a handle   to   the   CPS   API   service
    handle   =  cps.obj_init()

#  Register   the   above handlers   to   be run   when   a request   is received
#  for   the   given   key
cps.obj_register(handle, key,
                 {  get :   get_callback,
                    transaction :   transaction_callback
                 }
                )

#  Let   the   handlers   run
while   True:
    time.sleep(1000) 
