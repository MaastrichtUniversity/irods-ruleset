# /rules/tests/run_test.sh -r get_active_drop_zone -a "handsome-snake,false,direct" -j
import irods_types

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs, ProcessType
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path, format_project_path
from datahubirodsruleset.users.get_user_active_processes import get_drop_zone_percentage_ingested
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_active_drop_zone(ctx, token, check_ingest_resource_status, dropzone_type):
    """
    Get the attribute values for an active dropzone

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token : str
        The dropzone token
    check_ingest_resource_status : str
        'true'/'false' expected; If true, query the project resource status
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'

    Returns
    -------
    dict
        The attribute values
    """
    username = ctx.callback.get_client_username("")["arguments"][0]

    # Check if the user has right access at /nlmumc/ingest/zones
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    ret = ctx.callback.checkDropZoneACL(username, dropzone_type, "*has_dropzone_permission")
    has_dropzone_permission = ret["arguments"][2]
    if not formatters.format_string_to_boolean(has_dropzone_permission):
        msg = "User '{}' has insufficient DropZone permissions on /nlmumc/ingest/zones".format(username)
        # -818000 CAT_NO_ACCESS_PERMISSION
        ctx.callback.msiExit("-818000", msg)

    # Check if the dropzone exist
    try:
        ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    project_path = ""
    # Initialize the output
    avu = {
        "state": "",
        "title": "",
        "validateState": "",
        "validateMsg": "",
        "project": "",
        "projectTitle": "",
        "date": "",
        "token": token,
        "type": dropzone_type,
        "process_type": ProcessType.DROP_ZONE.value,
        "resourceStatus": "",
        "totalSize": "0",
        "destination": "",
        "creator": "",
        ProjectAVUs.ENABLE_DROPZONE_SHARING.value: "",
        "sharedWithMe": "",
    }
    # Query the dropzone metadata
    for result in row_iterator(
        "COLL_MODIFY_TIME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}'".format(dropzone_path),
        AS_LIST,
        ctx.callback,
    ):
        attr_name = result[1]
        attr_value = result[2]

        if attr_name == "project":
            avu[attr_name] = attr_value
            avu["date"] = result[0]
            project_path = format_project_path(ctx, attr_value)
            avu["projectTitle"] = ctx.callback.getCollectionAVU(
                project_path, ProjectAVUs.TITLE.value, "", "", TRUE_AS_STRING
            )["arguments"][2]
            avu[ProjectAVUs.ENABLE_DROPZONE_SHARING.value] = ctx.callback.getCollectionAVU(
                project_path, ProjectAVUs.ENABLE_DROPZONE_SHARING.value, "", FALSE_AS_STRING, FALSE_AS_STRING
            )["arguments"][2]
        else:
            avu[attr_name] = attr_value

    if username == avu["creator"]:
        avu["sharedWithMe"] = "false"
    else:
        avu["sharedWithMe"] = "true"

    if formatters.format_string_to_boolean(check_ingest_resource_status):
        # Query project resource avu
        resource = ctx.callback.getCollectionAVU(
            project_path, ProjectAVUs.RESOURCE.value, "*resource", "", TRUE_AS_STRING
        )["arguments"][2]
        # Query the resource status
        avu["resourceStatus"] = ctx.callback.get_resource_status(resource, "")["arguments"][1]

    avu["percentage_ingested"] = get_drop_zone_percentage_ingested(ctx, avu)

    return avu
