"""Read both dropzone metadata files in the caller's rule context."""
import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path
from datahubirodsruleset.utils import read_data_object_from_irods


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def read_dropzone_metadata(ctx, token, dropzone_type):
    """Return the instance and schema using the caller's file permissions."""
    path = format_dropzone_path(ctx, token, dropzone_type)
    return {
        "instance": json.loads(read_data_object_from_irods(ctx, path + "/instance.json")),
        "schema": json.loads(read_data_object_from_irods(ctx, path + "/schema.json")),
    }
