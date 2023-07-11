from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_mounted_dropzone
import subprocess


class BaseTestCaseMountedIngest(BaseTestCaseIngest):
    dropzone_type = "mounted"
    # For mounted ingest tests, there are no files in the mounted 'network' dropzone folder /mnt/ingest/zones/*token.
    # This is why dropzone_total_size = 0
    # The metadata files are stored in the logical dropzone folder in the resource 'stagingResc01'
    # e.g schema.json /nlmumc/ingest/zones/*token/schema.json -> /mnt/stagingResc01/ingest/zones/*token/schema.json
    dropzone_total_size = "62965760"
    dropzone_num_files = "6"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_mounted_dropzone(token)

    @classmethod
    def add_data_to_dropzone(cls):
        run_iquest = 'iquest "%s" "SELECT RESC_LOC WHERE RESC_NAME = \'{}\'"'.format(cls.ingest_resource)
        remote_resource = subprocess.check_output(run_iquest, shell=True).strip()
        rule = "irule -r irods_rule_engine_plugin-python-instance -F /rules/utils/createFakeFiles.r '*dropzonePath=\"/mnt/ingest/zones/{}\"' '*remoteResource=\"{}\"'".format(
            cls.token, remote_resource
        )
        subprocess.check_call(rule, shell=True)


class TestMountedIngestUM(BaseTestCaseMountedIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestMountedIngestAZM(BaseTestCaseMountedIngest):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"


class TestMountedIngestS3(BaseTestCaseMountedIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"
