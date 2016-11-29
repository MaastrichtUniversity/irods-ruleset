# Call with
#
# irule -F listContributingProjects.r

listContributingProjects {
    *json_str = '[]';
    *size = 0;

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_ACCESS_NAME = 'modify object' and COLL_PARENT_NAME = "/nlmumc/projects" ) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);

        *title = "";
        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project") {
            if ( *av.META_COLL_ATTR_NAME == "title" ) {
                *title = *av.META_COLL_ATTR_VALUE;
            }
        }

        msiString2KeyValPair("", *kvp);
        *o = "";

        msiAddKeyVal(*kvp, 'project', *project);

        if ( *title == "" ) {
            msiAddKeyVal(*kvp, 'title', "no-title-AVU-set");
        } else {
            msiAddKeyVal(*kvp, 'title', *title);
        }

        msi_json_objops(*o, *kvp, "set");

        msi_json_arrayops(*json_str, *o, "add", *size);
    }

    writeLine("stdout", *json_str);
}

INPUT *token=""
OUTPUT ruleExecOut
