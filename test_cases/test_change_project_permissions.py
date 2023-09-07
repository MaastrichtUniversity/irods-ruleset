import json
import subprocess

from dhpythonirodsutils import formatters

from test_cases.utils import (
    create_project,
    remove_project,
    create_user,
    remove_user,
    create_dropzone,
    start_and_wait_for_ingest,
    add_metadata_files_to_direct_dropzone,
    create_data_steward,
    wait_for_change_project_permissions_to_finish,
    get_project_collection_instance_in_elastic,
    run_index_all_project_collections_metadata,
)

"""
iRODS native rules usage summary:
- changeProjectPermissions: valid
"""


class TestChangeProjectPermissions:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    # a user who doesn't have any project access after the iRODS bootstraps
    depositor = "foobar"
    manager1 = depositor
    manager2 = "test_datasteward"
    data_steward = manager2

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = "direct"
    token = ""

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title = "collection_title"
    collection_id = "C000000001"
    project_collection_path = ""

    archive_destination_resource = "arcRescSURF01"
    new_user = "new_user"

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        # Running the index all rule: delete the current elasticsearch index that could be in a bad state
        run_index_all_project_collections_metadata()
        create_user(cls.depositor)
        create_data_steward(cls.data_steward)
        create_user(cls.new_user)
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        add_metadata_files_to_direct_dropzone(cls.token)
        start_and_wait_for_ingest(cls)

        cls.project_collection_path = formatters.format_project_collection_path(cls.project_id, cls.collection_id)

        cls.change_project_permissions_rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance \"changeProjectPermissions('{}','{}:{}')\" null  ruleExecOut"

        cls.rule_project_details = '/rules/tests/run_test.sh -r get_project_details -a "{},false" -u {}'.format(
            cls.project_path, cls.depositor
        )

        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)

        remove_user(cls.depositor)
        remove_user(cls.new_user)
        remove_user(cls.data_steward)
        print("End {}.teardown_class".format(cls.__name__))

    def test_new_user_has_no_access(self):
        # Check that new user has no rights on the project
        ret = subprocess.check_output(self.rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

    def test_new_user_has_own_access(self):
        # Add own rights for new user to the project
        subprocess.check_output(
            self.change_project_permissions_rule.format(self.project_id, self.new_user, "own"), shell=True
        )

        # Check that new user is in project managers
        ret = subprocess.check_output(self.rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has been added to the collection ACL with read rights
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:read".format(self.new_user) in ret_acl

        # Check that the elastic search document also includes new user
        instance = get_project_collection_instance_in_elastic(self.project_id)
        assert self.new_user in instance["user_access"]

    def test_new_user_has_write_access(self):
        # Update rights for new user to write on the project
        subprocess.check_output(
            self.change_project_permissions_rule.format(self.project_id, self.new_user, "write"), shell=True
        )

        # Check that new user is in project contributors
        ret = subprocess.check_output(self.rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has been added to the collection ACL with read rights
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:read".format(self.new_user) in ret_acl

    def test_new_user_has_read_access(self):
        # Update rights for new user to read on the project
        subprocess.check_output(
            self.change_project_permissions_rule.format(self.project_id, self.new_user, "read"), shell=True
        )

        # Check that new user is in project viewers
        ret = subprocess.check_output(self.rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has been added to the collection ACL with read rights
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:read".format(self.new_user) in ret_acl

    def test_new_user_has_access_removed(self):
        # Remove all new user right from the project
        subprocess.check_output(
            self.change_project_permissions_rule.format(self.project_id, self.new_user, "remove"), shell=True
        )

        # Check that new user has no rights anymore on the project
        ret = subprocess.check_output(self.rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has no rights anymore on the collection
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert self.new_user not in ret_acl

        # Check that new user has been removed from the elastic search document
        instance = get_project_collection_instance_in_elastic(self.project_id)
        assert self.new_user not in instance["user_access"]
