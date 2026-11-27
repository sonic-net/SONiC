#!/usr/bin/env python3

import subprocess
import os
import pprint
import json
import time
from datetime import datetime
import argparse

#
# List of repros
#
repros = [
    "SONiC",          "sonic-host-services",  "sonic-mgmt-framework",    "sonic-quagga",     "sonic-swss",         "sonic-ztp",
    "sonic-dbsyncd",  "sonic-linux-kernel",   "sonic-platform-common",   "sonic-restapi",    "sonic-swss-common",  "sonic-buildimage",
    "sonic-fips",     "sonic-mgmt",           "sonic-platform-daemons",  "sonic-sairedis",   "sonic-telemetry",
    "sonic-frr",      "sonic-mgmt-common",    "sonic-py-swsssdk",        "sonic-snmpagent",  "sonic-utilities"
]

#repros = ["sonic-buildimage" ]

#
# Util function: debugprint
#
debug = False

def debugprint(str):
    global debug
    if debug:
        print(str
        )
#
# Per company commit counts, companys for per repro counts, gcompanys for all repro's counts
#
companys={}
gcompanys={}
def update_company_commit_counts(comp, count =1):
    global companys
    global gcompanys

    # Per company per repor

    if comp in companys:
        companys[comp] = companys[comp] +count
    else:
        companys[comp] = count

    # Total per repro        
    if "Total" in companys:
        companys["Total"] = companys["Total"] +count
    else:
        companys["Total"] = count

    # Per company all repro        
    if comp in gcompanys:
        gcompanys[comp] = gcompanys[comp] +count
    else:
        gcompanys[comp] = count

    # Total all repro                
    if "Total" in gcompanys:
        gcompanys["Total"] = gcompanys["Total"] +count
    else:
        gcompanys["Total"] = count        

#
# github id to company mapping
#
id2company={}
def is_entry_in_id2company(id):
    global id2company
    if id in id2company:
        return True, id2company[id]
    return False, ""

def add_entry_to_id2company(id, comp):
    global id2company
    id2company[id] = comp

#
# Util function for sleep
#
def wait_for(t):
    time.sleep(t)

#
# Util function for github RESTFUL query with retry.   github RESTFUL has rate limit on usage
# url : query url,
# t   : sleep duration for retry
#
gtoken=""
lookup_count = 0
def lookup_with_retry(url, t=2):
    lookupid = True
    response = {}
    global lookup_count
    global gtoken
    lookup_count = lookup_count + 1
    header = ""
    if gtoken!="":
        header = "--header \"Authorization: Bearer {}\"".format(gtoken)
        
    cmd = "curl -s --request GET --url {} {}".format(url, header)
    while lookupid:
        output = subprocess.check_output(cmd, shell=True)
        try:
            response = json.loads(output.decode('utf-8'))
            if "message" in response and  "API rate limit exceeded" in response["message"]:
                # Retry due to API rate limit
                wait_for(t)
                dt = datetime.now()
                debugprint("{} Sleep and retry for  {}".format(dt, cmd))
            else:
                lookupid = False
        except:
            lookupid = False
            print("{} : {}".format(cmd, output))
    return response

#
# Util function: get company info via github id. If it fails, try its committer email address
#
def get_company_from_id(id, email):

    # Use github id to find out company name from profile
    url = "https://api.github.com/users/{}".format(id)
    response = lookup_with_retry(url)

    #
    # NOTFOUND: default failure reason, profile is found, but no company info is set in profile
    #
    src = "NOTFOUND_COMPANYINFO"
    if  "message" in response and  "Not Found" in response["message"]:
        #
        # NOTFOUND: Can't find profile for a given id
        #
        src = "NOTFOUND_PROFILE"
        
    if "company" in response:
        comp = response["company"]
        if comp == None:
            if id not in email or "noreply.github.com" not in email:
                #
                # NOTFOUND: User sets company  as None in profile
                #            
                ret, comp = use_email_to_find_company(email, "NOTFOUND_COMPANYISNONE")
            else:
                comp = "NOTFOUND_COMPANYISNONE"

        comp = fixup_companyname(comp)
    else:
        ret, comp = use_email_to_find_company(email, src)

    return comp

