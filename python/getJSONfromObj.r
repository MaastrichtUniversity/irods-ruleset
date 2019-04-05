# This rule return a json string from AVU's set to an object
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
#              if empty string is supplied the irods_avu_json parsing is skipped and a json representing a array of avu's is returned

# Example : irule -r irods_rule_engine_plugin-python-instance -F getJSONfromObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld'" "*inputType='-d'" "*jsonRoot='root'"

from genquery import (row_iterator, paged_iterator, AS_DICT, AS_LIST)
import json
import jsonavu


def main(rule_args, callback, rei):
    object = global_vars["*object"][1:-1]  
    input_type = global_vars["*inputType"][1:-1]  
    json_root = global_vars["*jsonRoot"][1:-1]  

    result_list = []
    # data object
    if input_type == '-d':
        callback.writeLine("serverLog", "type is -d")
        ret_val = callback.msiSplitPath(object, "", "")
        data_object = ret_val['arguments'][2]
        collection = ret_val['arguments'][1]
        callback.writeLine("serverLog", "dataObject = " + str(data_object))
        callback.writeLine("serverLog", "collection = " + str(collection))
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
        callback.writeLine("serverLog", "type is -C")
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
        callback.writeLine("serverLog", "type is -R")
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
        callback.writeLine("serverLog", "type is -u")
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
        callback.writeLine("stdout", json.dumps(result_list))
    else:
        data_back = jsonavu.avu2json(result_list, json_root)
        callback.writeLine("stdout", json.dumps(data_back))

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld', *inputType = '-d', *jsonRoot = 'root'
OUTPUT ruleExecOut
