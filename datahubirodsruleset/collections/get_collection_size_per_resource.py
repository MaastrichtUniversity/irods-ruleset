# /rules/tests/run_test.sh -r get_collection_size_per_resource -a "P000000028" -j
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_collection_size_per_resource(ctx, project_id):
    """
    Query the resource attribute for the files in a collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        Project ID

    Returns
    -------
    A dictionary of project collections with the location of their data
    """
    from collections import OrderedDict
    import re

    # create empty output dict
    output = OrderedDict()

    # create empty resources dictionary
    resources = {}
    # query resources (names) and their respective attributes (IDs)
    for row in row_iterator("RESC_NAME, RESC_ID", "", AS_LIST, ctx.callback):
        resources[row[1]] = row[0]

    # set collection path based on input
    project_path = format_project_path(ctx, project_id)
    total_sizes = {}
    resource_sizes = []
    for row in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        f"META_COLL_ATTR_NAME like 'dcat:byteSize%' AND COLL_PARENT_NAME = '{project_path}'",
        AS_LIST,
        ctx.callback,
    ):
        if row[1] == "dcat:byteSize":
            collection_id = formatters.get_collection_id_from_project_collection_path(row[0])
            total_sizes[collection_id] = row[2]
        elif row[1].startswith("dcat:byteSize_resc"):
            resource_sizes.append(row)

    # Calculate resource percentages after collecting all collection totals.
    for row in resource_sizes:
        collection_id = formatters.get_collection_id_from_project_collection_path(row[0])
        resource_id = re.sub("^dcat:byteSize_resc_", "", row[1])
        relative_size = (float(row[2]) / float(total_sizes[collection_id])) * 100
        result = {
            "resourceName": resources[resource_id],
            "resourceId": resource_id,
            "size": row[2],
            "relativeSize": round(relative_size, 1),
        }
        if collection_id in output:
            output[collection_id].append(result)
        else:
            output[collection_id] = [result]

    return output
