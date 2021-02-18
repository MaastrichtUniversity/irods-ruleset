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
        project["project"] = project["path"].split("/")[3]

        # List Contributors
        # TODO: find out why this rule is a json without values
        #project["contributors"] = ctx.callback.listProjectContributors(project["path"], "false", "")["arguments"][2]
        # TODO: Hardcoded for the time-being
        project["contributors"] = {
            "users": [
                "service-pid"
            ],
            "groups": [
                "datahub"
            ],
            "groupObjects": [
                {
                    "groupName": "datahub",
                    "groupId": "10142",
                    "description": "It's DataHub! The place to store your data.",
                    "displayName": "DataHub"
                }
            ],
            "userObjects": [
                {
                    "displayName": "service-pid",
                    "userName": "service-pid",
                    "userId": "10130"
                }
            ]
            }
        # List Managers
        # TODO: find out why this rule is a json without values
        #project["managers"] = ctx.callback.listProjectManagers(project["path"], "")["arguments"][1]
        # TODO: Hardcoded for the time-being
        project["managers"] = {
            "users": [
                "psuppers",
                "opalmen"
            ],
            "groups": [],
            "groupObjects": [],
            "userObjects": [
                {
                    "userName": "psuppers",
                    "displayName": "Pascal Suppers",
                    "userId": "10053"
                },
                {
                    "displayName": "Olav Palmen",
                    "userName": "opalmen",
                    "userId": "10098"
                }
            ]
        }

        # List Viewers
        # TODO: find out why this rule is a json without values
        #project["viewers"] = ctx.callback.listProjectViewers(project["path"], "false", "")["arguments"][2]
        # TODO: Hardcoded for the time-being
        project["viewers"] = {
            "users": [
                "service-disqover"
            ],
            "groups": [],
            "groupObjects": [],
            "userObjects": [
                {
                    "displayName": "service-disqover",
                    "userName": "service-disqover",
                    "userId": "10133"
                }
            ]
        }

        # Get project metadata
        # Note: Retrieving the rule outcome is done with '["arguments"][2]'
        project["title"] = ctx.callback.getCollectionAVU(project["path"], "title", "", "", "true")["arguments"][2]
        project["enableOpenAccessExport"] = ctx.callback.getCollectionAVU(project["path"], "enableOpenAccessExport", "", "false", "false")["arguments"][2]
        project["enableArchive"] = ctx.callback.getCollectionAVU(project["path"], "enableArchive", "", "false", "false")["arguments"][2]
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
