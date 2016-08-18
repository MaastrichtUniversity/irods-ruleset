# Call with
#
# irule -F sendMetadataFromIngest.r "*token='creepy-click'"

irule_dummy() {
    IRULE_sendMetadataFromIngest(*token)
}

IRULE_sendMetadataFromIngest(*token) {
    # TODO: Parametrize this URL somehow
    msi_http_send_file("http://fhml-srv024.unimaas.nl:6669/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml")
}

INPUT *token=''
OUTPUT ruleExecOut
