# /rules/tests/run_test.sh -r calculate_direct_dropzone_size_files -a "crazy-frog"
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def calculate_direct_dropzone_size_files(ctx, token):
    """
    Calculate the number of files and the total size in bytes for a direct dropzone

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token : str
        The token (i.e. 'vast-chinchilla')

    Returns
    -------
    dict
         "total_file_count" : int: The total number of files in the dropzone
         "total_file_size" : int : The dropzone size in bytes
    """
    dropzone_path = formatters.format_dropzone_path(token, "direct")
    total_file_count = 0
    total_file_size = 0

    # WARNING: this query only works as long the data objects are not replicated
    for result in row_iterator(
        "count(DATA_NAME),sum(DATA_SIZE)", "COLL_NAME like '{}%'".format(dropzone_path), AS_LIST, ctx.callback
    ):
        total_file_count = int(result[0])
        total_file_size = int(result[1])

    return {"total_file_count": total_file_count, "total_file_size": total_file_size}
