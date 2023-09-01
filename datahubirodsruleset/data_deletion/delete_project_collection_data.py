# /rules/tests/run_test.sh -r delete_project_collection_data -a "/nlmumc/projects/P000000008/C000000001,false"
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionState, DataDeletionAttribute
from dhpythonirodsutils.exceptions import ValidationError
from dhpythonirodsutils.formatters import format_string_to_boolean
from dhpythonirodsutils.validators import validate_project_collection_path
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import FALSE_AS_STRING
from datahubirodsruleset.data_deletion.restore_project_collection_user_access import check_collection_delete_data_state
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def delete_project_collection_data(ctx, user_project_collection, commit):
    """
    Rule to trigger the deletion of all the data files inside the input project collection.
    All AVUs and metadata files are preserved.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_collection : str
        The absolute path of the project collection
    commit : str
        expected values: "true" or "false". If true, execute the data file deletion.
    """
    commit = format_string_to_boolean(commit)
    ctx.callback.writeLine("stdout", "")
    ctx.callback.writeLine("stdout", "* Running delete_project_collection_data with commit mode as '{}'".format(commit))

    check_collection_delete_data_state(ctx, user_project_collection, DataDeletionState.PENDING.value)

    ctx.callback.writeLine("stdout", "* Update ACL of rods for {}".format(user_project_collection))
    if commit:
        ctx.callback.msiSetACL("recursive", "admin:own", "rods", user_project_collection)

    ctx.callback.writeLine("stdout", "* Start deletion for {}".format(user_project_collection))
    delete_collection_data(ctx, user_project_collection, commit)


def delete_collection_data(ctx, project_collection_path, commit):
    """
    Function to take care of the deletion of all the data files inside the input project collection.
    All AVUs and metadata files are preserved.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the project collection
    commit : bool
        If true, execute the data file deletion.
    """
    metadata_files_count = set_metadata_files_acl_to_read(ctx, project_collection_path, commit)
    count_project_collection_number_of_files(ctx, project_collection_path)

    delete_project_collection_sub_folder(ctx, project_collection_path, commit)
    delete_project_collection_root_files(ctx, project_collection_path, commit)

    total_number_of_files = count_project_collection_number_of_files(ctx, project_collection_path)

    check_number_of_files_left = total_number_of_files == metadata_files_count
    ctx.callback.writeLine("stdout", "\t\t> Check number of files left\t\t\t: {}".format(check_number_of_files_left))

    # Cleanup
    if commit and check_number_of_files_left:
        ctx.callback.setCollectionAVU(
            project_collection_path, DataDeletionAttribute.STATE.value, DataDeletionState.DELETED.value
        )
        project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
        collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
        ctx.callback.setCollectionSize(project_id, collection_id, FALSE_AS_STRING, FALSE_AS_STRING)
    elif commit and not check_number_of_files_left:
        ctx.callback.msiExit(
            "-1",
            "Check of the number of files left after deletion failed for: {}".format(project_collection_path),
        )

    ctx.callback.msiSetACL("recursive", "admin:read", "rods", project_collection_path)


def delete_project_collection_sub_folder(ctx, project_collection_path, commit):
    """
    Query for all sub-folders at the root of the project collection to delete them.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the project collection
    commit : bool
        If true, execute the sub folders deletion.
    """
    for result in row_iterator(
        "COLL_NAME", "COLL_PARENT_NAME = '{}'".format(project_collection_path), AS_LIST, ctx.callback
    ):
        sub_folder = result[0]

        try:
            validate_project_collection_path(project_collection_path)
        except ValidationError:
            ctx.callback.writeLine("stdout", "Invalid collection path\t\t\t\t: {}".format(project_collection_path))

        project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
        collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
        metadata_versions_path = formatters.format_metadata_versions_path(project_id, collection_id)

        if sub_folder != metadata_versions_path:
            ctx.callback.writeLine("stdout", "\t\t- Delete collection sub-folder\t\t\t: {}".format(sub_folder))
            if commit:
                ctx.callback.msiRmColl(sub_folder, "forceFlag=", 0)
        else:
            ctx.callback.writeLine("stdout", "\t\t+ Keep collection sub-folder\t\t\t: {}".format(sub_folder))


