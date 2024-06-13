# TODO explain the nosec
import json
from subprocess import check_call, CalledProcessError  # nosec

import irods_types  # pylint: disable=import-error
import session_vars  # pylint: disable=import-error
from dhpythonirodsutils import formatters, loggers
from dhpythonirodsutils.enums import DropzoneState, AuditTailTopics, ProjectAVUs
from genquery import *  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path

# Global vars
COLLECTION_METADATA_INDEX = "collection_metadata"

FALSE_AS_STRING = "false"
TRUE_AS_STRING = "true"

IRODS_ZONE_BASE_PATH = "/nlmumc"
IRODS_BACKUP_ACL_BASE_PATH = "/nlmumc/backupACL"


@make(inputs=[0, 1], outputs=[2], handler=Output.STDOUT)
def test_rule_output(ctx, rule_name, args):
    # Case the list argument is empty and the rule expect no argument
    if args == "":
        output = getattr(ctx.callback, rule_name)("")
        ctx.callback.writeLine("stdout", output["arguments"][0])
    # The rule expect some arguments, and test_rule_output expect them as a csv string
    else:
        args = args.split(",")
        # we need to add an empty string as the last index for the output argument.
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
def get_project_id_from_project_collection_path(ctx, objectpath):
    project_id = formatters.get_project_id_from_project_collection_path(objectpath)
    return project_id


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_collection_id_from_project_collection_path(ctx, objectpath):
    collection_id = formatters.get_collection_id_from_project_collection_path(objectpath)
    return collection_id


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_collection_path(ctx, project_id, collection_id):
    project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
    return project_collection_path


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


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def submit_automated_support_request(ctx, username, description, error_message):
    """
    This rule submits an automated support request to the Jira Service Desk Cloud instance through
    our help center backend.

    /rules/tests/run_test.sh -r submit_automated_support_request -a "email@example.org,description,error"

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username: str
        irods user who started the process to receive an email about the ticket
    description: str
       Description to be shown in the ticket
    error_message: str
        Error message to display in Jira Service Desk

    Returns
    -------
    str
        Jira Service desk issue key for newly created ticket
    """
    import requests
    import json
    from datetime import datetime

    ret = ctx.get_user_attribute_value(username, "email", FALSE_AS_STRING, "result")["arguments"][3]
    email = json.loads(ret)["value"]
    if email == "":
        email = "datahub-support@maastrichtuniversity.nl"

    # Get the Help Center Backend url
    help_center_backend_base = ctx.callback.get_env("HC_BACKEND_URL", TRUE_AS_STRING, "")["arguments"][2]
    help_center_request_endpoint = "{}/help_backend/submit_request/automated_process_support".format(
        help_center_backend_base
    )

    error_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    request_json = {
        "email": email,
        "description": description,
        "error_timestamp": error_timestamp,
        "error_message": error_message,
    }
    try:
        response = requests.post(
            help_center_request_endpoint,
            json=request_json,
        )
        if response.ok:
            issue_key = response.json()["issueKey"]
            ctx.callback.msiWriteRodsLog("Support ticket '{}' created after process error".format(issue_key), 0)

        else:
            ctx.callback.msiWriteRodsLog(
                "ERROR: Response Help center backend not HTTP OK: '{}'".format(response.status_code), 0
            )
    except requests.exceptions.RequestException as e:
        ctx.callback.msiWriteRodsLog(
            "ERROR: Exception while requesting Support ticket after process error '{}'".format(e), 0
        )


def read_data_object_from_irods(ctx, path):
    """This rule gets a JSON schema stored as an iRODS object
    :param ctx:  iRODS context
    :param path: Full path of the file to read (e.g: '/nlmumc/ingest/zones/crazy-frog/instance.json')
    :return: The content of the file to open
    """
    # Open iRODS file
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val["arguments"][1]

    ret_stats = ctx.callback.msiObjStat(path, irods_types.RodsObjStat())
    stats = ret_stats["arguments"][1]
    size = int(stats.objSize)

    # Read iRODS file
    ret_val = ctx.callback.msiDataObjRead(file_desc, size, irods_types.BytesBuf())
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


