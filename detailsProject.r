# Call with
#
# irule -F detailsProject.r "*project='MUMC-M4I-00001'"

irule_dummy() {
    IRULE_detailsProject(*project, *result);

    writeLine("stdout", *result);
}

IRULE_detailsProject(*project, *result) {
    *details = "";

    listProjectContributors(*project,*contributors);
    listProjectManagers(*project,*managers);

    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project") {
         if ( *av.META_COLL_ATTR_NAME == "resource" ) {
             *resource = *av.META_COLL_ATTR_VALUE;
         }
    }

    *details = '{ "resource": "*resource", "contributors": *contributors, "managers": *managers}';
    *result = *details;
}

INPUT *project=""
OUTPUT ruleExecOut

