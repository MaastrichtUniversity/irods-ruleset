# Call with
#
# irule -F listActiveDropZones.r

listActiveDropZones {
    *json_str = '[]';
    *size = 0;

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_ACCESS_NAME = 'own' and COLL_PARENT_NAME = '/nlmumc/ingest/zones' ) {
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
            msiAddKeyVal(*kvp, 'state', "open");
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
            msiAddKeyVal(*kvp, 'project', "No-project-AVU-set");
            msiAddKeyVal(*kvp, 'projectTitle', "No-projectTitle-AVU-set");
        } else {
            msiAddKeyVal(*kvp, 'project', *project);
            msiAddKeyVal(*kvp, 'projectTitle', *projectTitle);
        }

        msiAddKeyVal(*kvp, 'date', *date);


        msi_json_objops(*o, *kvp, "set");

        msi_json_arrayops(*json_str, *o, "add", *size)
    }

    writeLine("stdout", *json_str);
}

INPUT *token=""
OUTPUT ruleExecOut
