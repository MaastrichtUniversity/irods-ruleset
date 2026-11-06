import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
PROJECT = "/nlmumc/projects/P000000001"
DROPZONE = "/nlmumc/ingest/direct/test-token"


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class DropzoneACLQueryTests(unittest.TestCase):
    def setUp(self):
        self.dropzones = [DROPZONE]
        self.metadata = {DROPZONE: {"creator": "alice", "state": "open"}}
        self.sharing = "true"
        self.privilege = "modify_object"
        self.acls = {PROJECT: [("10", "own", ""), ("20", "modify_object", ""), ("30", "own", ""),
                               ("40", "own", ""), ("50", "modify_object", ""), ("missing", "own", "")]}
        self.acls[DROPZONE] = self.acls[PROJECT][:]
        self.identities = [("10", "alice", "rodsuser"), ("20", "team", "rodsgroup"),
                           ("30", "rods", "rodsadmin"), ("40", "service-sync", "rodsuser"),
                           ("50", "a-service-person", "rodsuser")]
        self.query = Mock(side_effect=self.rows)
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        self.callback.get_user_id.return_value = {"arguments": ["bob", "60"]}
        self.callback.getCollectionAVU.side_effect = self.get_avu
        self.callback.is_dropzone_state_ingestable.side_effect = lambda state, output: {
            "arguments": [state, "true" if state == "open" else "false"]}
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))
        modules = {
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(format_string_to_boolean=lambda value: value == "true")),
            "dhpythonirodsutils.enums": SimpleNamespace(ProjectAVUs=SimpleNamespace(ENABLE_DROPZONE_SHARING=SimpleNamespace(value="enableDropzoneSharing"))),
            "datahubirodsruleset.utils": SimpleNamespace(TRUE_AS_STRING="true", FALSE_AS_STRING="false"),
            "datahubirodsruleset.formatters": SimpleNamespace(
                format_project_path=lambda ctx, project: "/nlmumc/projects/" + project,
                format_dropzone_path=lambda ctx, token, kind: "/nlmumc/ingest/" + kind + "/" + token),
        }
        for name in ("datahubirodsruleset", "datahubirodsruleset.drop_zones"):
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        modules_patch = patch.dict(sys.modules, modules)
        modules_patch.start()
        self.addCleanup(modules_patch.stop)
        load("datahubirodsruleset.decorator", "decorator.py")
        load("datahubirodsruleset.listing_queries", "listing_queries.py")
        self.single = load("datahubirodsruleset.drop_zones.set_project_acl_to_dropzone", "drop_zones/set_project_acl_to_dropzone.py")
        self.bulk = load("bulk_dropzone_acl", "drop_zones/set_project_acl_to_dropzones.py")
        self.user = load("user_dropzone_acl", "drop_zones/set_single_user_project_acl_to_dropzones.py")

    def get_avu(self, path, attribute, output, default, fatal):
        value = self.sharing if attribute == "enableDropzoneSharing" else self.metadata.get(path, {}).get(attribute, "")
        if not value and fatal == "true":
            raise RuntimeError(f"ERROR: The attribute '{attribute}' of collection '{path}' has no value in iCAT")
        return {"arguments": [path, attribute, value or default, default, fatal]}

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        self.assertLess(len(condition.encode()), 1024)
        if columns == "COLL_NAME":
            self.assertIn("COLL_PARENT_NAME = '/nlmumc/ingest/direct'", condition)
            self.assertIn("META_COLL_ATTR_VALUE = 'P000000001'", condition)
            return [(path,) for path in self.dropzones]
        if columns == "COLL_ACCESS_NAME":
            self.assertIn("COLL_ACCESS_USER_ID = '60'", condition)
            return [(self.privilege,)] if self.privilege else []
        match = re.search(r"(?:COLL_NAME|USER_ID) in \((.*?)\)", condition)
        self.assertIsNotNone(match, condition)
        values = re.findall(r"'([^']*)'", match[1])
        self.assertLessEqual(len(values), 20)
        if columns == "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
            return [(path, attr, value) for path, attrs in self.metadata.items() if path in values for attr, value in attrs.items()]
        if columns == "COLL_NAME, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE":
            return [(path, *entry) for path in values for entry in self.acls.get(path, [])]
        if columns == "USER_ID, USER_NAME, USER_TYPE":
            return [identity for identity in reversed(self.identities) if identity[0] in values]
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def run_bulk(self):
        self.bulk.set_project_acl_to_dropzones(["P000000001"], self.callback, None)

    def run_user(self, username="bob"):
        self.user.set_single_user_project_acl_to_dropzones(["P000000001", username], self.callback, None)

    def test_bulk_sharing_preserves_write_order_and_account_filters(self):
        self.run_bulk()
        self.assertEqual(self.callback.msiSetACL.call_args_list, [
            call("recursive", "admin:own", "rods", DROPZONE),
            call("recursive", "admin:own", "alice", DROPZONE),
            call("default", "admin:read", "alice", DROPZONE + "/instance.json"),
            call("default", "admin:read", "alice", DROPZONE + "/schema.json"),
            call("recursive", "admin:own", "team", DROPZONE),
            call("default", "admin:read", "team", DROPZONE + "/instance.json"),
            call("default", "admin:read", "team", DROPZONE + "/schema.json"),
            call("default", "admin:read", "rods", DROPZONE + "/instance.json"),
            call("default", "admin:read", "rods", DROPZONE + "/schema.json"),
        ])
        self.assertEqual(self.query.call_count, 4)
        self.assertEqual(self.callback.getCollectionAVU.call_count, 1)
        self.callback.set_project_acl_to_dropzone.assert_not_called()

    def test_bulk_disabling_restores_creator_then_removes_caller(self):
        self.sharing = "false"
        self.run_bulk()
        self.assertEqual(self.callback.msiSetACL.call_args_list, [
            call("recursive", "admin:null", "alice", DROPZONE),
            call("recursive", "admin:null", "team", DROPZONE),
            call("recursive", "admin:own", "alice", DROPZONE),
            call("default", "admin:read", "alice", DROPZONE + "/instance.json"),
            call("default", "admin:read", "alice", DROPZONE + "/schema.json"),
            call("recursive", "admin:null", "rods", DROPZONE),
        ])
        self.assertEqual(self.callback.getCollectionAVU.call_count, 1)

    def test_bulk_disabling_missing_creator_still_fails_after_revocations(self):
        self.sharing = "false"
        del self.metadata[DROPZONE]["creator"]
        with self.assertRaisesRegex(RuntimeError, "The attribute 'creator'.*has no value in iCAT"):
            self.run_bulk()
        self.assertEqual(self.callback.msiSetACL.call_count, 2)

    def test_non_rods_caller_uses_default_acl_mode(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        self.run_bulk()
        self.assertTrue(all(not entry.args[1].startswith("admin:") for entry in self.callback.msiSetACL.call_args_list))

    def test_user_permission_is_resolved_once_for_many_dropzones(self):
        self.dropzones = [f"/nlmumc/ingest/direct/token-{i:04d}" for i in range(1000)]
        self.metadata = {path: {"creator": "alice", "state": "open"} for path in self.dropzones}
        self.run_user()
        self.callback.get_user_id.assert_called_once_with("bob", "")
        self.assertEqual(sum(entry.args[0] == "COLL_ACCESS_NAME" for entry in self.query.call_args_list), 1)
        self.assertLess(self.query.call_count, 100)
        self.assertEqual(self.callback.getCollectionAVU.call_count, 1)
        self.assertEqual(self.callback.msiSetACL.call_count, 3000)

    def test_bulk_shared_project_acl_and_identities_are_resolved_once(self):
        self.dropzones = [f"/nlmumc/ingest/direct/token-{i:04d}" for i in range(1000)]
        self.metadata = {path: {"creator": "alice", "state": "open"} for path in self.dropzones}
        self.run_bulk()
        for columns in ("COLL_NAME, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE", "USER_ID, USER_NAME, USER_TYPE"):
            self.assertEqual(sum(entry.args[0] == columns for entry in self.query.call_args_list), 1)
        self.assertLess(self.query.call_count, 100)
        self.assertEqual(self.callback.getCollectionAVU.call_count, 1)

    def test_bulk_disabled_batches_dropzone_acls_and_reuses_shared_identities(self):
        self.sharing = "false"
        self.dropzones = [f"/nlmumc/ingest/direct/token-{i:04d}" for i in range(45)]
        self.metadata = {path: {"creator": "alice", "state": "open"} for path in self.dropzones}
        self.acls.update({path: self.acls[PROJECT] for path in self.dropzones})
        self.run_bulk()
        self.assertEqual(sum(entry.args[0] == "USER_ID, USER_NAME, USER_TYPE" for entry in self.query.call_args_list), 1)
        self.assertLess(self.query.call_count, 15)
        self.assertEqual(self.callback.msiSetACL.call_count, 45 * 6)

    def test_creator_and_non_ingestable_dropzones_do_not_resolve_user_permission(self):
        self.run_user("alice")
        self.metadata[DROPZONE]["state"] = "ingested"
        self.run_user()
        self.callback.get_user_id.assert_not_called()
        self.callback.msiSetACL.assert_not_called()

    def test_missing_state_is_not_ingestable_and_empty_listing_skips_sharing_read(self):
        self.metadata[DROPZONE] = {}
        self.run_bulk()
        self.callback.getCollectionAVU.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.dropzones = []
        self.run_bulk()
        self.callback.getCollectionAVU.assert_not_called()

    def test_user_with_read_or_no_project_access_is_revoked(self):
        for privilege in ("read_object", ""):
            with self.subTest(privilege=privilege):
                self.callback.reset_mock()
                self.privilege = privilege
                self.run_user()
                self.callback.msiSetACL.assert_called_once_with("recursive", "admin:null", "bob", DROPZONE)

    def test_disabled_sharing_leaves_single_user_dropzones_unchanged(self):
        self.sharing = "false"
        self.run_user()
        self.query.assert_not_called()
        self.callback.msiSetACL.assert_not_called()

    def test_single_dropzone_new_flag_and_batched_account_resolution(self):
        self.sharing = "false"
        self.single.set_project_acl_to_dropzone(["P000000001", "test-token", "true"], self.callback, None)
        self.query.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.sharing = "true"
        self.single.set_project_acl_to_dropzone(["P000000001", "test-token", "false"], self.callback, None)
        self.assertEqual(self.query.call_count, 2)
        self.assertEqual(self.callback.msiSetACL.call_count, 9)


if __name__ == "__main__":
    unittest.main()
