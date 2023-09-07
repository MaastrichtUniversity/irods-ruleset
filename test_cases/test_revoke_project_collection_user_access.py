import json
import os
import subprocess

import pytest
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionState, DataDeletionAttribute, ProcessAttribute

from test_cases.utils import (
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    add_metadata_files_to_direct_dropzone,
    remove_project,
    run_index_all_project_collections_metadata,
    wait_for_revoke_project_collection_user_acl,
    get_project_collection_instance_in_elastic,
    wait_for_change_project_permissions_to_finish,
)


class BaseRevokeProjectCollectionUserAccess:
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

    deletion_reason = "reason42"
    deletion_description = "description24"
    deletion_state = DataDeletionState.PENDING.value

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
        start_and_wait_for_ingest(cls)

        # Running the index all rule: delete the current elasticsearch index that could be in a bad state
        run_index_all_project_collections_metadata()

        cls.revoke_rule = '/rules/tests/run_test.sh -r revoke_project_collection_user_access -a "{},{},{}" '.format(
            cls.project_collection_path, cls.deletion_reason, cls.deletion_description
        )
        cls.revoke_project_collection_user_access()
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        print("End {}.teardown_class".format(cls.__name__))

    @classmethod
    def revoke_project_collection_user_access(cls):
        pass


class TestRevokeRevokeProjectUserAccess(BaseRevokeProjectCollectionUserAccess):
    @classmethod
    def revoke_project_collection_user_access(cls):
        instance = get_project_collection_instance_in_elastic(cls.project_id)
        assert instance["project_title"] == cls.project_title
        assert instance["project_id"] == cls.project_id
        assert instance["collection_id"] == cls.collection_id

        subprocess.check_call(cls.revoke_rule, shell=True)
        wait_for_revoke_project_collection_user_acl()

    def test_revoke_project_collection_user_acl(self):
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc".format(self.manager1) not in ret_acl
        assert "{}#nlmumc".format(self.manager2) not in ret_acl

        assert "{}#nlmumc".format("rods") in ret_acl
        assert "{}#nlmumc".format("service-disqover") in ret_acl
        assert "{}#nlmumc".format("service-pid") in ret_acl

        # Check the ACL of a file in a sub-folder
        version_schema = formatters.format_schema_versioned_collection_path(self.project_id, self.collection_id, "1")
        acl_version_schema = "ils -A {}".format(version_schema)
        ret_acl_version_schema = subprocess.check_output(acl_version_schema, shell=True)
        assert "{}#nlmumc".format(self.manager1) not in ret_acl_version_schema
        assert "{}#nlmumc".format(self.manager2) not in ret_acl_version_schema

        assert "{}#nlmumc".format("rods") in ret_acl_version_schema
        assert "{}#nlmumc".format("service-disqover") in ret_acl_version_schema
        assert "{}#nlmumc".format("service-pid") in ret_acl_version_schema

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

    def test_delete_project_collection_metadata_from_index(self):
        result = self.get_metadata_in_elastic_search()
        assert result["hits"]["total"]["value"] == 0

    def test_change_project_permissions(self):
        user_to_check = "auser"
        change_project_permissions_rule = (
            "irule -r irods_rule_engine_plugin-irods_rule_language-instance"
            " \"changeProjectPermissions('{}','{}:{}')\" null  ruleExecOut"
        )
        rule_project_details = '/rules/tests/run_test.sh -r get_project_details -a "{},false" -u {}'.format(
            self.project_path, self.depositor
        )

        # Add write rights for user_to_check to the project
        subprocess.check_output(
            change_project_permissions_rule.format(self.project_id, user_to_check, "write"), shell=True
        )

        # Check that user_to_check is in project contributors
        ret = subprocess.check_output(rule_project_details, shell=True)
        project = json.loads(ret)
        assert user_to_check not in project["managers"]["users"]
        assert user_to_check in project["contributors"]["users"]
        assert user_to_check not in project["viewers"]["users"]

        wait_for_change_project_permissions_to_finish()

        # Check that user_to_check is still not part of the project collection ACL.
        # changeProjectPermissions mustn't give access (back) to user to project collection that are deleted
        # or pending-for-deletion.
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:read".format(user_to_check) not in ret_acl

    def test_index_all_project_collections_metadata(self):
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


class TestRevokeRevokeProjectUserAccessWithActiveProcess(BaseRevokeProjectCollectionUserAccess):
    def test_revoke_project_collection_user_access(self):
        mod_acl = "ichmod -M own rods {}".format(self.project_collection_path)
        subprocess.check_call(mod_acl, shell=True)

        # Archive
        set_enable_archive = "imeta set -C {} {} stuff".format(
            self.project_collection_path, ProcessAttribute.ARCHIVE.value
        )
        subprocess.check_call(set_enable_archive, shell=True)

        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(self.revoke_rule, shell=True)

        # Un-Archive
        set_enable_archive = "imeta set -C {} {} stuff".format(
            self.project_collection_path, ProcessAttribute.UNARCHIVE.value
        )
        subprocess.check_call(set_enable_archive, shell=True)

        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(self.revoke_rule, shell=True)

        # Export
        set_enable_archive = "imeta set -C {} {} dataverse:stuff".format(
            self.project_collection_path, ProcessAttribute.EXPORTER.value
        )
        subprocess.check_call(set_enable_archive, shell=True)

        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(self.revoke_rule, shell=True)