#
# Company name mapping
#
def company_name_check(key):
    key = key.lower()
    if "azure" in key:
        return True, "MICROSOFT"    
    if "microsoft" in key:
        return True, "MICROSOFT"
    if "nephosinc" in key:
        return True, "NEPHOSINC"
    if "intel" in key:
        return True, "INTEL"
    if "edge-core" in key:
        return True, "EDGE-CORE"
    if "metaswitch" in key:
        return True, "METASWITCH"
    if "google" in key:
        return True, "GOOGLE"
    if "alibaba" in key:
        return True, "ALIBABA"
    if "mellanox" in key:
        return True, "NVIDIA"
    if "arista" in key:
        return True, "ARISTA"
    if "dell" in key:
        return True, "DELL"
    if "linkedin" in key:
        return True, "LINKEDIN"
    if "broadcom" in key:
        return True, "BROADCOM"    
    if "accton" in key:
        return True, "ACCTON"
    if "thebollingers" in key:
        return True, "THEBOLLINGERS"
    if "cisco" in key:
        return True, "CISCO"
    if "nvidia" in key:
        return True, "NVIDIA"
    if "nokia" in key:
        return True, "NOKIA"
    if "barefootnetworks" in key:
        return True, "INTEL"
    if "innovium" in key:
        return True, "INNOVIUM"
    if "cavium" in key:
        return True, "CAVIUM"
    
    return False, ""

#
# Util: open a file and get a list of githubid， then check thislist github_id's company
#
def check_ids_to_company(filename):
    ids = []
    with open(filename) as file:
        ids= [line.rstrip() for line in file]
    for id in ids:
        comp =  get_company_from_id(id, "")
        if "NOTFOUND" in comp:
            print("{} :{}".format(id, comp))
        
    
    
#
# Util Function: Use committer's email to find his company name
#
def use_email_to_find_company(email, special_return=""):

    #
    # Step 1: check if email has some keyword for easy identify
    #
    ret, comp = company_name_check(email)
    if ret:
        return True, comp
    
    if "noreply.github.com" in email:
        s = email.split("@")
        gid = s[0]
        # use empty string for email to avoid endless loop
        comp = get_company_from_id(gid, "")
        return True, comp
    
    if special_return != "":
        return False, special_return.upper()

    # should not reach here
    return False, "NONE"

#
# Fix up company name
#
def fixup_companyname(comp):
    comp = comp.replace("@", "")
    comp = comp.upper()
    c = comp.split()
    comp = c[0]
    comp = comp.replace(",", "")
    ret, fix= company_name_check(comp)
    if ret:
        comp = fix
    return comp

#
# Fix up commiter's name, no space, no (), no "
#
def fixup_name(name):
    name = name.strip()
    name = name.replace(" ", "+")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace("'", "")        
    return name
    
#
# Pull workspace
#
def pull_repros():
    for repro in repros:
        cmd = "git clone https://github.com/sonic-net/{}".format(repro)
        subprocess.check_output(cmd, shell=True)


#
# Use git shortlog to count company commit contributions
#        
def count_repro_commits_via_short_log(repro, years):

    # Step 1: use git shortlog  to collect commit count, name and email
    os.chdir(repro)
    output = subprocess.check_output("git shortlog --since=\"{} years ago\" -sne".format(years), shell=True)
    infoarray = output.decode('utf-8').splitlines()
    count = 0
    cct = 0
    for info in infoarray:
        count = count + 1
        s = info.split("\t")

        # commit count
        ccount = int(s[0])
        cct = cct+ ccount
        
        # commiter name
        nearray = s[1].split("<")
        name = fixup_name(nearray[0])

        #email
        email = nearray[1].replace(">","")
        
        # Check if there is a cached info for githubid to company mapping entry
        ret, comp = is_entry_in_id2company(name)
        if ret:
        #if ret and "NOTFOUND_" not in comp:
            # Found cached info, no need to trigger lookup
            update_company_commit_counts(comp, ccount)
        else:
            # Step 2: Check email first for easy cases
            ret, comp = company_name_check(email)
            if not ret:
                # Step 3: use name to find githubid,then use github id to find profile.
                # Try to get company information from profile
                url = "https://api.github.com/search/users?q={}".format(name)
                response = lookup_with_retry(url)

                if "items" in response and len(response["items"])>0:
                    items=response["items"]
                    # TODO assume first item for now
                    id = items[0]["login"]
                    comp =  get_company_from_id(id, email)
                else:
                    ret, comp = use_email_to_find_company(email, "NOTFOUND_ID")

            # Update github id to company mapping db
            add_entry_to_id2company(name, comp)
            update_company_commit_counts(comp, ccount)                    
        debugprint("{} : {} : {} : {}".format(name, ccount, comp, email))

    os.chdir("..")
    debugprint("CCT: {}".format(cct))

