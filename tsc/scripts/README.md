# Pull codes from repro
Currently, only 22 repros are listed for testing purpose.

./git_count.py --pull_workspace

# Count commits based via organization names

github token string is needed for increasing github RESTFUL apis ratelimits
## Count all repros' commits with debug enable
./git_count.py --debug --token token_tring

## Count all repros' commits with without debug enable
./git_count.py --token token_string

## Count all repros' commits with without debug enable for the last 1 year
Default is 5 years.
./git_count.py --token token_string --years 1

# Check a list of github ids' company name.
The githubid list is provided as a file. The main id is to get github profile based on github id. Then we get company information based on github profile.
git_count.py --token token_string --check_ids --idfile id_file_name