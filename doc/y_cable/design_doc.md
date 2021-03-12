## Multiple y cable vendor API design

### Overview

This document summarizes the approach taken to accommodate multiple
Y cable vendors for supporting dual-ToR configurations in SONiC.
All the design choices are presented
such that vendors can implement the Y cable interface with ease and effeciency
and all the feature requirements are met.


Challenge: to provide an interface for Y cable to interact with PMON docker and HOST
           which can be uniform across all vendors.

### Directory Structure

#### Background

- We need to have an appropriate place where vendors can implement their modules/packages and provide Sonic with an abstraction layer where pmon and host can access the Y cable packages of all the vendors with ease
   
  - Currently the assumption is Y cable package implementation would be in python itself
  - If a vendor provides shared library, that scenario would be considered accordingly
  - Since sonic_y_cable (sonic-platform-common/sonic_y_cable) is already built as a package today (only for a single Y cable vendor with sonic-buildimage) vendors can also build packages along similar lines.

#### Proposed Solution

- Vendors can place their implementations in this format

```
	Sonic_platform_common/sonic_y_cable/<vendor>/y_cable.py
```
- For sxample

```
	Sonic_platform_common/sonic_y_cable/credo/y_cable.py
```
#### Rationale
- The requirement here would be that the vendors must create their packages such that It can easily be accessed/imported and the packages also adhere to a uniform convention

  - Vendor name should be derivable from the vendor name field inside the register spec of transceiver type.
  - This is essential so that host/pmon can determine the vendor name from eeprom and import the module of the transceiver appropriately

### Vendor to Module mapping

#### Background

- We need to have a vendor to Y cable module mappings defined and accessible somewhere for pmon/cli to import
   
  - Before calling any Y cable API, how do we know which type/vendor does the Y cable belong to ? 
  - Also lets suppose once the type/vendor of the cable is known from where does pmon or cli import the module ?
  - Since there can be many specs which vendors follow (8636, 8624 etc.) for transceivers it is important to have a solution which meets all requirements so that the API access is available to whoever wants to invoke it.
  - another issue is how do we support the multiple vendors modules/packages which could be used by both sonic pmon docker as well as the sonic cli (sonic-utilities). Basically the package should be available both in host and container.
#### Proposed Solution

- We define a file which would contain vendor to module mapping and put it in a place which is accessible to both pmon and host
- The vendor to module mapping can be present in a file which could be present in

```
	/usr/share/sonic/y_cable/y_cable_vendor_mapping.csv
```
or 

```
	/usr/share/sonic/y_cable/y_cable_vendor_mapping.yaml
```
- Mapping could be such that 
```
	<vendor_name>,<package_name>,<module>
```
- For example
```
	Credo,credo,y_cable
```

#### Rationale

  - This is because both the container and host can easily access this path. And it would be easy to mount this on container (pmon) as applicable. 
  - Also since python has built in support for both csv and yaml parsing, it would be convenient to retrieve the mappings.

#### Implementation details
- Once the xcvrd will start (daemon launched) it will know the Vendor name from the register specification and then it can appropriately read and parse the vendor name from the spec. Once it has this information it can then using this file Load/import the appropriate module.

### Port to module mapping
- Another thing that is required is once we do have a vendor to module mapping, we need to map appropriate port to a module as well

#### Background

  - Basically, the key idea is once we have a port identified as being of a certain vendor and it has been identified to load a certain module which we can gather from the mapping described above we still need to call the correct module on each port each time we call the API on the port 
  - want to maintain this mapping in memory since xcvrd does not want to read/parse this y_cable_vendor_mapping.csv file again and again each time we call the y cable API 
  - Also note that the module loaded might change during xcvrd running lifetime since cable can be changed from one vendor to another. So we need to take this into consideration as well

#### Proposed Solution

  - Each module of the Y cable vendor can be a class (of each transceiver type) and all we need to do is instantiate the objects of these classes as class instances and these objects will provide the interface of calling the API's for the appropriate vendor Y cable.
  - This instantiation will be done inside xcvrd, when xcvrd starts
  - These objects basically emulate Y cable instances and whatever action/interaction needs to be done with the Ycable the methods of these objects would provide that
  - each vendor in their implementation can inherit from a base class where there will be definitions for all the supported capabilities of the y cable.
  - If the vendor does not support or implement the utility, it will just raise a not implemented error from the base class itself

