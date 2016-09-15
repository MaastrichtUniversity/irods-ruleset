# Call with
#
# irule -F sendMetadataFromIngest.r "*token='creepy-click'"

irule_dummy() {
    IRULE_sendMetadataFromIngest(*token)
}

IRULE_sendMetadataFromIngest(*token) {
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthURL)

    msi_http_send_file("*mirthURL/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml")
}

INPUT *token='',*mirthURL=''
OUTPUT ruleExecOut
