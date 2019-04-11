# This rule return a json string from AVU's set to an object
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
#              if empty string is supplied the irods_avu_json parsing is skipped and a json representing a array of avu's is returned

# Example : irule -r irods_rule_engine_plugin-python-instance -F getJSONfromObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld'" "*inputType='-d'" "*jsonRoot='root'"


def main(rule_args, callback, rei):
    #load input variables
    object = global_vars["*object"][1:-1]
    input_type = global_vars["*inputType"][1:-1]  
    json_root = global_vars["*jsonRoot"][1:-1]

    #Make call to function in core.py
    ret_val = callback.getJSONfromObj(object, input_type, json_root, "")
    #Write output to stdout
    callback.writeLine("stdout", ret_val['arguments'][3])


INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld', *inputType = '-d', *jsonRoot = 'root'
OUTPUT ruleExecOut
