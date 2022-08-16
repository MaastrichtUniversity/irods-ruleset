# /rules/tests/run_test.sh -r list_destination_resources_status -j

@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_destination_resources_status(ctx):
    """
    Lists all the replicated resources and their availabilities.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    List
        The resources, their availabilities and comments
    """

    resources = []
    for row in row_iterator(
        "RESC_NAME, RESC_STATUS, RESC_COMMENT",
        "RESC_LOC = 'EMPTY_RESC_HOST' AND RESC_NAME != 'rootResc'",
        AS_LIST,
        ctx.callback,
    ):
        result = {"name": row[0], "available": row[1] != "down", "comment": row[2]}
        resources.append(result)

    return resources
