import json
import subprocess
import time

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs

from test_cases.utils import (
    create_project,
    remove_project,
    revert_latest_project_number,
    create_user,
    remove_user,
    create_dropzone,
    start_and_wait_for_ingest,
    add_metadata_files_to_direct_dropzone,
    set_irods_collection_avu,
    create_data_steward,
    wait_for_change_project_permissions_to_finish,
    get_project_collection_instance_in_elastic,
)

"""
iRODS native rules usage summary:
- changeProjectPermissions: valid
- detailsProject: 
    * IN RW, not in MDR
    * IN RS (reportProjects)
- getProjectCost: IN RS (detailsProject)


- listProjectManagers: not in RW, not in MDR
    * valid: IN detailsProjectCollection
    * obsolete: IN detailsProject 

- listProjectContributors: not in RW, not in MDR
    * valid: IN detailsProjectCollection
    * obsolete: IN detailsProject

- listProjectViewers: not in RW, not in MDR
    * valid: IN detailsProjectCollection
    * obsolete: IN detailsProject

- reportProjects:
    * used in disk_use_email.py -> docker-reporting
    * not in RW, not in MDR
"""


class TestProjects:
    project_paths = []
    project_ids = []
    project_titles = []
    project_title_base = "PROJECTNAME"
    project_title = ""

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

    number_of_projects = 3
    archive_destination_resource = "arcRescSURF01"
    new_user = "new_user"

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        create_user(cls.depositor)
        create_data_steward(cls.data_steward)
        create_user(cls.new_user)
        for project_index in range(cls.number_of_projects):
            cls.project_title = "{}{}".format(cls.project_title_base, project_index)
            project = create_project(cls)
            cls.project_paths.append(project["project_path"])
            cls.project_ids.append(project["project_id"])
            cls.project_titles.append(cls.project_title)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        for project_path in cls.project_paths:
            remove_project(project_path)
            revert_latest_project_number()

        remove_user(cls.depositor)
        remove_user(cls.new_user)
        remove_user(cls.data_steward)
        print("End {}.teardown_class".format(cls.__name__))

    def test_list_projects(self):
        rule = "/rules/tests/run_test.sh -r optimized_list_projects -u {}".format(self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        projects = json.loads(ret)

        assert len(projects) == self.number_of_projects

        for project_index in range(self.number_of_projects):
            self.assert_project_avu(projects[project_index], project_index)
            assert projects[project_index]["path"] == self.project_ids[project_index]
            assert projects[project_index]["OBI:0000103"] == self.manager1
            assert projects[project_index]["storageQuotaGb"] == "0"
            assert projects[project_index]["responsibleCostCenter"] == self.budget_number
            assert projects[project_index]["archiveDestinationResource"] == self.archive_destination_resource
            assert projects[project_index]["authorizationPeriodEndDate"] == "01-01-9999"
            assert projects[project_index]["dataRetentionPeriodEndDate"] == "01-01-9999"
            assert projects[project_index]["dataSteward"] == self.manager2
            assert projects[project_index]["ingestResource"] == self.ingest_resource
            assert projects[project_index]["resource"] == self.destination_resource

            assert len(projects[project_index]["managers"]) == 2
            assert len(projects[project_index]["contributors"]) == 0
            assert len(projects[project_index]["viewers"]) == 0

            # check if the list members are user ids, not usernames
            for manager in projects[project_index]["managers"]:
                assert manager.isnumeric()

    def test_change_project_permissions(self):
        # setup
        self.project_id = self.project_ids[0]
        project_path = self.project_paths[0]
        project_collection_path = formatters.format_project_collection_path(self.project_id, self.collection_id)
        self.token = create_dropzone(self)
        add_metadata_files_to_direct_dropzone(self.token)
        start_and_wait_for_ingest(self)

        change_project_permissions_rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance \"changeProjectPermissions('{}','{}:{}')\" null  ruleExecOut"

        # Check that new user has no rights on the project
        rule_project_details = '/rules/tests/run_test.sh -r get_project_details -a "{},false" -u {}'.format(
            project_path, self.depositor
        )
        ret = subprocess.check_output(rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        # Add own rights for new user to the project
        subprocess.check_output(
            change_project_permissions_rule.format(self.project_ids[0], self.new_user, "own"), shell=True
        )

        # Check that new user is in project managers
        ret = subprocess.check_output(rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has been added to the collection ACL with read rights
        acl = "ils -A {}".format(project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "{}#nlmumc:read".format(self.new_user) in ret_acl

        # Check that the elastic search document also includes new user
        instance = get_project_collection_instance_in_elastic(self.project_id)
        assert self.new_user in instance["user_access"]

        # Update rights for new user to write on the project
        subprocess.check_output(
            change_project_permissions_rule.format(self.project_ids[0], self.new_user, "write"), shell=True
        )

        # Check that new user is in project contributors
        ret = subprocess.check_output(rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has been added to the collection ACL with read rights
        acl = "ils -A {}".format(project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "{}#nlmumc:read".format(self.new_user) in ret_acl

        # Update rights for new user to read on the project
        subprocess.check_output(
            change_project_permissions_rule.format(self.project_ids[0], self.new_user, "read"), shell=True
        )

        # Check that new user is in project viewers
        ret = subprocess.check_output(rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has been added to the collection ACL with read rights
        acl = "ils -A {}".format(project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "{}#nlmumc:read".format(self.new_user) in ret_acl

        # Remove all new user right from the project
        subprocess.check_output(
            change_project_permissions_rule.format(self.project_ids[0], self.new_user, "remove"), shell=True
        )

        # Check that new user has no rights anymore on the project
        ret = subprocess.check_output(rule_project_details, shell=True)
        project = json.loads(ret)
        assert self.new_user not in project["managers"]["users"]
        assert self.new_user not in project["contributors"]["users"]
        assert self.new_user not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that new user has no rights anymore on the collection
        acl = "ils -A {}".format(project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert self.new_user not in ret_acl

        # Check that new user has been removed from the elastic search document
        instance = get_project_collection_instance_in_elastic(self.project_id)
        assert self.new_user not in instance["user_access"]

        # teardown
        subprocess.check_call("ichmod -rM own rods {}".format(project_collection_path), shell=True)
        subprocess.check_call("irm -rf {}".format(project_collection_path), shell=True)

    def test_project_manager_access(self):
        cmd = '/rules/tests/run_test.sh -r get_project_acl_for_manager -a "{},false" -u {}'
        rule = cmd.format(self.project_ids[0], self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)
        assert self.depositor in project["managers"]["users"]

        rule = cmd.format(self.project_ids[0], self.new_user)
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)
        assert not project

    def test_project_roles(self):
        project_id = self.project_ids[0]
        rule = '/rules/tests/run_test.sh -r get_project_contributors_metadata -a "{}" -u {}'.format(
            project_id, self.depositor
        )
        ret = subprocess.check_output(rule, shell=True)
        roles = json.loads(ret)

        assert roles["principalInvestigator"]["username"] == self.manager1
        assert roles["principalInvestigator"]["displayName"] == self.manager1 + " LastName"
        assert roles["principalInvestigator"]["email"] == self.manager1 + "@maastrichtuniversity.nl"
        assert roles["principalInvestigator"]["givenName"] == self.manager1
        assert roles["principalInvestigator"]["familyName"] == "LastName"

        assert roles["dataSteward"]["username"] == self.manager2

    def test_project_details(self):
        project_path = self.project_paths[0]
        project_id = self.project_ids[0]
        rule = '/rules/tests/run_test.sh -r get_project_details -a "{},false" -u {}'.format(
            project_path, self.depositor
        )
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)

        self.assert_project_avu(project)
        assert project["path"] == project_path
        assert project["project"] == project_id
        assert project["dataStewardDisplayName"] == self.data_steward + " LastName"
        assert project["principalInvestigatorDisplayName"] == self.manager1 + " LastName"
        assert project["respCostCenter"] == self.budget_number
        assert project["storageQuotaGiB"] == "0"
        assert project["has_financial_view_access"]
        assert project["description"] == ""

    def test_projects_finance(self):
        # setup
        self.project_id = self.project_ids[0]
        project_collection_path = formatters.format_project_collection_path(self.project_id, self.collection_id)
        self.token = create_dropzone(self)
        add_metadata_files_to_direct_dropzone(self.token)
        start_and_wait_for_ingest(self)

        # asserts
        rule = "/rules/tests/run_test.sh -r get_projects_finance -u {}".format(self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        projects = json.loads(ret)

        assert len(projects) == self.number_of_projects
        for project in projects:
            assert project["project_id"] in self.project_ids
            assert project["title"] in self.project_titles
            assert project["budget_number"] == self.budget_number

            # the project with an ingested collection
            if project["project_id"] == self.project_id:
                assert project["collections"][0]["collection"] == project_collection_path
                assert project["collections"][0]["data_size_gib"] == 0.0005072075873613358
                assert project["collections"][0]["details_per_resource"]
                assert int(project["collections"][0]["collection_storage_cost"]) == 0
                assert int(project["project_cost_monthly"]) == 0
                assert int(project["project_cost_yearly"]) == 0
                assert project["project_size_gb"] == 0.0005446100000000001
                assert project["project_size_gib"] == 0.0005072075873613358
            else:
                assert project["project_cost_monthly"] == 0
                assert project["project_cost_yearly"] == 0
                assert project["project_size_gb"] == 0.0
                assert project["project_size_gib"] == 0
                assert project["collections"] == []

        # teardown
        subprocess.check_call("ichmod -rM own rods {}".format(project_collection_path), shell=True)
        subprocess.check_call("irm -rf {}".format(project_collection_path), shell=True)

    def test_project_resource_availability(self):
        project_id = self.project_ids[0]

        assert self.get_project_resource_availability(project_id)

        self.update_resource_availability(self.ingest_resource, "down")
        assert not self.get_project_resource_availability(project_id)
        self.update_resource_availability(self.ingest_resource, "up")

        self.update_resource_availability(self.destination_resource, "down")
        assert not self.get_project_resource_availability(project_id)
        self.update_resource_availability(self.destination_resource, "up")

        self.update_resource_availability(self.archive_destination_resource, "down")
        assert not self.get_project_resource_availability(project_id)
        self.update_resource_availability(self.archive_destination_resource, "up")

        assert self.get_project_resource_availability(project_id)

    def test_list_contributing_projects(self):
        # assert depositor has contributing access to all projects
        cmd = '/rules/tests/run_test.sh -r list_contributing_projects -a "false" -u {}'
        rule_as_depositor = cmd.format(self.depositor)
        ret = subprocess.check_output(rule_as_depositor, shell=True)
        projects = json.loads(ret)

        assert len(projects) == self.number_of_projects
        for project_index in range(self.number_of_projects):
            assert projects[project_index]["id"] == self.project_ids[project_index]
            assert projects[project_index]["title"] == self.project_titles[project_index]
            assert projects[project_index]["collectionMetadataSchemas"] == self.schema_name
            assert projects[project_index]["resource"] == self.destination_resource

            assert len(projects[project_index]["managers"]["users"]) == 2
            assert self.manager1 in projects[project_index]["managers"]["users"]
            assert self.manager2 in projects[project_index]["managers"]["users"]

        # setup new user
        project_path = self.project_paths[0]
        rule_as_new_user = cmd.format(self.new_user)

        # assert new user has no project access
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        projects = json.loads(ret)
        assert len(projects) == 0

        # assert new user has one project access
        ichmod = "ichmod -rM {} {} {}"
        run_ichmod = ichmod.format("write", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        projects = json.loads(ret)
        assert len(projects) == 1

        # teardown
        run_ichmod = ichmod.format("null", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)

    def test_list_contributing_projects_by_attribute(self):
        # assert no project with ENABLE_ARCHIVE true
        rule = '/rules/tests/run_test.sh -r list_contributing_projects_by_attribute -a "{}" -u {}'.format(
            ProjectAVUs.ENABLE_ARCHIVE.value, self.depositor
        )
        ret = subprocess.check_output(rule, shell=True)
        projects = json.loads(ret)
        assert len(projects) == 0

        # setup set all project to ENABLE_ARCHIVE true
        for project_path in self.project_paths:
            set_irods_collection_avu(project_path, ProjectAVUs.ENABLE_ARCHIVE.value, "true")

        # assert
        ret = subprocess.check_output(rule, shell=True)
        projects = json.loads(ret)
        assert len(projects) == self.number_of_projects
        for project_index in range(self.number_of_projects):
            assert projects[project_index]["id"] == self.project_ids[project_index]
            assert projects[project_index]["title"] == self.project_titles[project_index]
            assert projects[project_index]["path"] == self.project_paths[project_index]

        # teardown
        for project_path in self.project_paths:
            set_irods_collection_avu(project_path, ProjectAVUs.ENABLE_ARCHIVE.value, "false")

    def test_list_project_managers(self):
        # assert depositor has manager access to all projects
        project_id = self.project_ids[0]
        project_path = self.project_paths[0]
        cmd = '/rules/tests/run_test.sh -r list_project_managers -a "{},false" -u {}'
        rule = cmd.format(project_id, self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 2
        assert self.manager1 in project["users"]
        assert self.manager2 in project["users"]

        # assert new user has no access
        rule_as_new_user = cmd.format(project_id, self.new_user)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 0

        # assert new user has access
        ichmod = "ichmod -rM {} {} {}"
        run_ichmod = ichmod.format("own", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 3
        assert self.manager1 in project["users"]
        assert self.manager2 in project["users"]
        assert self.new_user in project["users"]

        # teardown
        run_ichmod = ichmod.format("null", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)

    def test_list_project_contributors(self):
        # assert depositor has contributing access to all projects (inherited by being manager)
        project_id = self.project_ids[0]
        project_path = self.project_paths[0]
        cmd = '/rules/tests/run_test.sh -r list_project_contributors -a "{},{},false" -u {}'
        rule = cmd.format(project_id, "true", self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 2
        assert self.manager1 in project["users"]
        assert self.manager2 in project["users"]

        # assert new user has no access
        rule_as_new_user = cmd.format(project_id, "false", self.new_user)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 0

        # assert new user has access
        ichmod = "ichmod -rM {} {} {}"
        run_ichmod = ichmod.format("write", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 1
        assert self.new_user in project["users"]

        # teardown
        run_ichmod = ichmod.format("null", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)

    def test_list_project_viewers(self):
        # assert depositor has contributing access to all projects (inherited by being manager)
        project_id = self.project_ids[0]
        project_path = self.project_paths[0]
        cmd = '/rules/tests/run_test.sh -r list_project_viewers -a "{},{},false" -u {}'
        rule = cmd.format(project_id, "true", self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 2
        assert self.manager1 in project["users"]
        assert self.manager2 in project["users"]

        # assert new user has no access
        rule_as_new_user = cmd.format(project_id, "false", self.new_user)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 0

        # assert new user has access
        ichmod = "ichmod -rM {} {} {}"
        run_ichmod = ichmod.format("read", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)
        ret = subprocess.check_output(rule_as_new_user, shell=True)
        project = json.loads(ret)
        assert len(project["users"]) == 1
        assert self.new_user in project["users"]

        # teardown
        run_ichmod = ichmod.format("null", self.new_user, project_path)
        subprocess.check_call(run_ichmod, shell=True)

    def test_list_projects_minimal(self):
        rule = "/rules/tests/run_test.sh -r list_projects_minimal -u {}".format(self.depositor)
        ret = subprocess.check_output(rule, shell=True)
        projects = json.loads(ret)
        assert len(projects) == self.number_of_projects
        for project_index in range(self.number_of_projects):
            assert projects[project_index]["id"] == self.project_ids[project_index]
            assert projects[project_index]["title"] == self.project_titles[project_index]

    def test_get_contributing_project(self, project_index=0):
        project_id = self.project_ids[project_index]
        project_title = self.project_titles[project_index]
        rule = '/rules/tests/run_test.sh -r get_contributing_project -a "{},false" -u {}'.format(
            project_id, self.manager1
        )
        ret = subprocess.check_output(rule, shell=True)
        project = json.loads(ret)
        assert project["id"] == project_id
        assert project["title"] == project_title

    def assert_project_avu(self, project, project_index=0):
        assert project["collectionMetadataSchemas"] == self.schema_name
        assert project["dataSizeGiB"] == 0.0
        assert project["enableArchive"] == "false"
        assert project["enableContributorEditMetadata"] == "false"
        assert project["enableDropzoneSharing"] == "true"
        assert project["enableOpenAccessExport"] == "false"
        assert project["enableUnarchive"] == "false"
        assert project["title"] == self.project_titles[project_index]

    @staticmethod
    def update_resource_availability(resource, availability):
        run_imeta = "iadmin modresc {} status {}".format(resource, availability)
        subprocess.check_call(run_imeta, shell=True)

    @staticmethod
    def get_project_resource_availability(project_id):
        rule = '/rules/tests/run_test.sh -r get_project_resource_availability -a "{},true,true,true"'.format(project_id)
        ret = subprocess.check_output(rule, shell=True)
        available = json.loads(ret)

        return available
