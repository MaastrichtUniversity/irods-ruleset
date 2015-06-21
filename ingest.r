ingest {
    writeLine("stdout", "Start ingest");

    msiDataObjCopy(*objPath,*objPath ++ "copy","forceFlag=",*Status); 
}

INPUT *objPath="/ritZone/home/rods/testdir/foo.txt"
OUTPUT ruleExecOut
