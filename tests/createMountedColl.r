# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F createMountedColl.r

createMountedColl(*irodsColl, *irodsResc, *phyDir, *status) {
    msiPhyPathReg(*irodsColl, *irodsResc, *phyDir, "mountPoint", *status);
}

INPUT *rodsColl="/nlmumc/home/rods/mounted_coll", *irodsResc="rootResc", *phyDir="/tmp/mounted-coll"
OUTPUT ruleExecOut