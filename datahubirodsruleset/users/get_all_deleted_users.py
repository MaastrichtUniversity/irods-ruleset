# /rules/tests/run_test.sh -r get_all_deleted_users -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_deleted_users(ctx):

    output = []

    for account in row_iterator("USER_NAME", "META_USER_ATTR_NAME = 'pendingDeletionProcedure'", AS_LIST, ctx.callback):
        output.append(account[0])

    return output
