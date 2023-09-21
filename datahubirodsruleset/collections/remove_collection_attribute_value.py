# /rules/tests/run_test.sh -r remove_collection_attribute_value -a "/nlmumc/projects/P000000008,deletionState"

import irods_types  # pylint: disable=import-error
import json
from datahubirodsruleset.decorator import make, Output


# TODO crash on multiple instances of the attribute
@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def remove_collection_attribute_value(ctx, project_collection_path, attribute):
    """
    Remove the attribute value from a project collection given an attribute

    Parameters
    ----------
    attribute
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the collection
    attribute : str
        The attribute to delete
    """
    output = ctx.get_collection_attribute_value(project_collection_path, attribute, "result")["arguments"][2]
    value = json.loads(output)["value"]

    if value != "":
        kvp = ctx.callback.msiString2KeyValPair("{}={}".format(attribute, value), irods_types.BytesBuf())["arguments"][
            1
        ]
        ctx.callback.msiRemoveKeyValuePairsFromObj(kvp, project_collection_path, "-C")
        ctx.callback.msiWriteRodsLog(
            "INFO: {}: Remove AVU '{}':'{}'".format(project_collection_path, attribute, value), 0
        )
