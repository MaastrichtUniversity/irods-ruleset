from dhpythonirodsutils import formatters, exceptions
from genquery import *  # pylint: disable=import-error


def convert_to_current_timezone(date, date_format="%Y-%m-%d %H:%M:%S"):
    import pytz

    old_timezone = pytz.timezone("UTC")
    new_timezone = pytz.timezone("Europe/Amsterdam")
    return old_timezone.localize(date).astimezone(new_timezone).strftime(date_format)


def format_dropzone_path(ctx, token, dropzone_type):
    try:
        dropzone_path = formatters.format_dropzone_path(token, dropzone_type)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid dropzone type, supported 'mounted' and 'direct', got '{dropzone_type}'."
        )
    return dropzone_path


def format_project_path(ctx, project_id):
    try:
        project_path = formatters.format_project_path(project_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit("-1", f"Invalid project ID format: '{project_id}'")
    return project_path


def format_project_collection_path(ctx, project_id, collection_id):
    try:
        project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid project ID or collection ID format: '{project_id}/{collection_id}'"
        )
    return project_collection_path


def format_instance_collection_path(ctx, project_id, collection_id):
    try:
        instance_path = formatters.format_instance_collection_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid project ID or collection ID format: '{project_id}/{collection_id}'"
        )
    return instance_path


def format_schema_collection_path(ctx, project_id, collection_id):
    try:
        schema_path = formatters.format_schema_collection_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid project ID or collection ID format: '{project_id}/{collection_id}'"
        )
    return schema_path


def format_instance_versioned_collection_path(ctx, project_id, collection_id, version):
    try:
        instance_path = formatters.format_instance_versioned_collection_path(project_id, collection_id, version)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid project ID or collection ID format: '{project_id}/{collection_id}'"
        )
    return instance_path


def format_schema_versioned_collection_path(ctx, project_id, collection_id, version):
    try:
        schema_path = formatters.format_schema_versioned_collection_path(project_id, collection_id, version)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid project ID or collection ID format: '{project_id}/{collection_id}'"
        )
    return schema_path


def format_metadata_versions_path(ctx, project_id, collection_id):
    try:
        metadata_versions_path = formatters.format_metadata_versions_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", f"Invalid project ID or collection ID format: '{project_id}/{collection_id}'"
        )
    return metadata_versions_path


def format_human_bytes(B):
    """
    Return the given bytes as a human friendly KB, MB, GB, or TB string.
    """
    B = float(B)
    KB = float(1024)
    MB = float(KB**2)  # 1,048,576
    GB = float(KB**3)  # 1,073,741,824
    TB = float(KB**4)  # 1,099,511,627,776

    if B < KB:
        return f"{B} {'Bytes' if 0 == B > 1 else 'Byte'}"
    elif KB <= B < MB:
        return f"{B / KB:.2f} KB"
    elif MB <= B < GB:
        return f"{B / MB:.2f} MB"
    elif GB <= B < TB:
        return f"{B / GB:.2f} GB"
    elif TB <= B:
        return f"{B / TB:.2f} TB"
