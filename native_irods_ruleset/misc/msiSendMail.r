# This rule is not part of any workflow.
# It is use to mitigate the issue DHDO-1289.
#
# Check if the rule is correctly triggered:
# irule -r irods_rule_engine_plugin-irods_rule_language-instance "msiSendMail('a','b','c')" null ruleExecOut

msiSendMail(*a,*b,*c){ writeLine('serverLog','intercepted msiSendMail with this custom rule'); }

INPUT null
OUTPUT ruleExecOut
