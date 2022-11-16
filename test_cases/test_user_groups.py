import subprocess
import pytest
import json
import os

from test_cases.utils import (
    TMP_INSTANCE_PATH,
    get_instance,
    remove_project,
    revert_latest_project_number,
    remove_dropzone,
    create_project,
    create_dropzone,
    add_metadata_files_to_direct_dropzone,
)

"""
Python 

get_all_users_groups_memberships
    Not used MDR, RW or RS. 
    Created for PO metrics user mapping
get_all_users_id
    Not used in MDR, RW
    Used in RS (optimized_list_projects)
get_contributing_project
    Not used in RS
    Used in MDR, RW
get_groups
    Not used in RS
    Used in MDR, RW
get_service_accounts_id
    Not used in MDR, RW
    Used in RS (optimized_list_projects)
get_temporary_password_lifetime
    Not used in RS
    Used in MDR, RW   
get_user_admin_status
    Not used in MDR, RW
    Used in RS(acPreProcForModifyAVUMetadata) 
get_user_attribute_value
    Used in MDR, RW and RS (create_drop_zone ....)
get_user_group_memberships
    Used in MDR, RW and RS (check_edit_metadata_permission ....) 
get_user_id
    Not used in MDR, RW
    Used in RS(checkDropZoneACL)
get_user_internal_affiliation_status
    Not used in RS
    Used in MDR, RW
get_user_metadata
    Not used in MDR, RW
    Used in RS(get_project_contributors_metadata)
get_user_or_group_by_id
    Not used in MDR
    Used in RW and RS
set_user_attribute_value
    Not used in RS
    Used in MDR, RW

iRODS Rule language

getDataStewards
    Not used in RS
    Used in MDR, RW
getDisplayNameForAccount
    Not used in MDR, RW
    Used in RS(getProjectCollectionsArray)
getEmailForAccount
    Not used MDR, RW or RS. 
getGroups
    Not used MDR, RW or RS. 
getUsers
    Used in MDR, RW and RS (get_all_users_groups_memberships)
getUsersInGroup
    Not used in RS
    Used in MDR, RW
listGroupsByUser
    Used in RW
    Not used in MDR and RS
"""


