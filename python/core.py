import json
import irods_types
import session_vars
from genquery import *

from dhpythonirodsutils import formatters, exceptions, loggers, validators
from dhpythonirodsutils.enums import DropzoneState, ProjectAVUs, AuditTailTopics

from enum import Enum

# Global vars
activelyUpdatingAVUs = False
COLLECTION_METADATA_INDEX = "collection_metadata"

FALSE_AS_STRING = "false"
TRUE_AS_STRING = "true"


# https://github.com/UtrechtUniversity/irods-ruleset-uu/blob/development/util/rule.py
# __copyright__ = 'Copyright (c) 2019, Utrecht University'
# __license__   = 'GPLv3, see LICENSE'


class Context(object):
    """Combined type of a callback and rei struct.
    `Context` can be treated as a rule engine callback for all intents and purposes.
    However @rule and @api functions that need access to the rei, can do so through this object.
    """

    def __init__(self, callback, rei):
        self.callback = callback
        self.rei = rei

    def __getattr__(self, name):
        """Allow accessing the callback directly."""
        return getattr(self.callback, name)


class Output(Enum):
    """Specifies rule output handlers."""

    STORE = 0  # store in output parameters
    STDOUT = 1  # write to stdout
    STDOUT_BIN = 2  # write to stdout, without a trailing newline


def make(inputs=None, outputs=None, transform=lambda x: x, handler=Output.STORE):
    """Create a rule (with iRODS calling conventions) from a Python function.
    :param inputs:    Optional list of rule_args indices to influence how parameters are passed to the function.
    :param outputs:   Optional list of rule_args indices to influence how return values are processed.
    :param transform: Optional function that will be called to transform each output value.
    :param handler:   Specifies how return values are handled.
    inputs and outputs can optionally be specified as lists of indices to
    influence how parameters are passed to this function, and how the return
    value is processed. By default, 'inputs' and 'outputs' both span all rule arguments.
    transform can be used to apply a transformation to the returned value(s),
    e.g. by encoding them as JSON.
    handler specifies what to do with the (transformed) return value(s):
    - Output.STORE:      stores return value(s) in output parameter(s) (this is the default)
    - Output.STDOUT:     prints return value(s) to stdout
    - Output.STDOUT_BIN: prints return value(s) to stdout, without a trailing newline
    Examples:
        @rule.make(inputs=[0,1], outputs=[2])
        def foo(ctx, x, y):
            return int(x) + int(y)
    is equivalent to:
        def foo(rule_args, callback, rei):
            x, y = rule_args[0:2]
            rule_args[2] = int(x) + int(y)
    and...
        @rule.make(transform=json.dumps, handler=Output.STDOUT)
        def foo(ctx, x, y):
            return {'result': int(x) + int(y)}
    is equivalent to:
        def foo(rule_args, callback, rei):
            x, y = rule_args[0:2]
            callback.writeString('stdout', json.dumps(int(x) + int(y)))
    :returns: Decorator to create a rule from a Python function
    """

    def encode_val(v):
        """Encode a value such that it can be safely transported in rule_args, as output."""
        if type(v) is str:
            return v
        else:
            # Encode numbers, bools, lists and dictionaries as JSON strings.
            # note: the result of encoding e.g. int(5) should be equal to str(int(5)).
            return json.dumps(v)

    def deco(f):
        def r(rule_args, callback, rei):
            a = rule_args if inputs is None else [rule_args[i] for i in inputs]
            result = f(Context(callback, rei), *a)

            if result is None:
                return

            result = map(transform, list(result) if type(result) is tuple else [result])

            if handler is Output.STORE:
                if outputs is None:
                    # outputs not specified? overwrite all arguments.
                    rule_args[:] = map(encode_val, result)
                else:
                    # set specific output arguments.
                    for i, x in zip(outputs, result):
                        rule_args[i] = encode_val(x)
            elif handler is Output.STDOUT:
                for x in result:
                    callback.writeString("stdout", encode_val(x) + "\n")
                    # For debugging:
                    # log.write(callback, 'rule output (DEBUG): ' + encode_val(x))
            elif handler is Output.STDOUT_BIN:
                for x in result:
                    callback.writeString("stdout", encode_val(x))

        return r

    return deco


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


# region formatter utils rules
# The following rules are needed for the native rules to use the python formatter functions


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def format_audit_trail_message(ctx, username, event):
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    return loggers.format_audit_trail_message(int(user_id), AuditTailTopics.POLICY.value, event)


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

# endregion


