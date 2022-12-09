# Gets fired after collection creation
acPostProcForCollCreate {
    ### Policy to increment the value of the 'latest_project_number' AVU on /nlmumc/projects ###
    if ($collName like regex "/nlmumc/projects/P[0-9]{9}") {
        *latest = 0;
        # Find out the current max project number
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects' ) {
            uuChopPath(*Row.COLL_NAME, *path, *c);
            *i = int(substr(*c, 1, 10));

            if ( *i > *latest ) {
                *latest = *i;
            }
        }
        msiAddKeyVal(*latestProjectNumberAVU, "latest_project_number", str(*latest));
        msiSetKeyValuePairsToObj(*latestProjectNumberAVU, "/nlmumc/projects", "-C");
    }
}