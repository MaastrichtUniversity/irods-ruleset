from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_direct_dropzone, add_data_to_direct_dropzone
import subprocess


class BaseTestCaseDirectIngest(BaseTestCaseIngest):
    dropzone_type = "direct"
    dropzone_total_size = "63169378"
    dropzone_num_files = "6"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def add_data_to_dropzone(cls):
        add_data_to_direct_dropzone(cls)


class BaseTestCaseMountedIngestAsContributor(BaseTestCaseDirectIngest):
    @classmethod
    def perform_tasks_after_project_creation(cls):
        cls.depositor = "dlinssen"
        cls.collection_creator = "d.linssen@maastrichtuniversity.nl"
        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,write,{},{}"'.format(
            cls.depositor, cls.project_path
        )
        subprocess.check_call(rule_set_acl, shell=True)

class TestDirectIngestUM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestDirectIngestAZM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"


class TestDirectIngestS3(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestDirectIngestUMAsContributor(BaseTestCaseMountedIngestAsContributor):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestDirectIngestAZMAsContributor(BaseTestCaseMountedIngestAsContributor):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"


class TestDirectIngestS3AsContributor(BaseTestCaseMountedIngestAsContributor):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"
