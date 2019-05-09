# This rule return a json string from AVU's set to an object
# Argument 1: The object name (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc)
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
#              if empty string is supplied the irods_avu_json parsing is skipped and a json representing a array of avu's is returned

# Example : irule -F getJsonFromObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*objectType='-d'" "*jsonRoot='root'"


main(){
    # Defining result first is mandatory!
    *result = ""

    # Call the python function
    getJsonFromObj(*object, *objectType, *jsonRoot, *result)

    # Print
    writeLine("stdout", *result)
}

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *objectType = '-d', *jsonRoot = 'root'
OUTPUT ruleExecOut
