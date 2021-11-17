import json
import irods_types
import session_vars
from genquery import *

from enum import Enum


# Global vars
activelyUpdatingAVUs = False

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
    ret_val = ctx.callback.msiDataObjRead(file_desc, 2 ** 31 - 1, irods_types.BytesBuf())
    read_buf = ret_val["arguments"][2]

    # Convert BytesBuffer to string
    ret_val = ctx.callback.msiBytesBufToStr(read_buf, "")
    output_json = ret_val["arguments"][1]

    # Close iRODS file
    ctx.callback.msiDataObjClose(file_desc, 0)

    return output_json
