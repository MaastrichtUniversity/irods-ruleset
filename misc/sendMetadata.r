# Call with
#
# irule -F sendMetadata.r "*project='P000000001'" "*collection='C000000001'"

irule_dummy() {
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthMetaDataUrl);
    IRULE_sendMetadata(*mirthMetaDataUrl, *project, *collection);
}

IRULE_sendMetadata(*mirthURL , *project, *collection) {
    msiWriteRodsLog("DEBUG: mirthMetaDataUrl from msi_getenv is '*mirthURL'", 0);
    *postFields."data" = ""
    msiCurlPost("http://*mirthURL/?project=*project&collection=*collection", *postFields, *response);
}

INPUT *project='',*collection=''
OUTPUT ruleExecOut
