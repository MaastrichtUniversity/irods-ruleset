# Call with
#
# irule -F rules/projects/listContributingProjects.r
#
# This rule returns a JSON array of projects for which the calling user is a Manager or a Contributor
# By default, iRODS returns only the projects for which a user is authorized. If a user has read-access to a
# project, he is allowed to list the ACL's. However, this does not mean that the user is entitled to WRITE to the project.
# Therefore, we have to build some logic first to find out to which groups a user belongs, store those in a list and
# filter the resultset on modify rights for the groups in that list (= COLL_ACCESS_USER_ID in (*groups) ).
# Example use-case:
# - user X is member of group Y.
# - project 0001 has readonly access for group Y
# - the user should not be able to select project 0001 to ingest data
#
listContributingProjects {
    *json_str = '[]';
    *size = 0;
    *groups = '';

    userNameToUserId($userNameClient, *userId);

    # Create a list of group-IDs (the user-ID is also a "group-ID")
    foreach ( *Row2 in SELECT USER_GROUP_ID where USER_ID = *userId ) {
         *groupID = "'" ++ *Row2.USER_GROUP_ID ++ "'";
         *groups= *groups ++ "," ++ *groupID;
    }

    # Remove first comma
    *groups=substr(*groups, 1, strlen(*groups));

    # Create GenQuery since ordinary select statement cannot deal with "in (*groups)" construction
    msiMakeGenQuery("COLL_NAME", "COLL_ACCESS_NAME in ('own', 'modify object') and COLL_ACCESS_USER_ID in (*groups) and COLL_PARENT_NAME = '/nlmumc/projects'", *Query);
    msiExecGenQuery(*Query, *QOut);

    # Loop over SQL result and generate JSON array with project info
    foreach ( *Row in *QOut) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);

        # Get project details
        getCollectionAVU("/nlmumc/projects/*project","title",*title,"no-title-AVU-set","false");
        listProjectContributors(*project, 'false', *contributors);
        listProjectManagers(*project, *managers);
        listProjectViewers(*project, 'false', *viewers);

        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, 'project', *project);
        msiAddKeyVal(*kvp, 'title', *title);
        msiAddKeyVal(*kvp, 'contributors', *contributors);
        msiAddKeyVal(*kvp, 'managers', *managers);
        msiAddKeyVal(*kvp, 'viewers', *viewers);

        *o = ""
        msi_json_objops(*o, *kvp, "set");

        msi_json_arrayops(*json_str, *o, "add", *size);
    }
    writeLine("stdout", *json_str);
}

INPUT *token=""
OUTPUT ruleExecOut
