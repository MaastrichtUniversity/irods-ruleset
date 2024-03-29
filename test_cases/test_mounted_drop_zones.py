from test_cases.base_dropzone_test_case import BaseTestCaseDropZones
from test_cases.utils import add_metadata_files_to_mounted_dropzone


class TestMountedDropZonesUM(BaseTestCaseDropZones):
    dropzone_type = "mounted"

    ingest_resource = "ires-hnas-umResource"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)


class TestMountedDropZonesAZM(BaseTestCaseDropZones):
    dropzone_type = "mounted"

    ingest_resource = "ires-hnas-azmResource"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)
