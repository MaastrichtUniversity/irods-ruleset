# iRULE tests

This document describes how to run irods rules using the **run_test.sh** script. This script was create to easily test irods rules. 
It is basically a wrapper around the test_rule_output.py rule that can be found in the python subfolder. 

The script has 5 arguments:
- -r rulename
- -a arguments (comma seperated list)
- -u username (As which user should the rule be ran)
- -j if provided: run output trough python -m json.tool
- -d if provided: Show debug statements


## Usage
```
./run_test.sh -r get_client_username
./run_test.sh -r get_client_username -d
./run_test.sh -r get_project_details -a "/nlmumc/projects/P000000015,true"
./run_test.sh -r get_project_details -a "/nlmumc/projects/P000000015,true" -j

./run_test.sh -r get_client_username -u psuppers
./run_test.sh -r check_edit_metadata_permission -a "/nlmumc/projects/P000000015"
./run_test.sh -r check_edit_metadata_permission -a "/nlmumc/projects/P000000015" -u psuppers
```
