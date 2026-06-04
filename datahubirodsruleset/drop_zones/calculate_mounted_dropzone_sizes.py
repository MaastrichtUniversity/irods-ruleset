import json
import os
from datetime import datetime, timezone

from datahubirodsruleset.decorator import make, Output


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
        total_size = 0
        if os.path.exists(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        pass
        return total_size

    for token in json.loads(list_of_tokens):
        dropzone_path = f"/nlmumc/ingest/zones/{token}"
        physical_dropzone_path = f"/mnt/ingest/zones/{token}"
        
        size = get_directory_size(physical_dropzone_path)
        ctx.callback.setCollectionAVU(dropzone_path, "dropzoneSize", str(size))
        ctx.callback.setCollectionAVU(
            dropzone_path, "dropzoneSizeUpdated", str(int(datetime.now().timestamp()))
        )
