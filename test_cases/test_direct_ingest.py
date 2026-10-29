import pytest

from test_cases.base_ingest_test_case import BaseTestCaseIngest, INGEST_SCENARIOS
from test_cases.utils import add_metadata_files_to_direct_dropzone, add_data_to_direct_dropzone
import subprocess

from dhpythonirodsutils import formatters


pytestmark = pytest.mark.parallel


@pytest.mark.parametrize("ingest_scenario", INGEST_SCENARIOS, indirect=True, scope="class")
@pytest.mark.xdist_group("direct")
class TestDirectIngest(BaseTestCaseIngest):
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
