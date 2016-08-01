import   cps

handle   =  cps.event_connect()

cps.event_register(handle,   cps.key_from_name('observed','base-port/interface'))
while   True:
    obj  =  cps.event_wait(handle)
    print   obj
