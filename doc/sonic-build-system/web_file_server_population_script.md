# Web file server population script
&nbsp;
&nbsp;
## _Revision History_
                    
Date          | Description
----------- | -------------
3/9/22        | First draft


## _Table of Contents_

1. [Overview](#Overview)
    1. [In scope](#subparagraph1)
2. [Download web packages from external file storage](#paragraph1)
    1. [Work Items](#subparagraph1)
3. [Upload web packages to trusted file storage](#paragraph2)
    1. [Work Items](#subparagraph1)
4. [User Input](#paragraph3)
5. [Script outputs](#paragraph4)
6. [Build flow integration](#paragraph5)
7. [Source tree location](#paragraph6)
8. [Q&A](#paragraph7)



## Overview
The SONiC reproducible build framework provides a way to lock the versions of external packages. It will lock the versions for all the docker images including the slave docker images, host images, and docker slave containers which are used to build the SONiC targets, such as deb files, python wheels, etc.
SONiC reproducible build allows to identify specific version of a web package retrieved by wget/curl and download it from an external file storage. 
The web site may be not stable, and the web packages may be replaced to another one unexpectedly, so we do not want to depend on the web packages at a remote web site. 
Before a web package is used in the SONiC repository, the package should be uploaded to a trusted file storage. Currently SONiC offers to do that manually or automatically via Jenkins pipeline.
The file Server population script is a complementary utility for “SONiC reproducible build” and suppose to ease the process of downloading the web packages from an external file storage and uploading them to trusted file storage.
The script will be triggered manually or part of the build flow (part of “make freeze”) whenever the developer intend to populate the web server which packages associated to specific tag. 

### In scope:
- Download web packages from external file storage
- Rename and upload web packages to trusted file storage
- Script output

## Download web packages from external file storage
The script will identify all relevant web packages, collect their hash value and url and then download them from the remote site to a local cache.
The script search over the source tree path recursively and look for ‘version-web’ files.
Those file are being parsed in order to retrieve the path to the package and its hash value. The script is expecting for such format:
[package url]==[hash value]

```sh
For example:
https://storage.googleapis.com/golang/go1.14.2.linux-amd64.tar.gz==ebef065e4d35572af5b03e2be957a9c6c5063b38
```

### Work Items:
- Identify relevant versions-web files
- Parse versions-web files and identify relevant web packages
- Download web packages from their external file storage


## Upload web packages to trusted file storage

Although there is no version for a package downloaded by wget/curl, the hash value of the package file can be used as the version value. 
The script would rename the Web package and then upload it from cache to a trusted file server. The file name format in the file storage is as below:
[original file name]-[hash value]
```sh
For an example: 
go1.14.2.linux-amd64.tar.gz-ebef065e4d35572af5b03e2be957a9c6c5063b38
```
For the same web package, it supports to have multiple versions of the file in the file storage
for example:
```sh
For an example: 
go1.14.2.linux-amd64.tar.gz-ebef065e4d35572af5b03e2be957a9c6c5063b38
go1.14.2.linux-amd64.tar.gz-b73d6366c0bce441d20138c150e2ddcdf406e654
```
Same file name is used with different hash 

### Work Items:
- Rename web package
- Upload web package to trusted file storage
- Generate output version file (optional)

## User Input:
The user would provide the script the following parameters:

| Name        	| Description                                                                                                	| Tag          	| Type    	| Default value                      	|
|-------------	|------------------------------------------------------------------------------------------------------------	|--------------	|---------	|------------------------------------	|
| source      	| Search path for source tree where to  look for<br> compilation artifacts (version files)                   	| -s, --source 	| String  	| CWD<br>(current working directory) 	|
| cache       	| Path for temporary storage where to download Web Packages                                                  	| -c, --cache  	| String  	| CWD/tmp                            	|
| output      	| Output file name to hold the list of packages.<br> The file will be created in the format of version files 	| -o, --output 	| String  	| none                               	|
| print       	| Print level verbosity                                                                                      	| -p, --print  	| integer 	| 1 (info level)                     	|
| user        	| User for trusted server authentication                                                                     	| -u, --user   	| String  	| none                               	|
| key         	| key server authentication                                                                                  	| -k, --key    	| String  	| none                               	|
| Destination 	| URL for destination web file server                                                                        	| -d, --dest   	| String  	| none                               	|


## Script outputs:

The script would print out to STDOUT its current download progress (progress bar) and error messages in case of errors.
The script can produce a list of packages that were uploaded in a format of version file.
The script would return 0 in case of success and an errors code (see table below) in case of failure.
### Error codes:

Code         | Description					        | Comments
------------ | -------------------------------------| -------------
 0		     | Success						        |
-1		     | Cannot write to cache                |
-2		     | Cannot access trusted server         |
-3		     | Cannot authenticate trusted server   |


## Build flow integration:
Script will be integrated into SONiC build environment as part of “make freeze” where invocation of the script is optional. User may choose to call script by defining following environment variables:

```sh
export SONIC_REPRODUCABLE_BUILD_UPLAOD_ENABLE=1
export SONIC_REPRODUCABLE_BUILD_UPLAOD_USER=<User for trusted server authentication>
export SONIC_REPRODUCABLE_BUILD_UPLAOD_KEY=<API key server authentication>
export SONIC_REPRODUCABLE_BUILD_UPLAOD_DEST=< URL for destination web file server>
```

Another approach is to call the script manually and provide as an input the pat where the script would search for version files (version files which were generated as part of "make freeze" invocation or by previous invocation of the script).

## Source tree location:
 
 The script will be located under
sonic-buildimage/scripts/populate_file_web_server.py

## Q&A
Who should run this script?
When should user run this script?

