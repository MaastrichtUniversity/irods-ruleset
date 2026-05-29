import subprocess
import json
import pytest

from test_cases.utils import (
    TMP_INSTANCE_PATH,
    start_and_wait_for_ingest,
    remove_project,
    remove_dropzone,
    create_project,
    create_dropzone,
    add_metadata_files_to_direct_dropzone,
)

"""
Python rules:
- get_resource_size_for_all_collections: valid, used by DevOps to calculate how much data is in iRODS in total


Native rules:
- calcCollectionFilesAcrossResc: used in setCollectionSize
- calcCollectionSizeAcrossResc: used in setCollectionSize
- getDestinationResources: used in MDR/RW (createProject)
- getIngestResources: used in MDR/RW (createProject)
- getResourceAVU: used in tapeUnarchive, prepareTapeUnarchive, prepareTapeArchive
- getResourcesInCollection: used in calcCollectionSizeAcrossResc and thus in setCollectionSize
"""


class TestResources:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = "direct"
    token = ""

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_id = "C000000001"
    collection_title = "collection_title"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def setup_class(cls):
        print(f"Start {cls.__name__}.setup_class")
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        start_and_wait_for_ingest(cls)
        subprocess.check_call(
            f"ichmod own -M rods /nlmumc/projects/{cls.project_id}/{cls.collection_id}", shell=True
        )
        print(f"End {cls.__name__}.setup_class")

    @classmethod
    def teardown_class(cls):
        print(f"Start {cls.__name__}.teardown_class")
        remove_project(cls.project_path)
        remove_dropzone(cls.token, cls.dropzone_type)
        print(f"End {cls.__name__}.teardown_class")

    def test_calc_collection_files_across_resc(self):
        resc_found = False
        rule = f"irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/calcCollectionFilesAcrossResc.r \"*collection='/nlmumc/projects/{self.project_id}/{self.collection_id}'\""
        rule_output = subprocess.check_output(rule, shell=True)
        rule_parsed = json.loads(rule_output)
        assert rule_parsed["numFilesPerResc"][0]["numFiles"] == "4"
        assert rule_parsed["numFilesPerResc"][0]["resourceID"].isnumeric()
        subprocess.check_call(
            f"iput -R replRescAZM02 {TMP_INSTANCE_PATH} /nlmumc/projects/{self.project_id}/{self.collection_id}/temp_file",
            shell=True,
        )
        rule_output = subprocess.check_output(rule, shell=True)
        run_iquest = 'iquest "%s" "SELECT RESC_ID WHERE RESC_NAME = \'replRescAZM02\' "'
        iquest_result = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()
        rule_parsed = json.loads(rule_output)
        assert len(rule_parsed) > 0
        for resc in rule_parsed["numFilesPerResc"]:
            if resc["resourceID"] == iquest_result:
                assert resc["numFiles"] == "1"
                resc_found = True
        assert resc_found == True
        subprocess.check_call(
            f"irm -f /nlmumc/projects/{self.project_id}/{self.collection_id}/temp_file", shell=True
        )

    def test_calc_collection_size_across_resc(self):
        resc_found = False
        rule = f"irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/calcCollectionSizeAcrossResc.r \"*collection='/nlmumc/projects/{self.project_id}/{self.collection_id}'\" \"*unit='KiB'\" \"*round='ceiling'\""
        rule_output = subprocess.check_output(rule, shell=True, encoding="UTF-8")
        rule_parsed = json.loads(rule_output)
        assert rule_parsed["sizePerResc"][0]["dataSize"] == "532"
        assert rule_parsed["sizePerResc"][0]["resourceID"].isnumeric()
        subprocess.check_call(
            f"iput -R replRescAZM02 {TMP_INSTANCE_PATH} /nlmumc/projects/{self.project_id}/{self.collection_id}/temp_file",
            shell=True,
        )
        rule_output = subprocess.check_output(rule, shell=True)
        run_iquest = 'iquest "%s" "SELECT RESC_ID WHERE RESC_NAME = \'replRescAZM02\' "'
        iquest_result = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()
        rule_parsed = json.loads(rule_output)
        assert len(rule_parsed) > 0
        for resc in rule_parsed["sizePerResc"]:
            if resc["resourceID"] == iquest_result:
                assert resc["dataSize"] == "13"
                resc_found = True
        assert resc_found == True
        subprocess.check_call(
            f"irm -f /nlmumc/projects/{self.project_id}/{self.collection_id}/temp_file", shell=True
        )

    def test_get_destination_resources(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getDestinationResources.r"
        rule_output = subprocess.check_output(rule, shell=True)
        rule_parsed = json.loads(rule_output)
        assert len(rule_parsed) > 0
        for item in rule_parsed:
            assert item["name"] in ["replRescAZM02", "passRescUM01", "replRescUMCeph01"]

    def test_get_ingest_resources(self):
        rule = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getIngestResources.r"
        rule_output = subprocess.check_output(rule, shell=True)
        rule_parsed = json.loads(rule_output)
        assert len(rule_parsed) > 0
        for item in rule_parsed:
            assert item["name"] in [
                "ires-hnas-azmResource",
                "ires-hnas-umResource",
                "ires-ceph-acResource",
                "ires-ceph-glResource",
            ]

    def test_get_resource_avu(self):
        base_rule = (
            "irule -r irods_rule_engine_plugin-irods_rule_language-instance "
            "-F /rules/native_irods_ruleset/misc/getResourceAVU.r "
            "\"*resourceName='arcRescSURF01'\""
        )
        rule_output = subprocess.check_output(
            f"{base_rule} \"*attribute='archiveDestResc'\" \"*overrideValue=''\" \"*fatal='true'\"",
            shell=True,
            encoding="UTF-8",
        ).strip()
        assert rule_output == "true"
        rule_output = subprocess.check_output(
            f"{base_rule} \"*attribute='non_existing'\" \"*overrideValue=''\" \"*fatal='false'\"",
            shell=True,
            encoding="UTF-8",
        ).strip()
        assert rule_output != "override"
        rule_output = subprocess.check_output(
            f"{base_rule} \"*attribute='non_existing'\" \"*overrideValue='override'\" \"*fatal='false'\"",
            shell=True,
            encoding="UTF-8",
        ).strip()
        assert rule_output == "override"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(
                f"{base_rule} \"*attribute='non_existing'\" \"*overrideValue=''\" \"*fatal='true'\"",
                shell=True,
            )
