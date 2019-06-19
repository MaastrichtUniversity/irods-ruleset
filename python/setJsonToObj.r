# This rule stores a given json string as AVU's to an object
# Argument 1: The object name (/nlmumc/home/rods/test.file, /nlmumc/home/rods, user@mail.com, demoResc)
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root (see documentation).
# Argument 4:  the JSON string {"firstName":"John","lastName":"Doe","age":21}
#

# Example : irule -F setJsonToObj.r "*object='/nlmumc/home/rods/test.file'" "*objectType='-d'" "*jsonRoot='root'" '*jsonString='\''{"firstName":"John","lastName":"Doe","age":21}'\'''


main() {
    # Make call to function in core.py
    setJsonToObj(*object, *objectType, *jsonRoot, *jsonString)
}

INPUT *object=$'/nlmumc/home/rods/test.file', *objectType=$'-d', *jsonRoot=$'root', *jsonString=$'{"firstName":"John","lastName":"Doe","age":21}'
OUTPUT ruleExecOut
