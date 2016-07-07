# Call with
#
# irule -F closeProjectCollection.r "*projectCollection='/nlmumc/projects/MUMC-M4I-00001/20160707_0803_p.vanschayck'"

irule_dummy() {
    IRULE_closeProjectCollection(*projectCollection);
}

IRULE_closeProjectCollection(*projectCollection) {

    # Degrade all access to read only
    foreach ( *Row in select COLL_ACCESS_USER_ID where COLL_NAME = '*projectCollection' ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';
        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        msiSetACL("recursive", "read", *objectName, *projectCollection);
    }
}

INPUT *projectCollection=$"/nlmumc/projects/MUMC-M4I-00001/20160707_0803_p.vanschayck"
OUTPUT ruleExecOut