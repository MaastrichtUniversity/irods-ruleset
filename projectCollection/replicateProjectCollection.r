# Call with
#
# irule -F replicateProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'"

irule_dummy() {
    IRULE_replicateProjectCollection(*project, *projectCollection)
}

IRULE_replicateProjectCollection(*project, *projectCollection) {
    # Find out the resource and replication resource
    getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
    getCollectionAVU("/nlmumc/projects/*project","replResource",*replResource,"","true");

    *dstColl = "/nlmumc/projects/*project/*projectCollection";

    # Execute the replication
    msiCollRepl(*dstColl, "destRescName=*replResource++++rescName=*resource", *status);
}

INPUT *project='',*projectCollection=''
OUTPUT ruleExecOut