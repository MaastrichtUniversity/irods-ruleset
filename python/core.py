import json
import sys
import jsonavu
import session_vars
import genquery
import jsonschema
import requests
import re

# Global vars
activelyUpdatingAVUs = False


# This rule stores a given json string as AVU's to an object
# Argument 0: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
# Argument 3:  the JSON string (make sure the quotes are escaped)  {\"k1\":\"v1\",\"k2\":{\"k3\":\"v2\",\"k4\":\"v3\"},\"k5\":[\"v4\",\"v5\"],\"k6\":[{\"k7\":\"v6\",\"k8\":\"v7\"}]}
#
def setJsonToObj(rule_args, callback, rei):
    object = rule_args[0]
    object_type = rule_args[1]
    json_root = rule_args[2]
    json_string = rule_args[3]

    try:
        data = json.loads(json_string)
    except ValueError:
        callback.writeLine("serverLog", "Invalid json provided")
        callback.msiExit("-1101000", "Invalid json provided")
        return

    # check if validation is required
    validation_required = False
    json_schema_url = ""

    # Find AVUs with a = '$id', and u = json_root. Their value is the JSON-schema URL
    fields = getFieldsForType(callback, object_type, object)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id' AND %s = '%s'" % (fields['a'], fields['u'], json_root)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # We're only expecting one row to be returned if any
    for row in rows:
        validation_required = True
        json_schema_url = row[fields['v']]

    if validation_required:
        # TODO: This needs to accept more types of URLs, and handle errors
        r = requests.get(json_schema_url)
        schema = r.json()
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError, e:
            callback.writeLine("serverLog",
                               "JSON Instance could not be validated against JSON-schema " + str(e.message))
            callback.msiExit("-1101000", "JSON Instance could not be validated against JSON-schema : " + str(e.message))
            return

    # Load global variable activelyUpdatingAVUs and set this to true. At this point we are actively updating
    # AVUs and want to disable the check for not being able to set JSON AVUs directly
    global activelyUpdatingAVUs
    activelyUpdatingAVUs = True

    ret_val = callback.msi_rmw_avu(object_type, object, "%", "%", json_root + "_%")
    if ret_val['status'] == False and ret_val['code'] != -819000:
        callback.writeLine("serverLog", "msi_rmw_avu failed with: " + ret_val['code'])
        return

    avu = jsonavu.json2avu(data, json_root)

    for i in avu:
        callback.msi_add_avu(object_type, object, i["a"], i["v"], i["u"])

    # Set global variable activelyUpdatingAVUsthis to false. At this point we are done updating AVU and want
    # to enable some of the checks.
    activelyUpdatingAVUs = False


# This rule return a json string from AVU's set to an object
# Argument 0: The object (/nlmumc/projects/P000000003/C000000001/metadata_cedar.jsonld, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:  the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
#
# OUTPUT:  json string from AVU's set to an object
def getJsonFromObj(rule_args, callback, rei):
    object = rule_args[0]
    object_type = rule_args[1]
    json_root = rule_args[2]

    # Get all AVUs
    fields = getFieldsForType(callback, object_type, object)
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    avus = []
    for row in rows:
        avus.append({
            "a": row["META_DATA_ATTR_NAME"],
            "v": row["META_DATA_ATTR_VALUE"],
            "u": row["META_DATA_ATTR_UNITS"]
        })

    # Convert AVUs to JSON
    parsed_data = jsonavu.avu2json(avus, json_root)
    result = json.dumps(parsed_data)

    rule_args[3] = result


# Helper function to convert iRODS object type to the corresponding field names
def getFieldsForType(callback, object_type, object):
    fields = dict()

    if object_type.lower() == '-d':
        fields['a'] = "META_DATA_ATTR_NAME"
        fields['v'] = "META_DATA_ATTR_VALUE"
        fields['u'] = "META_DATA_ATTR_UNITS"

        # For a data object the path needs to be split in the object and collection
        ret_val = callback.msiSplitPath(object, "", "")
        object = ret_val['arguments'][2]
        collection = ret_val['arguments'][1]

        fields['WHERE'] = "COLL_NAME = '" + collection + "' AND DATA_NAME = '" + object + "'"

    elif object_type.lower() == '-c':
        fields['a'] = "META_COLL_ATTR_NAME"
        fields['v'] = "META_COLL_ATTR_VALUE"
        fields['u'] = "META_COLL_ATTR_UNITS"

        fields['WHERE'] = "COLL_NAME = '" + object + "'"

    elif object_type.lower() == '-r':
        fields['a'] = "META_RESC_ATTR_NAME"
        fields['v'] = "META_RESC_ATTR_VALUE"
        fields['u'] = "META_RESC_ATTR_UNITS"

        fields['WHERE'] = "RESC_NAME = '" + object + "'"

    elif object_type.lower() == '-u':
        fields['a'] = "META_USER_ATTR_NAME"
        fields['v'] = "META_USER_ATTR_VALUE"
        fields['u'] = "META_USER_ATTR_UNITS"

        fields['WHERE'] = "USER_NAME = '" + object + "'"
    else:
        callback.writeLine("serverLog", "Object type should be -d, -C, -R or -u")
        callback.msiExit("-1101000", "Object type should be -d, -C, -R or -u")

    return fields


