# /rules/tests/run_test.sh -r get_user_active_processes -a "true,true,true,true" -u dlinssen -j
import json

from dhpythonirodsutils.formatters import (
    format_string_to_boolean,
    get_project_id_from_project_collection_path,
    get_collection_id_from_project_collection_path,
    get_project_path_from_project_collection_path,
)
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING


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

    drop_zones = {}
    if query_drop_zones:
        drop_zones = get_list_active_drop_zones(ctx)

    archive_state = []
    unarchive_state = []
    exporter_state = {}
    if query_archive and query_unarchive and query_export:
        archive_state, unarchive_state, exporter_state = get_list_active_project_processes(ctx)
    elif query_archive and query_unarchive and not query_export:
        archive_state = get_list_active_archives(ctx)
        unarchive_state = get_list_active_unarchives()
    elif query_archive and not query_unarchive and query_export:
        archive_state = get_list_active_archives(ctx)
        exporter_state = get_list_active_exports(ctx)
    elif not query_archive and query_unarchive and query_export:
        unarchive_state = get_list_active_unarchives()
        exporter_state = get_list_active_exports(ctx)
    elif query_archive and not query_unarchive and not query_export:
        archive_state = get_list_active_archives(ctx)
    elif not query_archive and not query_unarchive and not query_export:
        unarchive_state = get_list_active_unarchives()
    elif not query_archive and not query_unarchive and query_export:
        exporter_state = get_list_active_exports(ctx)

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
    archive_state_attribute = "archiveState"
    unarchive_state_attribute = "unArchiveState"
    exporter_state_attribute = "exporterState"

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}', '{}') ".format(
        archive_state_attribute, unarchive_state_attribute, exporter_state_attribute
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        collection = result[0]
        attribute = result[1]
        value = result[2]

        if attribute == archive_state_attribute:
            archive_state.append(get_process_information(ctx, collection, "SURFSara Tape", value))
        if attribute == unarchive_state_attribute:
            unarchive_state.append(get_process_information(ctx, collection, "SURFSara Tape", value))
        elif attribute == exporter_state_attribute:
            state_split = value.split(":")
            exporter_state.append(get_process_information(ctx, collection, state_split[0], state_split[1]))

    return archive_state, unarchive_state, exporter_state


def get_list_active_exports(ctx):
    exporter_state = []

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME = 'exporterState' "

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        value = result[2]
        state_split = value.split(":")
        exporter_state.append(get_process_information(ctx, result[0], state_split[0], state_split[1]))

    return exporter_state


def get_list_active_archives(ctx):
    archive_state = []

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME = 'archiveState' "

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        archive_state.append(get_process_information(ctx, result[0], "SURFSara Tape", result[2]))

    return archive_state


def get_list_active_unarchives(ctx):
    unarchive_state = []

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME = 'unArchiveState' "

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        unarchive_state.append(get_process_information(ctx, result[0], "SURFSara Tape", result[2]))

    return unarchive_state


def get_process_information(ctx, project_collection_path, repository, state):
    project_path = get_project_path_from_project_collection_path(project_collection_path)
    return {
        "project": get_project_id_from_project_collection_path(project_collection_path),
        "collection": get_collection_id_from_project_collection_path(project_collection_path),
        "project_title": ctx.callback.getCollectionAVU(project_path, "title", "", "", TRUE_AS_STRING)["arguments"][2],
        "title": ctx.callback.getCollectionAVU(project_collection_path, "title", "", "", TRUE_AS_STRING)["arguments"][
            2
        ],
        "state": state,
        "repository": repository,
    }
