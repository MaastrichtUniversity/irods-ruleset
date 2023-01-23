# /rules/tests/run_test.sh -r get_user_active_processes -a "true,true,true" -j
import json

from dhpythonirodsutils.formatters import format_string_to_boolean
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_user_active_processes(ctx, query_drop_zones, query_archive, query_export):
    """
    Query all the active process status (ingest, tape archive & DataverseNL export) of the user.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    query_drop_zones: str
        'true'/'false' expected; If true, query the list of active drop_zones & ingest processes
    query_archive: str
        'true'/'false' expected; If true, query the list of active archive & un-archive processes
    query_export: str
        'true'/'false' expected; If true, query the list of active export (to DataverseNl) processes

    Returns
    -------
    dict
        Key => process type; Value => dict|list
    """
    query_drop_zones = format_string_to_boolean(query_drop_zones)
    query_archive = format_string_to_boolean(query_archive)
    query_export = format_string_to_boolean(query_export)

    drop_zones = {}
    if query_drop_zones:
        drop_zones = get_list_active_drop_zones(ctx)

    archive_state = {}
    exporter_state = {}
    if query_archive and query_export:
        archive_state, exporter_state = get_list_active_project_processes(ctx)
    elif query_archive and not query_export:
        archive_state = get_list_active_archives(ctx)
    elif not query_archive and query_export:
        exporter_state = get_list_active_exports(ctx)

    output = {
        "drop_zones": drop_zones,
        "archive": archive_state,
        "export": exporter_state,
    }

    return output


def get_list_active_drop_zones(ctx):
    ret = ctx.callback.listActiveDropZones("false", "")["arguments"][1]
    return json.loads(ret)


def get_list_active_project_processes(ctx):
    archive_state = {}
    exporter_state = {}
    archive_state_attribute = "archiveState"
    exporter_state_attribute = "exporterState"

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME in ('archiveState', 'exporterState') "

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        collection = result[0]
        attribute = result[1]
        value = result[2]

        if attribute == archive_state_attribute:
            archive_state[collection] = value
        elif attribute == exporter_state_attribute:
            exporter_state[collection] = value

    return archive_state, exporter_state


def get_list_active_exports(ctx):
    exporter_state = {}
    # exporter_state_attribute = "exporterState"

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME = 'exporterState' "

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        collection = result[0]
        value = result[2]
        exporter_state[collection] = value

    return exporter_state


def get_list_active_archives(ctx):
    archive_state = {}
    # archive_state_attribute = "archiveState"

    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME = 'archiveState' "

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        collection = result[0]
        value = result[2]
        archive_state[collection] = value

    return archive_state
