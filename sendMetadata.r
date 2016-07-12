# Call with
#
# irule -F sendMetadata.r "*project='MUMC-M4I-00001',*collection='20160711_1312_p.vanschayck'"

irule_dummy() {
    IRULE_sendMetadata(*project, *collection)
}

IRULE_sendMetadata(*project, *collection) {
    msi_http_send_file("http://fhml-srv024.unimaas.nl:6669/?project=*project&collection=*collection", "/nlmumc/projects/*project/*collection/metadata.xml")
}

INPUT *project='',*collection=''
OUTPUT ruleExecOut
