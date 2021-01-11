# This rule stores a given json-schema as AVU's to an object
# Argument 1: The object name (/nlmumc/home/rods/test.file, /nlmumc/home/rods, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  URL to the JSON-Schema
# Argument 4:  the JSON root (see documentation)
#

# Example : irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"


main() {
    # Make call to function in core.py
    setJsonSchemaToObj(*object, *objectType, *jsonSchema, *jsonRoot)
}

INPUT *object=$'/nlmumc/home/rods/test.file', *objectType=$'-d', *jsonSchema=$'https://api.myjson.com/bins/17vejk', *jsonRoot=$'root'
OUTPUT ruleExecOut
