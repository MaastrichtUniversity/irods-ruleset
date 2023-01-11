import json
import irods_types  # pylint: disable=import-error
import session_vars  # pylint: disable=import-error
from dhpythonirodsutils import formatters, loggers
from dhpythonirodsutils.enums import DropzoneState, AuditTailTopics
from genquery import *  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output

# Global vars
COLLECTION_METADATA_INDEX = "collection_metadata"

FALSE_AS_STRING = "false"
TRUE_AS_STRING = "true"


@make(inputs=[0, 1], outputs=[2], handler=Output.STDOUT)
def test_rule_output(ctx, rule_name, args):
    # Case the list argument is empty and the rule expect no argument
    if args == "":
        output = getattr(ctx.callback, rule_name)("")
        ctx.callback.writeLine("stdout", output["arguments"][0])
    # The rule expect some arguments, and test_rule_output expect them as a csv string
    else:
        args = args.split(",")
        # we need to add a empty string as the last index for the output argument.
        args.append("")
        output = getattr(ctx.callback, rule_name)(*args)
        ctx.callback.writeLine("stdout", str(output["arguments"][len(args) - 1]))


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_client_username(ctx):
    # Get the client username
    username = ""
    var_map = session_vars.get_map(ctx.rei)
    user_type = "client_user"
    userrec = var_map.get(user_type, "")
    if userrec:
        username = userrec.get("user_name", "")
    return username


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def is_dropzone_state_ingestable(ctx, state):
    ingestable = False
    if type(state) == str:
        try:
            state = DropzoneState(state)
            ingestable = formatters.get_is_dropzone_state_ingestable(state)
        except ValueError:
            pass
    elif type(state) == DropzoneState:
        ingestable = formatters.get_is_dropzone_state_ingestable(state)
    return ingestable


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def is_dropzone_state_in_active_ingestion(ctx, state):
    in_active_ingestion = True
    if type(state) == str:
        try:
            state = DropzoneState(state)
            in_active_ingestion = formatters.get_is_dropzone_state_in_active_ingestion(state)
        except ValueError:
            pass
    elif type(state) == DropzoneState:
        in_active_ingestion = formatters.get_is_dropzone_state_in_active_ingestion(state)
    return in_active_ingestion


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def format_audit_trail_message(ctx, username, event):
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    return loggers.format_audit_trail_message(int(user_id), AuditTailTopics.POLICY.value, event)


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_env(ctx, key, fatal="false"):
    import os

    value = os.environ.get(key)
    if fatal == TRUE_AS_STRING and not value:
        ctx.callback.msiExit("-1", "Environment variable '{}' has no value".format(key))
    return value


@make(inputs=[0, 1], outputs=[0, 2], handler=Output.STORE)
def json_arrayops_add(ctx, json_str, item):
    """
    Add item to stringified json array
    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    json_str : str
        initial json array
    item : str
        item to be added to the json array

    Returns
    -------
    json_obj : str
        updated json array
    size : str
        size of the updated json array
    """
    if not json_str:
        json_str = "[]"
    json_obj = json.loads(json_str)
    if item == "null":
        size = len(json_obj)
        return json_obj, int(size)
    elif item == "false":
        item = False
    elif item == "true":
        item = True
    else:
        try:
            item = json.loads(item)
        except ValueError:
            item = str(item)
    if not item in json_obj:
        json_obj.append(item)
    size = len(json_obj)
    print(size)
    return json_obj, size


@make(inputs=[0, 1], outputs=[0, 2], handler=Output.STORE)
def json_arrayops_get(ctx, json_str, index):
    """
    get item from stringified json array at the specified index
    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    json_str : str
        json array
    index : str
        index of the item to be returned

    Returns
    -------
    json_obj : str
        update json array
    object : str
        object in json_str at specified index
    """
    if not json_str:
        json_str = "[]"
    json_obj = json.loads(json_str)
    index = int(index)
    object = json_obj[index]
    return json_obj, object

@make(inputs=[0], outputs=[0, 1], handler=Output.STORE)
def json_arrayops_size(ctx, json_str):
    """
    get size of stringified json array
    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    json_str : str
        json array
    Returns
    -------
    json_obj : str
        update json array
    size : str
        size of json array
    """
    if not json_str:
        json_str = "[]"
    json_obj = json.loads(json_str)
    size = len(json_obj)
    return json_obj, size

@make(inputs=[0, 1], outputs=[0], handler=Output.STORE)
def json_objops_add(ctx, json_str, kvp):
    if not json_str:
        json_str = "{}"
    json_obj = json.loads(json_str)
    pairs = kvp.split("++++")
    for key_value_pair in pairs:
        print(key_value_pair)
        pair = key_value_pair.split("=")
        key = pair[0]
        value = pair[1]
        try:
            value = json.loads(value)
        except ValueError:
            value = str(value)
        json_obj[key] = value
    return json_obj

@make(inputs=[0, 1], outputs=[0], handler=Output.STORE)
def json_objops_set(ctx, json_str, kvp):
    if not json_str:
        json_str = "{}"
    json_obj = json.loads(json_str)
    pairs = kvp.split("++++")
    for key_value_pair in pairs:
        print(key_value_pair)
        pair = key_value_pair.split("=")
        key = pair[0]
        value = pair[1]
        try:
            value = json.loads(value)
        except ValueError:
            value = str(value)
        json_obj[key] = value
    return json_obj




def read_data_object_from_irods(ctx, path):
    """This rule gets a JSON schema stored as an iRODS object
    :param ctx:  iRODS context
    :param path: Full path of the file to read (e.g: '/nlmumc/ingest/zones/crazy-frog/instance.json')
    :return: The content of the file to open
    """
    # Open iRODS file
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val["arguments"][1]

    # Read iRODS file
    ret_val = ctx.callback.msiDataObjRead(file_desc, 2 ** 31 - 1, irods_types.BytesBuf())
    read_buf = ret_val["arguments"][2]

    # Convert BytesBuffer to string
    ret_val = ctx.callback.msiBytesBufToStr(read_buf, "")
    output_json = ret_val["arguments"][1]

    # Close iRODS file
    ctx.callback.msiDataObjClose(file_desc, 0)

    return output_json


def get_elastic_search_connection(ctx):
    from elasticsearch import Elasticsearch

    environment = ctx.callback.get_env("ENVIRONMENT", "true", "")["arguments"][2]
    use_ssl = True if environment == "acc" or environment == "prod" else False

    elastic_password = ctx.callback.get_env("ELASTIC_PASSWORD", "true", "")["arguments"][2]
    elastic_host = ctx.callback.get_env("ELASTIC_HOST", "true", "")["arguments"][2]
    elastic_port = ctx.callback.get_env("ELASTIC_PORT", "true", "")["arguments"][2]
    es = Elasticsearch(
        [{"host": elastic_host, "port": elastic_port}], http_auth=("elastic", elastic_password), use_ssl=use_ssl
    )

    return es
