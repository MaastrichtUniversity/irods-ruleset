# Call with
#
# irule -F listViewingProjects.r

listViewingProjects {
    *json_str = '[]';
    *size = 0;

    # I did not manage to get this query to work in a LIGQ way directly in foreach(). It fails over
    # the `in` condition with parentheses.
    # SELECT COLL_NAME WHERE COLL_ACCESS_NAME in ('read object', 'modify object') and COLL_PARENT_NAME = '/nlmumc/projects'"

    msiMakeGenQuery("COLL_NAME", "COLL_ACCESS_NAME in ('read object', 'modify object')  and COLL_PARENT_NAME = '/nlmumc/projects'", *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach (*Row in *QOut) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);
        msi_json_arrayops(*json_str, *project, "add", *size);
    }

    writeLine("stdout", *json_str);
}

INPUT null
OUTPUT ruleExecOut
