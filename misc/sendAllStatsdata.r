# Call with (execute as rodsadmin user with full permission to /nlmumc/projects)
#
# irule -F /rules/misc/sendAllStatsdata.r

sendAllStatsdata() {
    *mirthUrl = 'mirthconnect:7777';
    foreach ( *Row in select COLL_NAME, COLL_PARENT_NAME, DATA_NAME where COLL_NAME like '/nlmumc/projects/%/%' and DATA_NAME = "metadata.xml") {
        uuChopPath(*Row.COLL_NAME, *head, *collection);
        uuChopPath(*Row.COLL_PARENT_NAME, *head, *project);
        writeLine("stdout", "Sending " ++ *project ++ " " ++ *collection);
        sendStatsData(*mirthUrl, *project, *collection,*response);
    }
}

INPUT null
OUTPUT ruleExecOut