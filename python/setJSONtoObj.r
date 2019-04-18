# This rule stores a given json string as AVU's to an object
# Argument 1: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 2: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 3:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
# Argument 4:  the JSON string (make sure the quotes are escaped)  {\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}
#            

# Example : irule -F setJSONtoObj.r "*object='/nlmumc/projects/P000000003/C000000001/metadata.xml'" "*inputType='-d'" "*jsonRoot='root'" "*jsonString='{\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}'"


main() {
    # Make call to function in core.py
    setJSONtoObj(*object, *objectType, *jsonRoot, *jsonString)
}

INPUT *object = '/nlmumc/projects/P000000003/C000000001/metadata.xml', *objectType = '-d', *jsonRoot = 'root', *jsonString='{\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}'
OUTPUT ruleExecOut

