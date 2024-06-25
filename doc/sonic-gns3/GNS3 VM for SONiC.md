# SONiC on GNS3 VM 

GNS3 is an environment that allows simulation of networking equipment in realistic scenarios. It can be used to emulate, configure, test, and troubleshoot networks in a simulated environment. GNS3 allows you to run a small network topology
consisting of only a few devices on your Windows 10 laptop, or larger network topologies using a GNS Server that is installed on an Ubuntu Linux server. You can use the GNS3 simulator to create a virtual environment to emulate various networks. See [GNS3 online documentation](https://docs.gns3.com/) and [Getting started](https://docs.gns3.com/docs/) with GNS3 for complete information.
Use GNS3 to run SONiC simulator VMs. GNS3 consists of the following components:

### For Windows Environment

GNS3 user interface — Used to create and visualize network connections for the Windows environment.

### For Client Server Model

GNS3 client — Used to create and visualize complex network connections for the Windows environment. 
GNS3 server — Controls SONiC VM execution (natively supported on Ubuntu Linux running on a Dell server)
	
### GNS3 VM installation overview

1. Install GNS3 on a windows environment using [GNS3 VM installation guide](https://docs.gns3.com/docs/getting-started/installation/windows/#:~:text=The%20following%20are%20the%20optimal%20requirements%20for%20a,%2F%20RVI%20Series%20or%20Intel%20VT-X%20%2F%20EPT).
2. Download the SONiC image from the [azure pipeline](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/142/builds?branchName=master) to the windows environment.
3. Import the SONiC image the GNS3 VM environment.
4. Build your SONiC topology virtual devices.
5. Log in and configure each device.


### SONiC image download

1. Goto azure pipeline under [master branch](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/142/builds?branchName=master) 
2. Select the latest successful build by clicking the Artifacts.

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image12.jpg)

3. Under artifacts, click on sonic-buildimage.vs

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image13.jpg)

4. Now, download the sonic image with the name target/sonic-vs.img.gz

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image14.jpg)

5. Extract sonic-vs-img.gz to a folder in your windows environment. Example: d:\sonic-vs.img

### GNS3 VM set up

Once the GNS3 VM is installed and application is opened. We see a window as shown below,

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image1.jpg)


In the GNS3 window, create a project.

a. Select File->New blank project.
b. Name: Enter a new project name.
c. Location: The default projects folder name changes to the new project name.
d. Click OK.

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image2.jpg)

The project window opens. The window title displays the name of the new project.

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image3.jpg)

Install an SONiC image for GNS3 appliance file.
	- Go to [SONiC pipeline](https://sonic-build.azurewebsites.net/ui/sonic/pipelines) and select the version of the SONiC image that you want to use.
	- Select an SONiC build image zip file and click Download. The zip file contains an SONiC image file.
	- On the windows environment, extract the SONiC image file.
	
In the GNS3 project window, Click on New template on the left corner of the screen
Select the option "Manually createa new template"

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image4.jpg)

Under the new tab, select Qemu VM and then select a new template as shown below. Key in the desired type of device and its RAM details as recommended. 

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image5.jpg)

Now, we should be able to find a new device on the left side panel to configure our device template. 
	- In the QEMU VM template configuration window, under the General Settings tab, change the RAM size to 8192 MB (8GB) and the vCPU number to 4.
	- Select Auto Start Console to automatically open the console when the Community SONiC appliances start.
	- Click OK to save the changes.

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image6.jpg)

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image7.jpg)

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image11.jpg)

### Build your network topology

In the GNS3 project window, click the Browse Routers icon on the left side bar. Drag and drop CommunitySONiC devices in the middle project frame as required for your network topology. Place each device in the appropriate location on the screen. To rename a switch, click its icon and overwrite the text

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image8.jpg)

Connect the Community SONiC switches. Select the "Add a link" icon on the left side bar. Click a switch in the project frame and select an available port in the drop-down list.

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image9.jpg)

Drag the connection line to another switch, click the switch icon, and select a port from the drop-down list to establish the link.

![](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-gns3/image10.jpg)

Repeat this step to connect each Community SONiC devices. 

Configure the Management IP address on each Community SONiC switch. Start each Community SONiC switch by right-clicking the icon and selecting Start. The connections from the switch to other devices in the project frame turn from red to green and the console window opens.

In the console window of each Enterprise SONiC switch, log in by entering the default username admin and the default password YourPaSsWoRd.

Access Configuration mode in the Community SONiC command-line interface to configure each switch. See the Community [SONiC User Guide](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC-User-Manual.md) for configuration information and procedures.
