# Call with
#
# irule -F createProjectCollection.r "*project='MUMC-M4I-00001'"

irule_dummy() {
    IRULE_createProjectCollection(*project, *result);

    writeLine("stdout", *result);
}

IRULE_createProjectCollection(*project, *dstColl) {
    msiGetIcatTime(*dateTime, "unix");
    *dateUser = *dateTime ++ "_" ++ $userNameClient;

    *dstColl = /nlmumc/projects/*project/*dateUser;

    msiCollCreate(*dstColl, 0, *status);
}

INPUT *project=$"MUMC-M4I-00001"
OUTPUT ruleExecOut