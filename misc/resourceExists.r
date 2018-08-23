# Basic existence checker of resources
#
# Call with
#
# irule -F misc/resourceExists.r "*resource='rootResc'"
#

irule_dummy() {
    if( IRULE_resourceExists(*resource) == 1 ) {
        writeLine("stdout", "true");
    } else {
        writeLine("stdout", "false");
    }
}

# Checks if a resources exists
#
# Returns 0 if no file, 1 if resource is found.
IRULE_resourceExists(*i){
    *b = 0;

    foreach (*r in select RESC_NAME where RESC_NAME = '*i') {
        *b = 1;
        break;
    }

    # This returns the value of the var *b to the caller
    *b;
}

INPUT *resource=''
OUTPUT ruleExecOut