from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_direct_dropzone


class TestDirectIngest(BaseTestCaseIngest):
    dropzone_type = "direct"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)
