# This rule removes the AVU set by setJSONtoObj.r using the json root 
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json. For example: "root"
#            

# Example : irule -r irods_rule_engine_plugin-python-instance -F removeAVUfromObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld'" "*inputType='-d'" "*jsonRoot='root'" 

def main(rule_args, callback, rei):
    object = global_vars["*object"][1:-1]  # strip the quotes
    input_type = global_vars["*inputType"][1:-1]  # strip the quotes
    json_root = global_vars["*jsonRoot"][1:-1]  # strip the quotes
    callback.writeLine("serverLog", "type is " + input_type )

    ret_val = callback.msi_rmw_avu(input_type, object, "%","%","%"+json_root+"%")
    callback.writeLine("serverLog", str(ret_val) )
    if ret_val['status'] == False and ret_val['code'] == -819000:
      callback.writeLine("stdout", "No metadata items could be removed")
    elif ret_val['status'] == "False":
      callback.writeLine("stdout", "msi failed with: " + ret_val['code'])


INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld', *inputType = '-d', *jsonRoot = 'root']}'
OUTPUT ruleExecOut

