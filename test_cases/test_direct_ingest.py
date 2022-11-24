from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_direct_dropzone


class TestDirectIngestUM(BaseTestCaseIngest):
    dropzone_type = "direct"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)


class TestDirectIngestAZM(BaseTestCaseIngest):
    dropzone_type = "direct"

    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)


class TestDirectIngestS3(BaseTestCaseIngest):
    dropzone_type = "direct"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)
