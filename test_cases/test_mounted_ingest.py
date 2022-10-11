from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_mounted_dropzone


class TestMountedIngestUM(BaseTestCaseIngest):
    dropzone_type = "mounted"

    ingest_resource = "iresResource"
    destination_resource = "replRescUM01"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)


class TestMountedIngestAZM(BaseTestCaseIngest):
    dropzone_type = "mounted"

    ingest_resource = "ires-centosResource"
    destination_resource = "replRescAZM01"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)


class TestMountedIngestS3(BaseTestCaseIngest):
    dropzone_type = "mounted"

    ingest_resource = "iresResource"
    destination_resource = "replRescUMCeph01"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)
