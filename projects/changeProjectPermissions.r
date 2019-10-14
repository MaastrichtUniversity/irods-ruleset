# Call with
#
# irule -s -F changeProjectPermissions.r *project="P000000016" *users="rit-l:read"
#
# Change immediately the ACL on the project level.
# Then in the delay queue, change recursively all the collections under the project.

irule_dummy() {
    IRULE_changeProjectPermissions(*project, *users);
}

IRULE_changeProjectPermissions(*project, *users){
    # Save users list before uuChop
    *input_users = *users;

    # Change ACL on the project level
    uuChop(*users, *head, *tail, " ", true);
    if (*head != ""){
        # Case where users contains multiple inputs "account:right"
        # Execute first uuChop result
        uuChop(*head, *account, *rights, ":", true);
        msiSetACL("default", "*rights", "*account", '/nlmumc/projects/*project');
    }
    else{
        # Case where users contains only one input account:right
        uuChop(*users, *account, *rights, ":", true);
        msiSetACL("default", "*rights", "*account", '/nlmumc/projects/*project');
    }

    # Infinite loop safe-guard
    *count = 25;

    # Handle the rest of uuChop result
    *users = *tail;
    while ( *head != "" && *count != 0){
        uuChop(*users, *head, *tail, " ", true);
        if (*head != ""){
            uuChop(*head, *account, *rights, ":", true);
            msiSetACL("default", "*rights", "*account", '/nlmumc/projects/*project');
        }
        else{
            uuChop(*tail, *account, *rights, ":", true);
            msiSetACL("default", "*rights", "*account", '/nlmumc/projects/*project');
        }
        *users = *tail;
        *count = *count-1;
    }

    delay("<EF>1s REPEAT UNTIL SUCCESS OR 1 TIMES</EF>") {
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
            *projectCollection = *Row.COLL_NAME;
            # Reset user list to original input value
            *delay_users = *input_users;
            # Open the collection to be able to modify the collection ACL
            msiSetACL("recursive", "admin:own", "rods", "*projectCollection");
            # Change collection ACL recursively
            uuChop(*delay_users, *head, *tail, " ", true);
            *collection_rights = "read";
            if (*head != ""){
                uuChop(*head, *account, *rights, ":", true);
                if (*rights == "null"){
                    *collection_rights = "null";
                }
                msiSetACL("recursive", "*collection_rights", "*account", "*projectCollection");
            }
            else{
                uuChop(*delay_users, *account, *rights, ":", true);
                if (*rights == "null"){
                    *collection_rights = "null";
                }
                msiSetACL("recursive", "*collection_rights", "*account", "*projectCollection");
            }
            *delay_users = *tail;
            # Infinite loop safe-guard
            *count = 25;
            while ( *head != ""){
                uuChop(*delay_users, *head, *tail, " ", true);
                if (*head != ""){
                    uuChop(*head, *account, *rights, ":", true);
                    *collection_rights = "read";
                    if (*rights == "null"){
                        *collection_rights = "null";
                    }
                    msiSetACL("recursive", "*collection_rights", "*account", "*projectCollection");
                }
                if (*tail != ""){
                    uuChop(*tail, *account, *rights, ":", true);
                    *collection_rights = "read";
                    if (*rights == "null"){
                        *collection_rights = "null";
                    }
                    msiSetACL("recursive", "*collection_rights", "*account", "*projectCollection");
                }
                *delay_users = *tail;
                *count = *count-1;
            }
            #Close
            msiSetACL("recursive", "read", "rods", "*projectCollection");
        }
    }
}


INPUT *project="", *users=""
OUTPUT ruleExecOut