def delete_project_collection_root_files(ctx, project_collection_path, commit):
    """
    Query for all data files at the root of the project collection to delete them.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the project collection
    commit : bool
        If true, execute the data files deletion.
    """
    for result in row_iterator(
        "COLL_NAME, DATA_NAME", "COLL_NAME = '{}'".format(project_collection_path), AS_LIST, ctx.callback
    ):
        collection_path = result[0]
        data_name = result[1]
        data_path = "{}/{}".format(collection_path, data_name)

        try:
            validate_project_collection_path(collection_path)
        except ValidationError:
            ctx.callback.writeLine("stdout", "Invalid collection path\t\t\t\t: {}".format(collection_path))

        valid_metadata_file_names = ["instance.json", "schema.json", "metadata.xml"]
        if data_name not in valid_metadata_file_names:
            ctx.callback.writeLine("stdout", "\t\t- Delete data file\t\t\t\t: {}".format(data_path))
            if commit:
                ctx.callback.msiDataObjUnlink("objPath={}++++forceFlag=".format(data_path), 0)
        else:
            ctx.callback.writeLine("stdout", "\t\t+ Keep data file\t\t\t\t: {}".format(data_path))


def set_metadata_files_acl_to_read(ctx, project_collection_path, commit):
    """
    Set ACL to read for all metadata files: instance.json, schema.json, metadata.xml & .metadata_versions

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the project collection
    commit : bool
        If true, execute the ACL changes.

    Returns
    --------
    int
        The total number of metadata files inside the project collection
    """
    metadata_files_count = 0

    # Update the metadata files at the root
    for result in row_iterator(
        "COLL_NAME, DATA_NAME",
        "COLL_NAME = '{}' AND DATA_NAME in ('instance.json','schema.json','metadata.xml')".format(
            project_collection_path
        ),
        AS_LIST,
        ctx.callback,
    ):
        collection_path = result[0]
        data_name = result[1]
        data_path = "{}/{}".format(collection_path, data_name)
        metadata_files_count += 1
        ctx.callback.writeLine("stdout", "\t\t# Protect metadata file\t\t\t\t: {}".format(data_path))
        if commit:
            ctx.callback.msiSetACL("default", "admin:read", "rods", data_path)

    # Update the metadata files in the ".metadata_versions" folder
    project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
    collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
    metadata_versions_path = formatters.format_metadata_versions_path(project_id, collection_id)

    ctx.callback.writeLine("stdout", "\t\t# Protect metadata files in\t\t\t: {}".format(metadata_versions_path))
    if commit:
        ctx.callback.msiSetACL("recursive", "admin:read", "rods", metadata_versions_path)

    for result in row_iterator(
        "COLL_NAME, DATA_NAME",
        "COLL_NAME = '{}'".format(metadata_versions_path),
        AS_LIST,
        ctx.callback,
    ):
        collection_path = result[0]
        data_name = result[1]
        data_path = "{}/{}".format(collection_path, data_name)
        metadata_files_count += 1
        ctx.callback.writeLine("stdout", "\t\t# Protect metadata file\t\t\t\t: {}".format(data_path))

    ctx.callback.writeLine("stdout", "\t\t> metadata_files_count\t\t\t\t: {}".format(metadata_files_count))

    return metadata_files_count


def count_project_collection_number_of_files(ctx, project_collection_path):
    """
    Execute a query to get the total number of files inside the project collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the project collection

    Returns
    --------
    int
        The total number of files
    """
    total_number_of_files = 0
    for result in row_iterator(
        "DATA_ID",
        "COLL_NAME like '{}%'".format(project_collection_path),
        AS_LIST,
        ctx.callback,
    ):
        total_number_of_files += 1

    ctx.callback.writeLine("stdout", "\t\t> total_number_of_files\t\t\t\t: {}".format(total_number_of_files))

    return total_number_of_files
