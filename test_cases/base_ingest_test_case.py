import fcntl
import json
import subprocess
import time
from contextlib import contextmanager
import pytest

from dhpythonirodsutils import formatters

from test_cases.utils import (
    remove_project,
    wait_for_set_acl_for_metadata_snapshot_to_finish,
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    run_index_all_project_collections_metadata,
    get_project_collection_instance_in_elastic,
    get_log_position,
    wait_for_log_matching,
)


INGEST_SCENARIOS = [
    pytest.param(("ires-hnas-umResource", "passRescUM01", False),
                 id="um-manager", marks=pytest.mark.xdist_group("um-manager")),
    pytest.param(("ires-hnas-azmResource", "replRescAZM02", False),
                 id="azm-manager", marks=pytest.mark.xdist_group("azm-manager")),
    pytest.param(("ires-hnas-umResource", "replRescUMCeph01", False),
                 id="s3-manager", marks=pytest.mark.xdist_group("s3-manager")),
    pytest.param(("ires-hnas-umResource", "passRescUM01", True),
                 id="um-contributor", marks=pytest.mark.xdist_group("um-contributor")),
    pytest.param(("ires-hnas-azmResource", "replRescAZM02", True),
                 id="azm-contributor", marks=pytest.mark.xdist_group("azm-contributor")),
    pytest.param(("ires-hnas-umResource", "replRescUMCeph01", True),
                 id="s3-contributor", marks=pytest.mark.xdist_group("s3-contributor")),
]


