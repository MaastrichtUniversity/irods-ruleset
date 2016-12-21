# Call with
#
# irule -F openProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'"
#
# This rule reopens a projectCollection in order to add, modify or delete data by an admin.
# Since the rodsadmin user has readonly permissions on collection-level at the start of this rule
# (= result of closeProjectCollection.r), we have to reopn the collection in a two-step fashion (see comments inline).

irule_dummy() {
    IRULE_openProjectCollection(*project, *projectCollection);
}

IRULE_openProjectCollection(*project, *projectCollection) {

    # Recursively assign ownership rights for rodsadmin to all collections within project
    msiSetACL("recursive", "own", "rods", "/nlmumc/projects/*project");

    # Reset 'read' permission on all collections, except for the one that we want to open
    foreach ( *Row in select COLL_NAME where COLL_PARENT_NAME = "/nlmumc/projects/*project" ) {
        #writeLine("stdout", *Row.COLL_NAME);
        if (*Row.COLL_NAME != "/nlmumc/projects/*project/*projectCollection") {
            msiSetACL("recursive", "read", "rods", *Row.COLL_NAME);
        }
    }
}

INPUT *project='', *projectCollection=''
OUTPUT ruleExecOut
