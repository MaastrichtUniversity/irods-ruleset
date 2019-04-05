# This rule stores a given json string as AVU's to an object
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
# Argument 4:  the JSON string (make sure the quotes are escaped)  {\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}
#            

# Example : irule -r irods_rule_engine_plugin-python-instance -F setJSONtoObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*inputType='-d'" "*jsonRoot='root'" "*jsonString='{\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}'"


from genquery import (row_iterator, paged_iterator, AS_DICT, AS_LIST)
import json
import jsonavu


def main(rule_args, callback, rei):
    object = global_vars["*object"][1:-1]  # strip the quotes
    input_type = global_vars["*inputType"][1:-1]  # strip the quotes
    json_root = global_vars["*jsonRoot"][1:-1]  # strip the quotes
    json_string = global_vars["*jsonString"][1:-1]  # strip the quotes
    callback.writeLine("serverLog", json_string)
    callback.writeLine("serverLog", "type is " + input_type )
  
    data = json.loads(json_string)
    avu = jsonavu.json2avu(data, json_root)
    max_a_len = len(max(avu, key=lambda k: len(str(k["a"])))["a"])
    max_v_len = len(max(avu, key=lambda k: len(str(k["v"])))["v"])
    out_format = "%" + str(max_a_len + 5) + "s %" + str(max_v_len + 5) + "s %15s"
    for i in avu:
          #ret_val = callback.msiSetAVU(input_type, object, i["a"],i["v"],i["u"])
          callback.writeLine("stdout", out_format % (i["a"], i["v"], i["u"]))


INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *inputType = '-d', *jsonRoot = 'root', *jsonString='{\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}'
OUTPUT ruleExecOut

