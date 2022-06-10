@make(inputs=range(7), outputs=[7], handler=Output.STORE)
def create_new_project(
    ctx,
    ingest_resource,
    resource,
    title,
    principal_investigator,
    data_steward,
    responsible_cost_center,
    extra_parameters
):
    """
    Create a new iRODS project

    Parameters
    ----------
    ingest_resource : str
        The ingest resource to use during the ingestion
    resource : str
        The destination resource to store future collection
    title : str
        The project title
    principal_investigator : str
        The principal investigator(OBI:0000103) for the project
    data_steward : str
        The data steward for the project
    responsible_cost_center : str
        The budget number
    extra_parameters: str
        Json formatted list of extra parameters.
        Currently supported are:
            authorization_period_end_date : str
                Date
            data_retention_period_end_date : str
                Date
            storage_quota_gb  : str
                The storage quota in Gb
            enable_open_access : str
                'true'/'false' expected values
            enable_archive : str
                'true'/'false' expected values
            enable_unarchive : str
                'true'/'false' expected values
            enable_dropzone_sharing : str
                'true'/'false' expected values
            collection_metadata_schemas : str
                csv string that contains the list of schema names
    """
    import ast

    retry = 0
    error = -1
    new_project_path = ""
    project_id = ""
    extra_parameter_default_values = {"authorization_period_end_date": "01-01-9999",
                                                "data_retention_period_end_date": "01-01-9999",
                                                "storage_quota_gb": "0",
                                                "enable_open_access": "false",
                                                "enable_archive": "false",
                                                "enable_unarchive": "false",
                                                "enable_dropzone_sharing": "false",
                                                "collection_metadata_schemas": "DataHub_general_schema"}

    extra_parameter_AVU_names = {"authorization_period_end_date": "authorizationPeriodEndDate",
                                                "data_retention_period_end_date": "dataRetentionPeriodEndDate",
                                                "storage_quota_gb": "storageQuotaGb",
                                                "enable_open_access": "enableOpenAccessExport",
                                                "enable_archive": "enableArchive",
                                                "enable_unarchive": "enableUnarchive",
                                                "enable_dropzone_sharing": "enableDropzoneSharing",
                                                "collection_metadata_schemas": "collectionMetadataSchemas"}

    if not extra_parameters or extra_parameters == '':
        extra_parameters = "{}"

    extra_parameters = ast.literal_eval(extra_parameters)

    # Try to create the new_project_path. Exit the loop on success (error = 0) or after too many retries.
    # The while loop adds compatibility for usage in parallelized runs of the delayed rule engine.
    while error < 0 and retry < 10:
        latest_project_number = ctx.callback.getCollectionAVU(
            "/nlmumc/projects", "latest_project_number", "*latest_project_number", "", TRUE_AS_STRING
        )["arguments"][2]
        new_latest = int(latest_project_number) + 1
        project_id = str(new_latest)
        while len(project_id) < 9:
            project_id = "0" + str(project_id)
        project_id = "P" + project_id

        new_project_path = format_project_path(ctx, project_id)
        retry = retry + 1
        try:
            ctx.callback.msiCollCreate(new_project_path, 0, 0)
        except RuntimeError:
            error = -1
        else:
            error = 0

    # Make the rule fail if it doesn't succeed in creating the project
    if error < 0 and retry >= 10:
        msg = "ERROR: Collection '{}' attempt no. {} : Unable to create {}".format(title, retry, new_project_path)
        ctx.callback.msiExit(str(error), msg)

    ctx.callback.setCollectionAVU(new_project_path, "ingestResource", ingest_resource)
    ctx.callback.setCollectionAVU(new_project_path, "resource", resource)
    ctx.callback.setCollectionAVU(new_project_path, "title", title)
    ctx.callback.setCollectionAVU(new_project_path, "OBI:0000103", principal_investigator)
    ctx.callback.setCollectionAVU(new_project_path, "dataSteward", data_steward)
    ctx.callback.setCollectionAVU(new_project_path, "responsibleCostCenter", responsible_cost_center)

    for extra_parameter_name in extra_parameter_default_values:
        if extra_parameter_name in extra_parameters:
            ctx.callback.setCollectionAVU(new_project_path, extra_parameter_AVU_names[extra_parameter_name] ,
                                          extra_parameters[extra_parameter_name])
        else:
            ctx.callback.setCollectionAVU(new_project_path, extra_parameter_AVU_names[extra_parameter_name],
                                          extra_parameter_default_values[extra_parameter_name])

    ctx.callback.setCollectionAVU(new_project_path, "enableContributorEditMetadata", FALSE_AS_STRING)

    archive_dest_resc = ""
    for result in row_iterator(
        "RESC_NAME", "META_RESC_ATTR_NAME = 'archiveDestResc' AND META_RESC_ATTR_VALUE = 'true'", AS_LIST, ctx.callback
    ):
        archive_dest_resc = result[0]
    if archive_dest_resc == "":
        ctx.callback.msiExit("-1", "ERROR: The attribute 'archiveDestResc' has no value in iCAT")

    ctx.callback.setCollectionAVU(new_project_path, "archiveDestinationResource", archive_dest_resc)

    # Set recursive permissions
    ctx.callback.msiSetACL("default", "write", "service-pid", new_project_path)
    ctx.callback.msiSetACL("default", "read", "service-disqover", new_project_path)
    ctx.callback.msiSetACL("recursive", "inherit", "", new_project_path)

    current_user = ctx.callback.get_client_username("")["arguments"][0]
    # If the user calling this function is someone other than 'rods' (so a project admin)
    # we need to add rods as a owner on this project and remove the person calling this method
    # from the ACLs
    if current_user != "rods":
        ctx.callback.msiSetACL("default", "own", "rods", new_project_path)
        ctx.callback.msiSetACL("default", "null", current_user, new_project_path)

    return {"project_path": new_project_path, "project_id": project_id}
