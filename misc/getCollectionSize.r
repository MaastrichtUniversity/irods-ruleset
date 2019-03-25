# This rule will retrieve the total size of a collection (folder) in iRODS from an iCAT AVU
# Call with
#
# irule -F getCollectionSize.r "*collection='/nlmumc/projects/P000000001/'" "*unit='GiB'" "*round='ceiling'"
#
# Rounding options
# *round='none' returns float with decimals
# *round='ceiling' returns integer rounded up 
# *round='floor' returns integer rounded down 


irule_dummy() {
    IRULE_getCollectionSize(*collection, *unit, *round, *result);
    writeLine("stdout", *result);
}

IRULE_getCollectionSize(*collection, *unit, *round, *result) {
    *sizeBytes = "0";

    getCollectionAVU(*collection,"dcat:byteSize",*sizeBytes,"0","false")

    if ( *unit == "B" ) {
        *size = double(*sizeBytes);
    } else if ( *unit == "KiB" ) {
        *size = double(*sizeBytes)/1024;
    } else if ( *unit == "MiB" ) {
        *size = double(*sizeBytes)/1024/1024;
    } else if ( *unit == "GiB" ) {
        *size = double(*sizeBytes)/1024/1024/1024;
    } else if ( *unit == "TiB" ) {
        *size = double(*sizeBytes)/1024/1024/1024/1024;
    } else {
        failmsg(-1, "Invalid input for 'unit'. Options are: B | KiB | MiB | GiB | TiB");
    }

    # Do the rounding
    if ( *round == "none") {
        *size = *size;
    } else if ( *round == "floor") {
        *size = floor(*size);
    } else if ( *round == "ceiling") {
        *size = ceiling(*size);
    } else {
        failmsg(-1, "Invalid input for 'round'. Options are: none | floor | ceiling");
    }
    
    *result = *size;
}

INPUT *collection="",*unit="",*round=""
OUTPUT ruleExecOut