# Part of the ingest workflow. To use, call the rule sync_collection_data
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path


@make(inputs=range(5), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, destination_resource, token, destination_collection, depositor, dropzone_type):
    """
    This rule is part the ingest workflow.
    It takes care of actually copying (syncing) the content of the drop-zone into the destination collection.

    Should not be called directly, instead call the wrapper function sync_collection_data.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    destination_resource: str
        The resource that the ingestion should end up in; e.g. 'replRescUM01'
    token: str
        The dropzone token, to locate the source collection; e.g: 'handsome-snake'
    destination_collection: str
        The absolute path to the newly created project collection; e.g: '/nlmumc/projects/P000000018/C000000001'
    depositor: str
        The iRODS username of the user who started the ingestion
    dropzone_type: str
        The type of dropzone to be ingested (mounted or direct)
    """

    # Suppress [B404:blacklist] Consider possible security implications associated with subprocess module.
    # subprocess is only use for subprocess.check_call to execute irsync.
    # The irsync checkcall has 3 variable inputs:
    # * destination_resource, queried directly from iCAT with getCollectionAVU ProjectAVUs.RESOURCE
    # * source_collection, token is validated with format_dropzone_path & check the ACL with getCollectionAVU state
    # * destination_collection, validated with the formatter functions get_*_from_project_collection_path
    from subprocess import CalledProcessError, check_call  # nosec
    import time

    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    if dropzone_type == "mounted":
        source_collection = "/mnt/ingest/zones/{}".format(token)
        # Revoke the user CIFS ACL on the mounted network dropzone folder
        ctx.callback.set_dropzone_cifs_acl(token, "null")
    elif dropzone_type == "direct":
        # We need to prefix the dropzone path with 'i:' to indicate to iRODS that it is an iRODS - iRODS sync
        source_collection = "i:{}".format(dropzone_path)

    RETRY_MAX_NUMBER = 5
    RETRY_SLEEP_NUMBER = 20

    retry_counter = RETRY_MAX_NUMBER
    return_code = 0
    while retry_counter > 0:
        try:
            return_code = check_call(
                [
                    "irsync",
                    "-K",
                    "-v",
                    "-R",
                    destination_resource,
                    "-r",
                    source_collection,
                    "i:" + destination_collection,
                ],
                shell=False,
            )
        except CalledProcessError as err:
            ctx.callback.msiWriteRodsLog("ERROR: irsync: cmd '{}' retcode'{}'".format(err.cmd, err.returncode), 0)
            return_code = 1

        if return_code != 0:
            retry_counter -= 1
            ctx.callback.msiWriteRodsLog("DEBUG: Decrement irsync retry_counter: {}".format(str(retry_counter)), 0)
            time.sleep(RETRY_SLEEP_NUMBER)
        else:
            retry_counter = 0
            ctx.callback.msiWriteRodsLog(
                "INFO: Ingest collection data '{}' was successful".format(source_collection), 0
            )

    if return_code != 0:
        if dropzone_type == "mounted":
            # Re-set the user CIFS ACL on the mounted network dropzone folder
            ctx.callback.set_dropzone_cifs_acl(token, "write")
        # Perform an MSIEXIT here. If this rule is called from the 'perform_ingest' part of the ingest flow,
        # then this error should be caught as a "RuntimeError" and should translate into the creation of a Jira ticket
        # and setting the error-ingestion AVU.
        # If the rule is called by directly calling 'sync_collection_data', then this will just stop execution and *not*
        # create a Jira ticket and *not* set the error-ingestion AVU.
        ctx.callback.msiExit(
            "-1",
            "Error while performing perform_irsync towards '{}:{}'".format(
                destination_collection, destination_resource
            ),
        )
