# /rules/tests/run_test.sh -r delete_project_data -a "/nlmumc/projects/P000000002,false"
import re

from dhpythonirodsutils.exceptions import ValidationError
from dhpythonirodsutils.validators import validate_project_collection_path
from genquery import row_iterator, AS_LIST


from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def delete_project_data(ctx, user_project, commit):
    ctx.callback.writeLine("stdout", "")
    ctx.callback.writeLine("stdout", "* Running delete_project_data with commit mode as '{}'".format(commit))

    deletion_state = ""
    for value in row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'deletionState' ".format(user_project),
        AS_LIST,
        ctx.callback,
    ):
        deletion_state = value[0]

    if deletion_state != "pending-for-deletion":
        ctx.callback.msiExit("-1", "Project deletion state is not valid {}".format(deletion_state))
        return

    ctx.callback.writeLine("stdout", "* Update ACL of rods for {}".format(user_project))
    if commit == "true":
        ctx.callback.msiSetACL("recursive", "admin:own", "rods", user_project)

    project_collections = []
    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '{}'".format(user_project), AS_LIST, ctx.callback):
        project_collections.append(result[0])

    ctx.callback.writeLine("stdout", "* Start deletion for {}".format(user_project))
    for collection_path in project_collections:
        ctx.callback.writeLine("stdout", "\t* Loop collection {}".format(collection_path))

        delete_collection_data(ctx, collection_path, commit)

    # TODO: Remove project from /nlmumc/trash
    # TODO: Update deletionState to deleted????


def delete_collection_data(ctx, collection_path, commit):
    set_metadata_files_acl_to_read(ctx, collection_path, commit)
    count_project_collection_number_of_files(ctx, collection_path)

    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '{}'".format(collection_path), AS_LIST, ctx.callback):
        sub_folder = result[0]

        try:
            validate_project_collection_path(collection_path)
        except ValidationError:
            ctx.callback.writeLine("stdout", "Invalid collection path\t\t\t\t: {}".format(collection_path))

        version_regex = "^{collection_path}/\.metadata_versions$".format(collection_path=collection_path)

        if re.search(version_regex, sub_folder) is None:
            ctx.callback.writeLine("stdout", "\t\t- Delete collection sub-folder\t\t\t: {}".format(sub_folder))
            if commit == "true":
                ctx.callback.msiRmColl(sub_folder, "forceFlag=", 0)
        else:
            ctx.callback.writeLine("stdout", "\t\t+ Keep collection sub-folder\t\t\t: {}".format(sub_folder))

    for result in row_iterator(
        "COLL_NAME, DATA_NAME", "COLL_NAME = '{}'".format(collection_path), AS_LIST, ctx.callback
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
            if commit == "true":
                ctx.callback.msiDataObjUnlink("objPath={}++++forceFlag=".format(data_path), 0)
        else:
            ctx.callback.writeLine("stdout", "\t\t+ Keep data file\t\t\t\t: {}".format(data_path))

    # TODO Update deletionState to deleted????
    count_project_collection_number_of_files(ctx, collection_path)


def set_metadata_files_acl_to_read(ctx, project_collection, commit):
    #  Set ACL to read for all metadata files (instance.json, schema.json, .metadata_versions & metadata.xml

    metadata_files_count = 0
    for result in row_iterator(
        "COLL_NAME, DATA_NAME",
        "COLL_NAME = '{}' AND DATA_NAME in ('instance.json','schema.json','metadata.xml')".format(project_collection),
        AS_LIST,
        ctx.callback,
    ):
        collection_path = result[0]
        data_name = result[1]
        data_path = "{}/{}".format(collection_path, data_name)
        metadata_files_count += 1
        ctx.callback.writeLine("stdout", "\t\t# Protect metadata file\t\t\t\t: {}".format(data_path))
        if commit == "true":
            ctx.callback.msiSetACL("default", "admin:read", "rods", data_path)

    metadata_versions_path = "{}/.metadata_versions".format(project_collection)
    ctx.callback.writeLine("stdout", "\t\t# Protect metadata files in\t\t\t: {}".format(metadata_versions_path))
    if commit == "true":
        ctx.callback.msiSetACL("recursive", "admin:read", "rods", metadata_versions_path)

    for result in row_iterator(
        "COLL_NAME, DATA_NAME",
        "COLL_NAME = '{}/.metadata_versions'".format(project_collection),
        AS_LIST,
        ctx.callback,
    ):
        collection_path = result[0]
        data_name = result[1]
        data_path = "{}/{}".format(collection_path, data_name)
        metadata_files_count += 1
        ctx.callback.writeLine("stdout", "\t\t# Protect metadata file\t\t\t\t: {}".format(data_path))

    ctx.callback.writeLine("stdout", "\t\t> metadata_files_count\t\t\t\t: {}".format(metadata_files_count))


def count_project_collection_number_of_files(ctx, project_collection):
    total_number_of_files = 0
    for result in row_iterator(
        "DATA_ID",
        "COLL_NAME like '{}%'".format(project_collection),
        AS_LIST,
        ctx.callback,
    ):
        total_number_of_files += 1

    ctx.callback.writeLine("stdout", "\t\t> total_number_of_files\t\t\t\t: {}".format(total_number_of_files))
