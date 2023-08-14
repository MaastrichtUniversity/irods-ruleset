from genquery import *

# Custom rule created for DHS-1353
# Print a row(s) of user(s) information in csv:
# Display name, email, data steward(s), group(s)
# irule -r irods_rule_engine_plugin-python-instance -F users_by_ds.r


def main(rule_args, callback, rei):
        users = []
        # Query all rodsuser
        for user_result in row_iterator("USER_NAME, USER_ID",
                                "USER_TYPE = 'rodsuser' ",
                                AS_LIST,
                                callback):
            user = user_result[0]
            user_id = user_result[1]
            if "service-" in user:
                continue
            user_output = {"user": user}

            user_output["display_name"] = user
            # Get display name
            for displayName in row_iterator("META_USER_ATTR_VALUE",
                                            "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(user),
                                            AS_LIST,
                                            callback):
                display_name = displayName[0]
                user_output["display_name"] = display_name

            user_output["email"] = user
            # Get display email
            for email_result in row_iterator("META_USER_ATTR_VALUE",
                                            "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'email'".format(user),
                                            AS_LIST,
                                            callback):
                email = email_result[0]
                user_output["email"] = email


            groups = []
            # Get user group membership
            for result in row_iterator("order(USER_GROUP_NAME)",
                                       "USER_ID = '{}'".format(user_id),
                                       AS_LIST,
                                       callback):

                group_name = result[0]

                if group_name != "public" and group_name != "rodsadmin" \
                        and group_name != "DH-ingest" and group_name != "DH-project-admins" and group_name != user:
                    groups.append(group_name)

            user_output["groups"] = groups
            users.append(user_output)

            groups = ""
            for result in row_iterator("USER_GROUP_ID",
                              "USER_ID = '{}'".format(user_id),
                              AS_LIST,
                              callback):
                group_id = "'" + result[0] + "'"
                groups = groups + "," + group_id

            groups = groups[1:]
            parameters = "COLL_NAME"
            conditions = "COLL_ACCESS_NAME in ('own', 'modify object', 'read object') " \
                         "and COLL_ACCESS_USER_ID in ({}) " \
                         "and COLL_PARENT_NAME = '/nlmumc/projects'".format(groups)

            dataStewards = []
            # Get all projects with read access
            for collection_result in row_iterator(parameters, conditions, AS_LIST, callback):
                # Get project data steward
                dataSteward = callback.getCollectionAVU(collection_result[0], "dataSteward", "", "", "true")["arguments"][2]
                dataStewards.append(dataSteward)
            user_output["dataStewards"] = set(dataStewards)

        for user in users:
            ds = " | ".join(user["dataStewards"])
            groups = " | ".join(user["groups"])
            output = user["display_name"]+";"+user["email"]+";"+ str(ds) +";"+ str(groups)
            callback.writeLine("stdout", output)

INPUT null
OUTPUT ruleExecOut