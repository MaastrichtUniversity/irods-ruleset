# /rules/tests/run_test.sh -r set_dropzone_cifs_acl -a "vast-dove,null"
import json
from datahubirodsruleset.core import make, Output, format_dropzone_path, TRUE_AS_STRING


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def set_dropzone_cifs_acl(ctx, token, access):
    """
    Change the user network mounted dropzone folder ACL.
    Just before starting to ingest the network mounted dropzone folder into iRODS, the user's access is revoked at
    root level, to prevent editing the content while an 'irsync' is ongoing.
    If an ingestion error occurs, the user ACL is re-established.

    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    token: str
       The dropzone token
    access: str
       The access to assign. e.g: "write" & "null"
    """
    # Suppress [B404:blacklist] Consider possible security implications associated with subprocess module.
    # subprocess is only use for subprocess.check_call to execute 'setcifsacl' via the 'ingest-zone-access' scripts.
    # The '*-ingest-zone-access' checkcall has 3 variable inputs:
    # * remove_script_path, hard-coded path
    # * vo_person_external_id, queried directly from iCAT to the user AVU voPersonExternalID
    # * source_collection, token is validated with format_dropzone_path & check the ACL with getCollectionAVU creator
    from subprocess import CalledProcessError, check_call  # nosec

    source_collection = "/mnt/ingest/zones/{}".format(token)
    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    script_path = ""
    if access == "null":
        script_path = "/var/lib/irods/msiExecCmd_bin/remove-ingest-zone-access.sh"
    elif access == "write":
        script_path = "/var/lib/irods/msiExecCmd_bin/add-ingest-zone-access.sh"
    else:
        ctx.callback.msiExit(
            "-1", "Invalid setcifsacl access parameter '{}'! Aborting perform_irsync".format(access)
        )

    creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
    ret = ctx.callback.get_user_attribute_value(creator, "voPersonExternalID", TRUE_AS_STRING, "")[
        "arguments"
    ][3]
    vo_person_external_id = json.loads(ret)["value"]
    try:
        check_call([script_path, vo_person_external_id,  source_collection], shell=False)
    except CalledProcessError as err:
        message = "ERROR: set_dropzone_cifs_acl: cmd '{}' retcode'{}'".format(err.cmd, err.returncode)
        ctx.callback.msiWriteRodsLog(message, 0)
