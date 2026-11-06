import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CollectionMetadataSaveTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
        decorator = load("collection_save_decorator", root / "decorator.py")
        self.instance = {
            "@id": "old", "1_Identifier": {"datasetIdentifier": {}, "datasetIdentifierType": {}},
            "title": "é漢字🙂'\"\\\n",
        }
        self.schema = {"@id": "old", "description": "keep this"}
        self.read = Mock(return_value=json.dumps(self.schema))
        self.copy = Mock()
        formatters = SimpleNamespace(**{
            name: (lambda *args, path=path: path) for name, path in {
                "format_project_collection_path": "collection",
                "format_project_path": "project",
                "format_metadata_versions_path": "versions",
                "format_instance_collection_path": "instance",
                "format_schema_collection_path": "schema",
                "format_instance_versioned_collection_path": "versions/instance.8",
                "format_schema_versioned_collection_path": "versions/schema.8",
            }.items()
        })
        modules = {
            "irods_types": SimpleNamespace(RodsObjStat=Mock()),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(format_string_to_boolean=lambda x: x == "true")),
            "datahubirodsruleset": ModuleType("datahubirodsruleset"),
            "datahubirodsruleset.decorator": decorator,
            "datahubirodsruleset.formatters": formatters,
            "datahubirodsruleset.utils": SimpleNamespace(
                FALSE_AS_STRING="false", icp_wrapper=self.copy, read_data_object_from_irods=self.read,
            ),
        }
        update_name = "datahubirodsruleset.customizable_metadata.update_metadata_during_edit_collection"
        with patch.dict(sys.modules, modules):
            self.update = load(update_name, root / "customizable_metadata/update_metadata_during_edit_collection.py")
            with patch.dict(sys.modules, {update_name: self.update}):
                self.rule = load("collection_save_rule", root / "customizable_metadata/create_collection_metadata_snapshot.py")
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["opalmen"]}
        self.callback.check_edit_metadata_permission.return_value = {"arguments": [None, "true"]}
        self.callback.getCollectionAVU.return_value = {"arguments": [None, None, "7"]}
        self.callback.get_versioned_pids.return_value = {"arguments": [None, None, None, '{"collection":{"handle":"handle"}}']}
        self.callback.get_env.return_value = {"arguments": [None, None, "http://pid/prefix/"]}
        self.callback.msiExit.side_effect = lambda *args: (_ for _ in ()).throw(RuntimeError(str(args)))
        self.callback.msiDataObjOpen.side_effect = lambda path, _: {"arguments": [path, path]}
        self.payload = {
            "instance": self.instance, "schema": None,
            "metadata": {"schemaVersion": "1.0", "schemaName": "general", "title": self.instance["title"]},
        }
        self.filename = ".metadata-save-" + "a" * 32 + ".json"
        self.read.side_effect = lambda ctx, path: json.dumps(
            self.payload if path.endswith(self.filename) else self.schema
        )

    def invoke(self):
        args = ["P000000001", "C000000001", self.filename, ""]
        self.rule.save_collection_metadata(args, self.callback, None)
        return args[3]

    def assert_not_published(self):
        self.assertFalse(any(c.args[1] == "latest_version_number" for c in self.callback.setCollectionAVU.call_args_list))
        self.callback.index_update_single_project_collection_metadata.assert_not_called()

    def test_edit_writes_final_documents_once_and_preserves_schema(self):
        original = copy.deepcopy(self.payload)
        self.assertEqual(self.invoke(), "true")
        self.assertEqual(self.payload, original)
        self.assertEqual(self.read.call_count, 2)
        self.assertEqual(self.read.call_args.args[1], "schema")
        self.assertEqual(self.callback.msiDataObjWrite.call_count, 2)
        instance, schema = [json.loads(c.args[1]) for c in self.callback.msiDataObjWrite.call_args_list]
        self.assertEqual(instance["@id"], "https://hdl.handle.net/prefix/P000000001C000000001instance.8")
        self.assertEqual(instance["schema:isBasedOn"], schema["@id"])
        self.assertTrue(instance["1_Identifier"]["datasetIdentifier"]["@value"].endswith("C000000001.8"))
        self.assertEqual(instance["title"], self.instance["title"])
        self.assertEqual(schema["description"], "keep this")
        self.assertEqual(self.copy.call_count, 2)
        self.assertTrue(all(c.kwargs["transfer_threading"] is False for c in self.copy.call_args_list))
        self.callback.setCollectionAVU.assert_any_call("collection", "latest_version_number", "8")
        self.callback.update_metadata_during_edit_collection.assert_not_called()

    def test_schema_save_reads_only_staged_payload_and_truncates_both_writes(self):
        self.payload["schema"] = {"description": "replacement"}
        self.invoke()
        self.assertEqual(self.read.call_count, 1)
        self.assertTrue(self.read.call_args.args[1].endswith(self.filename))
        schema = json.loads(self.callback.msiDataObjWrite.call_args_list[1].args[1])
        self.assertEqual(schema["description"], "replacement")
        self.assertTrue(all("O_WRONLYO_TRUNC" in c.args[0] for c in self.callback.msiDataObjOpen.call_args_list))

    def test_unauthorized_call_does_not_read_or_write_documents(self):
        self.callback.check_edit_metadata_permission.return_value = {"arguments": [None, "false"]}
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.read.assert_not_called()
        self.callback.msiDataObjOpen.assert_not_called()
        self.callback.get_versioned_pids.assert_not_called()
        self.assert_not_published()

    def test_invalid_version_does_not_write(self):
        self.callback.getCollectionAVU.return_value = {"arguments": [None, None, "invalid"]}
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.callback.msiDataObjOpen.assert_not_called()
        self.assert_not_published()

    def test_arbitrary_paths_and_live_metadata_filenames_are_rejected(self):
        for name in ["../schema.json", "schema.json", "instance.json", "/other/file.json"]:
            with self.subTest(name=name):
                self.filename = name
                with self.assertRaises(RuntimeError):
                    self.invoke()
                self.read.assert_not_called()
                self.callback.msiDataObjOpen.assert_not_called()

    def test_write_failure_closes_descriptor_and_does_not_publish(self):
        self.callback.msiDataObjWrite.side_effect = RuntimeError("write failed")
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.callback.msiDataObjClose.assert_called_once()
        self.copy.assert_not_called()
        self.assert_not_published()

    def test_copy_failure_does_not_publish_version_or_index(self):
        self.copy.side_effect = RuntimeError("copy failed")
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.assert_not_published()

    def test_pid_failure_keeps_existing_false_status_and_snapshot_behavior(self):
        self.callback.get_versioned_pids.return_value = {"arguments": [None, None, None, '{}']}
        self.assertEqual(self.invoke(), "false")
        self.assertEqual(self.copy.call_count, 2)
        self.callback.setCollectionAVU.assert_any_call("collection", "latest_version_number", "8")

    def test_legacy_snapshot_still_calls_existing_update_rule(self):
        args = ["P000000001", "C000000001", ""]
        self.rule.create_collection_metadata_snapshot(args, self.callback, None)
        self.assertEqual(args[2], "true")
        self.callback.update_metadata_during_edit_collection.assert_called_once_with("P000000001", "C000000001", "8")
        self.assertEqual(self.copy.call_count, 2)


if __name__ == "__main__":
    unittest.main()