# This rule stores a given JSON-schema as AVU's to an object
# Argument 0: The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1: The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:   Url to the JSON-Schema example https://api.myjson.com/bins/17vejk
# Argument 3:   the JSON root according to https://github.com/MaastrichtUniversity/irods_avu_json.
def setJsonSchemaToObj(rule_args, callback, rei):
    object = rule_args[0]
    object_type = rule_args[1]
    json_schema_url = rule_args[2]
    json_root = rule_args[3]

    # Check if this root has been used before
    fields = getFieldsForType(callback, object_type, object)
    avus = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # Regular expression pattern for unit field
    # TODO: Get this from avujson module
    pattern = re.compile('^([a-zA-Z0-9_]+)_([0-9]+)_([osbnze])((?<=o)[0-9]+)?((?:#[0-9]+?)*)')

    root_list = []
    for avu in avus:
        # Match unit to extract all info
        unit = pattern.match(str(avu[fields['u']]))

        # If unit is matching
        if unit:
            root = unit.group(1)
            root_list.append(root)

    if json_root in root_list:
        callback.writeLine("serverLog", "JSON root " + json_root + " is already in use")
        callback.msiExit("-1101000", "JSON root " + json_root + " is already in use")

    # Delete existing $id AVU for this JSON root
    callback.msi_rmw_avu(input_type, object, '$id', "%", json_root)

    # Set new $id AVU
    callback.msi_add_avu(input_type, object, '$id', json_schema_url, json_root)


# This function checks if a UNIT change should be allowed. If UNIT is part of an existing json changing should not be allowed.
# Only in the case we we are actively updating AVU trough setJsonToObj
# Argument 0:   The object (/nlmumc/projects/P000000003/C000000001/metadata.xml, /nlmumc/projects/P000000003/C000000001/, user@mail.com, demoResc
# Argument 1:   The object type -d for data object
#                             -R for resource
#                             -C for collection
#                             -u for user
# Argument 2:   The existing value for unit
# Output 0:     Boolean
def allowAvuChange(object, object_type, unit, callback):
    global activelyUpdatingAVUs
    # Check if we are activelyUpdatingAVUs from setJSONtoObj. In that case we do not want the filtering below
    if activelyUpdatingAVUs:
        return True

    # Get all AVUs with attribute $id
    fields = getFieldsForType(callback, object_type, object)
    fields['WHERE'] = fields['WHERE'] + " AND %s = '$id'" % (fields['a'])
    rows = genquery.row_iterator([fields['a'], fields['v'], fields['u']], fields['WHERE'], genquery.AS_DICT, callback)

    # From these AVUs extract the unit (root)
    root_list = []
    for row in rows:
        root_list.append(row[fields['u']])

    callback.writeLine("serverLog", "foo: " + str(unit))

    # Get the unit from the avu that is currently added.
    for root in root_list:
        # If the unit start with one of the roots, disallow the operation
        if str(unit).startswith(root + "_"):
            return False

    return True


def pep_database_set_avu_metadata_pre(rule_args, callback, rei):
    callback.writeLine("serverLog", "Python pep_database_set_avu_metadata_pre")
    callback.writeLine("serverLog", "Length of arguments is: " + str(len(rule_args)))

    object_name = rule_args[4]
    object_type = rule_args[3]
    object_unit = rule_args[7]

    # TODO: Implement case where old root is being modified during set

    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()


def pep_database_add_avu_metadata_wild_pre(rule_args, callback, rei):
    callback.writeLine("serverLog", "Python pep_database_add_avu_metadata_wild_pre")
    callback.writeLine("serverLog", "Length of arguments is: " + str(len(rule_args)))
    object_name = rule_args[5]
    object_type = rule_args[4]
    object_unit = rule_args[8]

    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()


def pep_database_add_avu_metadata_pre(rule_args, callback, rei):
    callback.writeLine("serverLog", "Python pep_database_add_avu_metadata_pre")
    callback.writeLine("serverLog", "Length of arguments is: " + str(len(rule_args)))
    object_name = rule_args[5]
    object_type = rule_args[4]
    object_unit = rule_args[8]
    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()


def pep_database_mod_avu_metadata_prep(rule_args, callback, rei):
    callback.writeLine("serverLog", "Python pep_database_mod_avu_metadata_prep")
    callback.writeLine("serverLog", "Length of arguments is: " + str(len(rule_args)))
    object_name = rule_args[4]
    object_type = rule_args[3]
    object_old_unit = rule_args[7]
    object_new_unit = rule_args[10]

    # If old unit starts with one of the roots disallow
    if not allowAvuChange(object_name, object_type, object_old_unit, callback):
        callback.msiOprDisallowed()

    # If new unit starts with one of the roots disallow
    if not allowAvuChange(object_name, object_type, object_new_unit, callback):
        callback.msiOprDisallowed()


def pep_database_del_avu_metadata_pre(rule_args, callback, rei):
    callback.writeLine("serverLog", "Python pep_database_del_avu_metadata_pre")
    callback.writeLine("serverLog", "Length of arguments is: " + str(len(rule_args)))
    object_name = rule_args[5]
    object_type = rule_args[4]
    object_unit = rule_args[8]

    if not allowAvuChange(object_name, object_type, object_unit, callback):
        callback.msiOprDisallowed()


def pep_database_copy_avu_metadata_pre(rule_args, callback, rei):
    callback.writeLine("serverLog", "Python pep_database_copy_avu_metadata_pre")
    callback.writeLine("serverLog", "Length of arguments is: " + str(len(rule_args)))

    # TODO: Implement allowAvuChange() check during copy operation
