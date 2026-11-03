# /rules/tests/run_test.sh -r get_dropzone_folders -a "vast-dove,/"
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import query_value


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_dropzone_folders(ctx, token, path):
    """
    Lists recursively the folders at the input 'path'

    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    token: str
       The dropzone token
    path: str
       Relative path in dropzone for folder

    Returns
    -------
    list
       The recursive folders list at the requested path
    """
    dropzone_path = formatters.format_dropzone_path(token, "direct")
    absolute_path = f"{dropzone_path}{path}"

    root = []
    children = {}
    prefix = absolute_path.rstrip("/") + "/"
    for folder, parent in row_iterator(
        "order(COLL_NAME), COLL_PARENT_NAME",
        f"COLL_NAME like {query_value(prefix + '%')}",
        AS_LIST,
        ctx.callback,
    ):
        # LIKE may match literal '%' or '_' in a folder name; only retain
        # actual descendants and attach children through visible parents.
        if not folder.startswith(prefix):
            continue
        node = {"value": folder.rsplit("/", 1)[1], "full_path": folder,
                "id": folder.replace(absolute_path, ""), "data": []}
        children.setdefault(parent, []).append(node)

    # Keep the root spelling (including its trailing slash) used by the old
    # parent-name query and relative IDs.
    pending = [(absolute_path, root)]
    while pending:
        parent, output = pending.pop()
        output.extend(children.get(parent, []))
        pending.extend((node["full_path"], node["data"]) for node in output)
    return root
