# /rules/tests/run_test.sh -r checksum_collection -a "P000000014,C000000006" -j -u jmelius
@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def checksum_collection(ctx, project_id, collection_id):
    """

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    """
    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    output = {}

    for row in row_iterator("DATA_NAME, COLL_NAME", "COLL_NAME LIKE '{}%'".format(project_collection_path), AS_LIST, ctx.callback):
        virtual_path = row[1] + "/" + row[0]
        checksum = ctx.callback.msiDataObjChksum(virtual_path,"forceChksum=", "")["arguments"][2]
        formatted_checksum = checksum.replace("sha2:", "")
        output[virtual_path] = formatted_checksum

    return output
