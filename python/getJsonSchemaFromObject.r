# This rule get the json formatted Schema AVUs
# Argument 1: The object name (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc)
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user

# Example : irule -F getJsonSchemaFromObject.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*objectType='-d'"


main(){
    # Defining result first is mandatory!
    *result = ""

    # Call the python function

    getJsonSchemaFromObject(*object, *objectType, *result)

    # Print
    writeLine("stdout", *result)
}

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *objectType = '-d'
OUTPUT ruleExecOut
