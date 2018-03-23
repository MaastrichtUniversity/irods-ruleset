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

    getCollectionAVU(*collection,"dcat:byteSize",*sizeBytes,"","true")

	if ( *unit == "B" ) {
		*size = double(*sizeBytes);
	}
	if ( *unit == "KiB" ) {
		*size = double(*sizeBytes)/1024;
	}
	if ( *unit == "MiB" ) {
		*size = double(*sizeBytes)/1024/1024;
	}
	if ( *unit == "GiB" ) {
		*size = double(*sizeBytes)/1024/1024/1024;
	}
	if ( *unit == "TiB" ) {
		*size = double(*sizeBytes)/1024/1024/1024/1024;
	}

    # Do the rounding
    if ( *round == "none") {
        *size = *size;
    }
    if ( *round == "floor") {
        *size = floor(*size);
    }
    if ( *round == "ceiling") {
        *size = ceiling(*size);
    }
    
    *result = *size;
}

INPUT *collection="",*unit="",*round=""
OUTPUT ruleExecOut