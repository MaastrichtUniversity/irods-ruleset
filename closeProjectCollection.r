# Call with
#
# irule -F closeProjectCollection.r "*project='MUMC-M4I-00001'" "*projectCollection='20160707_0803_p.vanschayck'"

irule_dummy() {
    IRULE_closeProjectCollection(*project, *projectCollection);
}

IRULE_closeProjectCollection(*project, *projectCollection) {

    # Degrade all access to read only
    foreach ( *Row in select COLL_ACCESS_USER_ID where COLL_NAME = '/nlmumc/projects/*project/*projectCollection' ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';
        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        msiSetACL("recursive", "read", *objectName, "/nlmumc/projects/*project/*projectCollection");
    }
}

INPUT *project=$"MUMC-M4I-00001", *projectCollection='20160707_0803_p.vanschayck'
OUTPUT ruleExecOut