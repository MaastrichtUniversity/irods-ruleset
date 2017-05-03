# Call with
#
# irule -F listContributingProjects.r

listContributingProjects {
    *json_str = '[]';
    *size = 0;

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_ACCESS_NAME = 'modify object' and COLL_PARENT_NAME = "/nlmumc/projects" ) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);

        # Get project details
        getCollectionAVU("/nlmumc/projects/*project","title",*title,"no-title-AVU-set","false");
        listProjectContributors(*project,*contributors);
        listProjectManagers(*project,*managers);

        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, 'project', *project);
        msiAddKeyVal(*kvp, 'title', *title);
        msiAddKeyVal(*kvp, 'contributors', *contributors);
        msiAddKeyVal(*kvp, 'managers', *managers);

        *o = ""
        msi_json_objops(*o, *kvp, "set");

        msi_json_arrayops(*json_str, *o, "add", *size);
    }

    writeLine("stdout", *json_str);
}

INPUT *token=""
OUTPUT ruleExecOut
