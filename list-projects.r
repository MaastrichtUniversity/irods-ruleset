# Call with
#
# irule -F list-projects.r

listProjects {
    *json_str = '[]';
    *size = 0;

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_ACCESS_NAME = 'modify object' and COLL_PARENT_NAME = '/nlmumc/projects' ) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);
        msi_json_arrayops(*json_str, *project, "add", *size)
    }

    writeLine("stdout", *json_str);
}


INPUT *token=""
OUTPUT ruleExecOut
