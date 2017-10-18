# Call with
#
# irule -F /rules/misc/sendStatsData.r "*project='P000000001'" "*collection='C000000002'"

irule_dummy() {
    *mirthUrl = 'mirthconnect:7777';
    IRULE_sendStatsData(*mirthUrl, *project, *collection, *response);
}

IRULE_sendStatsData(*mirthUrl , *project, *collection,*response) {
    getCollectionStatistics(*project, *collection, *result);
    curlPost(*mirthUrl, *result, *response);
}

INPUT *project='',*collection=''
OUTPUT ruleExecOut
