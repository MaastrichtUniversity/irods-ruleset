import subprocess

from dhpythonirodsutils import formatters

from test_cases.base_tape_archive import BaseTestTapeArchive
from test_cases.utils import add_metadata_files_to_direct_dropzone


class BaseTestTapeArchiveDirect(BaseTestTapeArchive):
    depositor = "tape_direct_test_manager"
    manager1 = depositor
    manager2 = "tape_direct_test_data_steward"
    data_steward = manager2
    dropzone_type = "direct"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def add_archive_data_to_dropzone(cls):
        cls.add_archive_data_to_dropzone_direct()

    @classmethod
    def add_archive_data_to_dropzone_direct(cls):
        dropzone_path = formatters.format_dropzone_path(cls.token, cls.dropzone_type)
        large_file_path = "/tmp/large_file"
        logical_path = "{}/large_file".format(dropzone_path)

        with open(large_file_path, "wb") as large_file:
            num_chars = 262144001
            large_file.write("0" * num_chars)
        iput = "iput -R stagingResc01 {} {}".format(large_file_path, logical_path)
        subprocess.check_call(iput, shell=True)


class TestTapeArchiveS3Direct(BaseTestTapeArchiveDirect):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestTapeArchiveUMDirect(BaseTestTapeArchiveDirect):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestTapeArchiveAZMDirect(BaseTestTapeArchiveDirect):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"
