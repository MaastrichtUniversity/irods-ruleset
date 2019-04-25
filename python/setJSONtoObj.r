# This rule stores a given json string as AVU's to an object
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  Url to the JSON-Schema example https://api.myjson.com/bins/17vejk
# Argument 4:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
# Argument 5:  the JSON string (make sure the quotes are escaped) {\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}
#

# Example : irule -F setJSONtoObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"


main() {
    # Make call to function in core.py
    setJSONtoObj(*object, *objectType, *jsonSchema, *jsonRoot, *jsonString)
}

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *objectType = '-d', *jsonSchema = 'https://api.myjson.com/bins/17vejk', *jsonRoot = 'root', *jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'
OUTPUT ruleExecOut
