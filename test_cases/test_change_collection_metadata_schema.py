import json
import subprocess
from os import path

from dhpythonirodsutils import formatters

from test_cases.base_customizable_metadata_test_case import BaseTestCaseCustomizableMetadata
from test_cases.utils import add_metadata_files_to_direct_dropzone, get_schema, TMP_SCHEMA_PATH


class BaseTestChangeCollectionMetadataSchema(BaseTestCaseCustomizableMetadata):
    dropzone_type = "direct"

    new_schema_name = "New DataHub General Schema"
    new_collection_title = "collection_title"
    num_files = 6
    byte_size = 816923

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def edit_metadata_schema(cls):
        if not path.exists(TMP_SCHEMA_PATH):
            get_schema()

        tmp_edit_schema_path = "/tmp/edit_metadata_schema.json"
        with open(TMP_SCHEMA_PATH, "r") as json_file, open(tmp_edit_schema_path, "w") as edit_json_file:
            schema_json = json.load(json_file)
            schema_json["schema:name"] = cls.new_schema_name
            edit_json_file.write(json.dumps(schema_json))

        schema_collection_path = formatters.format_schema_collection_path(cls.project_id, cls.collection_id)
        iput_instance = "iput -f {} {}".format(tmp_edit_schema_path, schema_collection_path)
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

    def test_collection_schema_version(self):
        tmp_schema_path = "/tmp/tmp_schema.json"
        iget = "iget -f {}/{}/schema.json {}".format(self.project_path, self.collection_id, tmp_schema_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_schema = json.load(tmp_schema_file)
            pid = tmp_schema["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}schema.2".format(self.project_id, self.collection_id))

            schema_name = tmp_schema["schema:name"]
            assert schema_name == self.new_schema_name


class TestChangeCollectionMetadataSchemaUM(BaseTestChangeCollectionMetadataSchema):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"


class TestChangeCollectionMetadataSchemaS3(BaseTestChangeCollectionMetadataSchema):
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUMCeph01"


class TestChangeCollectionMetadataSchemaAZM(BaseTestChangeCollectionMetadataSchema):
    ingest_resource = "ires-hnas-azmResource"
    destination_resource = "replRescAZM01"