def icp_wrapper(ctx, source, destination, project_id, overwrite):
    """
    Workaround wrapper function to execute iRODS data object copy.
    Execute an 'icp' with a sub-process instead of msiDataObjCopy.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    source: str
        Full absolute iRODS logical source path
    destination: str
        Full absolute iRODS logical destination path
    project_id: str
        e.g: P000000010
    overwrite: bool
        write data-object even it exists already; overwrite it
    """
    destination_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]

    icp_cmd = ["icp", "-R", destination_resource, source, destination]
    if overwrite:
        icp_cmd = ["icp", "-f", "-R", destination_resource, source, destination]

    try:
        check_call(["ichmod", "-M", "own", "rods", source], shell=False)
        check_call(icp_cmd, shell=False)
    except CalledProcessError as err:
        ctx.callback.msiWriteRodsLog("ERROR: icp: cmd '{}' retcode'{}'".format(err.cmd, err.returncode), 0)
        ctx.callback.msiExit("-1", "ERROR: icp failed for '{}'->'{}'".format(source, destination))


def iput_wrapper(ctx, source, destination, project_id, overwrite):
    """
    Added in 4.3.2 development, review if still necessary on next version upgrade!
    This is because the microserice msiDataObjPut is only usable when called by a client with 'irule'
    https://docs.irods.org/4.3.2/doxygen/reDataObjOpr_8cpp.html#a8076987f48ddb90fdfc0a7f5c5dcf13b
    Workaround wrapper function to execute iRODS data object put.
    Execute an 'iput' with a sub-process instead of msiDataObjPut.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    source: str
        Full absolute local logical source path
    destination: str
        Full absolute iRODS logical destination path
    project_id: str
        e.g: P000000010
    overwrite: bool
        write data-object even it exists already; overwrite it
    """
    destination_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]
    iput_cmd = ["iput", "-R", destination_resource, source, destination]
    
    if overwrite:
        iput_cmd = ["iput", "-f", "-R", destination_resource, source, destination]

    try:
        check_call(["ichmod", "-M", "own", "rods", destination], shell=False)
        check_call(iput_cmd, shell=False)
    except CalledProcessError as err:
        ctx.callback.msiWriteRodsLog("ERROR: iput: cmd '{}' retcode'{}'".format(err.cmd, err.returncode), 0)
        ctx.callback.msiExit("-1", "ERROR: iput failed for '{}'->'{}'".format(source, destination))

def apply_batch_acl_operation(ctx, collection_path, acl_operations):
    """
    Apply the ACL operations in a single execution

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    collection_path : str
        The absolute path of iRODS collection
    acl_operations :  list[dict]
        The list of ACL operations in the expected format
    """
    json_input = {
        "logical_path": collection_path,
        "operations": acl_operations,
    }
    str_json_input = json.dumps(json_input)
    ctx.msi_atomic_apply_acl_operations(str_json_input, "")
    message = "INFO: Apply batch ACL operations for {}".format(collection_path)
    ctx.callback.msiWriteRodsLog(message, 0)


def apply_batch_collection_avu_operation(ctx, collection_path, operation_type, metadata):
    """
    Apply the AVU operations in a single execution

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    collection_path : str
        The absolute path of iRODS collection
    operation_type : str
        'add' or 'remove'
    metadata : dict
        Contains the AVUs to apply. key: attribute; value: value
    """
    json_input = {
        "entity_name": collection_path,
        "entity_type": "collection",
        "operations": create_metadata_operations(operation_type, metadata),
    }
    str_json_input = json.dumps(json_input)
    ctx.msi_atomic_apply_metadata_operations(str_json_input, "")
    message = "INFO: {} deletion metadata for {}".format(operation_type.capitalize(), collection_path)
    ctx.callback.msiWriteRodsLog(message, 0)


