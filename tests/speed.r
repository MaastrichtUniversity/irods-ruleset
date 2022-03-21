# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F speed.r

import json
import irods_types
import session_vars
from genquery import *

def main(rule_args, callback, rei):

    output = []

    project = reset_project_dict()

    previous_project_flag = ""

    # Query all the projects size in one query
    sizes = speed_get_projects_size(callback)
#     sizes = json.loads(ret)

    # Query the service accounts to filter out of the output
    filter = speed_get_service_accounts_id(callback)
#     filter = json.loads(ret)

    for result in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               callback):
        project_path = result[0]
        attribute_name = result[1]
        attribute_value = result[2]
        access_user_id = result[3]
        access_level_name = result[4]
        if previous_project_flag == project_path:
            project[attribute_name] = attribute_value

            if access_user_id not in filter:
                add_access_id_to_project(access_user_id, access_level_name, project)
        else:
            project = reset_project_dict()
            project["path"] = project_path.split("/")[3]

            # Calculate the project's size
            if project["path"] in sizes:
                project["dataSizeGiB"] = sizes[project["path"]]
            else:
                project["dataSizeGiB"] = float(0)

            output.append(project)

        previous_project_flag = project_path

    callback.writeLine("stdout", str(output))


def add_access_id_to_project(access_id, access_name, project):
    role = map_access_level_name_to_role(access_name)
    if access_id not in project[role]:
        project[role].append(access_id)


def map_access_level_name_to_role(access):
    role = ""
    if access == "own":
        role = "managers"
    elif access == "modify object":
        role = "contributors"
    elif access == "read object":
        role = "viewers"

    return role


def reset_project_dict():
    project = {
        "managers":  [],
        "contributors": [],
        "viewers":  [],
    }
    return project


def speed_get_projects_size(callback):
    """
    Query all the (authorized) projects sizes in one query.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    Dict
        Key => project id; Value => Project size
    """

    project = {}

    for proj_coll in row_iterator("COLL_NAME, META_COLL_ATTR_VALUE",
                                  "COLL_NAME like '/nlmumc/projects/%/%' AND META_COLL_ATTR_NAME = 'dcat:byteSize'",
                                  AS_LIST,
                                  callback):
        # Split path to id
        project_id = proj_coll[0].split("/")[3]
        # Convert bytes to GiB
        size_gib = float(proj_coll[1]) / 1024 / 1024 / 1024
        if project_id in project:
            project[project_id] += size_gib
        else:
            project[project_id] = size_gib

    return project

def speed_get_service_accounts_id(callback):
    """
    Query the hard-coded list of rods and service accounts ids

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    List[str]
        List of the service accounts ids
    """

    output = []
    names = "'rods', 'service-mdl', 'service-pid', 'service-disqover', 'service-surfarchive'"

    for account in row_iterator("USER_ID",
                                "USER_NAME in ({})".format(names),
                                AS_LIST,
                                callback):
        output.append(account[0])

    return output

INPUT null
OUTPUT ruleExecOut