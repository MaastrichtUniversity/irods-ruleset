# Call with
#
# irule -F rules/ingest/listActiveDropZones.r "*report='true'"

irule_dummy() {
    IRULE_listActiveDropZones(*report, *result);
    writeLine("stdout", *result);
}


# Wrapper rule specific for Pacman, which enforces the report argument to 'false'
listActiveDropZonesPacman {
    *report="false";
    listActiveDropZones(*report, *result);
    writeLine("stdout", *result);
}


IRULE_listActiveDropZones(*report, *result) {
    *json_str = '[]';
    *size = 0;

    foreach ( *Row in SELECT COLL_NAME, order_desc(COLL_MODIFY_TIME) WHERE COLL_ACCESS_NAME = 'own' and COLL_PARENT_NAME = "/nlmumc/ingest/zones" ) {
        uuChopPath(*Row.COLL_NAME, *collection, *token);

        *title = "";
        *state = "";
        *validateState = "";
        *validateMsg = "";
        *project = "";
        *projectTitle = "";
        *date = "";
        # Get contents of AVU's
        foreach (*av in SELECT COLL_MODIFY_TIME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/ingest/zones/*token") {
            if ( *av.META_COLL_ATTR_NAME == "title" ) {
                *title = *av.META_COLL_ATTR_VALUE;
            }
            if ( *av.META_COLL_ATTR_NAME == "state" ) {
                *state = *av.META_COLL_ATTR_VALUE;
            }
            if ( *av.META_COLL_ATTR_NAME == "validateState" ) {
                *validateState = *av.META_COLL_ATTR_VALUE;
            }
            if ( *av.META_COLL_ATTR_NAME == "validateMsg" ) {
                *validateMsg = *av.META_COLL_ATTR_VALUE;
            }
            if ( *av.META_COLL_ATTR_NAME == "project" ) {
                *project = *av.META_COLL_ATTR_VALUE;
                foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project") {
                    if ( *av.META_COLL_ATTR_NAME == "title" ) {
                        *projectTitle = *av.META_COLL_ATTR_VALUE;
                    }
                }
            }
            *date = *av.COLL_MODIFY_TIME;
        }

        msiString2KeyValPair("", *kvp);
        *o = "";

        # Map AVU's and construct json object
        msiAddKeyVal(*kvp, 'token', *token);

        if ( *title == "" ) {
            msiAddKeyVal(*kvp, 'title', "no-title-AVU-set");
        } else {
            msiAddKeyVal(*kvp, 'title', *title);
        }

        if ( *state == "" ) {
            msiAddKeyVal(*kvp, 'state', "no-state-AVU-set");
        } else {
            msiAddKeyVal(*kvp, 'state', *state);
        }

        if ( *validateState == "" ) {
            msiAddKeyVal(*kvp, 'validateState', "N/A");
        } else {
            msiAddKeyVal(*kvp, 'validateState', *validateState);
        }

        if ( *validateMsg == "" ) {
            msiAddKeyVal(*kvp, 'validateMsg', "N/A");
        } else {
            msiAddKeyVal(*kvp, 'validateMsg', *validateMsg);
        }

        if ( *project == "" ) {
            msiAddKeyVal(*kvp, 'project', "no-project-AVU-set");
            msiAddKeyVal(*kvp, 'projectTitle', "No-projectTitle-AVU-set");
        } else {
            msiAddKeyVal(*kvp, 'project', *project);
            msiAddKeyVal(*kvp, 'projectTitle', *projectTitle);
        }

        msiAddKeyVal(*kvp, 'date', *date);

        # Extract additional info when *report == "true"
        if ( *report == "true" ) {

            ### USERNAME
            *userList = list();
            *userName = "";

            foreach (*av in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME == "/nlmumc/ingest/zones/*token") {
                # Determine username for userID
                *userID = *av.COLL_ACCESS_USER_ID;
                foreach ( *Row in SELECT USER_NAME WHERE USER_ID == *userID ) {
                    # Limit to non-service accounts
                    # TODO: Can be limited further to only mumc.nl accounts
                    if ( *Row.USER_NAME like "*@mumc.nl" || *Row.USER_NAME like "*@maastrichtuniversity.nl" ) {
                        *userList = cons(*Row.USER_NAME, *userList);
                    }
                }
            }

            # Take the first element from the list and store it as userName.
            *length = size(*userList);
            if (*length > 1) {
                msiWriteRodsLog("WARNING: listActiveDropZones found multiple creators for DropZone /nlmumc/ingest/zones/*token. Only the first will be displayed in the report", 0);
            }
            *userName = elem(*userList,0)

            #writeLine("stdout", "DEBUG: userList is *userList");
            #writeLine("stdout", "DEBUG: userName is *userName");

            if ( *userName != "" ) {
                msiAddKeyVal(*kvp, 'userName', *userName);
            }

            ### DROPZONE START & END DATE
			*fmt = "%.4d-%.2d-%.2d";
			msi_time_ts2str( int(*date), *fmt, *startDate );
			msi_time_ts2str( (int(*date) + 7776000), *fmt, *endDate ); # increase with the amount of seconds in 90 days
          
            msiAddKeyVal(*kvp, 'startDate', *startDate);
            msiAddKeyVal(*kvp, 'endDate', *endDate);
        }

        msi_json_objops(*o, *kvp, "set");

        msi_json_arrayops(*json_str, *o, "add", *size)
    }

    *result = *json_str;
}

INPUT *report=''
OUTPUT ruleExecOut
