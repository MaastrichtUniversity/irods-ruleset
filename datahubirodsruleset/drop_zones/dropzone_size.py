import json
from datetime import datetime

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.utils import FALSE_AS_STRING, map_access_name_to_access_level


def store_dropzone_size(ctx, dropzone_path, size):
    """Touch changed dropzones before storing their size, restoring temporary ACLs.

    Callers must serialize calculations for each dropzone; these callbacks are
    separate operations. A missing previous size triggers a first-run touch.
    """
    size = str(int(size))
    rods_id = ctx.callback.get_user_id("rods", "")["arguments"][1]
    previous_access = "null"
    for row in row_iterator(
        "COLL_ACCESS_NAME",
        f"COLL_NAME = '{dropzone_path}' AND COLL_ACCESS_USER_ID = '{rods_id}'",
        AS_LIST,
        ctx.callback,
    ):
        previous_access = row[0]

    if previous_access != "own":
        ctx.callback.msiSetACL("default", "admin:own", "rods", dropzone_path)
    try:
        previous_size = ctx.callback.getCollectionAVU(
            dropzone_path, "dropzoneSize", "", "", FALSE_AS_STRING
        )["arguments"][2]
        if previous_size == "" or int(previous_size) != int(size):
            # Keep the old size on failure so the next calculation retries the touch.
            ctx.callback.msi_touch(json.dumps({
                "logical_path": dropzone_path,
                "options": {"no_create": True},
            }))

        ctx.callback.setCollectionAVU(dropzone_path, "dropzoneSize", size)
        ctx.callback.setCollectionAVU(
            dropzone_path, "dropzoneSizeUpdated", str(int(datetime.now().timestamp()))
        )
    finally:
        if previous_access != "own":
            ctx.callback.msiSetACL(
                "default", "admin:" + map_access_name_to_access_level(previous_access),
                "rods", dropzone_path,
            )