class TestUserGroups:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = "iresResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = "direct"
    token = ""

    collection_title = "collection_title"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def setup_class(cls):
        print("Start {}.setup_class".format(cls.__name__))
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        set_project_acl_to_dropzone = '/rules/tests/run_test.sh -r set_project_acl_to_dropzone -a "{},{},true"'.format(
            cls.project_id, cls.token
        )
        subprocess.check_call(set_project_acl_to_dropzone, shell=True)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        remove_dropzone(cls.token, cls.dropzone_type)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    def test_get_all_users_id(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.manager1)
        user_id = subprocess.check_output(run_iquest, shell=True).strip()

        rule = "/rules/tests/run_test.sh -r get_all_users_id"
        ret = subprocess.check_output(rule, shell=True)
        user_ids = json.loads(ret)
        assert user_ids[user_id] == user_id

    def test_get_contributing_project(self):
        rule = '/rules/tests/run_test.sh -r get_contributing_project -a "{},false" -u {}'.format(
            self.project_id, self.manager1
        )
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)

        assert project["id"] == self.project_id
        assert project["title"] == self.project_title

    def test_get_groups(self):
        rule = '/rules/tests/run_test.sh -r get_groups -a "false"'
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)
        assert check_if_key_value_in_dict_list(groups, "name", "datahub")

    def test_get_service_accounts_id(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format("service-pid")
        user_id = subprocess.check_output(run_iquest, shell=True).strip()

        rule = "/rules/tests/run_test.sh -r get_service_accounts_id"
        ret = subprocess.check_output(rule, shell=True)
        service_accounts = json.loads(ret)

        assert user_id in service_accounts

    def test_get_temporary_password_lifetime(self):
        rule = "/rules/tests/run_test.sh -r get_temporary_password_lifetime"
        ret = subprocess.check_output(rule, shell=True)
        temporary_password = json.loads(ret)

        assert temporary_password == int(os.getenv("IRODS_TEMP_PASSWORD_LIFETIME"))

    def test_get_user_admin_status(self):
        rule = "/rules/tests/run_test.sh -r get_user_admin_status -a {user}"

        ret = subprocess.check_output(rule.format(user=self.manager1), shell=True)
        admin_status = json.loads(ret)
        assert admin_status

        ret = subprocess.check_output(rule.format(user="auser"), shell=True)
        admin_status = json.loads(ret)
        assert not admin_status

    def test_get_user_attribute_value(self):
        rule = '/rules/tests/run_test.sh -r get_user_attribute_value -a "{},{},false"'.format(
            self.manager1, "eduPersonUniqueID"
        )
        ret = subprocess.check_output(rule, shell=True)
        edu_person_unique_id = json.loads(ret)

        assert edu_person_unique_id["value"] == "jmelius@sram.surf.nl"

    def test_get_user_group_memberships(self):
        rule = '/rules/tests/run_test.sh -r get_user_group_memberships -a "false,{}"'.format(self.manager1)
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)
        assert check_if_key_value_in_dict_list(groups, "name", "datahub")

    def test_get_user_id(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.manager1)
        user_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        rule = '/rules/tests/run_test.sh -r get_user_id -a "{}"'.format(self.manager1)
        ret = subprocess.check_output(rule, shell=True)
        user_id_irule = json.loads(ret)

        assert int(user_id_iquest) == user_id_irule

    def test_get_user_internal_affiliation_status(self):
        rule = "/rules/tests/run_test.sh -r get_user_internal_affiliation_status -a {user}"

        ret = subprocess.check_output(rule.format(user=self.manager1), shell=True)
        affiliation_status = json.loads(ret)
        assert affiliation_status

        ret = subprocess.check_output(rule.format(user="auser"), shell=True)
        affiliation_status = json.loads(ret)
        assert not affiliation_status

    def test_get_user_metadata(self):
        rule = "/rules/tests/run_test.sh -r get_user_metadata -a {}".format(self.manager2)
        ret = subprocess.check_output(rule.format(), shell=True)
        user = json.loads(ret)

        assert user["givenName"] == "Olav"

    def test_get_user_or_group_by_id(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.manager1)
        user_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format("datahub")
        group_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        rule = "/rules/tests/run_test.sh -r get_user_or_group_by_id -a {id}"

        ret = subprocess.check_output(rule.format(id=user_id_iquest), shell=True)
        user = json.loads(ret)
        assert user["userName"] == self.manager1

        ret = subprocess.check_output(rule.format(id=group_id_iquest), shell=True)
        group = json.loads(ret)
        assert group["groupName"] == "datahub"

    def test_set_user_attribute_value(self):
        field_name = "test"
        field_value = "value"

        run_iquest = "iquest \"%s\" \"SELECT META_USER_ATTR_VALUE WHERE USER_NAME = '{}' and META_USER_ATTR_NAME = '{}' \"".format(
            self.manager1, field_name
        )
        field_value_return = subprocess.check_output(run_iquest, shell=True).strip()
        assert "CAT_NO_ROWS_FOUND" in field_value_return

        rule = '/rules/tests/run_test.sh -r set_user_attribute_value -a "{},{},{}"'.format(
            self.manager1, field_name, field_value
        )
        subprocess.check_output(rule, shell=True)

        run_iquest = "iquest \"%s\" \"SELECT META_USER_ATTR_VALUE WHERE USER_NAME = '{}' and META_USER_ATTR_NAME = '{}' \"".format(
            self.manager1, field_name
        )
        field_value_return = subprocess.check_output(run_iquest, shell=True).strip()

        assert field_value_return == field_value

        imeta = "imeta rm -u {} {} {}".format(self.manager1, field_name, field_value)
        subprocess.check_output(imeta, shell=True)

    def test_get_data_stewards(self):
        rule = 'irule -F /rules/misc/getDataStewards.r'
        ret = subprocess.check_output(rule, shell=True)
        data_stewards = json.loads(ret)
        assert check_if_key_value_in_dict_list(data_stewards, "userName", self.manager2)

    def test_get_display_name_for_account(self):
        rule = 'irule -F /rules/misc/getDisplayNameForAccount.r \"*account=\'{}\'\"'.format(self.manager1)
        display_name = subprocess.check_output(rule, shell=True)
        assert "Jonathan" in display_name

    def test_get_email_for_account(self):
        rule = 'irule -F /rules/misc/getEmailForAccount.r \"*account=\'{}\'\"'.format(self.manager1)
        email = subprocess.check_output(rule, shell=True).rstrip("\n")
        assert email == "jonathan.melius@maastrichtuniversity.nl"

    def test_get_groups_rule_language(self):
        rule = 'irule -F /rules/misc/getGroups.r "*showSpecialGroups=\'false\'"'
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)
        assert check_if_key_value_in_dict_list(groups, "userName", "m4i-nanoscopy")

    def test_get_users(self):
        rule = 'irule -F /rules/misc/getUsers.r "*showServiceAccounts=\'false\'"'
        ret = subprocess.check_output(rule, shell=True)
        users = json.loads(ret)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager1)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager2)

    def test_get_users_in_group(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format("datahub")
        group_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        rule = 'irule -F /rules/misc/getUsersInGroup.r \"*groupId=\'{}\'\"'.format(group_id_iquest)
        ret = subprocess.check_output(rule, shell=True)
        users = json.loads(ret)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager1)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager2)

    def test_list_groups_by_user(self):
        rule = 'irule -F /rules/misc/listGroupsByUser.r'
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)

        for group in groups:
            if group["GroupName"] == "datahub":
                assert "Pascal Suppers" in group["Users"]
                assert "Maarten Coonen" in group["Users"]


def check_if_key_value_in_dict_list(dictionaries_list, key, value):
    found = False
    for dictionary in dictionaries_list:
        if dictionary[key] == value:
            found = True
    return found
