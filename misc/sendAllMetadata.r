# Call with (execute as rodsadmin user with full permission to /nlmumc/projects)
#
# irule -F sendAllMetadata.r

sendAllMetadata() {

    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthMetaDataUrl);

    foreach ( *Row in select COLL_NAME, COLL_PARENT_NAME, DATA_NAME where COLL_NAME like '/nlmumc/projects/%/%' and DATA_NAME = "metadata.xml") {
        if ( *Row.COLL_PARENT_NAME like regex "/nlmumc/projects/P[0-9]{9}$" ) {
            # metadata.xml at root folder of collection
            uuChopPath(*Row.COLL_NAME, *head, *collection);
            uuChopPath(*Row.COLL_PARENT_NAME, *head, *project);

            writeLine("stdout", "Sending " ++ *project ++ " " ++ *collection);
            sendMetadata(*mirthMetaDataUrl, *project, *collection);
        } else {
            # metadata.xml in a sub collection. We don't want to send that for indexing
            *subcoll = *Row.COLL_NAME
            writeLine("stdout", "NOT sending subcollection *subcoll");
        }
    }
}

INPUT null
OUTPUT ruleExecOut