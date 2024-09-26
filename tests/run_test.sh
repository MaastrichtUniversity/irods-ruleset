#!/bin/bash

# -r rulename
# -a arguments (CSV)
# -u username
# -j if provided run output trough python3 -m json.tool
# -d Show debug statements


#./run_test.sh -r get_client_username
#./run_test.sh -r get_client_username -d
#./run_test.sh -r get_project_details -a "/nlmumc/projects/P000000015,true"
#./run_test.sh -r get_project_details -a "/nlmumc/projects/P000000015,true" -j

#./run_test.sh -r get_client_username -u psuppers
#./run_test.sh -r check_edit_metadata_permission -a "/nlmumc/projects/P000000015"
#./run_test.sh -r check_edit_metadata_permission -a "/nlmumc/projects/P000000015" -u psuppers


while getopts "r:a::u::jd" opt; do
  case $opt in
    r)
      rule=$OPTARG
      ;;
    a)
      rule_arguments=$OPTARG
      ;;
    u)
      user_name=$OPTARG
      ;;
    j)
      json="json"
      ;;
    d)
      debug="debug"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done


if [ $OPTIND -eq 1 ];
  then
    echo "No options were passed";
    exit 1
fi

# Only rule defined no arguments or username
if [ ! -z $rule  ] && [ -z $rule_arguments ] && [ -z $user_name ];
 then
   if [[ ! -z $debug ]]
    then
      echo "[DEBUG] Running as rods admin"
      echo "[DEBUG] Running rule: $rule "
   fi
   if [[ -z $json ]]
      then
        irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"\")" null ruleExecOut
      else
       irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"\")" null ruleExecOut  | python3 -m json.tool
   fi
   exit $?
fi

# Rule and arguments defined  no username
if [ ! -z $rule  ] && [ ! -z $rule_arguments ] && [ -z $user_name ];
 then
  if [[ ! -z $debug ]]
    then
      echo "[DEBUG] Running as rods admin"
      echo "[DEBUG] Running rule: $rule with arguments $rule_arguments "
   fi
   if [[ -z $json ]]
      then
        irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"$rule_arguments\")" null ruleExecOut
      else
       irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"$rule_arguments\")" null ruleExecOut  | python3 -m json.tool
   fi
   exit $?
fi


# Rule and username defined  no arguments
if [ ! -z $rule  ] && [ -z $rule_arguments ] && [ ! -z $user_name ];
 then
   if [[ ! -z $debug ]]
    then
      echo "[DEBUG] Running as $user_name"
      echo "[DEBUG]Running rule: $rule"
   fi
   export clientUserName=$user_name
   if [[ -z $json ]]
     then
        irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"\")" null ruleExecOut
        EXITCODE=$?
      else
       irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"\")" null ruleExecOut  | python3 -m json.tool
       EXITCODE=$?
   fi
   unset clientUserName
   exit $EXITCODE
fi


# Rule, arguments and username defined
if [ ! -z $rule  ] && [ ! -z $rule_arguments ] && [ ! -z $user_name ];
 then
  if [[ ! -z $debug ]]
    then
      echo "[DEBUG] Running as $user_name"
      echo "[DEBUG] Running rule: $rule with arguments $rule_arguments "
   fi
   export clientUserName=$user_name
   if [[ -z $json ]]
      then
       irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"$rule_arguments\")" null ruleExecOut
       EXITCODE=$?
      else
       irule -r irods_rule_engine_plugin-irods_rule_language-instance "test_rule_output(\"$rule\", \"$rule_arguments\")" null ruleExecOut  | python3 -m json.tool
       EXITCODE=$?
   fi
   unset clientUserName
   exit $EXITCODE
fi

