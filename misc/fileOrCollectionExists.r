# Basic existence checker of iCAT object or collections.
#
# Call with
#
# irule -F misc/fileOrCollectionExists.r "*fileOrCollection='/nlmumc/projects'"
#

irule_dummy() {
    if( IRULE_fileOrCollectionExists(*fileOrCollection) == 1 ) {
        writeLine("stdout", "true");
    } else {
        writeLine("stdout", "false");
    }
}

# Checks if a file or collection exists
# *i is a full file path "/tempZone/home/rods/testfile.dat" or so
# Returns 0 if no file, 1 if file found.
IRULE_fileOrCollectionExists(*i){
    *b = 0;
    msiSplitPath(*i, *coll, *data);

    foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = '*coll' AND DATA_NAME = '*data'){
        *b = 1;
        break;
    }

    # Check for collection
    foreach(*row2 in SELECT COLL_NAME WHERE COLL_NAME = '*i'){
        *b = 1;
        break;
    }

    # This returns the value of the var *b to the caller
    *b;
}

INPUT *fileOrCollection=''
OUTPUT ruleExecOut