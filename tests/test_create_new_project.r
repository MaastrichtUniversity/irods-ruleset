# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_create_new_project.r  "*ingestResource='iresResource'" "*resource='replRescUM01'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*dataSteward='d.steward@maastrichtuniversity.nl'" "*responsibleCostCenter='UM-30001234X'" "*extraParameters='{\"enableDropzoneSharing\":\"true\"}'"
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_create_new_project.r  "*ingestResource='iresResource'" "*resource='replRescUM01'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*dataSteward='d.steward@maastrichtuniversity.nl'" "*responsibleCostCenter='UM-30001234X'" "*extraParameters=''"
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_create_new_project.r  "*ingestResource='iresResource'" "*resource='replRescUM01'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*dataSteward='d.steward@maastrichtuniversity.nl'" "*responsibleCostCenter='UM-30001234X'" "*extraParameters='{\"authorizationPeriodEndDate\":\"01-01-2022\", \"dataRetentionPeriodEndDate\":\"01-01-2022\", \"storageQuotaGb\":\"99\", \"enableOpenAccessExport\":\"true\", \"enableArchive\":\"true\", \"enableUnarchive\":\"true\",  \"enableDropzoneSharing\":\"true\", \"collectionMetadataSchemas\":\"DataHub_general_schema\"}'"

def main(rule_args, callback, rei):
    ingestResource = global_vars["*ingestResource"][1:-1] #
    resource = global_vars["*resource"][1:-1] #
    title = global_vars["*title"][1:-1] #
    principalInvestigator = global_vars["*principalInvestigator"][1:-1] #
    dataSteward = global_vars["*dataSteward"][1:-1] #
    respCostCenter = global_vars["*responsibleCostCenter"][1:-1] #
    extra_parameters = global_vars["*extraParameters"][1:-1] #


    output = callback.create_new_project( ingestResource, resource, title,
                                                   principalInvestigator, dataSteward,
                                                   respCostCenter,extra_parameters,
                                                   "result")

    callback.writeLine("stdout", output["arguments"][7])



INPUT  *ingestResource="", *resource="", *title="", *principalInvestigator="", *dataSteward="", *responsibleCostCenter="", *extraParameters=""
OUTPUT ruleExecOut
