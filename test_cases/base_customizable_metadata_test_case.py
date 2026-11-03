import json
import subprocess
import tempfile
from os import path

import pytest
from dhpythonirodsutils import formatters

from test_cases.utils import (
    does_path_exist,
    get_instance,
    get_schema,
    get_project_collection_instance_in_elastic,
    set_collection_avu,
    TMP_INSTANCE_PATH,
    TMP_SCHEMA_PATH,
)


def edit_collection_metadata(collection, edit_metadata):
    """
    Replicate save_metadata_json_to_collection:
    * set_acl_for_metadata_snapshot

    * save_metadata_json_to_collection
            metadata_json.write_instance(instance, instance_irods_path)
                self.session.data_objects.put(instance_path, instance_irods_path)

            metadata_json.write_schema(schema_dict["schema_path"], schema_irods_path)
                self.session.data_objects.put(schema_path, schema_irods_path)

            self.set_collection_avu(collection_path, "schemaVersion", schema_dict["schema_version"])
            self.set_collection_avu(collection_path, "schemaName", schema_dict["schema_file_name"])
            self.set_collection_avu(collection_path, "title", schema_dict["title"])

            pid_request_status = self.create_collection_metadata_snapshot(project_id, collection_id)
    """
    open_acl = f'/rules/tests/run_test.sh -r set_acl_for_metadata_snapshot -a "{collection.project_id},{collection.collection_id},{collection.manager1},true,false"'
    subprocess.check_call(open_acl, shell=True)

    edit_metadata(collection)
    collection_path = formatters.format_project_collection_path(collection.project_id, collection.collection_id)
    set_collection_avu(collection_path, "schemaVersion", collection.schema_version)
    set_collection_avu(collection_path, "schemaName", collection.schema_name)
    set_collection_avu(collection_path, "title", collection.new_collection_title)

    metadata_snapshot = f'/rules/tests/run_test.sh -r create_collection_metadata_snapshot -a "{collection.project_id},{collection.collection_id}" -u {collection.manager1}'
    pid_request_status = subprocess.check_output(metadata_snapshot, shell=True, encoding="UTF-8").strip()
    assert pid_request_status == "true"

    # setCollectionSize is also called in set_acl_for_metadata_snapshot but in a delay queue
    # to avoid using a sleep call, we execute it synchronously to have the updated value during the test.
    set_size = f"irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/setCollectionSize.r \"*project='{collection.project_id}'\" \"*projectCollection='{collection.collection_id}'\" \"*openPC='false'\" \"*closePC='false'\""
    subprocess.check_call(set_size, shell=True)

    close_acl = f'/rules/tests/run_test.sh -r set_acl_for_metadata_snapshot -a "{collection.project_id},{collection.collection_id},{collection.manager1},false,true"'
    subprocess.check_call(close_acl, shell=True)


def edit_metadata_instance(collection):
    if not path.exists(TMP_INSTANCE_PATH):
        get_instance()

    with tempfile.TemporaryDirectory(prefix="edit-metadata-") as directory:
        tmp_edit_instance_path = path.join(directory, "edit_metadata_instance.json")
        with open(TMP_INSTANCE_PATH, "r") as json_file, open(tmp_edit_instance_path, "w") as edit_json_file:
            instance = json.load(json_file)
            instance["3_Title"]["title"]["@value"] = collection.new_collection_title
            edit_json_file.write(json.dumps(instance, sort_keys=True, indent=4))

        instance_collection_path = formatters.format_instance_collection_path(collection.project_id, collection.collection_id)
        iput_instance = f"iput -f {tmp_edit_instance_path} {instance_collection_path}"
        subprocess.check_call(iput_instance, shell=True)


def edit_metadata_schema(collection):
    if not path.exists(TMP_SCHEMA_PATH):
        get_schema()

    with tempfile.TemporaryDirectory(prefix="edit-metadata-") as directory:
        tmp_edit_schema_path = path.join(directory, "edit_metadata_schema.json")
        with open(TMP_SCHEMA_PATH, "r") as json_file, open(tmp_edit_schema_path, "w") as edit_json_file:
            schema_json = json.load(json_file)
            schema_json["schema:name"] = collection.new_schema_name
            edit_json_file.write(json.dumps(schema_json))

        schema_collection_path = formatters.format_schema_collection_path(collection.project_id, collection.collection_id)
        iput_instance = f"iput -f {tmp_edit_schema_path} {schema_collection_path}"
        subprocess.check_call(iput_instance, shell=True)


