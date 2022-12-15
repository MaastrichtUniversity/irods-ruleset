import irods_types  # pylint: disable=import-error
import json

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def remove_size_ingested_avu(ctx, project_collection_path):
    """
    Set the ACL of a given collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
        The absolute path of the collection
    """
    attribute = "sizeIngested"
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
