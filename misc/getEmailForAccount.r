# Call with
#
# irule -F getEmailForAccount.r "*account='mcoonen'"

irule_dummy() {
    IRULE_getEmailForAccount(*account , *result);
    writeLine("stdout", *result);
}

IRULE_getEmailForAccount(*account,*result) {
    *userID = ""
    *userEmail = ""

     # Get the e-mail address given the username
     foreach (*Row in SELECT META_USER_ATTR_VALUE, USER_ID WHERE USER_NAME == "*account" AND META_USER_ATTR_NAME == "email" ) {
            *userEmail = *Row.META_USER_ATTR_VALUE
            *userID =  *Row.USER_ID
     }
     # If the userID is empty for this account, write rodsLog warning for missing irods account
     # The value returned for this function is this the account name
     if (*userID == "") {
         msiWriteRodsLog("Warning: getting email address for unknown account: *account", 0);
     }

     # If the Display name is missing revert to the account name
     if (*userEmail == "") {
           *userEmail = *account
     }

     *result = *userEmail;
}

INPUT *account='mcoonen'
OUTPUT ruleExecOut