# Gets fired after a file is PUT into iRODS
acPostProcForPut {
    # Policy to give read access on metadata files to dropzone creator
    if ($objPath like regex "/nlmumc/ingest/direct/.*/instance.json" || $objPath like regex "/nlmumc/ingest/direct/.*/schema.json"){
        msiSetACL("default", "read", "$userNameClient", "$objPath")
    }
}
