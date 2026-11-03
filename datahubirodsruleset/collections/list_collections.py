# /rules/tests/run_test.sh -r list_collections -a "/nlmumc/projects/P000000014" -j
from collections import Counter

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import collection_metadata, query_value


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_collections(ctx, project_path):
    """
    Get a listing of all the project's collections

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        Project absolute path

    Returns
    -------
    list
        a json list of collections objects
    """
    return _list_collections(ctx, project_path)


def _list_collections(ctx, project_path, admin=False):
    formatters.get_project_id_from_project_path(project_path)
    condition = f"COLL_PARENT_NAME = {query_value(project_path)}"
    paths = [row[0] for row in row_iterator("COLL_NAME", condition, AS_LIST, ctx.callback)]
    if not paths:
        return []

    attributes = ("dcat:byteSize", "title", "creator", "PID", "numFiles", "latest_version_number", "deletionState")
    metadata = collection_metadata(ctx, condition, attributes)
    excluded_files = Counter(path for path, _ in row_iterator(
        "COLL_NAME, DATA_NAME", condition + " AND DATA_NAME in ('metadata.xml')", AS_LIST, ctx.callback
    ))
    result = []
    for path in paths:
        values = metadata.get(path, {})
        size = values.get("dcat:byteSize", "0")
        num_files = values.get("numFiles", "0")
        # The admin rule historically uses getCollectionAVU's empty-value
        # fallbacks and floating byte sizes; the regular listing uses integers.
        size = float(size or "0") if admin else int(size)
        num_files = int(num_files or "0") if admin else int(num_files)
        versions = values.get("latest_version_number", "")
        metadata_files = (int(versions) * 2 + 2) if versions else 0
        collection = {
            "size": size, "title": values.get("title", ""), "creator": values.get("creator", ""),
            "PID": values.get("PID", ""), "numFiles": num_files,
            "id": formatters.get_collection_id_from_project_collection_path(path),
            "numUserFiles": num_files - metadata_files - excluded_files[path],
        }
        if admin:
            collection["deletionState"] = values.get("deletionState", "")
        result.append(collection)
    return result
