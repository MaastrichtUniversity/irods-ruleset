@make(inputs=range(11), outputs=[11], handler=Output.STORE)
def create_new_project(ctx, authorization_period_end_date, data_retention_period_end_date,
                       ingest_resource, resource, storage_quota_gb, title,
                       principal_investigator, data_steward,
                       resp_cost_center, open_access, tape_archive):

    retry = 0
    error = -1
    new_project_path = ""
    project = ""

    # Try to create the new_project_path. Exit the loop on success (error = 0) or after too many retries.
    # The while loop adds compatibility for usage in parallelized runs of the delayed rule engine.
    while error < 0 and retry < 10:
        last_id = 0
        for result in row_iterator("COLL_NAME",
                                   "COLL_PARENT_NAME = '/nlmumc/projects'",
                                   AS_LIST,
                                   ctx.callback):

            project_path = result[0]
            project_id = project_path.split("/")[3]
            project_number = project_id.strip("P")

            project_number = int(project_number)
            if project_number > last_id:
                last_id = project_number

        ctx.callback.writeLine("stdout", str(last_id))

        project = str(last_id + 1)
        while len(project) < 9:
            project = "0" + str(project)
        project = "P" + project
        ctx.callback.writeLine("stdout", str(project))

        new_project_path = "/nlmumc/projects/" + project

        retry = retry + 1
        result = ctx.callback.msiCollCreate(new_project_path, 0, 0)
        status = str(result["arguments"][2])
        ctx.callback.writeLine("stdout", status)

        result = ctx.callback.errorcode(status)
        error_code = str(result["arguments"][0])
        ctx.callback.writeLine("stdout", error_code)
        error = error_code

    # Make the rule fail if it doesn't succeed in creating the project
    if error < 0 and retry >= 10:
        msg = "ERROR: Collection '{}' attempt no. {} : Unable to create {}".format(title, retry, new_project_path)
        ctx.callback.failmsg(error, msg)

    ctx.callback.setCollectionAVU(new_project_path, "authorizationPeriodEndDate", authorization_period_end_date)
    ctx.callback.setCollectionAVU(new_project_path, "dataRetentionPeriodEndDate", data_retention_period_end_date)
    ctx.callback.setCollectionAVU(new_project_path, "ingestResource", ingest_resource)
    ctx.callback.setCollectionAVU(new_project_path, "resource", resource)
    ctx.callback.setCollectionAVU(new_project_path, "storageQuotaGb", storage_quota_gb)
    ctx.callback.setCollectionAVU(new_project_path, "title", title)
    ctx.callback.setCollectionAVU(new_project_path, "OBI:0000103", principal_investigator)
    ctx.callback.setCollectionAVU(new_project_path, "dataSteward", data_steward)
    ctx.callback.setCollectionAVU(new_project_path, "responsibleCostCenter", resp_cost_center)
    ctx.callback.setCollectionAVU(new_project_path, "enableOpenAccessExport", open_access)
    ctx.callback.setCollectionAVU(new_project_path, "enableArchive", tape_archive)

    archive_dest_resc = ""
    for result in row_iterator("RESC_NAME",
                               "META_RESC_ATTR_NAME = 'archiveDestResc' AND META_RESC_ATTR_VALUE = 'true'",
                               AS_LIST,
                               ctx.callback):
        archive_dest_resc = result[0]
        ctx.callback.writeLine("stdout", archive_dest_resc)
    if archive_dest_resc == "":
        ctx.callback.failmsg(-1, "ERROR: The attribute 'archiveDestResc' has no value in iCAT")

    ctx.callback.setCollectionAVU(new_project_path, "archiveDestinationResource", archive_dest_resc)

    # # Set recursive permissions
    ctx.callback.msiSetACL("default", "write", "service-pid", new_project_path)
    ctx.callback.msiSetACL("default", "read", "service-disqover", new_project_path)
    ctx.callback.msiSetACL("recursive", "inherit", "", new_project_path)

    return {"project_path": new_project_path, "project_id": project}