@contextmanager
def ingest_preparation(request, tmp_path_factory):
    if not hasattr(request.config, "workerinput"):
        run_index_all_project_collections_metadata()
        yield
        return

    # The session fixture has prepared the index. Stage files and calculate
    # global sizes without races.
    # Transfers and their assertions run after releasing this lock.
    shared_directory = tmp_path_factory.getbasetemp().parent
    with (shared_directory / "ingest-preparation.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


# TODO Test set_post_ingestion_error_avu
# TODO Test for item added to delayed queue (iqstat)
# TODO Test for trigger pre ingest error validation with corrupt metadata
# TODO Test for trigger post ingest with missing dropzone creator email

"""
Rule usage summary

checkDropZoneACL:
    *   In RS (create_drop_zone, get_active_drop_zone, validate_dropzone & list_active_drop_zones)

createRemoteDirectory:
    *   In RS (create_drop_zone)

delayRemoveDropzone:
    *   In RS (finish_ingest)

editIngest:
    *   In MDR, RW

list_active_drop_zones:
    *   NOT in RW, MDR
    *   In RS (get_user_active_processes)
"""


class BaseIngestScenario:
    # How long to wait for the first size ingested log message before failing the test
    SIZE_INGESTED_LOG_DETECTION_TIMEOUT_SECONDS = 10
    log_position_before_ingest = 0

    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = ""
    destination_resource = ""
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = ""
    token = ""
    dropzone_total_size = ""
    dropzone_num_files = ""

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title = "collection_title"
    collection_id = "C000000001"
    collection_number_files = 8
    collection_total_size = 63510370

    # iRODS seems to have 3 different ways/protocols to transfer data, depending on the file size:
    # * 0     < X < 4  MB
    # * 4 MB  < X < 32 MB
    # * 32 MB < X
    files_per_protocol = {
        "0bytes.file": 0,
        "50K' and data.file": 51200,
        "15M.file": 15728640,
        "45M.file": 47185920,
    }

    def add_metadata_files_to_dropzone(self, token):
        pass

    def add_data_to_dropzone(self):
        pass

    def calculate_all_dropzone_sizes(self):
        rule = '/rules/tests/run_test.sh -r calculate_all_dropzone_sizes'
        subprocess.check_call(rule, shell=True)


@pytest.fixture(scope="module")
def ingest_scenario(request, tmp_path_factory):
    """Set up one ingest per module/scenario, shared across its test classes.

    Tests request this fixture directly or through the metadata fixtures.
    request.param contains the resource/role scenario selected by indirect
    parametrization. Code before yield is setup; pytest runs the scenario's
    tests at yield, then resumes below it for teardown, even if a test fails.
    If setup fails before reaching yield, that teardown is not registered.
    """
    scenario = request.module.IngestScenario()
    scenario.ingest_resource, scenario.destination_resource, as_contributor = request.param
    scenario.depositor = BaseIngestScenario.depositor
    scenario.collection_creator = BaseIngestScenario.collection_creator
    scenario.project_path = ""
    scenario.project_id = ""
    scenario.token = ""
    scenario.log_position_before_ingest = 0
    print()
    print(f"Start {type(scenario).__name__}.ingest_scenario")
    with ingest_preparation(request, tmp_path_factory):
        project = create_project(scenario)
        scenario.project_path = project["project_path"]
        scenario.project_id = project["project_id"]
        if as_contributor:
            scenario.depositor = "dlinssen"
            scenario.collection_creator = "d.linssen@maastrichtuniversity.nl"
            rule_set_acl = f'/rules/tests/run_test.sh -r set_acl -a "default,write,{scenario.depositor},{scenario.project_path}"'
            subprocess.check_call(rule_set_acl, shell=True)
        scenario.token = create_dropzone(scenario)
        scenario.add_metadata_files_to_dropzone(scenario.token)
        scenario.add_data_to_dropzone()
        scenario.calculate_all_dropzone_sizes()
    scenario.log_position_before_ingest = get_log_position()
    start_and_wait_for_ingest(scenario)
    print(f"End {type(scenario).__name__}.ingest_scenario")

    yield scenario  # Hand control to the tests; resume here afterwards to clean up.

    print()
    print(f"Start {type(scenario).__name__}.ingest_scenario teardown")
    wait_for_set_acl_for_metadata_snapshot_to_finish(scenario.project_id)
    remove_project(scenario.project_path)
    print(f"End {type(scenario).__name__}.ingest_scenario teardown")


@pytest.fixture(scope="module")
def edited_collection(ingest_scenario):
    from test_cases.base_customizable_metadata_test_case import edit_collection_metadata, edit_metadata_instance

    ingest_scenario.project_collection_path = formatters.format_project_collection_path(
        ingest_scenario.project_id, ingest_scenario.collection_id
    )
    ingest_scenario.new_collection_title = "Test edit title"
    ingest_scenario.metadata_version = 2
    edit_collection_metadata(ingest_scenario, edit_metadata_instance)
    return ingest_scenario


@pytest.fixture(scope="module")
def schema_changed_collection(edited_collection):
    from test_cases.base_customizable_metadata_test_case import edit_collection_metadata, edit_metadata_schema

    # The previous close-ACL rule must finish before opening the same collection.
    wait_for_set_acl_for_metadata_snapshot_to_finish(edited_collection.project_id)
    edited_collection.new_schema_name = "New DataHub General Schema"
    edited_collection.metadata_version = 3
    edit_collection_metadata(edited_collection, edit_metadata_schema)
    return edited_collection


class BaseTestCaseIngest:
    lifecycle_phase = 0

    # region tests
    def test_verify_dropzone_size_is_correct(self, ingest_scenario):
        # Implementation for verifying dropzone size
        dropzone_path = formatters.format_dropzone_path(ingest_scenario.token, ingest_scenario.dropzone_type)
        metadata = f"imeta ls -C {dropzone_path} dropzoneSize"
        ret_metadata = subprocess.check_output(metadata, shell=True, encoding="UTF-8")
        if ingest_scenario.dropzone_type == "direct":
            assert f"value: 63169378" in ret_metadata
        if ingest_scenario.dropzone_type == "mounted":
            assert f"value: 62965760" in ret_metadata

    def test_collection_avu(self, ingest_scenario):
        rule_list_collections = f'/rules/tests/run_test.sh -r list_collections -a "{ingest_scenario.project_path}"'
        ret_list_collections = subprocess.check_output(rule_list_collections, shell=True)
        list_collections = json.loads(ret_list_collections)
        assert list_collections[0]["id"] == ingest_scenario.collection_id

        rule_collection_detail = f'/rules/tests/run_test.sh -r detailsProjectCollection -a "{ingest_scenario.project_id},{ingest_scenario.collection_id},false"'
        ret_collection_detail = subprocess.check_output(rule_collection_detail, shell=True)
        collection_detail = json.loads(ret_collection_detail)
        assert collection_detail["creator"] == ingest_scenario.collection_creator
        assert collection_detail["collection"] == ingest_scenario.collection_id
        assert collection_detail["title"] == ingest_scenario.collection_title
        assert int(collection_detail["numFiles"]) == ingest_scenario.collection_number_files
        assert int(collection_detail["byteSize"]) == ingest_scenario.collection_total_size
        assert ingest_scenario.manager1 in collection_detail["managers"]["users"]
        assert ingest_scenario.manager2 in collection_detail["managers"]["users"]

    def test_collection_instance(self, ingest_scenario, tmp_path):
        tmp_instance_path = tmp_path / "instance.json"
        iget = f"iget -f {ingest_scenario.project_path}/{ingest_scenario.collection_id}/instance.json {tmp_instance_path}"
        subprocess.check_call(iget, shell=True)
        with open(tmp_instance_path) as tmp_instance_file:
            tmp_instance = json.load(tmp_instance_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith(f"{ingest_scenario.project_id}{ingest_scenario.collection_id}instance.1")

    def test_collection_schema(self, ingest_scenario, tmp_path):
        tmp_schema_path = tmp_path / "schema.json"
        iget = f"iget -f {ingest_scenario.project_path}/{ingest_scenario.collection_id}/schema.json {tmp_schema_path}"
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_instance = json.load(tmp_schema_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith(f"{ingest_scenario.project_id}{ingest_scenario.collection_id}schema.1")

    def test_collection_acl(self, ingest_scenario):
        """
        Check the project collection acl; assume that all members only have read access.
        """
        acl = f"ils -A {ingest_scenario.project_path}/{ingest_scenario.collection_id}"
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "own" not in ret
        assert f"{ingest_scenario.manager1}#nlmumc:read_object" in ret
        assert f"{ingest_scenario.manager2}#nlmumc:read_object" in ret

    def test_project_acl(self, ingest_scenario):
        acl = f"ils -A {ingest_scenario.project_path}"
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{ingest_scenario.manager1}#nlmumc:own" in ret
        assert f"{ingest_scenario.manager2}#nlmumc:own" in ret

    def test_collection_pid(self, ingest_scenario):
        import requests

        # The public resolver can lag behind successful EpicPID registration.
        rule = f'/rules/tests/run_test.sh -r detailsProjectCollection -a "{ingest_scenario.project_id},{ingest_scenario.collection_id},false"'
        ret = subprocess.check_output(rule, shell=True)
        collection_detail = json.loads(ret)

        url = f"https://hdl.handle.net/{collection_detail['PID']}"
        for delay in (0, 1, 2, 4, 8):
            if delay:
                time.sleep(delay)
            response = requests.get(url, allow_redirects=False, timeout=8)
            if response.status_code == 302:
                return
        assert response.status_code == 302, f"{url}: HTTP {response.status_code} after 5 attempts"

    def test_collection_data_resource(self, ingest_scenario):
        """
        Check the data object that are in the project collection use the correct project destination resource.
        """
        query = f'iquest --no-page "%s" "SELECT DATA_RESC_HIER WHERE COLL_PARENT_NAME = \'{ingest_scenario.project_path}/{ingest_scenario.collection_id}\'"'
        ret = subprocess.check_output(query, shell=True, encoding="UTF-8")
        resources = ret.splitlines()
        if "repl" in ingest_scenario.destination_resource:
            assert len(resources) == 2
            assert ingest_scenario.destination_resource in resources[0]
            assert ingest_scenario.destination_resource in resources[1]
        elif "pass" in ingest_scenario.destination_resource:
            assert len(resources) == 1
            assert ingest_scenario.destination_resource in resources[0]

    def test_collection_data_replicas(self, ingest_scenario):
        """
        Check that data objects (instance.json & schema.json) at the root of project collection are correctly replicated
        """
        query = f'iquest --no-page "%s" "SELECT count(DATA_RESC_NAME) WHERE COLL_PARENT_NAME = \'{ingest_scenario.project_path}/{ingest_scenario.collection_id}\'"'
        ret = subprocess.check_output(query, shell=True)
        if "repl" in ingest_scenario.destination_resource:
            assert int(ret) == 4
        elif "pass" in ingest_scenario.destination_resource:
            assert int(ret) == 2

    def test_elastic_index_update(self, ingest_scenario):
        instance = get_project_collection_instance_in_elastic(ingest_scenario.project_id)
        # The collection title in the instance doesn't match the collection title AVU
        # because of the way, we ingest the instance.json in the test-cases
        # collection_title = instance["3_Title"]["title"]["@value"]
        # print(collection_title)
        # assert collection_title == ingest_scenario.collection_title

        project_title = instance["project_title"]
        assert project_title == ingest_scenario.project_title

        project_id = instance["project_id"]
        assert project_id == ingest_scenario.project_id

        collection_id = instance["collection_id"]
        assert collection_id == ingest_scenario.collection_id

    def test_dropzone_pre_ingest_avu(self, ingest_scenario):
        """This test asserts that the dropzone AVUs set with the rule 'save_dropzone_pre_ingest_info' are correct."""

        dropzone_path = formatters.format_dropzone_path(ingest_scenario.token, ingest_scenario.dropzone_type)

        run_iquest = (
            f'iquest "%s" "SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = \'{dropzone_path}\' '
            'and META_COLL_ATTR_NAME = \'totalSize\' "'
        )
        total_size = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()

        run_iquest = (
            f'iquest "%s" "SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = \'{dropzone_path}\' '
            'and META_COLL_ATTR_NAME = \'numFiles\' "'
        )
        num_files = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()

        assert total_size == ingest_scenario.dropzone_total_size
        assert num_files == ingest_scenario.dropzone_num_files

    def test_dropzone_validation_errors_document(self, ingest_scenario):
        """A successful direct or mounted ingest stores an empty validation error list."""
        rule = (
            f'/rules/tests/run_test.sh -r get_dropzone_validation_errors'
            f' -a "{ingest_scenario.token},{ingest_scenario.dropzone_type}"'
        )
        result = json.loads(subprocess.check_output(rule, shell=True, encoding="UTF-8"))
        assert result == {"found": True, "validation_errors": []}
    
    def test_size_ingested_avu(self, ingest_scenario):
        collection_path = f"{ingest_scenario.project_path}/{ingest_scenario.collection_id}"
        if not wait_for_log_matching(
            ingest_scenario.log_position_before_ingest,
            lambda msg: collection_path in msg and "sizeIngested" in msg and ingest_scenario.dropzone_total_size in msg,
            ingest_scenario.SIZE_INGESTED_LOG_DETECTION_TIMEOUT_SECONDS,
        ):
            pytest.fail(
                f"No size ingested log message detected within"
                f" {ingest_scenario.SIZE_INGESTED_LOG_DETECTION_TIMEOUT_SECONDS}s;"
                f" the size ingested mechanism may not be functioning"
            )
        
    # endregion tests
