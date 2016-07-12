# Call with
#
# irule -F createProjectCollection.r "*project='MUMC-M4I-00001'"

irule_dummy() {
    IRULE_createProjectCollection(*project, *result);

    writeLine("stdout", *result);
}


# Creates collections in this form 20160707_0802_p.vanschayck
IRULE_createProjectCollection(*project, *projectCollection) {
    msiGetFormattedSystemTime(*dateTime, "human", "%d%02d%02d_%02d%02d");

    *projectCollection = *dateTime ++ "_" ++ $userNameClient;

    *dstColl = /nlmumc/projects/*project/*projectCollection;

    msiCollCreate(*dstColl, 0, *status);
}

INPUT *project=$"MUMC-M4I-00001"
OUTPUT ruleExecOut