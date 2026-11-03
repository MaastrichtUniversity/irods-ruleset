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
from test_cases.utils import add_metadata_files_to_mounted_dropzone
import subprocess


pytestmark = [
    pytest.mark.parallel,
    pytest.mark.parametrize("ingest_scenario", INGEST_SCENARIOS, indirect=True, scope="module"),
    pytest.mark.xdist_group("mounted"),
]


class IngestScenario(BaseIngestScenario):
    dropzone_type = "mounted"
    # For mounted ingest tests, there are no files in the mounted 'network' dropzone folder /mnt/ingest/zones/*token.
    # This is why dropzone_total_size = 0
    # The metadata files are stored in the logical dropzone folder in the resource 'stagingResc01'
    # e.g schema.json /nlmumc/ingest/zones/*token/schema.json -> /mnt/stagingResc01/ingest/zones/*token/schema.json
    dropzone_total_size = "62965760"
    dropzone_num_files = "6"

    def add_metadata_files_to_dropzone(self, token):
        add_metadata_files_to_mounted_dropzone(token)

    def add_data_to_dropzone(self):
        run_iquest = f'iquest "%s" "SELECT RESC_LOC WHERE RESC_NAME = \'{self.ingest_resource}\'"'
        remote_resource = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()
        rule = f"irule -r irods_rule_engine_plugin-python-instance -F /rules/utils/createFakeFiles.r '*dropzonePath=\"/mnt/ingest/zones/{self.token}\"' '*remoteResource=\"{remote_resource}\"'"
        subprocess.check_call(rule, shell=True)


class TestMountedIngest(BaseTestCaseIngest):
    pass


class TestEditCollectionMetadata(BaseEditCollectionMetadata):
    pass


class TestChangeCollectionMetadataSchema(BaseTestChangeCollectionMetadataSchema):
    pass
