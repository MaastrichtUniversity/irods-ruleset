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
        restore_rule = f'/rules/tests/run_test.sh -r restore_project_user_access -a "{cls.project_path}" '
        subprocess.check_call(restore_rule, shell=True)
        # Then the project collection
        restore_rule = f'/rules/tests/run_test.sh -r restore_project_collection_user_access -a "{cls.project_collection_path}" '
        subprocess.check_call(restore_rule, shell=True)

    def test_restore_project_collection_user_acl(self):
        acl = f"ils -A {self.project_collection_path}"
        ret_acl = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.manager1}#nlmumc:read_object" in ret_acl
        assert f"{self.manager2}#nlmumc:read_object" in ret_acl

        assert "rods#nlmumc:read_object" in ret_acl
        assert "service-disqover#nlmumc:read_object" in ret_acl
        assert "service-pid#nlmumc:read_object" in ret_acl

        # Check the ACL of a file in a sub-folder
        version_schema = formatters.format_schema_versioned_collection_path(self.project_id, self.collection_id, "1")
        acl_version_schema = f"ils -A {version_schema}"
        ret_acl_version_schema = subprocess.check_output(acl_version_schema, shell=True, encoding="UTF-8")
        assert f"{self.manager1}#nlmumc:read_object" in ret_acl_version_schema
        assert f"{self.manager2}#nlmumc:read_object" in ret_acl_version_schema

        assert "rods#nlmumc:read_object" in ret_acl_version_schema
        assert "service-disqover#nlmumc:read_object" in ret_acl_version_schema
        assert "service-pid#nlmumc:read_object" in ret_acl_version_schema

    def test_delete_collection_deletion_metadata(self):
        metadata = f"imeta ls -C {self.project_collection_path} {DataDeletionAttribute.REASON.value}"
        ret_metadata = subprocess.check_output(metadata, shell=True, encoding="UTF-8")
        assert "None" in ret_metadata

        metadata = f"imeta ls -C {self.project_collection_path} {DataDeletionAttribute.DESCRIPTION.value}"
        ret_metadata = subprocess.check_output(metadata, shell=True, encoding="UTF-8")
        assert "None" in ret_metadata

        metadata = f"imeta ls -C {self.project_collection_path} {DataDeletionAttribute.STATE.value}"
        ret_metadata = subprocess.check_output(metadata, shell=True, encoding="UTF-8")
        assert "None" in ret_metadata

    # test metadata are back in the index
    def test_elastic_index_update(self):
        instance = get_project_collection_instance_in_elastic(self.project_id)
        assert instance["project_title"] == self.project_title
        assert instance["project_id"] == self.project_id
        assert instance["collection_id"] == self.collection_id
