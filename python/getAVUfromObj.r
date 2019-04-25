# This rule return a json string from AVU's set to an object
# Argument 0: The object (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:  if you want only items with specific attribute name you can set a filter here
#
# OUTPUT:  json string with AVU's set to an object


# Example : irule -F getAVUfromObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*objectType='-d'" "*filter='$id'"


main(){
    # Defining result first is mandatory!
    *result = ""

    # Call the python function
    getAVUfromObj(*object, *objectType, *filter, *result)

    # Print
    writeLine("stdout", *result)
}

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *objectType = '-d', *filter = '$id'
OUTPUT ruleExecOut


#TODO Filter on $id does not work from rule, it works from direct function call

