import json
import subprocess
import time

from dhpythonirodsutils import formatters

from test_cases.utils import (
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    add_metadata_files_to_direct_dropzone,
    remove_project,
    revert_latest_project_number,
)


class TestTapeArchive:
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

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title = "collection_title"
    collection_id = "C000000001"
    project_collection_path = ""

    service_account = "service-surfarchive"
    large_file_logical_path = ""

    run_ichmod = ""
    rule_status = ""
    check_small_file_resource = ""
    check_large_file_resource = ""

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        add_metadata_files_to_direct_dropzone(cls.token)
        cls.add_archive_data_to_dropzone()
        start_and_wait_for_ingest(cls)

        set_enable_archive = "imeta set -C /nlmumc/projects/{project_id} enableArchive true".format(
            project_id=cls.project_id
        )
        subprocess.check_call(set_enable_archive, shell=True)

        set_enable_un_archive = "imeta set -C /nlmumc/projects/{project_id} enableUnarchive true".format(
            project_id=cls.project_id
        )
        subprocess.check_call(set_enable_un_archive, shell=True)

        cls.project_collection_path = formatters.format_project_collection_path(cls.project_id, cls.collection_id)
        cls.large_file_logical_path = "{}/large_file".format(cls.project_collection_path)

        cls.run_ichmod = "ichmod -rM own {} {}".format(cls.service_account, cls.project_collection_path)
        cls.rule_status = '/rules/tests/run_test.sh -r get_project_migration_status -a "{}"'.format(cls.project_path)
        cls.check_small_file_resource = "ils -l {}/instance.json".format(cls.project_collection_path)
        cls.check_large_file_resource = "ils -l {}".format(cls.large_file_logical_path)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    # region extended setup
    @classmethod
    def add_archive_data_to_dropzone(cls):
        dropzone_path = formatters.format_dropzone_path(cls.token, cls.dropzone_type)
        large_file_path = "/tmp/large_file"
        logical_path = "{}/large_file".format(dropzone_path)

        with open(large_file_path, 'wb') as large_file:
            num_chars = 1024 * 1024 * 1024  # One GB
            large_file.write('0' * num_chars)
            iput = "iput -R stagingResc01 {} {}".format(large_file_path, logical_path)
            subprocess.check_call(iput, shell=True)

    # endregion

    # region tests
    def test_un_archive_collection(self):
        self.run_archive()
        self.run_un_archive(self.project_collection_path)

    def test_un_archive_file(self):
        self.run_archive()
        self.run_un_archive(self.large_file_logical_path)

    def run_archive(self):
        # Setup Archive
        subprocess.check_call(self.run_ichmod, shell=True)

        rule_archive = 'export clientUserName={} && irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/tapeArchive/prepareTapeArchive.r "*archColl=\'{}\'"'.format(
            self.service_account, self.project_collection_path
        )
        subprocess.check_call(rule_archive, shell=True)

        ret = subprocess.check_output(self.rule_status, shell=True)
        project_migration_status = json.loads(ret)

        self.assert_project_migration_output(project_migration_status)
        self.wait_for_migration(self.rule_status, project_migration_status)

        # Assert archive
        check_small_file_resource = "ils -l {}/instance.json".format(self.project_collection_path)
        output = subprocess.check_output(check_small_file_resource, shell=True)
        assert self.destination_resource in output

        check_large_file_resource = "ils -l {}".format(self.large_file_logical_path)
        output = subprocess.check_output(check_large_file_resource, shell=True)
        assert "arcRescSURF01" in output

    def run_un_archive(self, un_archive_path):
        # Setup Un-archive
        subprocess.check_call(self.run_ichmod, shell=True)
        rule_un_archive = 'export clientUserName={} && irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/tapeArchive/prepareTapeUnArchive.r "*archColl=\'{}\'"'.format(
            self.service_account, un_archive_path
        )
        subprocess.check_call(rule_un_archive, shell=True)

        ret = subprocess.check_output(self.rule_status, shell=True)
        project_migration_status = json.loads(ret)

        self.assert_project_migration_output(project_migration_status)
        self.wait_for_migration(self.rule_status, project_migration_status)

        # Assert un-archive
        output = subprocess.check_output(self.check_small_file_resource, shell=True)
        assert self.destination_resource in output

        output = subprocess.check_output(self.check_large_file_resource, shell=True)
        assert self.destination_resource in output

    # endregion

    # region helper functions
    def assert_project_migration_output(self, project_migration_status):
        assert project_migration_status[0]["repository"] == "SURFSara Tape"
        assert project_migration_status[0]["title"] == self.collection_title
        assert project_migration_status[0]["collection"] == self.collection_id
        assert project_migration_status[0]["status"]

    @staticmethod
    def wait_for_migration(rule_status, project_migration_status):
        fail_safe = 30
        while fail_safe != 0:
            ret = subprocess.check_output(rule_status, shell=True)

            project_migration_status = json.loads(ret)
            if not project_migration_status:
                fail_safe = 0
            else:
                fail_safe = fail_safe - 1
                time.sleep(2)
        assert not project_migration_status

    # endregion
