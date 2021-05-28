# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F opti.r

import json
import irods_types
import session_vars
from genquery import *

def main(rule_args, callback, rei):

    output = []

    project = reset_project_dict()

    users_name = {}

    previous_project_flag = ""


    for result in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               callback):

        if previous_project_flag == result[0]:
            project[result[1]] = result[2]
            account = query_account_info(callback, result[3], users_name)
            add_account_to_project_acl(project, result[4], account)
        else:
            project = reset_project_dict()
            project["path"] = result[0]

            # Calculate the project's size
            ret = callback.get_project_size(project["path"], '')["arguments"][1]
            project["dataSizeGiB"] = json.loads(ret)
            output.append(project)

        previous_project_flag = result[0]

    callback.writeLine("stdout", str(len(users_name)))
    callback.writeLine("stdout", str(output))


def query_account_info(callback, account_id, users_name):
    if account_id in users_name:
        return users_name[account_id]

    for result in row_iterator("USER_NAME, USER_TYPE",
                                "USER_ID = '{}'".format(account_id),
                                AS_LIST,
                                callback):
        account_name = result[0]
        account_type = result[1]
        account = False
        if account_type == "rodsgroup":
            account = query_group(callback, account_name, account_id)
            account["account_type"] = "rodsgroup"

        if account_type == "rodsuser":
            account = query_user(callback, account_name, account_id)
            if account:
                account["account_type"] = "rodsuser"
        # All other cases of objectType, such as "" or "rodsadmin", are skipped

        users_name[account_id] = account

        return account


def add_account_to_project_acl(project, access, account):
    if account and account["account_type"] == "rodsgroup":
        add_group(project, access, account)
    if account and account["account_type"] == "rodsuser":
        add_user(project, access, account)


def map_acl_to_role(access):
    role = ""
    if access == "own":
        role = "managers"

    if access == "modify object":
        role = "contributors"

    if access == "read object":
        role = "viewers"

    return role


def query_group(callback, account_name, account_id):
    display_name = account_name
    description = ""
    for group_result in row_iterator("META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
                                     "USER_TYPE = 'rodsgroup' AND USER_GROUP_ID = '{}'".format(account_id),
                                     AS_LIST,
                                     callback):

        if "displayName" == group_result[0]:
            display_name = group_result[1]

        elif "description" == group_result[0]:
            description = group_result[1]

    account = {
        "name": account_name,
        "id": account_id,
        "display_name": display_name,
        "description": description,
    }

    return account


def add_group(project, access, account):
    role = map_acl_to_role(access)
    if account["name"] not in project[role]["groups"]:
        project[role]["groups"].append(account["name"])
        group_object = {
            "groupName": account["name"], "groupId": account["id"],
            "displayName": account["display_name"], "description": account["description"]
        }
        project[role]["groupObjects"].append(group_object)


def query_user(callback, account_name, account_id):
    show_service_accounts = "false"

    # Filter out service account from output
    if show_service_accounts == "false" and "service-" in account_name:
        return

    display_name = account_name
    for user_result in row_iterator("META_USER_ATTR_VALUE",
                                    "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(
                                        account_name),
                                    AS_LIST,
                                    callback):
        display_name = user_result[0]

    account = {
        "name": account_name,
        "id": account_id,
        "display_name": display_name,
    }

    return account


def add_user(project, access, account):
    role = map_acl_to_role(access)
    if account["name"] not in project[role]["users"]:
        project[role]["users"].append(account["name"])
        user_object = {"userName": account["name"], "userId": account["id"], "displayName": account["display_name"]}
        project[role]["userObjects"].append(user_object)


def reset_project_dict():
    project = {
        "managers": {
            "groupObjects": [],
            "groups": [],
            "userObjects": [],
            "users": []
        },
        "contributors": {
            "groupObjects": [],
            "groups": [],
            "userObjects": [],
            "users": []
        },
        "viewers": {
            "groupObjects": [],
            "groups": [],
            "userObjects": [],
            "users": []
        }
    }
    return project


INPUT null
OUTPUT ruleExecOut