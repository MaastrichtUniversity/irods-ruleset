# Call with
#
# irule -F replicateProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'"

irule_dummy() {
    *status = 0;

    IRULE_replicateProjectCollection(*project, *projectCollection, *status)
}

IRULE_replicateProjectCollection(*project, *projectCollection, *status) {
    # Find out the replication resource
    getCollectionAVU("/nlmumc/projects/*project","replResource",*replResource,"","true");

    *dstColl = "/nlmumc/projects/*project/*projectCollection";

    # Execute the replication and verify checksum
    # The policy will also enforce the destination resource, but no harm in setting it here again
    msiCollRepl(*dstColl, "destRescName=*replResource++++verifyChksum=", *status);
}

INPUT *project='',*projectCollection=''
OUTPUT ruleExecOut