# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_create_new_project.r "*authorizationPeriodEndDate='1-1-2018'" "*dataRetentionPeriodEndDate='1-1-2018'" "*ingestResource='iresResource'" "*resource='replRescUM01'" "*storageQuotaGb='10'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*dataSteward='d.steward@maastrichtuniversity.nl'" "*respCostCenter='UM-30001234X'" "*openAccess='false'" "*tapeArchive='true'" "*tapeUnarchive='true'"

def main(rule_args, callback, rei):
    authorizationPeriodEndDate = global_vars["*authorizationPeriodEndDate"][1:-1]
    dataRetentionPeriodEndDate = global_vars["*dataRetentionPeriodEndDate"][1:-1]
    ingestResource = global_vars["*ingestResource"][1:-1]
    resource = global_vars["*resource"][1:-1]
    storageQuotaGb = global_vars["*storageQuotaGb"][1:-1]
    title = global_vars["*title"][1:-1]
    principalInvestigator = global_vars["*principalInvestigator"][1:-1]
    dataSteward = global_vars["*dataSteward"][1:-1]
    respCostCenter = global_vars["*respCostCenter"][1:-1]
    openAccess = global_vars["*openAccess"][1:-1]
    tapeArchive = global_vars["*tapeArchive"][1:-1]
    tapeUnarchive = global_vars["*tapeUnarchive"][1:-1]


    output = callback.create_new_project(authorizationPeriodEndDate, dataRetentionPeriodEndDate,
                                                   ingestResource, resource, storageQuotaGb, title,
                                                   principalInvestigator, dataSteward,
                                                   respCostCenter, openAccess, tapeArchive, tapeUnarchive,
                                                   "result")

    callback.writeLine("stdout", output["arguments"][12])



INPUT *authorizationPeriodEndDate="", *dataRetentionPeriodEndDate="", *ingestResource="", *resource="", *storageQuotaGb="", *title="", *principalInvestigator="", *dataSteward="", *respCostCenter="", *openAccess="", *tapeArchive="", *tapeUnarchive=""
OUTPUT ruleExecOut