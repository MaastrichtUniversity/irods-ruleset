# Call with
#
# irule -F sendMetadataFromIngest.r "*token='creepy-click'"

irule_dummy() {
    IRULE_sendMetadataFromIngest(*token)
}

IRULE_sendMetadataFromIngest(*token,*mirthURL) {
    # TODO: Parametrize this URL somehow
    #msi_http_send_file("http://fhml-srv024.unimaas.nl:6669/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml")
	msi_http_send_file("*mirthURL/?token=*token", "/nlmumc/ingest/zones/*token/metadata.xml")
}

INPUT *token='',*mirthURL=''
OUTPUT ruleExecOut
