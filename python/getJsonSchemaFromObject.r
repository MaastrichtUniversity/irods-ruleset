# This rule get the json formatted Schema AVUs
# Argument 1: The object name (/nlmumc/home/rods/test.file, /nlmumc/home/rods, user@mail.com, demoResc)
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.

# Example : irule -F getJsonSchemaFromObject.r "*object='/nlmumc/home/rods/test.file'" "*objectType='-d'"


main(){
    # Defining result first is mandatory!
    *result = ""

    # Call the python function

    getJsonSchemaFromObject(*object, *objectType, *result)

    # Print
    writeLine("stdout", *result)
}

INPUT *object=$'/nlmumc/home/rods/test.file', *objectType=$'-d'
OUTPUT ruleExecOut
