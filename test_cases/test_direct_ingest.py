from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_direct_dropzone


class BaseTestCaseDirectIngest(BaseTestCaseIngest):
    dropzone_type = "direct"
    dropzone_total_size = "203618"
    dropzone_num_files = "2"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)


class TestDirectIngestUM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestDirectIngestAZM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"


class TestDirectIngestS3(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"
