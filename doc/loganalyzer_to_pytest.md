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

##### When to use loganalyzer feature
Below are shown three stages when it is useful to use loganalyzer:
- setup - Before test case start, during some preconfigurations
- loganalyzer fixture - During the test case execution (before test start to test end)
- test case - Between specific commands executed during test case

Below
```"Init loganalyzer"``` and ```"Loganalyzer perform analysis"``` - reprezentation of loganalyzers init and analyze commands.

**Usage templates**
##### setup:
	- Init loganalyzer
	- Perform DUT preconfigurations before test case/cases run
	- Loganalyzer perform analysis. Don't run tests if error(s) was found.

##### loganalyzer_fixture:
	- Init loganalyzer

	- Yield loganalyzer object
	- Start test case
	- Finish test case

	- Loganalyzer perform analysis. Fail test case if error(s) was found.

##### test case:
	- Perform test steps...

	- Init loganalyzer
	- Perform test steps/commands...
	- Loganalyzer perform analysis. Fail test if error(s) was found.

	- Perform test steps...
	- Perform test steps...

	- Init loganalyzer
	- Perform test steps/commands...
	- Loganalyzer perform analysis. Fail test if error(s) was found.

	- Perform test steps...
	- Perform test steps...

#### Loganalyzer usage example on setup, fixture and test case stages

##### Setup (Before test case start)
```
marker = loganalyzer.init()
loganalyzer.load_common_config()
# Setup steps, configurations here...
loganalyzer.analyze(marker)
# Verify analysis result
# Skip all following tests if analisys contain errors
```


##### Fixture (During full test case execution)
```
marker = loganalyzer.init()
loganalyzer.load_common_config()
# Some fixture code, steps here...
yield loganalyzer
loganalyzer.analyze(marker)
# Verify analysis result
# Fail test if analisys contain errors
```

##### Test case (Between specific commands executed during test case)
```
# Test steps here...
# Load regular expressions from the test specific file
# Or define string of regular expressions to search
reg_exp = loganalyzer.parse_regexp_file(src=TEST_SPECIFIC_MATCH)
# Apply read reguar expressions
loganalyzer.match_regex.extend(reg_exp)

marker = loganalyzer.init()
# Perform some test steps here...
# Verify that added regular expressions were found by log analyzer
result = loganalyzer.analyze(marker)
# Verify analysis result
# Fail test if analisys contain errors
```

#### Stages when loganalyzer fixture can be used

setup stage | test case stage
------------- | -------------
loganalyzer fixture  | loganalyzer fixture
directly import loganalyzer module  | loganalyzer fixture

##### Setup stage:
- Can be implemented in some pytest hooks probably in some of:
	- pytest_runtest_setup
	- pytest_runtest_call

- Can be implemented as pytest fixture
----------------------------
#### Loganalyzer item definition in test framework
For end user loganalyzer item can be defined as:
- ```Autouse Pytest fixture```
- ```"LogAnayzer" class object```

```Autouse Pytest fixture```
- Will perform syslog analysis **during test case execution** (will start before test case start and finish after test case finish or fail).
- Provide interface to use during test case execution to verify DUT syslog **during specific commands execution** by the test case.
- Fixture use autouse flag, to have fixture get invoked automatically without declaring a function argument explicitly or a usefixtures decorator.
It gives flexibility:
	- no need to pass loganalyzer fixture to the test case parameter, unless user want to analyze syslog in test case during specific commands execution.
- Fixture can handle availability of "--disable_loganalyzer" pytest option. If passed to the console, will not analyze logs during test cases run. But loganalyzer interface still will be available to use inside the test case if so was defined.

```LogAnayzer class object``` - Directly imported loganalyzer class with similar interface that is provided by the "Autouse Pytest fixture". Can be used in pytest hooks.  Proposal is to avoid direct usage.

#### How to disable loganalyzer for all run or for specific test case
- For all tests run use ```--disable_loganalyzer``` option in the console.
- For specific test case use @disable_loganalyzer decorator

#### disable_loganalyzer decorator
Its role is to somehove indicate loganalyzer fixture to skip log analysis for specific test case. Proposed simple approach to create attribute in the pytest module and use it as global variable beatween all test modules.

#### Example how to skip specific test case
tests/conftest.py
```
import pytest
from ansible_host import ansible_host

pytest.disable_log_analyzer = False # Log analyzer will be turned on for all test cases

@pytest.fixture(autouse=True)
def loganalyzer(ansible_adhoc, testbed):
    loganalyzer = LogAnalyzer(ansible_host=ansible_host(ansible_adhoc, testbed['dut']), marker_prefix="loganalyzer")
    if not pytest.disable_loganalyzer:
	    marker = loganalyzer.init()
	yield loganalyzer
	if not pytest.disable_loganalyzer:
	    result = loganalyzer.analyze(marker)
		if not result:
			pytest.fail("Log analyzer failed.")
		assert result["total"]["match"] == 0, "Found errors: {}".format(result)
```

tests/lib/helpers.py
```
import pytest
def disable_loganalyzer(func):
    def wrapper(*args, **kwargs):
        pytest.disable_loganalyzer = True
        try:
            func(*args, **kwargs)
        finally:
            pytest.disable_loganalyzer = False
    return wrapper
```

Any test case which requires disabled loganalyzer should use ```disable_loganalyzer``` decorator:
```
@disable_loganalyzer
def test(x, y):
    assert x == y
```

#### Development
Module "loganalyzer.py" with class "Loganalyzer".

"Loganalyzer" class interface:
- **__init__**(ansible_host: ansible_host, marker_prefix, dut_run_dir="/tmp")
- **load_common_config()** - Clear previous configured match, expect and ignore. Load regular expressions from common configuration files: match, expect and ignore which are located in some configuration directory or with current module. Save loaded configuration to the self.match_regex, self.expect_regex and self.ignore_regex attributes.
- **parse_regexp_file(file_path)** - Read and parse regular expressions from specified file. Return list of strings of defined regular expressions.
- **run_cmd(callback, *args, **kwargs)** - Call function and analyze DUT syslog during function execution. Return the same result as "analyze" function.
- **init()** - Add start marker to the DUT syslog. Generated marker format: marker_prefix + "%Y-%m-%d-%H:%M:%S". Return generated prefix.
- **analyze(search_marker)** - Extract syslog based on the specified search marker and copy it to ansible host. Analyze extracted syslog file localy. Return python dictionary object.
Return example:

```html
{"match_messages": {"/tmp/pytest-run/syslog.DATE(%Y-%m-%d-%H:%M:%S)": ["Msg1", "Msg2"]},
"total": {"expected_match": 0, "expected_missing_match": 0, "match": 2},
"match_files": {"/tmp/pytest-run/syslog.DATE(%Y-%m-%d-%H:%M:%S)": {"expected_match": 0, "match": 2}},
"expect_messages": {"/tmp/pytest-run/syslog.DATE(%Y-%m-%d-%H:%M:%S)": []},
"unused_expected_regexp": []}
```

- **save_full_log(dest)** - Download extracted DUT syslog (/tmp/syslog) to the Ansible host folder specified in 'dest' input parameter.

Attributes:
- match_regex - list of regular expression strings to match
- expect_regex - list of regular expression strings to expect
- ignore_regex - list of regular expression strings to ignore

Usage example of loganalyzer API just to show how to use loganalyzer interface.

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
