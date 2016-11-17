# Call with
#
# irule -F validateMetadataFromIngest.r "*token='creepy-click'"

irule_dummy() {
    IRULE_validateMetadataFromIngest(*token)
}

IRULE_validateMetadataFromIngest(*token,*mirthURL) {
    *srcColl = /nlmumc/ingest/zones/*token;
    *delete = 0;
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
    
    msiWriteRodsLog("send ingest data url *mirthURL", 0);
    msi_http_send_file("*mirthURL/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml")
}

INPUT *token='',*mirthURL=''
OUTPUT ruleExecOut
