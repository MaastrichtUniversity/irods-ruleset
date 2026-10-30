from test_cases.base_ingest_test_case import BaseTestCaseIngest
from test_cases.utils import add_metadata_files_to_direct_dropzone, add_data_to_direct_dropzone
import subprocess

from dhpythonirodsutils import formatters


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

    def test_ingest_quote_and_combination(self, tmp_path):
        """Ingest a path containing both a single quote and ' and ' without changing its contents."""
        collection_path = formatters.format_project_collection_path(self.project_id, self.collection_id)
        destination = tmp_path / "ingested.file"
        subprocess.check_call(["iget", "-K", f"{collection_path}/50K' and data.file", str(destination)])
        assert destination.read_bytes() == b"0" * 51200


class BaseTestCaseMountedIngestAsContributor(BaseTestCaseDirectIngest):
    @classmethod
    def perform_tasks_after_project_creation(cls):
        cls.depositor = "dlinssen"
        cls.collection_creator = "d.linssen@maastrichtuniversity.nl"
        rule_set_acl = f'/rules/tests/run_test.sh -r set_acl -a "default,write,{cls.depositor},{cls.project_path}"'
        subprocess.check_call(rule_set_acl, shell=True)

class TestDirectIngestUM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"


class TestDirectIngestAZM(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM02"


class TestDirectIngestS3(BaseTestCaseDirectIngest):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestDirectIngestUMAsContributor(BaseTestCaseMountedIngestAsContributor):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"


class TestDirectIngestAZMAsContributor(BaseTestCaseMountedIngestAsContributor):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM02"


class TestDirectIngestS3AsContributor(BaseTestCaseMountedIngestAsContributor):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"
