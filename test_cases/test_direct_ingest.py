import pytest

from test_cases.base_ingest_test_case import (
    BaseIngestScenario,
    BaseTestCaseIngest,
    INGEST_SCENARIOS,
    # Module-level fixtures share one lifecycle across the three test classes.
    ingest_scenario,
    edited_collection,
    schema_changed_collection,
)
from test_cases.base_customizable_metadata_test_case import (
    BaseEditCollectionMetadata,
    BaseTestChangeCollectionMetadataSchema,
)
from test_cases.utils import add_metadata_files_to_direct_dropzone, add_data_to_direct_dropzone
import subprocess

from dhpythonirodsutils import formatters


pytestmark = [
    pytest.mark.parallel,
    pytest.mark.parametrize("ingest_scenario", INGEST_SCENARIOS, indirect=True, scope="module"),
    pytest.mark.xdist_group("direct"),
]


class IngestScenario(BaseIngestScenario):
    dropzone_type = "direct"
    dropzone_total_size = "63169378"
    dropzone_num_files = "6"

    def add_metadata_files_to_dropzone(self, token):
        add_metadata_files_to_direct_dropzone(token)

    def add_data_to_dropzone(self):
        add_data_to_direct_dropzone(self)


class TestDirectIngest(BaseTestCaseIngest):
    def test_ingest_quote_and_combination(self, ingest_scenario, tmp_path):
        """Ingest a path containing both a single quote and ' and ' without changing its contents."""
        collection_path = formatters.format_project_collection_path(ingest_scenario.project_id, ingest_scenario.collection_id)
        destination = tmp_path / "ingested.file"
        subprocess.check_call(["iget", "-K", f"{collection_path}/50K' and data.file", str(destination)])
        assert destination.read_bytes() == b"0" * 51200


class TestEditCollectionMetadata(BaseEditCollectionMetadata):
    pass


class TestChangeCollectionMetadataSchema(BaseTestChangeCollectionMetadataSchema):
    pass
