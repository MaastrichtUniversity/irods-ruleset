# /rules/tests/run_test.sh -r delete_project_collection_data -a "/nlmumc/projects/P000000008/C000000001,false"\
import json
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionState, DataDeletionAttribute
from dhpythonirodsutils.exceptions import ValidationError
from dhpythonirodsutils.formatters import format_string_to_boolean
from dhpythonirodsutils.validators import validate_project_collection_path
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import FALSE_AS_STRING
from datahubirodsruleset.data_deletion.restore_project_collection_user_access import check_collection_delete_data_state
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING

output_dict = {"messages": []}

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
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

    output_dict["messages"].append("Running delete_project_collection_data with commit mode as '{}'".format(commit))
    deletion_state = check_collection_delete_data_state(ctx, user_project_collection, DataDeletionState.PENDING.value)
    output_dict["messages"].append("Deletion state for {}: {}".format(user_project_collection, deletion_state))

    output_dict["messages"].append("Update ACL of rods for {}".format(user_project_collection))
    if commit:
        ctx.callback.msiSetACL("recursive", "admin:own", "rods", user_project_collection)

    output_dict["messages"].append("Start deletion for {}".format(user_project_collection))
    delete_collection_data(ctx, user_project_collection, commit, output_dict)

    # Convert the dictionary to JSON
    json_output = json.dumps(output_dict, indent=2)
    return json_output

def delete_collection_data(ctx, project_collection_path, commit, output_dict):
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
    metadata_files_count = set_metadata_files_acl_to_read(ctx, project_collection_path, commit, output_dict)
    count_project_collection_number_of_files(ctx, project_collection_path, output_dict)

    delete_project_collection_sub_folder(ctx, project_collection_path, commit, output_dict)
    delete_project_collection_root_files(ctx, project_collection_path, commit, output_dict)

    total_number_of_files = count_project_collection_number_of_files(ctx, project_collection_path, output_dict)

    check_number_of_files_left = total_number_of_files == metadata_files_count
    output_dict["messages"].append("Check number of files left: {}".format(check_number_of_files_left))

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

    return output_dict


def delete_project_collection_sub_folder(ctx, project_collection_path, commit, output_dict):
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
            output_dict["messages"].append("Invalid collection path: {}".format(project_collection_path))

        project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
        collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
        metadata_versions_path = formatters.format_metadata_versions_path(project_id, collection_id)

        if sub_folder != metadata_versions_path:
            output_dict["messages"].append("Delete collection sub-folder: {}".format(sub_folder))
            if commit:
                ctx.callback.msiRmColl(sub_folder, "forceFlag=", 0)
        else:
            output_dict["messages"].append("Keep collection sub-folder: {}".format(sub_folder))
    
    return output_dict


def delete_project_collection_root_files(ctx, project_collection_path, commit, output_dict):
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
            output_dict["messages"].append("Invalid collection path: {}".format(collection_path))

        valid_metadata_file_names = ["instance.json", "schema.json", "metadata.xml"]
        if data_name not in valid_metadata_file_names:
            output_dict["messages"].append("Delete data file: {}".format(data_path))
            if commit:
                ctx.callback.msiDataObjUnlink("objPath={}++++forceFlag=".format(data_path), 0)
        else:
            output_dict["messages"].append("Keep data file: {}".format(data_path))
    
    return output_dict


def set_metadata_files_acl_to_read(ctx, project_collection_path, commit, output_dict):
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
        output_dict["messages"].append("# Protect metadata file: {}".format(data_path))
        if commit:
            ctx.callback.msiSetACL("default", "admin:read", "rods", data_path)

    # Update the metadata files in the ".metadata_versions" folder
    project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
    collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
    metadata_versions_path = formatters.format_metadata_versions_path(project_id, collection_id)

    output_dict["messages"].append("# Protect metadata files in: {}".format(metadata_versions_path))
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
        output_dict["messages"].append("# Protect metadata file: {}".format(data_path))

    output_dict["messages"].append("metadata_files_count: {}".format(metadata_files_count))

    return metadata_files_count, output_dict


def count_project_collection_number_of_files(ctx, project_collection_path, output_dict):
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

    output_dict["messages"].append("total_number_of_files: {}".format(total_number_of_files))

    return total_number_of_files, output_dict
