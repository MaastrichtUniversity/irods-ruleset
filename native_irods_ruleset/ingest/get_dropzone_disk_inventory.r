# Internal remote inventory transport for the housekeeping dropzone audit.
# A native remote block propagates output variables back to the Python caller.
get_dropzone_disk_inventory(*host, *roots, *inventory) {
    *inventory = "";
    remote(*host, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        scan_dropzone_directories(*roots, *inventory);
    }
}
