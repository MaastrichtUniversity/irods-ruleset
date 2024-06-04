# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/projectCollection/closeProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'"

irule_dummy() {
    IRULE_closeProjectCollection(*project, *projectCollection);
}

IRULE_closeProjectCollection(*project, *projectCollection) {

    # Degrade all access to read only
    foreach ( *Row in select COLL_ACCESS_USER_ID where COLL_NAME = "/nlmumc/projects/*project/*projectCollection" ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';

        *objectName = "";
        *objectType = "";

        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        # Skip cases where *objectName could not be resolved (happens with deleted users)
        # && save yourself (= the current user) for last, otherwise you can't close anymore
        if ( *objectName != "" && *objectName != $userNameClient ) {
            msiSetACL("recursive", "admin:read", *objectName, "/nlmumc/projects/*project/*projectCollection");
        }
    }

    msiSetACL("recursive", "admin:read", $userNameClient, "/nlmumc/projects/*project/*projectCollection");
}

INPUT *project=$"P000000001", *projectCollection='C000000001'
OUTPUT ruleExecOut