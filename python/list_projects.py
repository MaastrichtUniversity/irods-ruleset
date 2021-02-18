@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_projects(ctx):
    """
        Get a listing of all (authorized) projects

        Parameters
        ----------
        ctx : Context
            Combined type of a callback and rei struct.

        Returns
        -------
        list
            a json list of projects objects
        """

    # Initialize the projects listing
    output = []

    # Loop over all projects
    for result in row_iterator("COLL_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               ctx.callback):

        # Reset the project dictionary
        project = {}

        project["path"] = result[0]
        # project["path"] = "/nlmumc/projects/P000000013"
        project["id"] = project["path"].split("/")[3]

        # List Contributors
        # TODO
        # List Managers
        # TODO
        # List Viewers
        # TODO

        # Get project metadata
        # Note: Retrieving the rule outcome is done with '["arguments"][2]'
        project["title"] = ctx.callback.getCollectionAVU(project["path"], "title", "", "", "true")["arguments"][2]
        project["enableOpenAccessExport"] = ctx.callback.getCollectionAVU(project["path"], "enableOpenAccessExport", "", "", "false")["arguments"][2]
        project["enableArchive"] = ctx.callback.getCollectionAVU(project["path"], "enableArchive", "", "", "false")["arguments"][2]
        # TODO: Convert into displayname
        project["principalInvestigatorDisplayName"] = ctx.callback.getCollectionAVU(project["path"], "OBI:0000103", "", "", "true")["arguments"][2]
        project["dataStewardDisplayName"] = ctx.callback.getCollectionAVU(project["path"], "dataSteward", "", "", "true")["arguments"][2]
        project["respCostCenter"] = ctx.callback.getCollectionAVU(project["path"], "responsibleCostCenter", "", "", "true")["arguments"][2]
        project["storageQuotaGiB"] = ctx.callback.getCollectionAVU(project["path"], "storageQuotaGb", "", "", "true")["arguments"][2]



        # Get cost (only for PI... TODO: in DHS-1143, probably in another rule and DTO)

        # Calculate size for entire project
        proj_size = float(0)
        for proj_coll in row_iterator("COLL_NAME",
                                   "COLL_PARENT_NAME = '" + project["path"] + "'",
                                   AS_LIST,
                                   ctx.callback):

            coll_size = float(ctx.callback.get_collection_size(proj_coll[0], "GiB", "none", "")["arguments"][3])
            proj_size = proj_size + coll_size

        project["dataSizeGiB"] = proj_size

        # Append this project to the list
        output.append(project)

    # return projects listing
    return output
