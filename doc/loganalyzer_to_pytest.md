#### Requirements
Move existed loganalyzer to be supported by pytest framework.

#### Overview
At this approach all the work will be done on the Ansible host in comparing with current implementation, so script will download extracted syslog file to the Ansible host.
Functionality will give possibility to:
- Add start marker to the DUT syslog. Start Marker will be automatically generated based on the prefix + date. Start marker format will be kept the same as in current implementation
- Configure regular expressions which will be used to found matches in the syslog logs
- Extract DUT syslog based on the markers. Download extracted logs to the Ansible host
- Perform analysis of downloaded syslog and return the result

Current loganalyzer implementation description:
https://github.com/Azure/SONiC/wiki/LogAnalyzer

#### Development
Module "loganalyzer.py" with class "Loganalyzer".

"Loganalyzer" class interface:
- __init__(ansible_host: ansible_host, marker_prefix, dut_run_dir="/tmp")
- load_common_config() - Clear previous configured match, expect and ignore. Load regular expressions from common configuration files: match, expect and ignore which are located in some configuration directory or with current module. Save loaded configuration to the self.match_regex, self.expect_regex and self.ignore_regex attributes.
- parse_regexp_file(file_path) - Read and parse regular expressions from specified file. Return list of strings of defined regular expressions.
- run_cmd(callback, *args, **kwargs) - Call function and analyze DUT syslog during function execution. Return the same result as "analyze" function.
- init() - Add start marker to the DUT syslog. Generated marker format: marker_prefix + "%Y-%m-%d-%H:%M:%S"
- analyze() - Extract syslog based on the start marker and copy it to ansible host. Analyze extracted syslog file localy. Return python dictionary object.
Return example:
{"counters": {"match": 1, "expected_match": 0, "expected_missing_match": 0},
 "match_files": {"/tmp/syslog": {"match": 0, "expected_match": 32},
					"/tmp/syslog1": {"match": 0, "expected_match": 15}
						},
 "match_messages": {"/tmp/syslog1": ["Message 1", "Message 2", "Message n"],
						 "/tmp/syslog2": ["Message 1", "Message 2", "Message n"]
						 }
}
- save_full_log(dest) - Download extracted DUT syslog (/tmp/syslog) to the Ansible host folder specified in 'dest' input parameter.

Attributes:
- match_regex - list of regular expression strings to match
- expect_regex - list of regular expression strings to expect
- ignore_regex - list of regular expression strings to ignore

Usage example of loganalyzer functionality just to show how to use loganalyzer interface.

```
def some_function(x, y=10, z=0):
    return x + y

def test_loganalyzer_functionality(localhost, ansible_adhoc, testbed):
    """
    @summary: Example of loganalyzer usage
    """

    hostname = testbed['dut']
    ans_host = ansible_host(ansible_adhoc, hostname)

    log = LogAnalyzer(ansible_host=ans_host, marker_prefix="test_loganalyzer")

    # Read existed common regular expressions located with legacy loganalyzer module
    log.load_common_config()

    # Add start marker to the DUT syslog
    log.init()

    # Emulate that new error messages appears in the syslog
    time.sleep(1)
    ans_host.command("echo '---------- ERR: error text --------------' >> /var/log/syslog")
    ans_host.command("echo '---------- Kernel Error: error text --------------' >> /var/log/syslog")
    time.sleep(2)
    ans_host.command("echo '---------- Interface Error: error text --------------' >> /var/log/syslog")

    # Perform syslog analysis based on added messages
    result = log.analyze()
    if not result:
        pytest.fail("Log analyzer failed.")
    assert result["total"]["match"] == 2, "Found errors: {}".format(result)

    # Download extracted syslog file from DUT to the local host
    res_save_log = log.save_extracted_log(dest=os.getcwd() + "/../log/syslog")

    # Example: update previously configured marker
    # Now start marker will have new prefix
    log.update_marker_prefix("log")

    # Execute function and analyze logs during function execution
    # Return tuple of (FUNCTION_RESULT, LOGANALYZER_RESULT)
    run_cmd_result = log.run_cmd(some_function, 5, y=5, z=11)

    # Clear current regexp match list
    log.match_regex = []

    # Load regular expressions from the specified file
    reg_exp = log.parse_regexp_file(src=COMMON_MATCH)

    # Extend existed match regular expresiions with previously read
    log.match_regex.extend(reg_exp)

    # Verify that new regular expressions are found by log analyzer
    log.init()
    ans_host.command("echo '---------- Kernel Error: error text --------------' >> /var/log/syslog")
    result = log.analyze()
    if not result:
        pytest.fail("Log analyzer failed.")
    assert result["total"]["match"] == 1, "Found errors: {}".format(result)
```
