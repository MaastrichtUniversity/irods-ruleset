import subprocess
import json
import os

from test_cases.utils import (
    remove_project,
    revert_latest_project_number,
    create_project,
    create_user,
    create_data_steward,
    create_group,
    remove_user,
    remove_group,
    add_user_to_group,
    remove_user_from_group,
    set_user_avu,
    check_if_key_value_in_dict_list,
)

"""
Rule usages:

Python rules

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

iRODS Rule language rules

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

    depositor = "test_manager"
    manager1 = depositor
    manager2 = "test_data_steward"
    data_steward = manager2
    group = "test_group"
    service_account = "service-test"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    @classmethod
    def setup_class(cls):
        print("Start {}.setup_class".format(cls.__name__))
        create_user(cls.manager1)
        add_user_to_group("DH-project-admins", cls.manager1)
        create_data_steward(cls.manager2)
        set_user_avu(cls.manager2, "voPersonExternalID", "{}@external.edu".format(cls.manager2))
        create_user(cls.service_account)
        create_group(cls.group)
        add_user_to_group(cls.group, cls.manager1)
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        revert_latest_project_number()
        remove_user_from_group("DH-project-admins", cls.manager1)
        remove_user(cls.manager1)
        remove_user(cls.manager2)
        remove_user(cls.service_account)
        remove_group(cls.group)
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
        assert check_if_key_value_in_dict_list(groups, "name", self.group)

    def test_get_service_accounts_id(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.service_account)
        user_id = subprocess.check_output(run_iquest, shell=True).strip()

        rule = "/rules/tests/run_test.sh -r get_service_accounts_id"
        ret = subprocess.check_output(rule, shell=True)
        service_accounts = json.loads(ret)
        assert user_id in service_accounts

    def test_get_temporary_password_lifetime(self):
        rule = "/rules/tests/run_test.sh -r get_temporary_password_lifetime"
        ret = subprocess.check_output(rule, shell=True)
        temporary_password = json.loads(ret)
        assert temporary_password == int(os.getenv("ENV_IRODS_TEMP_PASSWORD_LIFETIME"))

    def test_get_user_admin_status(self):
        rule = "/rules/tests/run_test.sh -r get_user_admin_status -a {user}"
        ret = subprocess.check_output(rule.format(user=self.manager1), shell=True)
        admin_status = json.loads(ret)
        assert admin_status

        ret = subprocess.check_output(rule.format(user=self.manager2), shell=True)
        admin_status = json.loads(ret)
        assert not admin_status

    def test_get_user_attribute_value(self):
        rule = '/rules/tests/run_test.sh -r get_user_attribute_value -a "{},{},false"'.format(
            self.manager1, "eduPersonUniqueID"
        )
        ret = subprocess.check_output(rule, shell=True)
        edu_person_unique_id = json.loads(ret)
        assert edu_person_unique_id["value"] == "{}@sram.surf.nl".format(self.manager1)

    def test_get_user_group_memberships(self):
        rule = '/rules/tests/run_test.sh -r get_user_group_memberships -a "false,{}"'.format(self.manager1)
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)
        assert check_if_key_value_in_dict_list(groups, "name", self.group)

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

        ret = subprocess.check_output(rule.format(user=self.manager2), shell=True)
        affiliation_status = json.loads(ret)
        assert not affiliation_status

    def test_get_user_metadata(self):
        rule = "/rules/tests/run_test.sh -r get_user_metadata -a {}".format(self.manager2)
        ret = subprocess.check_output(rule.format(), shell=True)
        user = json.loads(ret)
        assert user["givenName"] == "test_data_steward"
        assert user["familyName"] == "LastName"

    def test_get_user_or_group_by_id(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.manager1)
        user_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.group)
        group_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        rule = "/rules/tests/run_test.sh -r get_user_or_group_by_id -a {id}"
        ret = subprocess.check_output(rule.format(id=user_id_iquest), shell=True)
        user = json.loads(ret)
        assert user["userName"] == self.manager1

        ret = subprocess.check_output(rule.format(id=group_id_iquest), shell=True)
        group = json.loads(ret)
        assert group["groupName"] == self.group

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

    def test_get_expanded_user_group_information(self):
        rule = '/rules/tests/run_test.sh -r get_expanded_user_group_information -a "{};{}"'.format(
            self.manager2, self.group
        )
        ret = subprocess.check_output(rule, shell=True)
        output = json.loads(ret)
        assert self.manager1 in output
        assert self.manager2 in output
        assert self.group in output
        assert output[self.manager1]["email"] == "{}@maastrichtuniversity.nl".format(self.manager1)

    def test_get_data_stewards(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getDataStewards.r"
        ret = subprocess.check_output(rule, shell=True)
        data_stewards = json.loads(ret)
        assert check_if_key_value_in_dict_list(data_stewards, "userName", self.data_steward)

    def test_get_display_name_for_account(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getDisplayNameForAccount.r \"*account='{}'\"".format(
            self.manager1
        )
        display_name = subprocess.check_output(rule, shell=True).rstrip("\n")
        assert display_name == "{} LastName".format(self.manager1)

    def test_get_email_for_account(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getEmailForAccount.r \"*account='{}'\"".format(
            self.manager1
        )
        email = subprocess.check_output(rule, shell=True).rstrip("\n")
        assert email == "{}@maastrichtuniversity.nl".format(self.manager1)

    def test_get_groups_rule_language(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getGroups.r \"*showSpecialGroups='false'\""
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)
        assert check_if_key_value_in_dict_list(groups, "userName", self.group)

    def test_get_users(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getUsers.r \"*showServiceAccounts='false'\""
        ret = subprocess.check_output(rule, shell=True)
        users = json.loads(ret)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager1)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager2)

    def test_get_users_in_group(self):
        run_iquest = 'iquest "%s" "SELECT USER_ID WHERE USER_NAME = \'{}\'"'.format(self.group)
        group_id_iquest = subprocess.check_output(run_iquest, shell=True).strip()

        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getUsersInGroup.r \"*groupId='{}'\"".format(
            group_id_iquest
        )
        ret = subprocess.check_output(rule, shell=True)
        users = json.loads(ret)
        assert check_if_key_value_in_dict_list(users, "userName", self.manager1)
        assert not check_if_key_value_in_dict_list(users, "userName", self.manager2)

    def test_list_groups_by_user(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/listGroupsByUser.r"
        ret = subprocess.check_output(rule, shell=True)
        groups = json.loads(ret)
        for group in groups:
            if group["GroupName"] == self.group:
                assert "{} LastName".format(self.manager1) in group["Users"]
                assert not "{} LastName".format(self.manager2) in group["Users"]
