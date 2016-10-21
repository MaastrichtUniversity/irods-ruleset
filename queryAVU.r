# Call with
# irule -F queryAVU.r "*path='/nlmumc/ingest/zones/grieving-giant'" "*name='title'"

irule_dummy() {
    IRULE_queryAVU(*collName, *attribute, *value)
}


IRULE_queryAVU(*collName, *attribute, *value) {
    *output = "";
   foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == *collName) {
                    if ( *av.META_COLL_ATTR_NAME == *attribute) {
                        *value = *av.META_COLL_ATTR_VALUE;
                    }
   }
   msiWriteRodsLog("Output of query is value: *value", 0);
}

INPUT null
OUTPUT ruleExecOut