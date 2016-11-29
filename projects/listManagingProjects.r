# Call with
#
# irule -F listManagingProjects.r

listManagingProjects {
    *json_str = '[]';
    *size = 0;

    userNameToUserId($userNameClient, *userId);

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_ACCESS_USER_ID = *userId and COLL_ACCESS_NAME = 'own' and COLL_PARENT_NAME = '/nlmumc/projects' ) {
        uuChopPath(*Row.COLL_NAME, *collection, *project);
        msi_json_arrayops(*json_str, *project, "add", *size)
    }

    writeLine("stdout", *json_str);
}

userNameToUserId(*userName, *userId) {
    *O = select USER_ID where USER_NAME = '*userName';

    foreach (*R in *O) {
        *userId = *R.USER_ID;
    }
}

INPUT null
OUTPUT ruleExecOut
