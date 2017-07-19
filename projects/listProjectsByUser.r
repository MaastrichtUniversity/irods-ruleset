# Call with
#
# irule -F listProjectsByUser.r


listProjectsByUser{
     msiString2KeyValPair("", *titleKvp);
    *json_str2 = '[]';
    *size2 = 0;
    foreach ( *Row in SELECT USER_NAME WHERE USER_TYPE ='rodsuser') {
       *groups = '';
       *json_str = '[]';
       *size = 0;
       *username = *Row.USER_NAME;
       userNameToUserId(*username, *userId);
       #writeLine("stdout", "User:   *username" );
       #User rodsadmin crashes rest of scripts
       if (*userId != '9001') {
            # Create a list of group-IDs (the user-ID is also a "group-ID")
            foreach ( *Row2 in SELECT USER_GROUP_ID where USER_ID = *userId ) {
                 *groupID = "'" ++ *Row2.USER_GROUP_ID ++ "'";
                 *groups= *groups ++ "," ++ *groupID;
            }
          
            # Remove first comma
            *groups=substr(*groups, 1, strlen(*groups));
            
            # Create GenQuery since ordinary select statement cannot deal with "in (*groups)" construction
            msiMakeGenQuery("COLL_NAME", "COLL_ACCESS_NAME in ('own', 'read object', 'modify object') and COLL_ACCESS_USER_ID in (*groups) and COLL_PARENT_NAME = '/nlmumc/projects'", *Query);
            msiExecGenQuery(*Query, *QOut);
            foreach (*Row in *QOut) {
                uuChopPath(*Row.COLL_NAME, *collection, *project);
                msi_json_arrayops(*json_str, *project, "add", *size);
            }
            *details = '{ "Username": " *username", "Projects": *json_str}';
            msi_json_arrayops(*json_str2,  *details, "add", *size2);
            #writeLine("stdout", "User:   *json_str2" );
        }
    }

   writeLine("stdout", *json_str2);


}

userNameToUserId(*userName, *userId) {
    *O = select USER_ID where USER_NAME = '*userName';

    foreach (*R in *O) {
        *userId = *R.USER_ID;
    }
}

INPUT null
OUTPUT ruleExecOut