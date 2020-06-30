# Call with
#
# irule -F getDisplayNameForUserEmail.r "*email='d.theunissen@maastrichtuniversity.nl'"

irule_dummy() {
    IRULE_getDisplayNameForUserEmail(*email , *result);
    writeLine("stdout", *result);
}

IRULE_getDisplayNameForUserEmail(*email,*result) {
    *userName = ""
    *userDisplayName = ""

     # First try to find an irods account with a username equal to the email address provided
     foreach (*Row in SELECT USER_NAME WHERE USER_NAME == "*email"  ) {
            *userName = *Row.USER_NAME
     }
     # If the username does not exist try to find a user with a matching email address
     if (*userName == "") {
              foreach (*Row in SELECT USER_NAME WHERE META_USER_ATTR_VALUE == "*email" AND META_USER_ATTR_NAME == "email" ) {
                    *userName = *Row.USER_NAME
              }
              # If username is still empty the user cannot be found in the system
              if (*userName == "") {
                    failmsg(-1, "ERROR: A user with email address '*email' was not found!");
              }
      }
     # Get the display name given the username
     foreach (*Row in SELECT META_USER_ATTR_VALUE WHERE USER_NAME == "*userName" AND META_USER_ATTR_NAME == "displayName" ) {
            *userDisplayName = *Row.META_USER_ATTR_VALUE
     }
     # If the Display name is missing revert to the email
     if (*userDisplayName == "") {
           *userDisplayName = *email
     }

     *result = *userDisplayName;
}

INPUT *email='d.theunissen@maastrichtuniversity.nl'
OUTPUT ruleExecOut