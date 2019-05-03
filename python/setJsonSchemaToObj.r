# This rule stores a given json-schema as AVU's to an object
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  Url to the JSON-Schema example https://api.myjson.com/bins/17vejk
# Argument 4:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
#

# Example : irule -F setJsonSchemaToObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"


main() {
    # Make call to function in core.py
    setJsonSchemaToObj(*object, *objectType, *jsonSchema, *jsonRoot)
}

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *objectType = '-d', *jsonSchema = 'https://api.myjson.com/bins/17vejk', *jsonRoot = 'root'
OUTPUT ruleExecOut
