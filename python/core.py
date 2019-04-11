import json
import sys
import jsonavu
import session_vars
from genquery import (row_iterator, paged_iterator, AS_DICT, AS_LIST)


def acPreprocForDataObjOpen(rule_args, callback, rei):
    var_map = session_vars.get_map(rei)
    callback.writeLine("serverLog", "acPreprocForDataObjOpen")
    object_path = var_map['data_object']['object_path']
    callback.writeLine("serverLog", object_path)


# This rule stores a given json string as AVU's to an object
# Argument 0: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
# Argument 3:  the JSON string (make sure the quotes are escaped)  {\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}
#
def setJSONtoObj(rule_args, callback, rei):
    object = rule_args[0]
    input_type = rule_args[1]
    json_root = rule_args[2]
    json_string = rule_args[3]

    try:
        data = json.loads(json_string)
    except ValueError, e:
        callback.writeLine("serverLog", "Invalid json provided")
        raise

    ret_val = callback.msi_rmw_avu(input_type, object, "%", "%", "%" + json_root + "%")
    if ret_val['status'] == False and ret_val['code'] == -819000:
        callback.writeLine("stdout", "No metadata items could be removed")
    elif ret_val['status'] == "False":
        callback.writeLine("stdout", "msi failed with: " + ret_val['code'])

    avu = jsonavu.json2avu(data, json_root)

    for i in avu:
        ret_val = callback.msi_add_avu(input_type, object, i["a"], i["v"], i["u"])


# This rule return a json string from AVU's set to an object
# Argument 0: The object (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
#
# OUTPUT:  json string from AVU's set to an object
def getJSONfromObj(rule_args, callback, rei):
    object = rule_args[0]
    input_type = rule_args[1]
    json_root = rule_args[2]
    result_list = []
    # data object
    if input_type == '-d':
        ret_val = callback.msiSplitPath(object, "", "")
        data_object = ret_val['arguments'][2]
        collection = ret_val['arguments'][1]
        rows = row_iterator(
            ["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE", "META_DATA_ATTR_UNITS"],
            "COLL_NAME = '" + collection + "' AND DATA_NAME = '" + data_object + "'",
            AS_DICT,
            callback)
        for row in rows:
            result_list.append({
                "a": row["META_DATA_ATTR_NAME"],
                "v": row["META_DATA_ATTR_VALUE"],
                "u": row["META_DATA_ATTR_UNITS"]
            })
    # collection
    elif input_type == '-C':
        rows = row_iterator(
            ["META_COLL_ATTR_NAME", "META_COLL_ATTR_VALUE", "META_COLL_ATTR_UNITS"],
            "COLL_NAME = '" + object + "'",
            AS_DICT,
            callback)
        for row in rows:
            result_list.append({
                "a": row["META_COLL_ATTR_NAME"],
                "v": row["META_COLL_ATTR_VALUE"],
                "u": row["META_COLL_ATTR_UNITS"]
            })
    # resource
    elif input_type == '-R':
        rows = row_iterator(
            ["META_RESC_ATTR_NAME", "META_RESC_ATTR_VALUE", "META_RESC_ATTR_UNITS"],
            "RESC_NAME = '" + object + "'",
            AS_DICT,
            callback)
        for row in rows:
            result_list.append({
                "a": row["META_RESC_ATTR_NAME"],
                "v": row["META_RESC_ATTR_VALUE"],
                "u": row["META_RESC_ATTR_UNITS"]
            })
    # user
    elif input_type == '-u':
        rows = row_iterator(
            ["META_USER_ATTR_NAME", "META_USER_ATTR_VALUE", "META_USER_ATTR_UNITS"],
            "USER_NAME = '" + object + "'",
            AS_DICT,
            callback)
        for row in rows:
            result_list.append({
                "a": row["META_USER_ATTR_NAME"],
                "v": row["META_USER_ATTR_VALUE"],
                "u": row["META_USER_ATTR_UNITS"]
            })
    else:
        callback.writeLine("serverLog", "type should be -d, -C, -R or -u")

    if json_root == '':
        result = json.dumps(result_list)
    else:
        data_back = jsonavu.avu2json(result_list, json_root)
        result = json.dumps(data_back)
    rule_args[3] = result