#
# Util function for sorting json 
#
def get_sortest_key(a: dict, o: dict):
    v = None
    k = None
    for key, value in a.items():
        if v is None:
            v = value
            k = key
            continue
        if v < value:
            v = value
            k = key
    o.update({k: v})
    a.pop(k)
    if a:
        get_sortest_key(a, o)
    else:
        return

#
# Main entry
#
def main():

    #
    # Global variables
    #
    global id2company
    global companys
    global debug

    #
    # parser flags
    #
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true",
                        help="set debug flag")
    parser.add_argument("--check_ids", action="store_true",
                        help="check github id to company")
    parser.add_argument("--idfile", type=str, help="github id file", default="")    
    parser.add_argument("--pull_workspace", action="store_true",
                        help="pull workspace")
    parser.add_argument('--years', type=int, help="the number of years since now")
    parser.add_argument("--token", type=str, help="github access token", default="")
    args = parser.parse_args()

    debug = args.debug

    #
    # Pull workspace only
    #
    if args.pull_workspace:
         pull_repros()
         return
     
    #
    # Set up gtoken
    #
    if args.token != "":
        global gtoken
        gtoken = args.token
        
    print("Debug flag {}".format(debug))

    #
    # Check id to company via profile
    #
    if args.check_ids and args.idfile != "":
        check_ids_to_company(args.idfile)
        return
    
    #
    # Total is used to store all repro's commit info
    #
    total = {}

    #
    # github to company mapping
    #
    id2company={}

    #
    # Set up pp
    #
    pp = pprint.PrettyPrinter(width=41, compact=True)

    #
    # Read cached github id to company mapping if it is available
    #
    idfname = "/tmp/id2comp.json"
    if os.path.isfile(idfname):
        with open(idfname, 'r') as openfile:
            # Reading from json file
            try:
                id2company = json.load(openfile)
                debugprint("Read back id2commpany")
            except:
                id2company={}

    num_repro = 0
    years = 5
    #
    # loop through all repros
    #
    for repro in repros:
        num_repro = num_repro +1
        companys={}

        #
        # Collect commit info from each repro
        #
        count_repro_commits_via_short_log(repro, years)

        #
        # Print out sorted info for each repro if company is not empty for that repro, a.k.a there
        # are some commits 
        #
        if len(companys) > 0 :
            print("Sorted commit counts by companys for repro {}".format(repro))
            outcome = {}
            get_sortest_key(companys, outcome)
            print("{} Counters for {} ".format(num_repro, repro))
            print(outcome)
            total[repro] = outcome

        #
        # write back for caching purpose
        #
        debugprint("Write back id2commpany")
        with open(idfname, "w") as outfile:
            json.dump(id2company, outfile)

    #
    # Analyze
    #
    print("Counters for All {} repros".format(num_repro))
    if len(gcompanys)>0:
        outcome = {}
        get_sortest_key(gcompanys, outcome)
        print(outcome)

    #
    # write back company commit counts, per repro and all repro
    #
    compfname = "/tmp/comp_commits.json"
    debugprint("Write back counnt counts per company")
    with open(compfname, "w") as outfile:
        json.dump(total, outfile)     

    #
    # debug github restful lookup count
    #
    global lookup_count
    debugprint ("Lookup {}".format(lookup_count))
        
if __name__ == "__main__":
    main()
