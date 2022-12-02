# /rules/tests/run_test.sh -r get_data_object_size -a "/nlmumc/projects/P000000001/C000000002,instance.json" -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_data_object_size(ctx, collection_path, data_object_name):
    """
    Query the input data object size

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    collection_path: str
        Collection absolute path. e.g: /nlmumc/ingest/direct/excited-sardine, /nlmumc/projects/P000000026/C000000001
    data_object_name: str
        The file name. e.g: instance.json, foobar.txt

    Returns
    -------
    int
        The data object byte size; Returns also 0 if the data object doesn't exist
    """
    query_parameters = "DATA_ID, DATA_SIZE"
    query_conditions = "COLL_NAME = '{}' AND DATA_NAME = '{}'".format(collection_path, data_object_name)

    size = 0

    for result in row_iterator(query_parameters, query_conditions, AS_LIST, ctx.callback):
        size = result[1]

    return size
