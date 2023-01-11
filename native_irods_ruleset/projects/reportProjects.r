# This rule loops over all projects in iRODS, gets the project details and combines it in 1 large JSON string.
# The outcome can be used for (e-mail) reporting purposes or listing the Projects page in pacman.
# When called as rodsadmin (full permission to /nlmumc/projects) details of all projects are returned.
# When called as user with less privileges, only authorized projects will be returned.
#
# Call with:
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/projects/reportProjects.r
#
# Please note the different usage of size units:
# - bytes are used for the purpose of storing values in iCAT
# - GB is used for the purpose of calculating and displaying costs
# - GiB is used for the purpose of diplaying the size to end-user


irule_dummy() {
    IRULE_reportProjects(*result);

    writeLine("stdout", *result);
}

IRULE_reportProjects(*result) {
    *jsonStr = '[]';

    # Looping over projects
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = "/nlmumc/projects" ) {
        # Declare variables
        *project = "";
        *outcome = "";

        # Retrieve the project from the directory name
        uuChopPath(*Row.COLL_NAME, *dir, *project);

        # Retrieve the details for this project
        detailsProject(*project, "false", *outcome)

        # And append it to the jsonStr
        json_arrayops_add(*jsonStr, *outcome, "");
    }

    # jsonStr now contains information about all projects. Return this in the result variable
    *result = *jsonStr;
}

INPUT *result=''
OUTPUT ruleExecOut
