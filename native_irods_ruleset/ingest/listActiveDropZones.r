# Call with
#
# irule -F /rules/native_irods_ruleset/ingest/listActiveDropZones.r "*report='true'"

irule_dummy() {
    IRULE_listActiveDropZones(*report, *result);
    writeLine("stdout", *result);
}

IRULE_listActiveDropZones(*report, *result) {
    *hasDropZonepermission = "";
    checkDropZoneACL($userNameClient, "mounted", *hasDropZonePermissionMounted);
    checkDropZoneACL($userNameClient, "direct", *hasDropZonePermissionDirect);
    if (*hasDropZonePermissionMounted == "false" && *hasDropZonePermissionDirect == "false" ) {
        # -818000 CAT_NO_ACCESS_PERMISSION
        failmsg(-818000, "User '$userNameClient' has insufficient DropZone permissions on /nlmumc/ingest/zones");
    }
    *dropzoneQuery = ""
    if (*hasDropZonePermissionMounted == "true" && *hasDropZonePermissionDirect == "false" ) {
        *dropzoneQuery = "'/nlmumc/ingest/zones'"
    }
    if (*hasDropZonePermissionMounted == "false" && *hasDropZonePermissionDirect == "true" ) {
        *dropzoneQuery = "'/nlmumc/ingest/direct'"
    }
    if (*hasDropZonePermissionMounted == "true" && *hasDropZonePermissionDirect == "true" ) {
        *dropzoneQuery = "'/nlmumc/ingest/zones','/nlmumc/ingest/direct'"
    }

    *json_str = '[]';

    *param = "COLL_NAME, order_desc(COLL_MODIFY_TIME), COLL_PARENT_NAME";
    *cond = "COLL_ACCESS_NAME = 'own' and COLL_PARENT_NAME in (*dropzoneQuery)";
    msiMakeGenQuery(*param, *cond, *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach ( *Row in *QOut ) {
        *dropzone_path = *Row.COLL_NAME
        uuChopPath(*Row.COLL_NAME, *collection, *token);

        *type = ""
        if (*Row.COLL_PARENT_NAME == "/nlmumc/ingest/zones"){
            *type = "mounted"
        }
        else if (*Row.COLL_PARENT_NAME == "/nlmumc/ingest/direct"){
            *type = "direct"
        }

        *title = "";
        *state = "";
        *validateState = "";
        *validateMsg = "";
        *project = "";
        *projectTitle = "";
        *date = "";
        *totalSize = "";
        *destination = "";
        *creator = ""
        *enableDropzoneSharing = "";
        # Get contents of AVU's
        foreach (*av in SELECT COLL_MODIFY_TIME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*dropzone_path") {
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
                    if ( *av.META_COLL_ATTR_NAME == "enableDropzoneSharing" ) {
                        *enableDropzoneSharing = *av.META_COLL_ATTR_VALUE;
                    }
                }
            }
            *date = *av.COLL_MODIFY_TIME;
            if( *av.META_COLL_ATTR_NAME == "totalSize" ) {
                *totalSize = *av.META_COLL_ATTR_VALUE;
            }
            if( *av.META_COLL_ATTR_NAME == "destination" ) {
                *destination = *av.META_COLL_ATTR_VALUE;
            }
            if ( *av.META_COLL_ATTR_NAME == "creator" ) {
                *creator = *av.META_COLL_ATTR_VALUE;
            }
        }

        msiString2KeyValPair("", *kvp);
        *o = "";

        # Map AVU's and construct json object
        msiAddKeyVal(*kvp, 'token', *token);
        msiAddKeyVal(*kvp, 'type', *type);

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
            msiAddKeyVal(*kvp, 'enableDropzoneSharing', "false");
        } else {
            msiAddKeyVal(*kvp, 'project', *project);
            msiAddKeyVal(*kvp, 'projectTitle', *projectTitle);
            msiAddKeyVal(*kvp, 'enableDropzoneSharing', *enableDropzoneSharing);
        }

        msiAddKeyVal(*kvp, 'date', *date);

        if ( *totalSize == "" ) {
            msiAddKeyVal(*kvp, 'totalSize', "0");
        } else {
            msiAddKeyVal(*kvp, 'totalSize', *totalSize);
        }

        if ( *destination == "" ) {
            msiAddKeyVal(*kvp, 'destination', "");
        } else {
            msiAddKeyVal(*kvp, 'destination', *destination);
        }

        *creatorDisplayName = *creator;
        foreach (*Row in SELECT META_USER_ATTR_VALUE WHERE USER_NAME == "*creator" AND META_USER_ATTR_NAME == "displayName") {
            *creatorDisplayName = *Row.META_USER_ATTR_VALUE;
        }

        if (*creatorDisplayName == "") {
            msiAddKeyVal(*kvp, 'creator', *creator);
        } else {
            msiAddKeyVal(*kvp, 'creator', *creatorDisplayName);
        }

        if ( $userNameClient == *creator){
            msiAddKeyVal(*kvp, 'sharedWithMe', "false");
        } else {
            msiAddKeyVal(*kvp, 'sharedWithMe', "true");
        }

        # Extract additional info when *report == "true"
        if ( *report == "true" ) {

            ### USERNAME
            *userList = list();
            *userName = "";

            # DEBUG statements
            #writeLine("stdout", "DEBUG: Dropzone is *token");

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

            # Parse the userList and store the first element as userName (== creator).
            *length = size(*userList);
            if (*length == 0) {
                *userName = "N/A"
                msiWriteRodsLog("ERROR: Missing creator for dropzone /nlmumc/ingest/zones/*token", 0);
            } else {
                if (*length > 1) {
                    msiWriteRodsLog("WARNING: listActiveDropZones found multiple creators for DropZone /nlmumc/ingest/zones/*token. Only the first will be displayed in the report", 0);
                }
                *userName = elem(*userList,0)
            }

            # DEBUG statements
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

        json_arrayops_add(*json_str, *o, "")
    }

    *result = *json_str;
}

INPUT *report=''
OUTPUT ruleExecOut
