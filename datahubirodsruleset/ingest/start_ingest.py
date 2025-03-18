# To be called as an admin at all times
# /rules/tests/run_test.sh -r start_ingest -a "dlinssen,handsome-snake,direct"
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def start_ingest(ctx, depositor, token, dropzone_type):
    """
    Start to ingest
       Irods pre-ingest checks
       Metadata pre-ingest checks
        If those went well, call perform ingest

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    depositor: str
        The iRODS username of the user who started the ingestion, e.g: 'dlinssen'
    token: str
        The token, eg 'crazy-frog'
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'
    """

    ctx.delayExec(
        "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        "validate_and_ingest_dropzone('{}', '{}', '{}')".format(token, depositor, dropzone_type),
        "",
    )
