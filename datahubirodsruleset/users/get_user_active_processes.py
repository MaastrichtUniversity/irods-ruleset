# /rules/tests/run_test.sh -r get_user_active_processes -a "true,true,true,true" -u dlinssen -j
import json
from enum import Enum

from dhpythonirodsutils.formatters import (
    format_string_to_boolean,
    format_project_collection_path,
    get_project_id_from_project_collection_path,
    get_collection_id_from_project_collection_path,
    get_project_path_from_project_collection_path,
)
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING


class ProcessAttribute(Enum):
    """Enumerate all active process attribute names"""

    ARCHIVE = "archiveState"
    UNARCHIVE = "unArchiveState"
    EXPORTER = "exporterState"
    # INGEST = "state"


class ProcessType(Enum):
    """Enumerate the type of project collection process type"""

    ARCHIVE = "archive"
    DROP_ZONE = "drop_zone"
    EXPORT = "export"
    UNARCHIVE = "unarchive"


class ProcessState(Enum):
    """Enumerate the type of project collection process type"""

    COMPLETED = "completed"
    ERROR = "error"
    IN_PROGRESS = "in_progress"
    OPEN = "open"


ARCHIVAL_REPOSITORY_NAME = "SURFSara Tape"


@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def get_user_active_processes(ctx, query_drop_zones, query_archive, query_unarchive, query_export):
    """
    Query all the active process status (ingest, tape archive & DataverseNL export) of the user.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    query_drop_zones: str
        'true'/'false' expected; If true, query the list of active drop_zones & ingest processes
    query_archive: str
        'true'/'false' expected; If true, query the list of active archive processes
    query_unarchive: str
        'true'/'false' expected; If true, query the list of active un-archive processes
    query_export: str
        'true'/'false' expected; If true, query the list of active export (to DataverseNl) processes

    Returns
    -------
    dict
        Key => process type; Value => dict|list
    """
    query_drop_zones = format_string_to_boolean(query_drop_zones)
    query_archive = format_string_to_boolean(query_archive)
    query_unarchive = format_string_to_boolean(query_unarchive)
    query_export = format_string_to_boolean(query_export)

    output = {
        ProcessState.COMPLETED.value: [],
        ProcessState.ERROR.value: [],
        ProcessState.IN_PROGRESS.value: [],
        ProcessState.OPEN.value: [],
    }

    if query_drop_zones:
        get_list_active_drop_zones(ctx, output)

    if query_archive and query_unarchive and query_export:
        get_list_active_project_processes(ctx, output)
    else:
        if query_archive:
            get_list_active_project_process(ctx, ProcessAttribute.ARCHIVE, ProcessType.ARCHIVE, output)
        if query_unarchive:
            get_list_active_project_process(ctx, ProcessAttribute.UNARCHIVE, ProcessType.UNARCHIVE, output)
        if query_export:
            get_list_active_project_process(ctx, ProcessAttribute.EXPORTER, ProcessType.EXPORT, output)

    return output


def get_drop_zone_percentage_ingested(ctx, drop_zone):
    percentage = 0
    if not drop_zone["destination"]:
        return percentage

    collection_path = format_project_collection_path(drop_zone["project"], drop_zone["destination"])
    ret = ctx.callback.get_collection_attribute_value(collection_path, "sizeIngested", "")["arguments"][2]
    size_ingested = json.loads(ret)["value"]
    if drop_zone["state"] == "ingested":
        percentage = 100
    elif size_ingested and int(drop_zone["totalSize"]) > 0:
        percentage = round(float(size_ingested) / float(drop_zone["totalSize"]) * 100, 0)

    return percentage


def get_list_active_drop_zones(ctx, output):
    """

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    output: dict
    """
    ret = ctx.callback.listActiveDropZones("false", "")["arguments"][1]
    drop_zones = json.loads(ret)

    for drop_zone in drop_zones:
        drop_zone["process_type"] = ProcessType.DROP_ZONE.value
        drop_zone["percentage_ingested"] = get_drop_zone_percentage_ingested(ctx, drop_zone)
        if drop_zone["state"] == "open":
            output[ProcessState.OPEN.value].append(drop_zone)
        elif drop_zone["state"] == "ingested":
            output[ProcessState.COMPLETED.value].append(drop_zone)
        elif "error" in drop_zone["state"]:
            output[ProcessState.ERROR.value].append(drop_zone)
        else:
            output[ProcessState.IN_PROGRESS.value].append(drop_zone)


def parse_process_state(process, output):
    completed_state = ["unarchive-done", "archive-done", "exported"]
    if process["state"] in completed_state:
        output[ProcessState.COMPLETED.value].append(process)
    elif "error" in process["state"]:
        output[ProcessState.ERROR.value].append(process)
    else:
        output[ProcessState.IN_PROGRESS.value].append(process)


def get_list_active_project_processes(ctx, output):
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}', '{}') AND COLL_PARENT_NAME LIKE '/nlmumc/projects/%' ".format(
        ProcessAttribute.ARCHIVE.value,
        ProcessAttribute.UNARCHIVE.value,
        ProcessAttribute.EXPORTER.value,
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        attribute = result[1]
        process = None
        if attribute == ProcessAttribute.ARCHIVE.value:
            process = get_process_information(ctx, result, ProcessType.ARCHIVE)
        if attribute == ProcessAttribute.UNARCHIVE.value:
            process = get_process_information(ctx, result, ProcessType.UNARCHIVE)
        elif attribute == ProcessAttribute.EXPORTER.value:
            process = get_process_information(ctx, result, ProcessType.EXPORT)
        parse_process_state(process, output)


def get_list_active_project_process(ctx, attribute, process_type, output):
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID"
    conditions = "META_COLL_ATTR_NAME = '{}' AND COLL_PARENT_NAME LIKE '/nlmumc/projects/%' ".format(attribute.value)

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        process = get_process_information(ctx, result, process_type)
        parse_process_state(process, output)


def get_process_information(ctx, result, process_type):
    project_collection_path = result[0]
    state = result[2]
    process_id = result[3]
    repository = ""

    if process_type is ProcessType.ARCHIVE or process_type is ProcessType.UNARCHIVE:
        repository = ARCHIVAL_REPOSITORY_NAME
    elif process_type is ProcessType.EXPORT:
        state_split = result[2].split(":")
        repository = state_split[0]
        state = state_split[1]

    project_path = get_project_path_from_project_collection_path(project_collection_path)
    return {
        "project_id": get_project_id_from_project_collection_path(project_collection_path),
        "collection_id": get_collection_id_from_project_collection_path(project_collection_path),
        "project_title": ctx.callback.getCollectionAVU(project_path, "title", "", "", TRUE_AS_STRING)["arguments"][2],
        "collection_title": ctx.callback.getCollectionAVU(project_collection_path, "title", "", "", TRUE_AS_STRING)[
            "arguments"
        ][2],
        "state": state.strip(),
        "repository": repository,
        "process_id": process_id,
        "process_type": process_type.value,
    }
