import subprocess

from dhpythonirodsutils import formatters

from test_cases.base_tape_archive import BaseTestTapeArchive
from test_cases.utils import (
    add_metadata_files_to_direct_dropzone,
    add_metadata_files_to_mounted_dropzone,
)


class BaseTestTapeArchiveDirect(BaseTestTapeArchive):
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
            large_file.write(b"0" * num_chars)
        iput = "iput -R stagingResc01 {} {}".format(large_file_path, logical_path)
        subprocess.check_call(iput, shell=True)


class BaseTestTapeArchiveMounted(BaseTestTapeArchive):
    dropzone_type = "mounted"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)

    @classmethod
    def add_archive_data_to_dropzone(cls):
        cls.add_archive_data_to_mounted_dropzone()

    @classmethod
    def give_user_ingest_access(cls, user):
        run_ichmod = "ichmod -M write {} /nlmumc/ingest/zones".format(user)
        subprocess.check_call(run_ichmod, shell=True)

    @classmethod
    def add_archive_data_to_mounted_dropzone(cls):
        run_iquest = 'iquest "%s" "SELECT RESC_LOC WHERE RESC_NAME = \'{}\'"'.format(cls.ingest_resource)
        remote_resource = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()
        rule = "irule -r irods_rule_engine_plugin-python-instance -F /rules/utils/createFakeTapeFile.r '*dropzonePath=\"/mnt/ingest/zones/{}\"' '*remoteResource=\"{}\"'".format(
            cls.token, remote_resource
        )
        subprocess.check_call(rule, shell=True)


class TestTapeArchiveDirectS3(BaseTestTapeArchiveDirect):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestTapeArchiveMountedS3(BaseTestTapeArchiveMounted):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestTapeArchiveDirectUM(BaseTestTapeArchiveDirect):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestTapeArchiveMountedUM(BaseTestTapeArchiveMounted):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestTapeArchiveDirectAZM(BaseTestTapeArchiveDirect):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"


class TestTapeArchiveMountedAZM(BaseTestTapeArchiveMounted):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"
