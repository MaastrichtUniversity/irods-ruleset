import subprocess

from dhpythonirodsutils.enums import DataDeletionState

from test_cases.base_data_delete_test_case import BaseDataDeleteTestCase
from test_cases.utils import (
    wait_for_revoke_project_collection_user_acl,
)


class TestDeleteProjectData(BaseDataDeleteTestCase):
    deletion_state = DataDeletionState.DELETED.value
    number_metadata_files = 4

    @classmethod
    def run_after_ingest(cls):
        subprocess.check_call(cls.revoke_rule, shell=True)
        wait_for_revoke_project_collection_user_acl()

        delete_rule = '/rules/tests/run_test.sh -r delete_project_data -a "{},true" '.format(cls.project_path)
        subprocess.check_call(delete_rule, shell=True)

    def test_number_files_after_deletion(self):
        metadata = "imeta ls -C {} {}".format(self.project_collection_path, "numFiles")
        ret_metadata = subprocess.check_output(metadata, shell=True)
        assert "value: {}".format(self.number_metadata_files) in ret_metadata
