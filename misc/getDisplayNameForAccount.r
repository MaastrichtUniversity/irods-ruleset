# Call with
#
# irule -F getDisplayNameForAccount.r "*account='d.theunissen@maastrichtuniversity.nl'"

irule_dummy() {
    IRULE_getDisplayNameForAccount(*account , *result);
    writeLine("stdout", *result);
}

IRULE_getDisplayNameForAccount(*account,*result) {
    *userName = ""
    *userDisplayName = ""

     foreach (*Row in SELECT USER_NAME WHERE USER_NAME == "*account"  ) {
                *userName = *Row.USER_NAME
     }
     # If username is empty the user cannot be found in the system
     if (*userName == "") {
             failmsg(-1, "ERROR: The user '*account' was not found!");
     }

     # Get the display name given the username
     foreach (*Row in SELECT META_USER_ATTR_VALUE WHERE USER_NAME == "*account" AND META_USER_ATTR_NAME == "displayName" ) {
            *userDisplayName = *Row.META_USER_ATTR_VALUE
     }
     # If the Display name is missing revert to the account
     if (*userDisplayName == "") {
           *userDisplayName = *account
     }

     *result = *userDisplayName;
}

INPUT *account='d.theunissen@maastrichtuniversity.nl'
OUTPUT ruleExecOut