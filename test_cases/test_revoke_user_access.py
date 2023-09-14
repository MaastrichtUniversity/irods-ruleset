import json
import subprocess

import pytest
from dhpythonirodsutils.enums import ProcessAttribute

from test_cases.base_data_delete_test_case import BaseDataDelete, BaseDataDeleteTestCase
from test_cases.utils import (
    wait_for_revoke_project_collection_user_acl,
    get_project_collection_instance_in_elastic,
    wait_for_change_project_permissions_to_finish,
)


class TestRevokeProjectCollectionUserAccess(BaseDataDeleteTestCase):
    @classmethod
    def run_after_ingest(cls):
        instance = get_project_collection_instance_in_elastic(cls.project_id)
        assert instance["project_title"] == cls.project_title
        assert instance["project_id"] == cls.project_id
        assert instance["collection_id"] == cls.collection_id

        subprocess.check_call(cls.revoke_rule, shell=True)
        wait_for_revoke_project_collection_user_acl()

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


class TestRevokeProjectCollectionUserAccessWithActiveProcess(BaseDataDelete):
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
