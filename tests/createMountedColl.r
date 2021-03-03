# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F createMountedColl.r "*irodsColl='/nlmumc/home/rods/mounted_coll'" "*irodsResc='rootResc'" "*phyDir='/tmp/mounted-coll'"

irule_dummy() {
    IRULE_createMountedColl(*irodsColl, *irodsResc, *phyDir);
}

IRULE_createMountedColl(*irodsColl, *irodsResc, *phyDir) {
    msiCollCreate(*irodsColl, 0, *status)
    msiPhyPathReg(*irodsColl, *irodsResc, *phyDir, "mountPoint", *status);
}

INPUT *irodsColl="", *irodsResc="", *phyDir=""
OUTPUT ruleExecOut