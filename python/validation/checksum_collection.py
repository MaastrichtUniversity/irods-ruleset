# /rules/tests/run_test.sh -r checksum_collection -a "P000000014,C000000006" -j -u jmelius
@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def checksum_collection(ctx, project_id, collection_id):
    """
    Run checksum calculation for all data object inside the input project collection.
    Note: The user who execute the rule needs at least write access on the data object to calculate the checksum.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project ID ie P000000001
    collection_id: str
        The collection ID ie C000000001

    Returns
    -------
    dict[str]
        Key: data object logical path; Value: data object sha2 checksum value
    """
    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    output = {}

    for row in row_iterator("DATA_NAME, COLL_NAME", "COLL_NAME LIKE '{}%'".format(project_collection_path), AS_LIST, ctx.callback):
        virtual_path = row[1] + "/" + row[0]
        checksum = ctx.callback.msiDataObjChksum(virtual_path,"forceChksum=", "")["arguments"][2]
        formatted_checksum = checksum.replace("sha2:", "")
        output[virtual_path] = formatted_checksum

    return output
