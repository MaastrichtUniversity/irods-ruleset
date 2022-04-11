@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_contributors_metadata(ctx, project_id):
    """
    Get the contributors (PI, data-steward, etc) metadata of the given project.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id : str
        The project's id; eg.g P000000010

    Returns
    -------
    dict
        The contributors (PI, data-steward, etc) metadata
    """
    project_path = format_project_path(ctx, project_id)

    pi_username = ctx.callback.getCollectionAVU(project_path, "OBI:0000103", "", "", TRUE_AS_STRING)["arguments"][2]
    pi_dict = json.loads(ctx.get_user_metadata(pi_username, "")["arguments"][1])

    ds_username = ctx.callback.getCollectionAVU(project_path, "dataSteward", "", "", TRUE_AS_STRING)["arguments"][2]
    ds_dict = json.loads(ctx.get_user_metadata(ds_username, "")["arguments"][1])

    project = {"principalInvestigator": pi_dict, "dataSteward": ds_dict}

    return project
