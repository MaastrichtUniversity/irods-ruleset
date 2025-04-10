# /rules/tests/run_test.sh -r get_user_active_processes -a "true,true,true" -u dlinssen -j
import json

from dhpythonirodsutils.enums import (
    ProcessAttribute,
    ProcessType,
    ProcessState,
    DropzoneState,
    ArchiveState,
    UnarchiveState
)

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


ARCHIVAL_REPOSITORY_NAME = "SURFSara Tape"


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_user_active_processes(ctx, query_drop_zones, query_archive, query_unarchive):
    """
    Query all the active process status (ingest and tape archive ) of the user.

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

    Returns
    -------
    dict
        Key => process type; Value => dict|list
    """
    query_drop_zones = format_string_to_boolean(query_drop_zones)
    query_archive = format_string_to_boolean(query_archive)
    query_unarchive = format_string_to_boolean(query_unarchive)

    output = {
        ProcessState.COMPLETED.value: [],
        ProcessState.ERROR.value: [],
        ProcessState.IN_PROGRESS.value: [],
        ProcessState.OPEN.value: [],
    }

    if query_drop_zones:
        get_list_active_drop_zones(ctx, output)

    if query_archive and query_unarchive:
        get_list_active_project_processes(ctx, output)
    else:
        if query_archive:
            get_list_active_project_process(ctx, ProcessAttribute.ARCHIVE, ProcessType.ARCHIVE, output)
        if query_unarchive:
            get_list_active_project_process(ctx, ProcessAttribute.UNARCHIVE, ProcessType.UNARCHIVE, output)

    return output


def get_drop_zone_percentage_ingested(ctx, drop_zone):
    """
    Calculate the current percentage of data ingested towards the project collection destination.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    drop_zone: dict
        A drop-zone object item from listActiveDropZones

    Returns
    -------
    float
        The drop-zone percentage ingested
    """
    percentage = 0
    if not drop_zone["destination"]:
        return percentage

    collection_path = format_project_collection_path(drop_zone["project"], drop_zone["destination"])
    ret = ctx.callback.get_collection_attribute_value(collection_path, "sizeIngested", "")["arguments"][2]
    size_ingested = json.loads(ret)["value"]
    if drop_zone["state"] == DropzoneState.INGESTED.value:
        percentage = 100
    elif size_ingested and int(drop_zone["totalSize"]) > 0:
        percentage = round(float(size_ingested) / float(drop_zone["totalSize"]) * 100, 0)

    return percentage


def get_list_active_drop_zones(ctx, output):
    """
    Query the list of active drop-zones, add extra information and put the drop-zones to the output dictionary.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    output: dict
        The rule output to extend
    """
    ret = ctx.callback.listActiveDropZones("false", "")["arguments"][1]
    drop_zones = json.loads(ret)

    for drop_zone in drop_zones:
        drop_zone["process_type"] = ProcessType.DROP_ZONE.value
        drop_zone["percentage_ingested"] = get_drop_zone_percentage_ingested(ctx, drop_zone)
        add_process_to_output(drop_zone, output)


def get_list_active_project_processes(ctx, output):
    """
    Query the list of all active project processes, add extra information and put the processes to the output dict.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    output: dict
        The rule output to extend
    """
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}') AND COLL_PARENT_NAME LIKE '/nlmumc/projects/%' ".format(
        ProcessAttribute.ARCHIVE.value, ProcessAttribute.UNARCHIVE.value
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        attribute = result[1]
        process = None
        if attribute == ProcessAttribute.ARCHIVE.value:
            process = get_project_process_information(ctx, result, ProcessType.ARCHIVE)
        if attribute == ProcessAttribute.UNARCHIVE.value:
            process = get_project_process_information(ctx, result, ProcessType.UNARCHIVE)
        add_process_to_output(process, output)


def get_list_active_project_process(ctx, attribute, process_type, output):
    """
    Query the list for specific (as specified by the parameter) active project processes,
    add extra information and put the processes to the output dict.
    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    attribute: ProcessAttribute
        The active process attribute to query
    process_type: ProcessType
    output: dict
        The rule output to extend
    """
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID"
    conditions = "META_COLL_ATTR_NAME = '{}' AND COLL_PARENT_NAME LIKE '/nlmumc/projects/%' ".format(attribute.value)

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        process = get_project_process_information(ctx, result, process_type)
        add_process_to_output(process, output)


def add_process_to_output(process, output):
    """
    Based on the process state, append the item to the correct output list.

    Parameters
    ----------
    process: dict
        The process object to add to the output dict
    output: dict
        The rule output to extend
    """
    completed_state = [DropzoneState.INGESTED.value, UnarchiveState.UNARCHIVE_DONE.value, ArchiveState.ARCHIVE_DONE.value]
    if process["state"] in [DropzoneState.OPEN.value, DropzoneState.WARNING_VALIDATION_INCORRECT.value, DropzoneState.WARNING_UNSUPPORTED_CHARACTER.value]:
        output[ProcessState.OPEN.value].append(process)
    elif process["state"] in completed_state:
        output[ProcessState.COMPLETED.value].append(process)
    elif "error" in process["state"]:
        output[ProcessState.ERROR.value].append(process)
    else:
        output[ProcessState.IN_PROGRESS.value].append(process)


def get_process_repository_and_state(query_result, process_type):
    """
    For export process type, the repository and state values are both concatenated into the collection metadata
    attribute value, separated by ":".
    This function takes care of handling the different parsing method.

    Parameters
    ----------
    query_result: list[str]
        The active project process query result.
    process_type: ProcessType
    """
    state = query_result[2]
    repository = ""

    if process_type in [ProcessType.ARCHIVE, ProcessType.UNARCHIVE]:
        repository = ARCHIVAL_REPOSITORY_NAME

    return repository, state


def get_project_process_information(ctx, query_result, process_type):
    """
    Gather the project process information, then create and return a project process dictionary.

    Parameters
    ----------
    ctx
    query_result: list[str]
        The active project process query result.
    process_type: ProcessType

    Returns
    -------
    dict
        project process information
    """
    project_collection_path = query_result[0]
    process_id = query_result[3]
    repository, state = get_process_repository_and_state(query_result, process_type)
    project_path = get_project_path_from_project_collection_path(project_collection_path)

    process = {
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

    return process
