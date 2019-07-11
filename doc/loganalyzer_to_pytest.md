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
- __init__(ansible_host: ansible_host, run_dir="/tmp")
- load_common_config() - Clear previous configured match, expect and ignore. Load regular expressions from common configuration files: match, expect and ignore which are located in some configuration directory or with current module. Save loaded configuration to the self.match_regex, self.expect_regex and self.ignore_regex attributes.
- parse_regexp_file(file_path) - Read and parse regular expressions from specified file. Return list of strings of defined regular expressions.
- run_cmd(callable, *args, **kwargs) - Call function and analyze DUT syslog during function execution. Return the same result as "analyze" function.
- init(marker_prefix: string) - Add start marker to the DUT syslog. Generated marker format: marker_prefix + "%Y-%m-%d-%H:%M:%S"
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
- save_full_log(dest_path) - Download extracted DUT syslog (/tmp/syslog) to the Ansible host folder specified in 'dest_path' input parameter.

Attributes:
- match_regex - list of regular expression strings to match
- expect_regex - list of regular expression strings to expect
- ignore_regex - list of regular expression strings to ignore

Usage example:

	from ansible_host import ansible_host
	from loganalyzer import Loganalyzer

	def test(localhost, ansible_adhoc, testbed):
		hostname = testbed['dut']
		ans_host = ansible_host(ansible_adhoc, hostname)

		loganalyzer = Loganalyzer(ans_host)

		# If it is a need to load common search regular expressions. It will load regexp from common files and store values in the match_regex, expect_regex and ignore_regex attributes.
		loganalyzer.load_common_config()

		# Add start marker to DUT syslog
		loganalyzer.init("acl_test")

		# Example: If test need specific search marker it can be added
		loganalyzer.match.append("Runtime error: can't parse mac address 'None'")

		# Example: Get current match regular expressions
		print(loganalyzer.match_regex)

		# Example: Remove specific match regular expression
		loganalyzer.match_regex.remove("Runtime error: can't parse mac address 'None'")
		
		# Example: read test specific match file and add read strings to the existed match list
		loganalyzer.match_regex.extend(loganalyzer.parse_regexp_file("PATH_TO_THE_FILE/FILE.txt"))

		# Execute test steps here...

		result = loganalyzer.analyze()
		assert result["counters"]["match"] == 0, "Failure message\n{}\n{}".format(result["counters"], result["match_messages"])
