# Call with
#
# irule -F validateMetadataFromIngest.r "*token='creepy-click'"

irule_dummy() {
    IRULE_validateMetadataFromIngest(*token)
}

IRULE_validateMetadataFromIngest(*token) {
    msi_getenv("MIRTH_VALIDATION_CHANNEL", *mirthURL)
    msiWriteRodsLog("send ingest data url *mirthURL", 0);
    msi_http_send_file("*mirthURL/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml")
}

INPUT *token='',*mirthURL=''
OUTPUT ruleExecOut
