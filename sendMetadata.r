# Call with
#
# irule -F sendMetadata.r "*project='P000000001',*collection='C000000001'"

irule_dummy() {
    IRULE_sendMetadata(*project, *collection)
}

IRULE_sendMetadata(*project, *collection) {
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthURL)

    msi_http_send_file("*mirthURL/?project=*project&collection=*collection", "/nlmumc/projects/*project/*collection/metadata.xml")
}

INPUT *project='',*collection=''
OUTPUT ruleExecOut
