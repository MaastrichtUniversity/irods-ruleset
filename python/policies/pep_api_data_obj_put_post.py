# https://docs.irods.org/4.2.11/plugins/dynamic_policy_enforcement_points/
# https://github.com/irods/irods_rule_engine_plugin_python/blob/main/irods_types.cpp

# To clarify which and how all the parameters of a pep look,
# You can use the following code


# Show all keys in *COMM (rsComm_t) object (rule_args[1])
# import pprint
# pprint.pprint(rule_args[1].map().items())

# Show all keys in *DATAOBJINP (dataObjInp_t) object (rule_args[2])
# print(dir(rule_args[2]))
#
# # print all keys in rule_args[2]
# objectpath = str(rule_args[2].objPath)
# print(objectpath)
# createMode = str(rule_args[2].createMode)
# print(createMode)
# openFlags = str(rule_args[2].openFlags)
# print(openFlags)
# offset = str(rule_args[2].offset)
# print(offset)
# dataSize = str(rule_args[2].dataSize)
# print(dataSize)
# numThreads = str(rule_args[2].numThreads)
# print(numThreads)
# oprType = str(rule_args[2].oprType)
# print(oprType)
# specColl = str(rule_args[2].specColl)
# print(specColl)
# condInput = str(rule_args[2].condInput)
# print(condInput)
#
# # print all key value pairs in condInput
# for i in range(0, rule_args[2].condInput.len):
#     print(str(rule_args[2].condInput.key[i]) + " : " + str(rule_args[2].condInput.value[i]))
#
# # Print all the available session vars
# var_map = session_vars.get_map(rei)
# pprint.pprint(var_map)
# pprint.pprint(rei.doi)

#
# def pep_api_data_obj_put_post(rule_args, callback, rei):
#     import re
#
#     print("pep_api_data_obj_put_post")
#     # Policy to increment the size of the ingested files for the progress bar
#
#     objectpath = str(rule_args[2].objPath)
#     if re.search("^/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*$", objectpath):
#
#         size_ingested = 0
#         collection_id = formatters.get_collection_id_from_project_collection_path(objectpath)
#         project_id = formatters.get_project_id_from_project_collection_path(objectpath)
#
#         project_path = formatters.format_project_path(project_id)
#         project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
#
#         resource = callback.getCollectionAVU(project_path, ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING)[
#             "arguments"
#         ][2]
#         dest_resource = get_value_from_cond_input(rule_args[2].condInput, "destRescName")
#
#         if resource == dest_resource:
#             for row in row_iterator(
#                 "META_COLL_ATTR_NAME,META_COLL_ATTR_VALUE",
#                 "COLL_NAME = '{}'".format(project_collection_path),
#                 AS_LIST,
#                 callback,
#             ):
#                 if row[0] == "sizeIngested":
#                     size_ingested = float(row[1])
#             size_ingested = size_ingested + float(rule_args[2].dataSize)
#             callback.setCollectionAVU(project_collection_path, "sizeIngested", str(int(size_ingested)))
#
#     # Policy to give read access on metadata files to dropzone creator
#     if re.search("^/nlmumc/ingest/direct/.*/instance.json$", objectpath) or re.search(
#         "^/nlmumc/ingest/direct/.*/schema.json$", objectpath
#     ):
#         username = callback.get_client_username("")["arguments"][0]
#         callback.msiSetACL("default", "read", username, objectpath)
#
#
# def get_value_from_cond_input(cond_input, key):
#
#     for i in range(0, cond_input.len):
#         if str(cond_input.key[i]) == key:
#             return str(cond_input.value[i])
#     raise ValueError