def create_metadata_operations(operation_type, metadata):
    """
    Format the metadata operations in the expected format of msi_atomic_apply_metadata_operations

    Parameters
    ----------
    operation_type : str
        'add' or 'remove'
    metadata : dict
        Contains the AVUs to apply. key: attribute; value: value

    Returns
    -------
    list[dict]
        The list of AVU operations in the expected format
    """
    operations = []
    for attribute, value in metadata.items():
        operation = {
            "operation": operation_type,
            "attribute": attribute,
            "value": value,
        }
        operations.append(operation)

    return operations


def map_access_name_to_access_level(access_name):
    """
    The returns value from ACL queries (COLL_ACCESS_NAME) are access names.
    But msiSetACL or ichmod expect access type as arguments.
    This function converts "access name" to "access type"

    Parameters
    ----------
    access_name: str
        expected values: "own", "modify_object" & "read_object"

    Returns
    -------
    str
        The equivalent access type value: "own", "write" & "read"
    """

    user_access = access_name
    if access_name == "modify_object":
        user_access = "write"
    elif access_name == "read_object":
        user_access = "read"

    return user_access


@make(inputs=[0, 1], outputs=[0], handler=Output.STORE)
def json_arrayops_add(ctx, json_str, item):
    """
    Python function to replace the functionality of msi_json_arrayops.add
    ```
    if ( strOps == "add" ) {
        // append value only if it's a boolean, or it's not presented in the array
        if ( json_is_boolean(jval) || i_match == outSizeOrIndex ) {
            json_array_append_new(root, jval);
            outSizeOrIndex = (int) json_array_size(root);
        }
    }
    ```

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
    """
    if not json_str:
        json_str = "[]"

    json_obj = json.loads(json_str)

    if item == "null":
        return json_obj

    if item == "false":
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

    return json_obj


@make(inputs=[0, 1], outputs=[0], handler=Output.STORE)
def json_objops_add(ctx, json_str, kvp):
    """
    Python function to replace the functionality of  msi_json_objops.add
    ```
    else if ( strOps == "add" ) {
        if (json_is_array( data )) {
            json_array_append_new(data, jval);
        } else {
            json_object_set_new(root, inKey, jval);
        }
    ```

    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    json_str : str
        initial json object
    kvp : str
        item to be added to the json array

    Returns
    -------
    json_obj : str
        updated json object
    """
    if not json_str:
        json_str = "{}"
    json_obj = json.loads(json_str)

    for key, value in get_key_value_pair_iterator(kvp):
        if key in json_obj and type(json_obj[key]) == list:
            # json_is_array
            json_obj[key].append(value)
        else:
            # json_object_set_new
            json_obj[key] = value

    return json_obj


@make(inputs=[0, 1], outputs=[0], handler=Output.STORE)
def json_objops_set(ctx, json_str, kvp):
    """
    Python function to replace the functionality of msi_json_objops.set
    ```
    else if ( strOps == "set" ) {
        json_object_set_new(root, inKey, jval);
    ```

    Parameters
    ----------
    ctx: Context
        Combined type of callback and rei struct.
    json_str : str
        initial json object
    kvp : str
        item to be added to the json array

    Returns
    -------
    json_obj : str
        updated json object
    """
    if not json_str:
        json_str = "{}"
    json_obj = json.loads(json_str)

    for key, value in get_key_value_pair_iterator(kvp):
        json_obj[key] = value

    return json_obj


def get_key_value_pair_iterator(kvp):
    """
    Parse the key-value pair input object and create an iterator.

    Parameters
    ----------
    kvp: str
        key-value pair

    Yields
    -------
    (str,str)
    """
    pairs = kvp.split("++++")

    for key_value_pair in pairs:
        pair = key_value_pair.split("=")
        key = pair[0]
        value = pair[1]
        try:
            value = json.loads(value)
        except ValueError:
            value = str(value)

        yield key, value
