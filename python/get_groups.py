@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_groups(ctx, show_special_groups):
    """
    Get a listing of the all project's collections

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    show_special_groups: str
        Project absolute path

    Returns
    -------
    list
        a json list of collections objects
    """
    # Initialize the groups array
    groups = []

    for item in row_iterator("USER_NAME, USER_ID", "USER_TYPE = 'rodsgroup'", AS_LIST, ctx.callback):
        group_name = item[0]
        group_id = item[1]
        display_name = item[0]
        description = ""

        for meta in row_iterator("META_USER_ATTR_NAME, META_USER_ATTR_VALUE, USER_GROUP_ID, USER_GROUP_NAME",
                                 "USER_TYPE = 'rodsgroup' and USER_GROUP_ID = '{}'".format(group_id),
                                 AS_LIST, ctx.callback):
            if "displayName" == meta[0]:
                display_name = meta[1]
            elif "description" == meta[0]:
                description = meta[1]

        group_object = {
            "name": group_name,
            "groupId": group_id,
            "displayName": display_name,
            "description": description
        }
        if show_special_groups == "false":
            if group_name not in ["public", "rodsadmin", "DH-ingest", "DH-project-admins"]:
                groups.append(group_object)
        else:
            groups.append(group_object)

    return groups
