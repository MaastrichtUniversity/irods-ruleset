# Read-only bridge for returning a physical dropzone scan result from its resource host.

getDropzoneContentIngestability(*resourceHost, *dropzonePath, *dropzoneType, *result) {
    *result = "";
    remote(*resourceHost, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        get_dropzone_content_ingestability(*dropzonePath, *dropzoneType, *result);
    }
}

# Transport validation errors as parameters so their contents are not parsed as rule code.
saveDropzonePreIngestInfo(*resourceHost, *dropzonePath, *depositor, *dropzoneType, *validationErrors, *result) {
    *result = "";
    remote(*resourceHost, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        save_dropzone_pre_ingest_info(*dropzonePath, *depositor, *dropzoneType, *validationErrors, *result);
    }
}

getDropzoneValidationErrors(*resourceHost, *projectId, *token, *result) {
    *result = "";
    remote(*resourceHost, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        read_dropzone_validation_errors(*projectId, *token, *result);
    }
}