def read_data_object_from_irods(ctx, path):
    """This rule gets a JSON schema stored as an iRODS object
    :param ctx:  iRODS context
    :param path: Full path of the file to read (ie: '/nlmumc/ingest/zones/crazy-frog/instance.json')
    :return: The content of the file to open
    """
    # Open iRODS file
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val["arguments"][1]

    # Read iRODS file
    ret_val = ctx.callback.msiDataObjRead(file_desc, 2**31 - 1, irods_types.BytesBuf())
    read_buf = ret_val["arguments"][2]

    # Convert BytesBuffer to string
    ret_val = ctx.callback.msiBytesBufToStr(read_buf, "")
    output_json = ret_val["arguments"][1]

    # Close iRODS file
    ctx.callback.msiDataObjClose(file_desc, 0)

    return output_json


def convert_to_current_timezone(date, date_format="%Y-%m-%d %H:%M:%S"):
    import pytz

    old_timezone = pytz.timezone("UTC")
    new_timezone = pytz.timezone("Europe/Amsterdam")
    return old_timezone.localize(date).astimezone(new_timezone).strftime(date_format)


def format_dropzone_path(ctx, token, dropzone_type):
    try:
        dropzone_path = formatters.format_dropzone_path(token, dropzone_type)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid dropzone type, supported 'mounted' and 'direct', got '{}'.".format(dropzone_type)
        )
    return dropzone_path


def format_project_path(ctx, project_id):
    try:
        project_path = formatters.format_project_path(project_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit("-1", "Invalid project ID format: '{}'".format(project_id))
    return project_path


def format_project_collection_path(ctx, project_id, collection_id):
    try:
        project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid project ID or collection ID format: '{}/{}'".format(project_id, collection_id)
        )
    return project_collection_path


def format_instance_collection_path(ctx, project_id, collection_id):
    try:
        instance_path = formatters.format_instance_collection_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid project ID or collection ID format: '{}/{}'".format(project_id, collection_id)
        )
    return instance_path


def format_schema_collection_path(ctx, project_id, collection_id):
    try:
        schema_path = formatters.format_schema_collection_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid project ID or collection ID format: '{}/{}'".format(project_id, collection_id)
        )
    return schema_path


def format_instance_versioned_collection_path(ctx, project_id, collection_id, version):
    try:
        instance_path = formatters.format_instance_versioned_collection_path(project_id, collection_id, version)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid project ID or collection ID format: '{}/{}'".format(project_id, collection_id)
        )
    return instance_path


def format_schema_versioned_collection_path(ctx, project_id, collection_id, version):
    try:
        schema_path = formatters.format_schema_versioned_collection_path(project_id, collection_id, version)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid project ID or collection ID format: '{}/{}'".format(project_id, collection_id)
        )
    return schema_path


def format_metadata_versions_path(ctx, project_id, collection_id):
    try:
        metadata_versions_path = formatters.format_metadata_versions_path(project_id, collection_id)
    except exceptions.ValidationError:
        ctx.callback.msiExit(
            "-1", "Invalid project ID or collection ID format: '{}/{}'".format(project_id, collection_id)
        )
    return metadata_versions_path


def get_elastic_search_connection(ctx):
    from elasticsearch import Elasticsearch

    environment = ctx.callback.msi_getenv("ENVIRONMENT", "")["arguments"][1]
    use_ssl = True if environment == "acc" or environment == "prod" else False

    elastic_password = ctx.callback.msi_getenv("ELASTIC_PASSWORD", "")["arguments"][1]
    elastic_host = ctx.callback.msi_getenv("ELASTIC_HOST", "")["arguments"][1]
    elastic_port = ctx.callback.msi_getenv("ELASTIC_PORT", "")["arguments"][1]
    es = Elasticsearch([{"host": elastic_host, "port": elastic_port}], http_auth=("elastic", elastic_password), use_ssl=use_ssl)

    return es


def format_human_bytes(B):
    """
    Return the given bytes as a human friendly KB, MB, GB, or TB string.
    """
    B = float(B)
    KB = float(1024)
    MB = float(KB**2)  # 1,048,576
    GB = float(KB**3)  # 1,073,741,824
    TB = float(KB**4)  # 1,099,511,627,776

    if B < KB:
        return "{0} {1}".format(B, "Bytes" if 0 == B > 1 else "Byte")
    elif KB <= B < MB:
        return "{0:.2f} KB".format(B / KB)
    elif MB <= B < GB:
        return "{0:.2f} MB".format(B / MB)
    elif GB <= B < TB:
        return "{0:.2f} GB".format(B / GB)
    elif TB <= B:
        return "{0:.2f} TB".format(B / TB)
