from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_mounted_dropzone


class TestMountedIngest(BaseTestCaseIngest):
    dropzone_type = "mounted"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)
