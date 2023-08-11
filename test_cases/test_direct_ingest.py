import subprocess

from dhpythonirodsutils import formatters

from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_direct_dropzone


class BaseTestCaseDirectIngest(BaseTestCaseIngest):
    dropzone_type = "direct"
    dropzone_total_size = "63169378"
    dropzone_num_files = "6"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def add_data_to_dropzone(cls):
        for filename, size in cls.files_per_protocol.items():
            file_path = "/tmp/{}".format(filename)
            dropzone_path = formatters.format_dropzone_path(cls.token, cls.dropzone_type)
            logical_path = "{}/{}".format(dropzone_path, filename)

            with open(file_path, "wb") as file_buffer:
                file_buffer.write(b"0" * size)
            iput = "iput -R stagingResc01 {} {}".format(file_path, logical_path)
            subprocess.check_call(iput, shell=True)


class TestDirectIngestUM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestDirectIngestAZM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"


class TestDirectIngestS3(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"
