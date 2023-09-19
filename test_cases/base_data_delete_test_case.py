import json
import os
import subprocess

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionState, DataDeletionAttribute

from test_cases.utils import (
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    add_metadata_files_to_direct_dropzone,
    remove_project,
    run_index_all_project_collections_metadata,
    add_data_to_direct_dropzone,
    remove_dropzone,
)


class BaseDataDelete:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

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

    deletion_reason = "funding_expired"
    deletion_description = "description24"
    deletion_state = DataDeletionState.PENDING.value

    files_per_protocol = {
        "0bytes.file": 0,
        "50K.file": 51200,
        "15M.file": 15728640,
        "45M.file": 47185920,
        "256M.file": 262144001,
    }

    revoke_rule = ""

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.project_collection_path = formatters.format_project_collection_path(cls.project_id, cls.collection_id)
        cls.token = create_dropzone(cls)
        add_metadata_files_to_direct_dropzone(cls.token)
        add_data_to_direct_dropzone(cls)
        start_and_wait_for_ingest(cls)

        # Running the index all rule: delete the current elasticsearch index that could be in a bad state
        run_index_all_project_collections_metadata()

        # The rule revoke_project_collection_user_access checks if a dropzone is linked to the input project collection,
        # which is the case during the test case execution.
        # To by-pass this check, the call for the dropzone deletion is done immediately, instead of waiting
        # for *irodsIngestRemoveDelay* (5 minutes).
        remove_dropzone(cls.token, cls.dropzone_type)

        cls.revoke_rule = '/rules/tests/run_test.sh -r revoke_project_user_access -a "{},{},{}" '.format(
            cls.project_path, cls.deletion_reason, cls.deletion_description
        )
        cls.run_after_ingest()
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        print("End {}.teardown_class".format(cls.__name__))

    @classmethod
    def run_after_ingest(cls):
        pass


class BaseDataDeleteTestCase(BaseDataDelete):
    def test_revoke_project_collection_user_acl(self):
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc".format(self.manager1) not in ret_acl
        assert "{}#nlmumc".format(self.manager2) not in ret_acl

        assert "{}#nlmumc:read object".format("rods") in ret_acl
        assert "{}#nlmumc:read object".format("service-disqover") in ret_acl
        assert "{}#nlmumc:read object".format("service-pid") in ret_acl

        # Check the ACL of a file in a sub-folder
        version_schema = formatters.format_schema_versioned_collection_path(self.project_id, self.collection_id, "1")
        acl_version_schema = "ils -A {}".format(version_schema)
        ret_acl_version_schema = subprocess.check_output(acl_version_schema, shell=True)
        assert "{}#nlmumc".format(self.manager1) not in ret_acl_version_schema
        assert "{}#nlmumc".format(self.manager2) not in ret_acl_version_schema

        assert "{}#nlmumc:read object".format("rods") in ret_acl_version_schema
        assert "{}#nlmumc:read object".format("service-disqover") in ret_acl_version_schema
        assert "{}#nlmumc:read object".format("service-pid") in ret_acl_version_schema

    def test_set_collection_deletion_metadata(self):
        metadata = "imeta ls -C {} {}".format(self.project_collection_path, DataDeletionAttribute.REASON.value)
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "value: {}".format(self.deletion_reason) in ret_metadata

        metadata = "imeta ls -C {} {}".format(self.project_collection_path, DataDeletionAttribute.DESCRIPTION.value)
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "value: {}".format(self.deletion_description) in ret_metadata

        metadata = "imeta ls -C {} {}".format(self.project_collection_path, DataDeletionAttribute.STATE.value)
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "value: {}".format(self.deletion_state) in ret_metadata

    def test_project_collection_metadata_removal_from_index(self):
        result = self.get_metadata_in_elastic_search()
        assert result["hits"]["total"]["value"] == 0

    def test_re_index_all_project_collections_metadata(self):
        run_index_all_project_collections_metadata()
        result = self.get_metadata_in_elastic_search()
        # run_index_all_project_collections_metadata delete the existing index.
        # But the index is not re-created if there are no project collection metadata available.
        # Might give different result if some other project collection have been ingested before the test cases
        print(result)
        if "status" in result:
            assert result["status"] == 404
        else:
            assert result["hits"]["total"]["value"] == 0

    def get_metadata_in_elastic_search(self):
        elastic_host = os.environ.get("ENV_ELASTIC_HOST")
        elastic_port = os.environ.get("ENV_ELASTIC_PORT")
        elastic_password = os.environ.get("ENV_ELASTIC_PASSWORD")
        search_url = "{}:{}/collection_metadata/_doc/_search".format(elastic_host, elastic_port)
        query = "curl -u elastic:{} {}?q={}".format(elastic_password, search_url, self.project_id)

        ret = subprocess.check_output(query, shell=True)
        return json.loads(ret)
