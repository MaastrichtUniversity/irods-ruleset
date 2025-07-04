import json
import subprocess

from dhpythonirodsutils import formatters

from test_cases.utils import (
    remove_project,
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    run_index_all_project_collections_metadata,
    get_project_collection_instance_in_elastic,
)


# TODO Test set_post_ingestion_error_avu
# TODO Test for item added to delayed queue (iqstat)
# TODO Test for trigger pre ingest error validation with corrupt metadata
# TODO Test for trigger post ingest with missing dropzone creator email

"""
iRODS Rule language rules

checkDropZoneACL:
    *   In RS (create_drop_zone, get_active_drop_zone, validate_dropzone & listActiveDropZones)

createRemoteDirectory:
    *   In RS (create_drop_zone)

delayRemoveDropzone:
    *   In RS (finish_ingest)

editIngest:
    *   In MDR, RW

listActiveDropZones:
    *   NOT in RW, MDR
    *   In RS (get_user_active_processes)
"""


class BaseTestCaseIngest:
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
        "50K.file": 51200,
        "15M.file": 15728640,
        "45M.file": 47185920,
    }

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        pass

    @classmethod
    def add_data_to_dropzone(cls):
        pass

    @classmethod
    def perform_tasks_after_project_creation(cls):
        pass

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        # Running the index all rule: delete the current elasticsearch index that could be in a bad state
        run_index_all_project_collections_metadata()
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.perform_tasks_after_project_creation()
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        cls.add_data_to_dropzone()
        start_and_wait_for_ingest(cls)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        print("End {}.teardown_class".format(cls.__name__))

    def test_collection_avu(self):
        rule_list_collections = '/rules/tests/run_test.sh -r list_collections -a "{}"'.format(self.project_path)
        ret_list_collections = subprocess.check_output(rule_list_collections, shell=True)
        list_collections = json.loads(ret_list_collections)
        assert list_collections[0]["id"] == self.collection_id

        rule_collection_detail = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(
            self.project_id, self.collection_id
        )
        ret_collection_detail = subprocess.check_output(rule_collection_detail, shell=True)
        collection_detail = json.loads(ret_collection_detail)
        assert collection_detail["creator"] == self.collection_creator
        assert collection_detail["collection"] == self.collection_id
        assert collection_detail["title"] == self.collection_title
        assert int(collection_detail["numFiles"]) == self.collection_number_files
        assert int(collection_detail["byteSize"]) == self.collection_total_size
        assert self.manager1 in collection_detail["managers"]["users"]
        assert self.manager2 in collection_detail["managers"]["users"]

    def test_collection_instance(self):
        tmp_instance_path = "/tmp/tmp_instance.json"
        iget = "iget -f {}/{}/instance.json {}".format(self.project_path, self.collection_id, tmp_instance_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_instance_path) as tmp_instance_file:
            tmp_instance = json.load(tmp_instance_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}instance.1".format(self.project_id, self.collection_id))

    def test_collection_schema(self):
        tmp_schema_path = "/tmp/tmp_schema.json"
        iget = "iget -f {}/{}/schema.json {}".format(self.project_path, self.collection_id, tmp_schema_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_instance = json.load(tmp_schema_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}schema.1".format(self.project_id, self.collection_id))

    def test_collection_acl(self):
        """
        Check the project collection acl; assume that all members only have read access.
        """
        acl = "ils -A {}/{}".format(self.project_path, self.collection_id)
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "own" not in ret
        assert "{}#nlmumc:read_object".format(self.manager1) in ret
        assert "{}#nlmumc:read_object".format(self.manager2) in ret

    def test_project_acl(self):
        acl = "ils -A {}".format(self.project_path)
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "{}#nlmumc:own".format(self.manager1) in ret
        assert "{}#nlmumc:own".format(self.manager2) in ret

    def test_collection_pid(self):
        import requests

        # TODO How relevant is this test?
        # Note: This test can start to fail when reaching high project_id number (e.g: P000000150).
        # A potential first time PID registration can cause a synchronization timing issue between the EpicPID
        # registration service and the global Handle URL resolving service.
        rule = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(
            self.project_id, self.collection_id
        )
        ret = subprocess.check_output(rule, shell=True)
        collection_detail = json.loads(ret)

        url = "https://hdl.handle.net/{}".format(collection_detail["PID"])
        response = requests.get(url, allow_redirects=False)
        assert response.status_code == 302

    def test_collection_data_resource(self):
        """
        Check the data object that are in the project collection use the correct project destination resource.
        """
        query = 'iquest --no-page "%s" "SELECT DATA_RESC_HIER WHERE COLL_PARENT_NAME = \'{}/{}\'"'.format(
            self.project_path, self.collection_id
        )
        ret = subprocess.check_output(query, shell=True, encoding="UTF-8")
        resources = ret.splitlines()
        if "repl" in self.destination_resource:
            assert len(resources) == 2
            assert self.destination_resource in resources[0]
            assert self.destination_resource in resources[1]
        elif "pass" in self.destination_resource:
            assert len(resources) == 1
            assert self.destination_resource in resources[0]           

    def test_collection_data_replicas(self):
        """
        Check that data objects (instance.json & schema.json) at the root of project collection are correctly replicated
        """
        query = 'iquest --no-page "%s" "SELECT count(DATA_RESC_NAME) WHERE COLL_PARENT_NAME = \'{}/{}\'"'.format(
            self.project_path, self.collection_id
        )
        ret = subprocess.check_output(query, shell=True)
        if "repl" in self.destination_resource:
            assert int(ret) == 4
        elif "pass" in self.destination_resource:
            assert int(ret) == 2

    def test_elastic_index_update(self):
        instance = get_project_collection_instance_in_elastic(self.project_id)
        # The collection title in the instance doesn't match the collection title AVU
        # because of the way, we ingest the instance.json in the test-cases
        # collection_title = instance["3_Title"]["title"]["@value"]
        # print(collection_title)
        # assert collection_title == self.collection_title

        project_title = instance["project_title"]
        assert project_title == self.project_title

        project_id = instance["project_id"]
        assert project_id == self.project_id

        collection_id = instance["collection_id"]
        assert collection_id == self.collection_id

    def test_dropzone_pre_ingest_avu(self):
        """This test asserts that the dropzone AVUs set with the rule 'save_dropzone_pre_ingest_info' are correct."""

        query = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{}' and META_COLL_ATTR_NAME = '{}' \""
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)

        run_iquest = query.format(dropzone_path, "totalSize")
        total_size = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()

        run_iquest = query.format(dropzone_path, "numFiles")
        num_files = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()

        assert total_size == self.dropzone_total_size
        assert num_files == self.dropzone_num_files
