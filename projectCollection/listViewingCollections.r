# Call with
#
# irule -F listViewingCollections.r

listViewingCollections(*project) {
    *json_str = '[]';
    *size = 0;

    # I did not manage to get this query to work in a LIGQ way directly in foreach(). It fails over
    # the `in` condition with parentheses.
    # SELECT COLL_NAME WHERE COLL_ACCESS_NAME in ('read object', 'modify object') and COLL_PARENT_NAME = '/nlmumc/projects'"

    msiMakeGenQuery("COLL_NAME", "COLL_ACCESS_NAME in ('own', 'read object', 'modify object')  and COLL_PARENT_NAME = '/nlmumc/projects/*project'", *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach (*Row in *QOut) {
        uuChopPath(*Row.COLL_NAME, *trash, *collection);
        msi_json_arrayops(*json_str, *collection, "add", *size);
    }

    writeLine("stdout", *json_str);
}

INPUT null
OUTPUT ruleExecOut
