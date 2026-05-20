import json
import subprocess
import time

import pytest
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProcessState

from test_cases.utils import (
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    remove_project,
    create_data_steward,
    create_user,
    remove_user,
)


class BaseTestTapeArchive:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "tape_test_manager"
    manager1 = depositor
    manager2 = "tape_test_data_steward"
    data_steward = manager2
    service_account = "service-surfarchive"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = "direct"
    token = ""

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title = "collection_title"
    collection_id = "C000000001"

    project_collection_path = ""
    large_file_logical_path = ""
    run_ichmod = ""
    rule_status = ""
    check_small_file_resource = ""
    check_large_file_resource = ""

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        pass

    @classmethod
    def give_user_ingest_access(cls, user):
        pass

    @classmethod
    def setup_class(cls):
        print()
        print(f"Start {cls.__name__}.setup_class")
        create_user(cls.manager1)
        create_data_steward(cls.manager2)
        cls.give_user_ingest_access(cls.manager1)

        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        cls.add_archive_data_to_dropzone()
        start_and_wait_for_ingest(cls)

        set_enable_archive = f"imeta set -C {cls.project_path} enableArchive true"
        subprocess.check_call(set_enable_archive, shell=True)

        set_enable_unarchive = f"imeta set -C {cls.project_path} enableUnarchive true"
        subprocess.check_call(set_enable_unarchive, shell=True)

        cls.project_collection_path = formatters.format_project_collection_path(cls.project_id, cls.collection_id)
        cls.large_file_logical_path = f"{cls.project_collection_path}/large_file"

        cls.run_ichmod = f"ichmod -rM own {cls.service_account} {cls.project_collection_path}"
        cls.rule_status = '/rules/tests/run_test.sh -r get_user_active_processes -a "false,true,true"'
        cls.check_small_file_resource = f"ils -l {cls.project_collection_path}/instance.json"
        cls.check_large_file_resource = f"ils -l {cls.large_file_logical_path}"
        print(f"End {cls.__name__}.setup_class")

    @classmethod
    def teardown_class(cls):
        print()
        print(f"Start {cls.__name__}.teardown_class")
        remove_project(cls.project_path)
        remove_user(cls.manager1)
        remove_user(cls.manager2)
        print(f"End {cls.__name__}.teardown_class")

    # region extended setup
    @classmethod
    def add_archive_data_to_dropzone(cls):
        pass

    # endregion

    # region tests
    def test_unarchive_collection(self):
        self.run_archive()
        self.run_unarchive(self.project_collection_path)

    def test_unarchive_file(self):
        self.run_archive()
        self.run_unarchive(self.large_file_logical_path)

    def test_tape_avu_permissions(self):
        # setup
        subprocess.check_call(f"imeta set -C {self.project_path} enableArchive false", shell=True)
        subprocess.check_call(f"imeta set -C {self.project_path} enableUnarchive false", shell=True)

        # assert
        with pytest.raises(subprocess.CalledProcessError):
            self.run_archive()

        with pytest.raises(subprocess.CalledProcessError):
            self.run_unarchive(self.project_collection_path)

        # teardown
        subprocess.check_call(f"imeta set -C {self.project_path} enableArchive true", shell=True)
        subprocess.check_call(f"imeta set -C {self.project_path} enableUnarchive true", shell=True)

    def test_tape_running_archive_process(self):
        # setup
        subprocess.check_call(
            f"imeta -M set -C {self.project_collection_path} archiveState in-queue-for-archival", shell=True
        )

        # assert
        with pytest.raises(subprocess.CalledProcessError):
            self.run_archive()

        with pytest.raises(subprocess.CalledProcessError):
            self.run_unarchive(self.project_collection_path)

        # teardown
        subprocess.check_call(
            f"imeta -M rm -C {self.project_collection_path} archiveState in-queue-for-archival", shell=True
        )

    def test_tape_running_unarchive_process(self):
        # setup
        subprocess.check_call(
            f"imeta -M set -C {self.project_collection_path} unArchiveState in-queue-for-unarchival", shell=True
        )

        # assert
        with pytest.raises(subprocess.CalledProcessError):
            self.run_archive()

        with pytest.raises(subprocess.CalledProcessError):
            self.run_unarchive(self.project_collection_path)

        # teardown
        subprocess.check_call(
            f"imeta -M rm -C {self.project_collection_path} unArchiveState in-queue-for-unarchival", shell=True
        )

    def test_tape_when_tape_resc_is_down(self):
        # setup
        subprocess.check_call("iadmin modresc arcRescSURF01 status down", shell=True)

        # assert
        with pytest.raises(subprocess.CalledProcessError):
            self.run_archive()

        with pytest.raises(subprocess.CalledProcessError):
            self.run_unarchive(self.project_collection_path)

        # teardown
        subprocess.check_call("iadmin modresc arcRescSURF01 status up", shell=True)

    def test_tape_when_destination_resc_is_down(self):
        # setup
        subprocess.check_call(f"iadmin modresc {self.destination_resource} status down", shell=True)

        # assert
        with pytest.raises(subprocess.CalledProcessError):
            self.run_archive()

        with pytest.raises(subprocess.CalledProcessError):
            self.run_unarchive(self.project_collection_path)

        # teardown
        subprocess.check_call(f"iadmin modresc {self.destination_resource} status up", shell=True)

    def test_unarchive_invalid_path(self):
        # assert
        with pytest.raises(subprocess.CalledProcessError):
            self.run_unarchive("/nlmumc/home/rods")

    def test_archive_without_service_account(self):
        rule_archive = f'/rules/tests/run_test.sh -r start_archive -a "{self.project_collection_path},{self.manager1}" -u rods'
        # assert
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(rule_archive, shell=True)

    def test_unarchive_without_service_account(self):
        rule_unarchive = f'/rules/tests/run_test.sh -r start_unarchive -a "{self.project_collection_path},{self.manager1}" -u rods'
        # assert
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(rule_unarchive, shell=True)

    def test_tape_with_non_existent_pc(self):
        rule_unarchive = f'/rules/tests/run_test.sh -r start_unarchive -a "/nlmumc/projects/P100000000/C000000001,{self.manager1}" -u {self.service_account}'
        rule_archive = f'/rules/tests/run_test.sh -r start_archive -a "/nlmumc/projects/P100000000/C000000001,{self.manager1}" -u {self.service_account}'
        # assert
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(rule_unarchive, shell=True)
        # assert
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(rule_archive, shell=True)

    # endregion

    # region helper functions
    def run_archive(self):
        # Setup Archive
        subprocess.check_call(self.run_ichmod, shell=True)
        rule_archive = f'/rules/tests/run_test.sh -r start_archive -a "{self.project_collection_path},{self.manager1}" -u {self.service_account}'
        subprocess.check_call(rule_archive, shell=True)

        ret = subprocess.check_output(self.rule_status, shell=True)
        active_processes = json.loads(ret)

        self.assert_active_processes_output(active_processes)
        self.wait_for_active_processes(self.rule_status, active_processes)

        # Assert archive
        output = subprocess.check_output(self.check_small_file_resource, shell=True, encoding="UTF-8")
        assert self.destination_resource in output

        output = subprocess.check_output(self.check_large_file_resource, shell=True, encoding="UTF-8")
        assert "arcRescSURF01" in output

    def run_unarchive(self, unarchive_path):
        # Setup Un-archive
        subprocess.check_call(self.run_ichmod, shell=True)
        rule_unarchive = f'/rules/tests/run_test.sh -r start_unarchive -a "{unarchive_path},{self.manager1}" -u {self.service_account}'
        subprocess.check_call(rule_unarchive, shell=True)

        ret = subprocess.check_output(self.rule_status, shell=True)
        active_processes = json.loads(ret)

        self.assert_active_processes_output(active_processes)
        self.wait_for_active_processes(self.rule_status, active_processes)

        # Assert un-archive
        output = subprocess.check_output(self.check_small_file_resource, shell=True, encoding="UTF-8")
        assert self.destination_resource in output

        output = subprocess.check_output(self.check_large_file_resource, shell=True, encoding="UTF-8")
        assert self.destination_resource in output

    def assert_active_processes_output(self, active_processes):
        assert active_processes[ProcessState.IN_PROGRESS.value][0]["repository"] == "SURFSara Tape"
        assert active_processes[ProcessState.IN_PROGRESS.value][0]["collection_title"] == self.collection_title
        assert active_processes[ProcessState.IN_PROGRESS.value][0]["collection_id"] == self.collection_id
        assert active_processes[ProcessState.IN_PROGRESS.value][0]["state"]

    @staticmethod
    def wait_for_active_processes(rule_status, active_processes):
        fail_safe = 60
        while fail_safe != 0:
            ret = subprocess.check_output(rule_status, shell=True)

            active_processes = json.loads(ret)
            if not active_processes[ProcessState.IN_PROGRESS.value]:
                fail_safe = 0
            else:
                fail_safe = fail_safe - 1
                time.sleep(2)
        assert not active_processes[ProcessState.IN_PROGRESS.value]

    # endregion
