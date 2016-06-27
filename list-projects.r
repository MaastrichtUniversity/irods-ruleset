# Call with
#
# irule -F list-projects.r

listProjects {
    # writeLine("stdout", '[');

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_ACCESS_NAME = 'modify object' and COLL_PARENT_NAME = '/nlmumc/projects' ) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);

        # writeLine("stdout", "   \"*project\",");
        writeLine("stdout", "*project");
    }

    # writeLine("stdout", ']');
}


INPUT *token=""
OUTPUT ruleExecOut
