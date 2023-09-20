import subprocess

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionAttribute

from test_cases.base_data_delete_test_case import BaseDataDelete
from test_cases.utils import (
    wait_for_revoke_project_collection_user_acl,
    get_project_collection_instance_in_elastic,
)


class TestRestoreProjectUserAccess(BaseDataDelete):
    @classmethod
    def run_after_ingest(cls):
        subprocess.check_call(cls.revoke_rule, shell=True)
        wait_for_revoke_project_collection_user_acl()

        # First, restore the project
        restore_rule = '/rules/tests/run_test.sh -r restore_project_user_access -a "{}" '.format(cls.project_path)
        subprocess.check_call(restore_rule, shell=True)
        # Then the project collection
        restore_rule = '/rules/tests/run_test.sh -r restore_project_collection_user_access -a "{}" '.format(
            cls.project_collection_path
        )
        subprocess.check_call(restore_rule, shell=True)

    def test_restore_project_collection_user_acl(self):
        acl = "ils -A {}".format(self.project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:read object".format(self.manager1) in ret_acl
        assert "{}#nlmumc:read object".format(self.manager2) in ret_acl

        assert "{}#nlmumc:read object".format("rods") in ret_acl
        assert "{}#nlmumc:read object".format("service-disqover") in ret_acl
        assert "{}#nlmumc:read object".format("service-pid") in ret_acl

        # Check the ACL of a file in a sub-folder
        version_schema = formatters.format_schema_versioned_collection_path(self.project_id, self.collection_id, "1")
        acl_version_schema = "ils -A {}".format(version_schema)
        ret_acl_version_schema = subprocess.check_output(acl_version_schema, shell=True)
        assert "{}#nlmumc:read object".format(self.manager1) in ret_acl_version_schema
        assert "{}#nlmumc:read object".format(self.manager2) in ret_acl_version_schema

        assert "{}#nlmumc:read object".format("rods") in ret_acl_version_schema
        assert "{}#nlmumc:read object".format("service-disqover") in ret_acl_version_schema
        assert "{}#nlmumc:read object".format("service-pid") in ret_acl_version_schema

    def test_delete_collection_deletion_metadata(self):
        metadata = "imeta ls -C {} {}".format(self.project_collection_path, DataDeletionAttribute.REASON.value)
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "None" in ret_metadata

        metadata = "imeta ls -C {} {}".format(self.project_collection_path, DataDeletionAttribute.DESCRIPTION.value)
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "None" in ret_metadata

        metadata = "imeta ls -C {} {}".format(self.project_collection_path, DataDeletionAttribute.STATE.value)
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "None" in ret_metadata

    # test metadata are back in the index
    def test_elastic_index_update(self):
        instance = get_project_collection_instance_in_elastic(self.project_id)
        assert instance["project_title"] == self.project_title
        assert instance["project_id"] == self.project_id
        assert instance["collection_id"] == self.collection_id
