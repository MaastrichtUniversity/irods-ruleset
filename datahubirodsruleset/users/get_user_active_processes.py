# /rules/tests/run_test.sh -r get_user_active_processes -a "true,true,true,true" -u dlinssen -j
import json
from enum import Enum

from dhpythonirodsutils.formatters import (
    format_string_to_boolean,
    get_project_id_from_project_collection_path,
    get_collection_id_from_project_collection_path,
    get_project_path_from_project_collection_path,
)
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING


class ActiveProcessAttribute(Enum):
    """Enumerate all active process attribute names"""

    ARCHIVE = "archiveState"
    UNARCHIVE = "unArchiveState"
    EXPORTER = "exporterState"
    # INGEST = "State"


class ProcessType(Enum):
    """Enumerate the type of project collection process type"""

    ARCHIVAL = "archival"
    EXPORT = "export"


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

    drop_zones = []
    if query_drop_zones:
        drop_zones = get_list_active_drop_zones(ctx)

    archive_state = []
    unarchive_state = []
    exporter_state = []
    if query_archive and query_unarchive and query_export:
        archive_state, unarchive_state, exporter_state = get_list_active_project_processes(ctx)
    else:
        if query_archive:
            archive_state = get_list_active_project_process(ctx, ActiveProcessAttribute.ARCHIVE, ProcessType.ARCHIVAL)
        if query_unarchive:
            unarchive_state = get_list_active_project_process(
                ctx, ActiveProcessAttribute.UNARCHIVE, ProcessType.ARCHIVAL
            )
        if query_export:
            exporter_state = get_list_active_project_process(ctx, ActiveProcessAttribute.EXPORTER, ProcessType.EXPORT)

    output = {
        "drop_zones": drop_zones,
        "archive": archive_state,
        "unarchive": unarchive_state,
        "export": exporter_state,
    }

    return output


def get_list_active_drop_zones(ctx):
    ret = ctx.callback.listActiveDropZones("false", "")["arguments"][1]
    return json.loads(ret)


def get_list_active_project_processes(ctx):
    archive_state = []
    unarchive_state = []
    exporter_state = []

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}', '{}') AND COLL_PARENT_NAME LIKE '/nlmumc/projects/%' ".format(
        ActiveProcessAttribute.ARCHIVE.value,
        ActiveProcessAttribute.UNARCHIVE.value,
        ActiveProcessAttribute.EXPORTER.value,
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        attribute = result[1]

        if attribute == ActiveProcessAttribute.ARCHIVE.value:
            archive_state.append(get_process_information(ctx, result, ProcessType.ARCHIVAL))
        if attribute == ActiveProcessAttribute.UNARCHIVE.value:
            unarchive_state.append(get_process_information(ctx, result, ProcessType.ARCHIVAL))
        elif attribute == ActiveProcessAttribute.EXPORTER.value:
            exporter_state.append(get_process_information(ctx, result, ProcessType.EXPORT))

    return archive_state, unarchive_state, exporter_state


def get_list_active_project_process(ctx, attribute, process_type):
    output = []
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID"
    conditions = "META_COLL_ATTR_NAME = '{}' AND COLL_PARENT_NAME LIKE '/nlmumc/projects/%' ".format(attribute.value)

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        output.append(get_process_information(ctx, result, process_type))

    return output


def get_process_information(ctx, result, process_type):
    project_collection_path = result[0]
    state = result[2]
    process_id = result[3]
    repository = ""

    if process_type is ProcessType.ARCHIVAL:
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
    }
