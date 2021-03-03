# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F overwriteFileInMountedColl.r "*irodsColl='/nlmumc/home/rods/mounted_coll'" "*irodsResc='rootResc'" "*phyDir='/tmp/mounted-coll'"

irule_dummy() {
    IRULE_overwriteFileInMountedColl(*irodsColl, *irodsResc, *phyDir);
}

IRULE_overwriteFileInMountedColl(*irodsColl, *irodsResc, *phyDir) {
    # Create the mounted collection
    msiCollCreate(*irodsColl, 0, *status)
    msiPhyPathReg(*irodsColl, *irodsResc, *phyDir, "mountPoint", *status);

    # Write data to file
    *Obj1 = "*irodsColl/foo1"
    *OFlags1 = "destRescName=rootResc++++forceFlag="
    *R_BUF1 = "This is the content for the file that will be written to the mounted collection in iRODS. It is longer than 100 bytes.\n"

    msiDataObjCreate(*Obj1,*OFlags1,*D_FD1);
    msiDataObjWrite(*D_FD1,*R_BUF1,*W_LEN1);
    msiDataObjClose(*D_FD1,*Status1);

    writeLine("stdout","Wrote file *Obj1");

    # Overwrite data in file
    *Obj2 = *Obj1
    *OFlags2 = "destRescName=rootResc++++forceFlag="
    *R_BUF2 = "This is the CHANGED content for the file that will be written to the mounted collection in iRODS. It is definitely longer than 100 bytes.\n"

    msiDataObjCreate(*Obj2,*OFlags2,*D_FD2);
    msiDataObjWrite(*D_FD2,*R_BUF2,*W_LEN2);
    msiDataObjClose(*D_FD2,*Status2);

    writeLine("stdout","Overwrote file *Obj2");
}

INPUT *irodsColl="", *irodsResc="", *phyDir=""
OUTPUT ruleExecOut