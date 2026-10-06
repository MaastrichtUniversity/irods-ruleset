import json
import os

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.drop_zones.dropzone_size import store_dropzone_size


@make(inputs=[0], outputs=[], handler=Output.STORE)
def calculate_mounted_dropzone_sizes(ctx, list_of_tokens):
    """
    Calculate the total size of all files in all currently 'open' dropzones.
    This is an admin rule.
    To be executed on the ingest_resource_host, as only there the mounted dropzone physical paths are available.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    """
    def get_directory_size(path):
        """Calculate total size of all files in a directory."""
        def raise_scan_error(error):
            raise error

        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path, onerror=raise_scan_error):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size

    for token in json.loads(list_of_tokens):
        dropzone_path = f"/nlmumc/ingest/zones/{token}"
        physical_dropzone_path = f"/mnt/ingest/zones/{token}"
        
        try:
            size = get_directory_size(physical_dropzone_path)
        except OSError as error:
            ctx.callback.msiWriteRodsLog(
                f"ERROR: Skipping dropzone size update for '{dropzone_path}': {error}", 0
            )
            continue
        store_dropzone_size(ctx, dropzone_path, size)
