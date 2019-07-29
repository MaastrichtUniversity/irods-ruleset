# Call with
#
# irule -F validateMetadataFromIngest.r "*token='creepy-click', *mirthValidationURL='mirthconnect:6669'"
#
# This rule has 3 possible outcome states:
# - Validation channel has been reached in first attempt --> validateRepCounter AVU does not exist
# - Validation channel has been reached in 2nd to 10th attempt --> validateRepCounter AVU has been removed
# - Validation channel has NOT been reached in any of the 10 attempts --> validateRepCounter AVU has value 10

validateMetadataFromIngest(*token,*mirthURL) {
    *srcColl = "/nlmumc/ingest/zones/*token";
    *delete = 0;

    # Set DropZone status AVU to 'validating'
    msiAddKeyVal(*metaKV, "state", "validating");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    msiWriteRodsLog("Starting validation of *srcColl", 0);
    
    # Determine REPEAT count
    *validateRepCounter = "0";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
        if ( *av.META_COLL_ATTR_NAME == "validateRepCounter" ) {
            *validateRepCounter = *av.META_COLL_ATTR_VALUE;
            if (int(*validateRepCounter) >= 10) {
                # This must be a legacy counter from a previous ingest attempt.
                msiAddKeyVal(*delKV, *av.META_COLL_ATTR_NAME, *av.META_COLL_ATTR_VALUE);
                msiRemoveKeyValuePairsFromObj(*delKV,*srcColl, "-C");
                *validateRepCounter = "0";
                msiWriteRodsLog("Removed legacy validateRepCounter that originated from previous ingest attempt.", 0);
            }
        }
    }

    # Determine if AVU's that are going to be set via REST-operation need to be deleted first
    # This does not apply to AVU's that are being set by msiSetKeyValuePairsToObj, since the msi can also perform a 'modify'
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
        if ( *av.META_COLL_ATTR_NAME == "validateState" ) {
            msiAddKeyVal(*delKV, *av.META_COLL_ATTR_NAME, *av.META_COLL_ATTR_VALUE);
            *delete = *delete + 1;
        }
        if ( *av.META_COLL_ATTR_NAME == "validateMsg" ) {
            msiAddKeyVal(*delKV, *av.META_COLL_ATTR_NAME, *av.META_COLL_ATTR_VALUE);
             *delete = *delete + 1;
        }
    }
    
    if (*delete > 0){
       msiRemoveKeyValuePairsFromObj(*delKV,*srcColl, "-C");
       msiWriteRodsLog("Removed existing AVU from *srcColl", 0);
    }
    
    msiWriteRodsLog("DEBUG: mirthValidationURL from msi_getenv is '*mirthURL'", 0);
    *error = errorcode(msi_http_send_file("*mirthURL/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml"));

    if ( *error < 0 ) {
        *newCounter = int(*validateRepCounter) + 1;
        msiAddKeyVal(*metaKV, "validateRepCounter", str(*newCounter));
        msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
        failmsg(-1, "Error with validation channel");
    }else{
        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
            # Determine if there is a RepCounter and delete it, in order to let ingestNestedDelay1-rule know that it may continue
            if ( *av.META_COLL_ATTR_NAME == "validateRepCounter" ) {
                msiAddKeyVal(*delKV, *av.META_COLL_ATTR_NAME, *av.META_COLL_ATTR_VALUE);
                msiRemoveKeyValuePairsFromObj(*delKV,*srcColl, "-C");
                msiWriteRodsLog("Validation channel has been reached before attempt 10. Deleting validateRepCounter AVU...", 0);
            }
        }
    }
}

INPUT *token='',*mirthURL=''
OUTPUT ruleExecOut
