# /rules/tests/run_test.sh -r get_dropzone_folders -a "vast-dove,/"
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


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
    absolute_path = "{}{}".format(dropzone_path, path)

    root = []
    walk_dropzone_folders(ctx, root, absolute_path, absolute_path)

    return root


def get_collection_sub_folders(ctx, parent, parent_path, dropzone_root):
    """
    Query the list of sub folders at the parent location.

    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    parent: dict|list
        If the parent is the root, the input type is the output list. Otherwise, the input parent is a JSON object/dict
    parent_path: str
        The absolute path to query the list of sub-folders. e.g: /nlmumc/ingest/direct/vast-dove/foo/bar
    dropzone_root: str
        The absolute dropzone root path. e.g: /nlmumc/ingest/direct/vast-dove

    Returns
    -------
    dict|list
        If the parent is the root, return the updated list with the sub-folders on the root level.
        Otherwise, return the updated parent dict with the sub-folders list on the current location in the key "data".
    """
    for result in row_iterator(
        "COLL_NAME, COLL_CREATE_TIME, COLL_MODIFY_TIME",
        "COLL_PARENT_NAME = '{}'".format(parent_path),
        AS_LIST,
        ctx.callback,
    ):
        # Extract only the name of the sub_folder from the full name/path
        name = result[0].rsplit("/", 1)[1]
        relative_collection_path = result[0].replace(dropzone_root, "")
        folder_node = {"value": name, "full_path": result[0], "id": relative_collection_path, "data": []}
        if parent_path == dropzone_root:
            parent.append(folder_node)
        else:
            parent["data"].append(folder_node)

    return parent


def walk_dropzone_folders(ctx, parent, parent_path, dropzone_root):
    """
    Recursive function to walk through the entire dropzone collection and update the original input parent list.

    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    parent: dict|list
        If the parent is the root, the input type is the output list. Otherwise, the input parent is a JSON object/dict
    parent_path: str
        The absolute path to query the list of sub-folders. e.g: /nlmumc/ingest/direct/vast-dove/foo/bar
    dropzone_root: str
        The absolute dropzone root path. e.g: /nlmumc/ingest/direct/vast-dove
    """
    child_collections = get_collection_sub_folders(ctx, parent, parent_path, dropzone_root)

    collections_list = child_collections
    if parent_path != dropzone_root:
        collections_list = child_collections["data"]

    for child_collection in collections_list:
        walk_dropzone_folders(ctx, child_collection, child_collection["full_path"], dropzone_root)
