# /rules/tests/run_test.sh -r validate_data_post_ingestion -a "/nlmumc/projects/P000000019/C000000001,/nlmumc/ingest/direct/angry-elephant,direct,jmelius"

from datahubirodsruleset import formatters
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def validate_data_post_ingestion(ctx, project_collection, dropzone, dropzone_type, depositor):
    """
    This rule is part the ingestion workflow.
    It compares the size and number of files from the dropzone to the newly ingested project collection.

    Notes
    -----
    The calculation to compare the values only works before calling the rule 'finish_ingest'.
    Since 'finish_ingest' will modify instance.json and schema.json with the new PIDs and create 2 new files for
    the metadata version 1.

    Parameters
    ----------
    ctx: Context
         Combined type of callback and rei struct.
    project_collection: str
        The project id, e.g: /nlmumc/projects/P000000019/C000000001
    dropzone: str
        The collection id, e.g: /nlmumc/ingest/direct/angry-elephant
    dropzone_type: str
        The type of dropzone: direct or mounted.
    depositor: str
        The user who started the ingestion
    """
    collection_num_files = ctx.callback.getCollectionAVU(project_collection, "numFiles", "", "", TRUE_AS_STRING)[
        "arguments"
    ][2]
    collection_size = ctx.callback.getCollectionAVU(project_collection, "dcat:byteSize", "", "", TRUE_AS_STRING)[
        "arguments"
    ][2]

    # Compare drop-zone & project collection content
    instance_file_name = "instance.json"
    schema_file_name = "schema.json"

    # Dropzone
    if dropzone_type == "mounted":
        ret = ctx.callback.get_data_object_size(dropzone, instance_file_name, "")["arguments"][2]
        dropzone_instance_size = int(ret)
        ret = ctx.callback.get_data_object_size(dropzone, schema_file_name, "")["arguments"][2]
        dropzone_schema_size = int(ret)

        ctx.callback.msiWriteRodsLog(
            "DEBUG: '{}' dropzone_instance_size: {}".format(dropzone, str(dropzone_instance_size)), 0
        )
        ctx.callback.msiWriteRodsLog(
            "DEBUG: '{}' dropzone_schema_size: {}".format(dropzone, str(dropzone_schema_size)), 0
        )

    # Project collection
    ret = ctx.callback.get_data_object_size(project_collection, instance_file_name, "")["arguments"][2]
    collection_instance_size = int(ret)
    ret = ctx.callback.get_data_object_size(project_collection, schema_file_name, "")["arguments"][2]
    collection_schema_size = int(ret)

    dropzone_num_files = ctx.callback.getCollectionAVU(dropzone, "numFiles", "", "", TRUE_AS_STRING)["arguments"][2]
    dropzone_size = ctx.callback.getCollectionAVU(dropzone, "totalSize", "", "", TRUE_AS_STRING)["arguments"][2]

    match_num_files = int(dropzone_num_files) == int(collection_num_files)
    ctx.callback.msiWriteRodsLog(
        "DEBUG: dropzone_num_files = {} ;; collection_num_files = {}".format(
            str(dropzone_num_files), str(collection_num_files)
        ),
        0,
    )
    match_size = False
    if dropzone_type == "mounted":
        collection_user_size = int(collection_size) - collection_instance_size - collection_schema_size
        if not (collection_instance_size > 0 and collection_schema_size > 0):
            ctx.callback.msiWriteRodsLog(
                "DEBUG: collection_instance_size = {} ;; collection_schema_size = {}".format(
                    str(collection_instance_size), str(collection_schema_size)
                ),
                0,
            )
            ctx.callback.msiWriteRodsLog(
                "DEBUG: Incorrect metadata file sizes. Maybe 'replace_metadata_placeholder_files' was not executed.",
                0,
            )
        elif int(dropzone_size) == collection_user_size:
            match_size = True

        ctx.callback.msiWriteRodsLog(
            "DEBUG: Calculation: {} (collection_size) - {} (collection_instance_size) - {} (collection_schema_size) = {}".format(
                str(collection_size),
                str(collection_instance_size),
                str(collection_schema_size),
                str(collection_user_size),
            ),
            0,
        )
        ctx.callback.msiWriteRodsLog(
            "DEBUG: dropzone_size = {} ;; collection_user_size = {}".format(
                str(dropzone_size), str(collection_user_size)
            ),
            0,
        )
    elif dropzone_type == "direct":
        match_size = int(dropzone_size) == int(collection_size)
        ctx.callback.msiWriteRodsLog(
            "DEBUG: dropzone_size = {} ;; collection_size = {}".format(str(dropzone_size), str(collection_size)), 0
        )

    ctx.callback.msiWriteRodsLog(
        "DEBUG: Match dropzone '{}' to '{}' size: {}".format(dropzone, project_collection, str(match_size)), 0
    )
    ctx.callback.msiWriteRodsLog(
        "DEBUG: Match dropzone '{}' to '{}' file_count: {}".format(dropzone, project_collection, str(match_num_files)),
        0,
    )

    if match_size is False or match_num_files is False:
        project_id = formatters.get_project_id_from_project_collection_path(project_collection)
        ctx.callback.set_ingestion_error_avu(dropzone, "Error copying data", project_id, depositor)
