# Call with (execute as rodsadmin user with full permission to /nlmumc/projects)
#
# irule -F sendAllMetadata.r

sendAllMetadata() {

    foreach ( *Row in select COLL_NAME, COLL_PARENT_NAME where COLL_NAME like '/nlmumc/projects/%/%' ) {
        uuChopPath(*Row.COLL_NAME, *head, *collection);
        uuChopPath(*Row.COLL_PARENT_NAME, *head, *project);

        writeLine("stdout", "Sending " ++ *project ++ " " ++ *collection);
        sendMetadata(*project, *collection);
    }
}

INPUT null
OUTPUT ruleExecOut