createIngest {
    msiCollCreate(*ingestMount ++ "/" ++ *token, 0, *Status);

    msiExecCmd("enable-ingest-zone.sh", *user ++ " /mnt/ingest/" ++ *token, "null", "null", "null",*OUT);

    writeLine("stdout", *OUT);

    writeLine("stdout", "Ingestion token: " ++ *token );
}

INPUT *ingestMount="", *user="", *token=""
OUTPUT ruleExecCmd
