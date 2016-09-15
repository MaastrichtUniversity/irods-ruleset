# Call with
#
# irule -F sendMetadata.r "*project='MUMC-M4I-00001',*collection='20160711_1312_p.vanschayck'"

irule_dummy() {
    IRULE_sendMetadata(*project, *collection)
}

IRULE_sendMetadata(*project, *collection) {
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthURL)

    msi_http_send_file("*mirthURL/?project=*project&collection=*collection", "/nlmumc/projects/*project/*collection/metadata.xml")
}

INPUT *project='',*collection=''
OUTPUT ruleExecOut
