# /rules/tests/run_test.sh -r get_temporary_password_lifetime -j

@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_temporary_password_lifetime(ctx):
    """
    Get the server temporary password TTL environment variable

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    int
        The temporary password TTL in seconds. e.g: 7776000 => 30 days
    """
    return ctx.callback.msi_getenv("IRODS_TEMP_PASSWORD_LIFETIME", "")["arguments"][1]


