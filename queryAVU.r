# Call with
# irule -F queryAVU.r "*path='/nlmumc/ingest/zones/grieving-giant'" "*name='title'"

irule_dummy() {
    msiWriteRodsLog("DanielHAATirods", 0);
    IRULE_queryAVU(*path,*name,*validateState)
    writeLine("stdout", *output);
}


IRULE_queryAVU(*path,*name,*validateState) {
    *output = "";
   foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == *path) {
                    if ( *av.META_COLL_ATTR_NAME == *name) {
                        *validateState = *av.META_COLL_ATTR_VALUE;
                    }
   }
   msiWriteRodsLog("Output of query is *validateState", 0);
}

INPUT null
OUTPUT ruleExecOut