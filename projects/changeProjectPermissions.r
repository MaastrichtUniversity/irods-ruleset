# Call with
#
# irule -s -F changeProjectPermissions.r *project="P000000016" *users="p.vanschayck@maastrichtuniversity.nl:read m.coonen@maastrichtuniversity.nl:write"
#
# Change immediately the ACL on the project level.
# Then in the delay queue, change recursively all the collections under the project.

irule_dummy() {
    IRULE_changeProjectPermissions(*project, *users);
}

IRULE_changeProjectPermissions(*project, *users){
    # Save users list before uuChop
    *input_users = *users;

    # Infinite loop safe-guard. Protects again malformed input.
    # This is the maximum of permission changes that can be made
    *count = 100;

    # Change ACL on the project level by chopping up the input array on space, and looping over it
    while ( *users != "" ){

        uuChop(*users, *head, *tail, " ", true);
        if (*head != ""){
            # Still multiple users to parse
            uuChop(*head, *account, *rights, ":", true);

            # Process rest users following iteration
            *users = *tail;
        }
        else{
            # Final user
            uuChop(*tail, *account, *rights, ":", true);

            # Signal end of loop
            *users = ""
        }

        msiSetACL("default", "*rights", "*account", '/nlmumc/projects/*project');

        *count = *count-1;

        if ( *count == 0 ) {
            failmsg(-1, "Malformed input of the permission string of changeProjectPermission. Stopped execution. Permission string: *input_users");
        }
    }

    delay("<EF>1s REPEAT UNTIL SUCCESS OR 1 TIMES</EF>") {
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
            *projectCollection = *Row.COLL_NAME;

            # Reset user list to original input value
            *delay_users = *input_users;
            *count = 100;    

            # Open the collection to be able to modify the collection ACL
            msiSetACL("recursive", "admin:own", "rods", "*projectCollection");

            # Change ACL on the projectCollection level by chopping up the input array on space, and looping over it
            while (*delay_users != "") {
                uuChop(*delay_users, *head, *tail, " ", true);

                if (*head != ""){
                    # Still multiple users to parse
                    uuChop(*head, *account, *rights, ":", true);

                    # Process rest users following iteration
                    *delay_users = *tail;
                }
                else {
                    # Final user
                    uuChop(*tail, *account, *rights, ":", true);

                    # Signal end of loop
                    *delay_users = "";
                }

                # Always set rights to read, unless they are removed
                if (*rights == "null"){
                    *collection_rights = "null";
                } else {
                    *collection_rights = "read";
                }

                msiSetACL("recursive", "*collection_rights", "*account", "*projectCollection");

                *count = *count - 1;

                if ( *count == 0 ) {
                    failmsg(-1, "Malformed input of the permission string of changeProjectPermission. Stopped execution. Permission string: *input_users");
                }
            }

            # Close collection
            msiSetACL("recursive", "read", "rods", "*projectCollection");
        }
    }
}


INPUT *project="", *users=""
OUTPUT ruleExecOut
