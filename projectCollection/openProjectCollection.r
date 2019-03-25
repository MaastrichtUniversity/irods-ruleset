# Call with
#
# irule -F openProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'" "*user='rods'" "*rights='own'"
#
# This rule reopens a projectCollection in order to add, modify or delete data by an user. It uses user=rods and right=own as default
# for backwards compatibility

irule_dummy() {
    IRULE_openProjectCollection(*project, *projectCollection, *user, *rights);
}

IRULE_openProjectCollection(*project, *projectCollection, *user, *rights) {

    # Recursively assign ownership rights for rodsadmin to all collections within project
    msiSetACL("recursive", "admin:*rights", "*user", "/nlmumc/projects/*project/*projectCollection");

}

INPUT *project='', *projectCollection='', *user='rods' , *rights='own'
OUTPUT ruleExecOut
