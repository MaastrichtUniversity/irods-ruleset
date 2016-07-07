# Policies

acSetRescSchemeForCreate {
    if($objPath like "/nlmumc/projects/*/*") {
        *resource = "";

        uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);

        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project") {
            if ( *av.META_COLL_ATTR_NAME == "resource" ) {
                *resource = *av.META_COLL_ATTR_VALUE;
            }
        }

        if ( *resource == "") {
            failmsg(-1, "resource is empty!");
        }

        msiWriteRodsLog("Setting resource for project *project to resource *resource", *status);

        msiSetDefaultResc(*resource, "forced");
    } else {
        msiSetDefaultResc("demoResc","null");
    }
}