# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getDisplayNameForAccount.r "*account='dtheuniss'"

irule_dummy() {
    IRULE_getDisplayNameForAccount(*account , *result);
    writeLine("stdout", *result);
}

IRULE_getDisplayNameForAccount(*account,*result) {
    *userID = ""
    *userDisplayName = ""

     # Get the display name given the username
     foreach (*Row in SELECT META_USER_ATTR_VALUE, USER_ID WHERE USER_NAME == "*account" AND META_USER_ATTR_NAME == "displayName" ) {
            *userDisplayName = *Row.META_USER_ATTR_VALUE
            *userID =  *Row.USER_ID
     }

     # If the Display name is missing revert to the account name
     if (*userDisplayName == "") {
           *userDisplayName = *account
     }

     *result = *userDisplayName;
}

INPUT *account='d.theunissen@maastrichtuniversity.nl'
OUTPUT ruleExecOut
