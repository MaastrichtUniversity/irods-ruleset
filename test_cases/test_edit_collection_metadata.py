import json
import subprocess
from os import path

from dhpythonirodsutils import formatters

from test_cases.base_customizable_metadata_test_case import BaseTestCaseCustomizableMetadata
from test_cases.utils import (
    add_metadata_files_to_direct_dropzone,
    get_instance,
    get_project_collection_instance_in_elastic,
    TMP_INSTANCE_PATH,
)


class BaseEditCollectionMetadata(BaseTestCaseCustomizableMetadata):
    dropzone_type = "direct"

    new_collection_title = "Test edit title"
    num_files = 6
    byte_size = 816883

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def edit_metadata_instance(cls):
        if not path.exists(TMP_INSTANCE_PATH):
            get_instance()

        tmp_edit_instance_path = "/tmp/edit_metadata_instance.json"
        with open(TMP_INSTANCE_PATH, "r") as json_file, open(tmp_edit_instance_path, "w") as edit_json_file:
            instance = json.load(json_file)
            instance["3_Title"]["title"]["@value"] = cls.new_collection_title
            edit_json_file.write(json.dumps(instance, sort_keys=True, indent=4))

        instance_collection_path = formatters.format_instance_collection_path(cls.project_id, cls.collection_id)
        iput_instance = "iput -f {} {}".format(tmp_edit_instance_path, instance_collection_path)
        subprocess.check_call(iput_instance, shell=True)

    def test_collection_instance_version(self):
        tmp_instance_path = "/tmp/tmp_instance.json"
        iget = "iget -f {}/{}/instance.json {}".format(self.project_path, self.collection_id, tmp_instance_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_instance_path) as tmp_instance_file:
            tmp_instance = json.load(tmp_instance_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}instance.2".format(self.project_id, self.collection_id))

            collection_title = tmp_instance["3_Title"]["title"]["@value"]
            assert collection_title == self.new_collection_title

    def test_elastic_index_update(self):
        instance = get_project_collection_instance_in_elastic(self.project_id)
        collection_title = instance["3_Title"]["title"]["@value"]
        assert collection_title == self.new_collection_title

    def test_collection_schema_version(self):
        tmp_schema_path = "/tmp/tmp_schema.json"
        iget = "iget -f {}/{}/schema.json {}".format(self.project_path, self.collection_id, tmp_schema_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_instance = json.load(tmp_schema_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}schema.2".format(self.project_id, self.collection_id))


class TestEditCollectionMetadataUM(BaseEditCollectionMetadata):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"


class TestEditCollectionMetadataS3(BaseEditCollectionMetadata):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestEditCollectionMetadataAZM(BaseEditCollectionMetadata):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"