class BaseTestCaseCustomizableMetadata:
    # region default tests

    def test_collection_avu(self, metadata_collection, tmp_path):
        rule_collection_detail = f'/rules/tests/run_test.sh -r detailsProjectCollection -a "{metadata_collection.project_id},{metadata_collection.collection_id},false"'
        ret_collection_detail = subprocess.check_output(rule_collection_detail, shell=True)
        collection_detail = json.loads(ret_collection_detail)
        assert collection_detail["creator"] == metadata_collection.collection_creator
        assert collection_detail["collection"] == metadata_collection.collection_id
        assert collection_detail["title"] == metadata_collection.new_collection_title
        assert metadata_collection.manager1 in collection_detail["managers"]["users"]
        assert metadata_collection.manager2 in collection_detail["managers"]["users"]

        run_iquest = f"iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{metadata_collection.project_collection_path}' and META_COLL_ATTR_NAME = 'latest_version_number' \""
        latest_version_number = subprocess.check_output(run_iquest, shell=True, encoding="UTF-8").strip()
        assert latest_version_number.isdigit()
        assert int(latest_version_number) == metadata_collection.metadata_version

        # Each edit adds an instance/schema snapshot alongside the payload and
        # current documents. Verify the AVU total against the stored documents.
        versions = range(1, metadata_collection.metadata_version + 1)
        documents = ["instance.json", "schema.json"] + [
            f".metadata_versions/{kind}.{version}.json"
            for version in versions for kind in ("instance", "schema")
        ]
        metadata_size = 0
        for index, document in enumerate(documents):
            destination = tmp_path / f"metadata-{index}.json"
            subprocess.check_call(["iget", "-f", f"{metadata_collection.project_collection_path}/{document}", str(destination)])
            metadata_size += destination.stat().st_size
        assert int(collection_detail["numFiles"]) == len(metadata_collection.files_per_protocol) + len(documents)
        assert int(collection_detail["byteSize"]) == sum(metadata_collection.files_per_protocol.values()) + metadata_size

    def test_collection_metadata_version_folder(self, metadata_collection):
        metadata_versions_path = formatters.format_metadata_versions_path(metadata_collection.project_id, metadata_collection.collection_id)
        for version in range(1, metadata_collection.metadata_version + 1):
            instance_path = f"{metadata_versions_path}/instance.{version}.json"
            assert does_path_exist(instance_path)

            schema_path = f"{metadata_versions_path}/schema.{version}.json"
            assert does_path_exist(schema_path)

    # endregion


class BaseEditCollectionMetadata(BaseTestCaseCustomizableMetadata):
    lifecycle_phase = 1

    @pytest.fixture(scope="module")
    @staticmethod
    def metadata_collection(edited_collection):
        return edited_collection

    def test_collection_instance_version(self, metadata_collection, tmp_path):
        tmp_instance_path = tmp_path / "instance.json"
        iget = f"iget -f {metadata_collection.project_path}/{metadata_collection.collection_id}/instance.json {tmp_instance_path}"
        subprocess.check_call(iget, shell=True)
        with open(tmp_instance_path) as tmp_instance_file:
            tmp_instance = json.load(tmp_instance_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith(f"{metadata_collection.project_id}{metadata_collection.collection_id}instance.{metadata_collection.metadata_version}")

            collection_title = tmp_instance["3_Title"]["title"]["@value"]
            assert collection_title == metadata_collection.new_collection_title

    def test_elastic_index_update(self, metadata_collection):
        instance = get_project_collection_instance_in_elastic(metadata_collection.project_id)
        collection_title = instance["3_Title"]["title"]["@value"]
        assert collection_title == metadata_collection.new_collection_title

    def test_collection_schema_version(self, metadata_collection, tmp_path):
        tmp_schema_path = tmp_path / "schema.json"
        iget = f"iget -f {metadata_collection.project_path}/{metadata_collection.collection_id}/schema.json {tmp_schema_path}"
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_instance = json.load(tmp_schema_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith(f"{metadata_collection.project_id}{metadata_collection.collection_id}schema.{metadata_collection.metadata_version}")


class BaseTestChangeCollectionMetadataSchema(BaseTestCaseCustomizableMetadata):
    lifecycle_phase = 2

    @pytest.fixture(scope="module")
    @staticmethod
    def metadata_collection(schema_changed_collection):
        return schema_changed_collection

    def test_collection_instance_version(self, metadata_collection, tmp_path):
        tmp_instance_path = tmp_path / "instance.json"
        iget = f"iget -f {metadata_collection.project_path}/{metadata_collection.collection_id}/instance.json {tmp_instance_path}"
        subprocess.check_call(iget, shell=True)
        with open(tmp_instance_path) as tmp_instance_file:
            tmp_instance = json.load(tmp_instance_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith(f"{metadata_collection.project_id}{metadata_collection.collection_id}instance.{metadata_collection.metadata_version}")

    def test_collection_schema_version(self, metadata_collection, tmp_path):
        tmp_schema_path = tmp_path / "schema.json"
        iget = f"iget -f {metadata_collection.project_path}/{metadata_collection.collection_id}/schema.json {tmp_schema_path}"
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_schema = json.load(tmp_schema_file)
            pid = tmp_schema["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith(f"{metadata_collection.project_id}{metadata_collection.collection_id}schema.{metadata_collection.metadata_version}")

            schema_name = tmp_schema["schema:name"]
            assert schema_name == metadata_collection.new_schema_name
