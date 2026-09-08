# /rules/tests/run_test.sh -r get_dropzone_validation_errors -a "handsome-snake,direct" -j
import json

import irods_types  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path, format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_dropzone_validation_errors(ctx, token, dropzone_type):
    """Return validation errors from the newest pre-ingest document for a dropzone."""
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    try:
        ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    except RuntimeError:
        return {"found": False, "validation_errors": []}

    project_id = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    project_path = format_project_path(ctx, project_id)
    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
    except RuntimeError:
        return {"found": False, "validation_errors": []}

    resource_host = ctx.callback.get_dropzone_resource_host(dropzone_type, project_id, "")["arguments"][2]
    result = ctx.callback.getDropzoneValidationErrors(resource_host, project_id, token, "")
    return json.loads(result["arguments"][3])