For example a typical module of the vendor can be like this
```
        
	class Ycable(Ycablebase):
            #all vendor modules inherit from Ycablebase
	    def __init__(self):
		
	    def toggle_mux_to_torA(self, port):
		#implement or raise exception if not implemented
		raise NotImplementedError
	    def toggle_mux_to_torB(self, port):
		#implement or raise exception if not implemented
		raise NotImplementedError

	    def check_prbs(self, port):
		#implement or raise exception if not implemented
		raise NotImplementedError

	    def only_credo(self, port):
		raise NotImplementedError

	    def only_amphenol(self, port):
		raise NotImplementedError
	
```
the base class would be like this 

```   
	class Ycablebase(object):
	    def __init__(self, port):
		self.port = port
		
	    def toggle_mux_to_torA(self, port):
		raise NotImplementedError
	    def toggle_mux_to_torB(self, port):
		raise NotImplementedError

	    def check_prbs(self, port):
		raise NotImplementedError

	    def only_credo(self, port):
		raise NotImplementedError

	    def only_amphenol(self, port):
		raise NotImplementedError

```

#### Implementation details
- Now for xcvrd to use this solution, all it has to do is instantiate the class objects defined by importing the appropriate module. This should happen when xcvrd starts or if there is a change event  (xcvrd inserted/removed)

```
	from credo import y_cable
	y_cable_port_Ethernet0 = Ycable(port)



	# and to use the Y cable APIS 
	try:
	    y_cable_port_etherne0.toggle_mux_to_torA()
	except:
	    helper_logger.log(not able to toggle_mux_to_torA)
```
#### Rationale

  - xcvrd can maintain a dict of these objects an whenever it needs to call the API for the correct port (in this case physical port) it can easily achieve so by indexing into the instance of the physical port and calling the class object.  

```

	Y_cable_ports_instances = {}  
	  
	# appending instances in the dictionary  
	Y_cable_ports_instances[physical_port] = Ycable(port)

	# and to use the Y cable APIS 
	try:
	    Y_cable_ports_instances[physical_port].toggle_mux_to_torA()
	except:
	    helper_logger.log(not able to toggle_mux_to_torA)
```


### How does cli interact with Y cable api's
- Another thing that is required is once we do have a vendor to module mapping, we need to map appropriate port to a module as well

#### Background

  - Another requirement we have is Cli also requires to interact with the Ycable directly. This basically implies that all  Ycable vendor packages needs to be imported inside sonic-utilities/host as well 
  - This would come in the form of commands like setting PRBS, enabling disabling loopback and also get the BER info and EYE info etc 
  - Also commands such as config/show hwmode is important which gives the cli ability to toggle the mux without going into sonic modules like mux-mgr or orchagent.
  - All these require access to Y cable APIs to be directly called by the cli. But then again same problems arrive, how do we know which type/vendor does the cable/port belong to, how to load the appropriate module etc 

#### Proposed Solution(s)

  - One way is since CLI lives in the host, we can choose to do everything on xcvrd lines. Meaning once there is port number, convert to a physical port and look into vendor to module mapping file and then load the module and execute the API
  - Another way is cli can interact with pmon thorugh redis-db. Basically we can define a schema table for different operations which need to be performed on the y cable. 

```
	HW_MUX_OPERATION_TABLE|Ethernet0
	state active/standby
	enable_prbs true/false
	check_mux_direction true/false
```
  - In xcvrd we can have a thread running and listening to these events and execute the APIs since all the ports already have the correct mapping of the module (maintained in the form of a dictionary). The response of the API can be again written back to the redis table and absorbed by the CLI
 
### Concurrency for Y cables API 

#### Background

  - Since some vendors need to execute two or three transactions in a single API it is imperative to have a solution where we can protect the Y cable APIs for concurrent behavior 

#### Proposed Solution(s)

  - We might need to pass a semaphore or lock to the API to protect reexecuting or executing some other API in the meantime.
  - For now we insist on vendors to acquire/release locks in the API/implementation itself. So that if there is any possibility of concurrency the locking mechanism inside the the API prevents that from happening

 
### Storing the state within a Y cable Module 

#### Background

  - Another requirement in future that could arise is what if we need a feature which requires vendors to store a state with the Y cable. In this regard it is important to address this requirement in the initial design itself. (example port to bus mapping) 

#### Proposed Solution(s)

  - Since the vendor has class definitions associated with Y cable module, it can have attributes which store the information. However, it still needs to be decided how these attributes will be instantiated/configured. Whether this onus will be on xcvrd/daemon or whether it can be done within the module itself. 

