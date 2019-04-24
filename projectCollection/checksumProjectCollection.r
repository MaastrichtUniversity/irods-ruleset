# Call with
#
# irule -F checksumProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'"

irule_dummy() {
    *status = 0;

    IRULE_checksumProjectCollection(*project, *projectCollection, *status)
}

IRULE_checksumProjectCollection(*project, *projectCollection, *status) {
    *coll = "/nlmumc/projects/*project/*projectCollection";

    # Perform the checksum recursively
    *coll = *coll ++ "%"

    foreach(*data in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *coll) {
        *ipath = *data.COLL_NAME ++"/"++*data.DATA_NAME;

        msiDataObjChksum(*ipath, "verifyChksum=", *chkSum);
    }

}

INPUT *project='',*projectCollection=''
OUTPUT ruleExecOut