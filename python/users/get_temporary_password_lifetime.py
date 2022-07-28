# /rules/tests/run_test.sh -r get_temporary_password_lifetime -j
@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_temporary_password_lifetime(ctx):
    return ctx.callback.msi_getenv("IRODS_TEMP_PASSWORD_LIFETIME", "")["arguments"][1]


