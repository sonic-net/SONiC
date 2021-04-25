# Code Coverage Rate in SONiC
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [Revision](#revision)
  * [About this Document](#about-this-document)
  * [Problem Definition](#problem-definition)
  * [Solution](#solution)
  * [1 Introductions](#1-introductions)
    * [1.1 What-is-GCOV](#11-what-is-gcov)
    * [1.2 Main workflow](#12-main-workflow)
      * [1.2.1 User space modules](#121-user-space-modules)
      * [1.2.2 kernel modules](#122-kernel-modules)
  * [2 Design](#2-Design)
    * [2.1 New Configuration Parameters](#21-new-configuration-parameters)
    * [2.2 Compile to gcov-versioned debian packet](#22-compile-to-gcov-versioned-debian-packet)
    * [2.3 Collect gcno files](#23-collect-gcno-files)
    * [2.4 Collect gcda files](#24-collect-gcda-files)
    * [2.5 Generation of gcov report](#25-generation-of-gcov-report)
    * [2.6 Check the coverage report](#26-check-the-coverage-report)
  * [3 Safety instruction](#3-safety-instruction)
  * [4 Coverage data for python script](#4-coverage-data-for-python-script)

# Revision

| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 0.1 |  16/4/2019  |   Zhengnan Cheng   | Initial version       |

# About this Document
This document provides the high level design for code coverage rate testing.

# Problem Definition
Code coverage rate is a term that describe the rate of the number of code lines has been executed divide by the number of total code lines in switch operating system. We reuse this term in SONiC code testing and create some related tools for SONiC code testing.

# Solution
Use the Gcov tools to measure the code coverage rate in its commercial switch and white box switch. Create the Linux scripts for Gcov compiling, Gcov data collect, and Gcov report generation for SONiC. A ENABLE\_GCOV compiling tag is provided for SONiC code project. And we integrate all these Gcov functions into Jenkins CICD system. Our solution is a complete tool set for code coverage rate for SONiC. 

# 1. Introductions

## 1.1 What-is-GCOV
Gcov is one of the commonly-used tools capable of testing code coverage. It is usually released together with GCC, used in analyzing programs to help create a more efficient and fast running program and discover the untested codes. Every developer can apply gcov as a profiling tool to optimize where your codes are defect by checking the two basic statistics collected from gcov reports:<br>
- What codes have been executed.<br>
- How many times a code line has been executed.<br>

## 1.2 Main workflow

### 1.2.1 User space modules
Twp basic compiling flag for gcov:
- -ftest-coverage: This option helps to generate the .gcno notes file sharing the same name with each source file. The .gcno file saves the information required by rebuilding the basic block graphs and the source line numbers of blocks.<br>
- -fprofile-arcs: This option helps to generate the .gcda count data files when a compiled program is running. Same as .gcno files, an individual .gcda file is generated for each source file. The gcda file saves the information about arc transition counts, value profile counts and some summary.<br>

![](figure1.png)<br>
__Figure 1.1: Additional options for gcc compiler__.<br>

Successful building will create additional .gcno files in company with the object files, as it can be seen from figure 1.2. 

![](figure3.png)<br>
__Figure 1.2 .gcno files__.<br>

The execution of modules built with gcov options can create the .gcda file in running environment. gcno files and gcda files can then be put together using gcov command to generate the required report
- gcov dfd\_debug.c --> dfd\_debug.c.gcov<br>

While a better option is to apply lcov tool to create a html-formed report. There are two main advantages to use lcov:<br>
- The html-based report provides a better user-friendly view. All coverage data can be access by a simple web browser.<br>
- For a large project, the coverage data would be huge and comprehensive. The lcov can generate a merged report which includes all submodules and their coverage data in three levels: the directory level, the file level and the source code level.<br>

![](figure4.png)<br>
__Figure 1.3 Coverage details for a source file__.<br>

### 1.2.2 kernel modules
For linux kernel version larger than 2.6.31, gcov-based compiling can be directly enabled by configuring the kernel with the following macros:<br>
```
CONFIG_GCOV_KERNEL=y
CONFIG_GCOV_PROFILE_ALL=y
CONFIG_GCOV_FORMAT_AUTODETECT=y
# CONFIG_GCOV_FORMAT_3_4 is not set
# CONFIG_GCOV_FORMAT_4_7 is not set
```

# 2. Design
In order that a SONiC image can be complied with gcov option and a corresponding gcov report can be generated as easily as possible, a script named gcov\_support.sh will be added. Currently this script will be added to sonic-swss repo to provide help for gcno and gcda files colletion and report generating in a very simple way as shown in figure 2.1.<br>

![](figure21.png)<br>
__Figure 2.1 Workflow to enable gcov in SONiC__.<br>

## 2.1 New Configuration Parameters
ENABLE_GCOV as a new configuration parameter is added to SONiC build system. The default value is "n". When a gcov building is required, this parameter should be set to "y"
```
#gcov compiling option
ENABLE_GCOV=n
export ENABLE_GCOV
```
This parameter will control whether a specify module should be compiled with gcov options introduced in 1.2.1

## 2.2 Compile to gcov-versioned debian packet
The configure script for swss package should be modified to merge gcov compiling options.
```
dnl if the user has specified any CFLAGS, override our settings
if test "$enable_gcov" = "yes"; then
    CFLAGS_COMMON+=" -fprofile-arcs -ftest-coverage"
    AC_SUBST(CFLAGS_COMMON)

    LDFLAGS+=" -fprofile-arcs"
    AC_SUBST(LDFLAGS)
fi
...
AC_ARG_ENABLE([gcov], AS_HELP_STRING([--enable-gcov], [enable coverage test]))
AS_IF([test "x${enable_gcov}" = "xyes" ], AC_MSG_RESULT([yes]), AC_MSG_RESULT([no]))
AM_CONDITIONAL([ENABLE_GCOV],[test "x${enable_gcov}" = "xyes"])
```

## 2.3 Collect gcno files
The keyword "collect" in gcov_support.sh which has been added to swss repo will be used to collect gcno files, and it will be excuted during the "install" stage of the debian package building:
- All script keywords usage:
```
root@5c5e8c570c0f:/tmp/swss_gcov/src/sonic-swss# ./gcov_support.sh
Usage:
 init                initialize gcov compiling environment
 collect             collect .gcno files
 collect_gcda        collect .gcda files
 generate            generate gcov report in html form (all or submodule_name)
 clean               reset environment
 tar_output          tar gcov_output forder
```
- Adjustment towards the debian building rules
```
override_dh_auto_install:
	dh_auto_install --destdir=debian/swss

	mkdir -p debian/swss/tmp/swss_gcov

	sh ./gcov_support.sh collect
```
After the "collect" operation, a compressed gcno.tar.gz is sent to /tmp/swss\_gcov inside the debian package.

## 2.4 Collect gcda files
gcov_support.sh is also sent to /tmp/swss\_gcov inside the debian package. After the regular tests to the swss module inside a device, the keyword "collect\_gcda" can be used to collect the generating gcda files, produce gcda.tar.gz and move it into /tmp/swss_gcov together with gcno.tar.gz

## 2.5 Generation of gcov report
gcno.tar.gz and gcda.tar.gz are the two basic files required to generate an accessible coverage report. The user can enter the /tmp/swss\_gcov inside the swss docker and run:
```
./gcov_support.sh generate all
```
to generate the overall gcov report for swss module

## 2.6 Check the coverage report
Figure 2.2 shows that the coverage reports will be saved under /tmp/swss\_gcov/src/sonic-swss directory.<br>

![](figure26.png)<br>
__Figure 2.2 Contents in gcov\_output__.<br>

The output includes:<br>
- info folder: save info files for all modules according to their generated paths<br>
- html folder: save gcov html report for all modules according to their generated paths<br>
- AllMergeReport: save the merged overall report which contains all coverage information<br>
- info\_err\_list:record the modules which failed to generate the info files<br>
- gcda\_dir\_list.txt:record the directories of all .gcda files<br>
The merged overall report can be checked from index.html under AllMergeReport dir by a web browser.<br>

![](figure27.png)<br>
__Figure 2.3 Contents of AllMergeReport__.<br>
![](figure28.png)<br>
__Figure 2.4 Overall coverage report__.<br>

# 3. Safety instruction
The gcov support for SONiC totally depends on the open-source tools -- gcov/lcov. Hence the modification towards the sonic project is only limited to the compiling options of gcc in order that the additional gcov-required files (.gcno and .gcda) can be generated during compiling. This modification will not have any influence on other sections of the compiling process.<br> 

- When a source file is compiled with the gcov compiling options, each executable line in this source file will be followed by a new-added piece of code wihch updates coverage statistics. Gcov realizes this process by adding stubs when generating assembly files. Each stub point will be inserted into 3 to 4 new assembly statements. These statements are directly added to the .s files. Then the assembly files can be assembled to the object files and the executable file. After doing this, when the executable file is running, the stubs added during compiling will collect the execution information. The statistical approach for these stubs is very simple, they are just variables in the memory and record the execution times for each code line. Therefore in the practical running environment, the performance impact brought by generating .gcda files can be ignored. The user can also hardly feel the difference.<br> 

# 4. Coverage data for python script
The coverage report for a python script can be generated in the running environment by applying a tool called coverage. The steps are listed below:<br>

- Install the coverage tool in the device under test:<br>
```
pip install coverage<br>
```
Run a python script with coverage tool instead of direct execution:<br>
```
coverage run -a /usr/local/bin/fancontrol.py start --> python fancontrol.py start<br>
```
Check the coverage result:<br>
```
coverage report<br>
```
Generate html-based report:<br>
```
coverage html<br>
```

![](figure41.png)<br>
__Figure 4.1 Coverage report for python script__.<br>
The analysis to the coverage data collection of python scripts is till in progress. The elimination of the user's awareness to the coverage tool is our next step.<br>

