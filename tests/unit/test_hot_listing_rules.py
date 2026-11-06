import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / 'datahubirodsruleset'
PROJECT = '/nlmumc/projects/P000000001'
DROPZONE = '/nlmumc/ingest/direct/test-token'


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def constants(**values):
    return SimpleNamespace(**{key: SimpleNamespace(value=value) for key, value in values.items()})


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.query = Mock(side_effect=self.rows)
        self.callback = Mock()
        self.callback.get_client_username.return_value = {'arguments': ['alice']}
        self.callback.get_user_id.return_value = {'arguments': ['', '10']}
        self.callback.get_project_size.return_value = {'arguments': ['', '0.0']}
        self.callback.get_user_group_memberships.return_value = {'arguments': ['', '', '[]']}
        self.callback.checkDropZoneACL.return_value = {'arguments': ['', '', 'true']}
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))
        project_avus = constants(TITLE='title', RESOURCE='resource', COLLECTION_METADATA_SCHEMAS='collectionMetadataSchemas',
                                 ENABLE_ARCHIVE='enableArchive', ENABLE_UNARCHIVE='enableUnarchive',
                                 ENABLE_CONTRIBUTOR_EDIT_METADATA='enableContributorEditMetadata', DESCRIPTION='description',
                                 RESPONSIBLE_COST_CENTER='responsibleCostCenter', STORAGE_QUOTA_GB='storageQuotaGb',
                                 ENABLE_DROPZONE_SHARING='enableDropzoneSharing', PRINCIPAL_INVESTIGATOR='OBI:0000103', DATA_STEWARD='dataSteward')
        self.enums = SimpleNamespace(
            ProjectAVUs=project_avus, ProcessAttribute=constants(ARCHIVE='archiveState', UNARCHIVE='unArchiveState'),
            ProcessType=constants(DROP_ZONE='drop_zone', ARCHIVE='archive', UNARCHIVE='unarchive'),
            ProcessState=constants(COMPLETED='completed', ERROR='error', IN_PROGRESS='in_progress', OPEN='open'),
            DropzoneState=constants(INGESTED='ingested', OPEN='open', WARNING_VALIDATION_INCORRECT='warning-validation-incorrect',
                                    WARNING_UNSUPPORTED_CHARACTER='warning-unsupported-character'),
            ArchiveState=constants(ARCHIVE_DONE='archive-done'), UnarchiveState=constants(UNARCHIVE_DONE='unarchive-done'),
        )
        self.formatters = SimpleNamespace(
            format_string_to_boolean=lambda value: value == 'true',
            format_project_path=lambda value: '/nlmumc/projects/' + value,
            format_dropzone_path=lambda token, kind: '/nlmumc/ingest/' + ('direct' if kind == 'direct' else 'zones') + '/' + token,
            get_project_id_from_project_path=lambda path: path.rsplit('/', 1)[1],
            get_collection_id_from_project_collection_path=lambda path: path.split('/')[4],
            format_project_collection_path=lambda project, collection: '/nlmumc/projects/' + project + '/' + collection,
            get_project_id_from_project_collection_path=lambda path: path.split('/')[3],
            get_project_path_from_project_collection_path=lambda path: '/'.join(path.split('/')[:4]),
        )
        modules = {
            'genquery': SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            'dhpythonirodsutils': SimpleNamespace(formatters=self.formatters, validators=SimpleNamespace(
                validate_project_collections_action_avu=lambda value: None), exceptions=SimpleNamespace(ValidationError=ValueError)),
            'dhpythonirodsutils.formatters': self.formatters, 'dhpythonirodsutils.enums': self.enums,
            'datahubirodsruleset.utils': SimpleNamespace(TRUE_AS_STRING='true', FALSE_AS_STRING='false'),
            'datahubirodsruleset.formatters': SimpleNamespace(format_project_path=lambda ctx, identifier: PROJECT[:-10] + identifier),
        }
        for package in ('datahubirodsruleset', 'datahubirodsruleset.collections', 'datahubirodsruleset.projects',
                        'datahubirodsruleset.users', 'datahubirodsruleset.drop_zones', 'datahubirodsruleset.customizable_metadata'):
            modules[package] = ModuleType(package)
            modules[package].__path__ = []
        self.patch = patch.dict(sys.modules, modules)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        load('datahubirodsruleset.decorator', 'decorator.py')
        self.helpers = load('datahubirodsruleset.listing_queries', 'listing_queries.py')
        load('datahubirodsruleset.collections.list_collections', 'collections/list_collections.py')
        self.dropzones = load('datahubirodsruleset.drop_zones.list_active_drop_zones', 'drop_zones/list_active_drop_zones.py')

    def module(self, relative):
        return load('datahubirodsruleset.' + relative[:-3].replace('/', '.'), relative)

    def invoke(self, relative, name, *inputs):
        module = self.module(relative)
        args = list(inputs) + ['']
        getattr(module, name)(args, self.callback, None)
        return json.loads(args[-1])

    def rows(self, columns, condition, mode, callback):
        self.fail('Unexpected query: ' + columns + ' WHERE ' + condition)

    @staticmethod
    def selected(condition, column):
        match = re.search(re.escape(column) + r" in \((.*?)\)", condition)
        return re.findall(r"'((?:[^']|'')*)'", match[1]) if match else None


class CollectionProcessActivityTests(RuleTests):
    def test_active_dropzone_matches_project_and_collection(self):
        for project, collection, expected in [
            ('P000000001', 'C000000001', True),
            ('P000000002', 'C000000001', False),
            ('P000000001', 'C000000002', False),
        ]:
            with self.subTest(project=project, collection=collection):
                self.callback.list_active_drop_zones.return_value = {'arguments': ['', json.dumps([{
                    'project': project, 'destination': collection, 'token': 'test-token', 'state': 'open',
                }])]}
                module = self.module('collections/get_project_collection_process_activity.py')
                result = module.check_active_dropzone_by_project_collection_path(
                    SimpleNamespace(callback=self.callback), PROJECT + '/C000000001',
                )
                self.assertEqual(result, expected)
                self.callback.list_active_drop_zones.assert_called_with('false', '')


class CollectionTests(RuleTests):
    def setUp(self):
        super().setUp()
        self.paths = [PROJECT + '/C000000001', PROJECT + '/C000000002']
        self.metadata = [(self.paths[0], 'dcat:byteSize', '1024'), (self.paths[0], 'title', "A's title"),
                         (self.paths[0], 'numFiles', '10'), (self.paths[0], 'latest_version_number', '2'),
                         (self.paths[0], 'deletionState', 'deleted')]
        self.excluded = [(self.paths[0], 'metadata.xml')]

    def rows(self, columns, condition, mode, callback):
        self.assertIn("COLL_PARENT_NAME = '" + PROJECT + "'", condition)
        if columns == 'COLL_NAME':
            return [(path,) for path in self.paths]
        if columns == 'COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE':
            return self.metadata
        if columns == 'COLL_NAME, DATA_NAME':
            return self.excluded
        return super().rows(columns, condition, mode, callback)

    def test_regular_list_preserves_defaults_version_counts_and_deleted_rows(self):
        result = self.invoke('collections/list_collections.py', 'list_collections', PROJECT)
        self.assertEqual(result, [
            {'id': 'C000000001', 'size': 1024, 'title': "A's title", 'creator': '', 'PID': '', 'numFiles': 10, 'numUserFiles': 3},
            {'id': 'C000000002', 'size': 0, 'title': '', 'creator': '', 'PID': '', 'numFiles': 0, 'numUserFiles': 0},
        ])
        self.assertIsInstance(result[0]['size'], int)
        self.assertEqual(self.query.call_count, 3)
        self.callback.getCollectionAVU.assert_not_called()

    def test_admin_keeps_float_size_and_deletion_state(self):
        result = self.invoke('collections/admin_list_collections.py', 'admin_list_collections', PROJECT)
        self.assertIsInstance(result[0]['size'], float)
        self.assertEqual(result[0]['deletionState'], 'deleted')
        self.assertEqual(result[1]['deletionState'], '')
        self.assertEqual(self.query.call_count, 3)

    def test_empty_metadata_numbers_have_distinct_legacy_behavior(self):
        self.metadata = [(self.paths[0], 'numFiles', '')]
        with self.assertRaises(ValueError):
            self.invoke('collections/list_collections.py', 'list_collections', PROJECT)
        result = self.invoke('collections/admin_list_collections.py', 'admin_list_collections', PROJECT)
        self.assertEqual(result[0]['numFiles'], 0)

    def test_thousand_collections_still_use_three_queries(self):
        self.paths = [PROJECT + f'/C{i:09d}' for i in range(1000)]
        self.assertEqual(len(self.invoke('collections/list_collections.py', 'list_collections', PROJECT)), 1000)
        self.assertEqual(self.query.call_count, 3)

    def test_empty_project_skips_bulk_scans(self):
        self.paths = []
        self.assertEqual(self.invoke('collections/list_collections.py', 'list_collections', PROJECT), [])
        self.assertEqual(self.query.call_count, 1)


class FolderTests(RuleTests):
    def rows(self, columns, condition, mode, callback):
        return self.folders

    def test_tree_keeps_order_relative_ids_and_visible_parent_traversal(self):
        self.folders = [(DROPZONE + '/alpha', DROPZONE), (DROPZONE + '/alpha/child', DROPZONE + '/alpha'),
                        (DROPZONE + '/hidden/visible', DROPZONE + '/hidden'), (DROPZONE + '/z', DROPZONE),
                        (DROPZONE + '-sibling/leaf', DROPZONE + '-sibling')]
        result = self.invoke('drop_zones/get_dropzone_folders.py', 'get_dropzone_folders', 'test-token', '')
        self.assertEqual([node['value'] for node in result], ['alpha', 'z'])
        self.assertEqual(result[0]['data'][0]['id'], '/alpha/child')
        self.assertEqual(result[1]['data'], [])
        self.assertEqual(self.query.call_count, 1)

    def test_thousand_folders_need_one_query(self):
        self.folders = [(DROPZONE + f'/folder{i:04d}', DROPZONE) for i in range(1000)]
        self.assertEqual(len(self.invoke('drop_zones/get_dropzone_folders.py', 'get_dropzone_folders', 'test-token', '')), 1000)
        self.assertEqual(self.query.call_count, 1)

    def test_trailing_slash_keeps_legacy_parent_matching(self):
        self.folders = [(DROPZONE + '/alpha', DROPZONE)]
        self.assertEqual(self.invoke('drop_zones/get_dropzone_folders.py', 'get_dropzone_folders', 'test-token', '/'), [])


class ProjectTests(RuleTests):
    def setUp(self):
        super().setUp()
        self.values = {'title': 'Title', 'resource': 'disk', 'responsibleCostCenter': '123', 'storageQuotaGb': '10',
                       'collectionMetadataSchemas': 'general', 'OBI:0000103': 'pi', 'dataSteward': 'steward', 'enableArchive': 'true'}
        self.entries = [('10', 'own'), ('20', 'modify_object'), ('30', 'read_object'), ('40', 'own')]
        self.identities = [('alice', '10', 'rodsuser'), ('team', '20', 'rodsgroup'),
                           ('service-sync', '30', 'rodsuser'), ('rods', '40', 'rodsadmin')]
        def call_role(name, *args):
            arguments = list(args)
            getattr(self.module('projects/' + name + '.py'), name)(arguments, self.callback, None)
            return {'arguments': arguments}
        self.callback.list_project_managers.side_effect = lambda *args: call_role('list_project_managers', *args)
        self.callback.list_project_contributors.side_effect = lambda *args: call_role('list_project_contributors', *args)

    def rows(self, columns, condition, mode, callback):
        if columns == 'COLL_ACCESS_USER_ID, COLL_ACCESS_NAME':
            levels = self.selected(condition, 'COLL_ACCESS_NAME')
            return [row for row in self.entries if row[1] in levels]
        if columns == 'order(USER_NAME), USER_ID, USER_TYPE':
            ids = self.selected(condition, 'USER_ID')
            return [row for row in self.identities if row[1] in ids]
        if columns == 'USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE':
            return [('20', 'description', 'Team description')]
        if columns == 'COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE':
            return [(PROJECT, key, value) for key, value in self.values.items()]
        if columns == 'COLL_NAME, META_COLL_ATTR_VALUE':
            return [(PROJECT + '/C000000001', '1024'), (PROJECT + '/C000000001', '2048'),
                    (PROJECT + '/C000000002', '')]
        return super().rows(columns, condition, mode, callback)

    def test_project_details_fetches_metadata_once_and_keeps_fallbacks(self):
        result = self.invoke('projects/get_project_details.py', 'get_project_details', PROJECT, 'false')
        self.assertEqual(result['enableUnarchive'], 'true')
        self.assertEqual(result['enableContributorEditMetadata'], 'false')
        self.assertEqual(result['viewers']['users'], [])
        self.assertEqual(result['managers']['users'], ['alice'])
        self.assertEqual(result['contributors']['groupObjects'][0]['displayName'], 'team')
        self.assertEqual(result['contributors']['groupObjects'][0]['description'], 'Team description')
        self.assertFalse(result['has_financial_view_access'])
        self.assertEqual(self.query.call_count, 4)
        self.callback.getCollectionAVU.assert_not_called()

    def test_required_project_metadata_still_fails(self):
        self.values.pop('title')
        with self.assertRaisesRegex(RuntimeError, "attribute 'title'.*has no value"):
            self.invoke('projects/get_project_details.py', 'get_project_details', PROJECT, 'false')

    def test_inherited_roles_and_service_filters(self):
        result = self.invoke('projects/list_project_viewers.py', 'list_project_viewers', 'P000000001', 'true', 'true')
        self.assertEqual(result['users'], ['alice', 'service-sync'])
        self.assertEqual(result['groups'], ['team'])
        self.assertEqual(self.query.call_count, 3)

    def test_project_size_uses_last_value_and_one_query(self):
        result = self.invoke('projects/get_project_size.py', 'get_project_size', PROJECT)
        self.assertEqual(result, 2048 / 1024 / 1024 / 1024)
        self.assertEqual(self.query.call_count, 1)

    def test_shared_acl_account_batches_are_bounded_with_large_ids(self):
        self.entries = [(str(9000000000000000000 + i), 'own') for i in range(1000)]
        self.identities = [(f'user{i}', identifier, 'rodsuser') for i, (identifier, _) in enumerate(self.entries)]
        self.query.side_effect = lambda columns, condition, mode, callback: (
            [] if columns == 'USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE'
            else ProjectTests.rows(self, columns, condition, mode, callback))
        result = self.invoke('projects/list_project_managers.py', 'list_project_managers', 'P000000001', 'false')
        self.assertEqual(len(result['users']), 1000)
        self.assertEqual(self.query.call_count, 101)
        self.assertTrue(all(len(call.args[1].encode()) < 1024 for call in self.query.call_args_list))

    def test_permission_pi_and_steward_short_circuits(self):
        for name in ('pi', 'steward'):
            with self.subTest(name=name):
                self.callback.get_client_username.return_value = {'arguments': [name]}
                self.assertTrue(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))
        self.assertEqual(self.query.call_count, 2)

    def test_permission_direct_manager_and_group_manager(self):
        self.assertTrue(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))
        self.callback.get_client_username.return_value = {'arguments': ['group-member']}
        self.entries = [('20', 'own')]
        self.callback.get_user_group_memberships.return_value = {'arguments': ['', '', '[{"name":"team"}]']}
        self.assertTrue(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))

    def test_contributor_edit_requires_flag_and_excludes_service_accounts(self):
        self.entries = [('10', 'modify_object')]
        self.assertFalse(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))
        self.values['enableContributorEditMetadata'] = 'true'
        self.assertTrue(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))
        self.callback.get_client_username.return_value = {'arguments': ['service-sync']}
        self.entries = [('30', 'modify_object')]
        self.assertFalse(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))

    def test_missing_pi_returns_false_without_acl_queries(self):
        self.values.pop('OBI:0000103')
        self.assertFalse(self.invoke('customizable_metadata/check_edit_metadata_permission.py', 'check_edit_metadata_permission', PROJECT))
        self.assertEqual(self.query.call_count, 1)


class UserTests(RuleTests):
    def setUp(self):
        super().setUp()
        self.users = [('z-user', '10'), ('a-user', '20'), ('service-sync', '30')]
        self.names = [('10', 'Z user'), ('20', '')]

    def rows(self, columns, condition, mode, callback):
        if columns in ('USER_NAME, USER_ID', 'order(USER_NAME), USER_ID'):
            return self.users
        if columns == 'USER_ID, META_USER_ATTR_VALUE':
            return self.names
        return super().rows(columns, condition, mode, callback)

    def test_users_keep_catalog_order_fallback_names_and_service_prefix_filter(self):
        result = self.invoke('users/list_users.py', 'get_users', 'false')
        self.assertEqual(result, [{'userName': 'z-user', 'userId': '10', 'displayName': 'Z user'},
                                  {'userName': 'a-user', 'userId': '20', 'displayName': 'a-user'}])
        self.assertEqual(self.query.call_count, 2)

    def test_thousand_users_still_use_two_scans(self):
        self.users = [(f'user{i}', str(i)) for i in range(1000)]
        self.assertEqual(len(self.invoke('users/list_users.py', 'get_users', 'true')), 1000)
        self.assertEqual(self.query.call_count, 2)


class ProcessTests(RuleTests):
    def setUp(self):
        super().setUp()
        self.dz_rows = [(DROPZONE, '01700000000', '/nlmumc/ingest/direct', '01600000000')]
        self.values = {
            DROPZONE: {'project': 'P000000001', 'creator': 'alice', 'title': 'true', 'state': 'ingesting',
                       'totalSize': '1000', 'destination': 'C000000001', 'validateState': 'true', 'validateMsg': 'false'},
            PROJECT: {'title': '123', 'resource': 'disk', 'enableDropzoneSharing': 'false'},
            PROJECT + '/C000000001': {'title': 'Collection', 'sizeIngested': '333'},
        }
        self.processes = [(PROJECT + '/C000000001', 'archiveState', ' archive-done ', '100'),
                          (PROJECT + '/C000000001', 'unArchiveState', 'error-unarchive-failed', '101')]

    def rows(self, columns, condition, mode, callback):
        if columns == 'COLL_NAME, order_desc(COLL_MODIFY_TIME), COLL_PARENT_NAME, COLL_CREATE_TIME':
            return self.dz_rows
        if columns == 'COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE':
            selected = self.selected(condition, 'COLL_NAME')
            attributes = self.selected(condition, 'META_COLL_ATTR_NAME')
            return [(path, key, value) for path, values in self.values.items() if path in selected
                    for key, value in values.items() if attributes is None or key in attributes]
        if columns == 'order(USER_NAME), USER_ID, USER_TYPE':
            return [('alice', '10', 'rodsuser')]
        if columns == 'USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE':
            return [('10', 'displayName', 'Alice')]
        if columns == 'COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_ID':
            return self.processes
        return super().rows(columns, condition, mode, callback)

    def test_dropzone_output_keeps_native_scalar_types_and_title_strings(self):
        result = self.invoke('drop_zones/list_active_drop_zones.py', 'list_active_drop_zones', 'false')[0]
        self.assertEqual(result['title'], 'true')
        self.assertEqual(result['projectTitle'], '123')
        self.assertIs(result['enableDropzoneSharing'], False)
        self.assertIs(result['validateState'], True)
        self.assertIs(result['validateMsg'], False)
        self.assertIs(result['sharedWithMe'], False)
        self.assertEqual(result['totalSize'], 1000)
        self.assertEqual(result['date'], '01700000000')
        self.assertEqual(result['creator'], 'Alice')

    def test_user_and_admin_progress_keep_their_distinct_rounding_and_fields(self):
        user = self.invoke('users/get_user_active_processes.py', 'get_user_active_processes', 'true', 'false', 'false')
        admin = self.invoke('users/admin_get_user_active_processes.py', 'admin_get_user_active_processes', 'true', 'false', 'false')
        self.assertEqual(user['in_progress'][0]['percentage_ingested'], 33.0)
        self.assertNotIn('size_ingested', user['in_progress'][0])
        self.assertEqual(admin['in_progress'][0]['percentage_ingested'], 33.3)
        self.assertEqual(admin['in_progress'][0]['size_ingested'], '333')
        self.assertEqual(admin['in_progress'][0]['destination_resource'], 'disk')
        self.callback.getCollectionAVU.assert_not_called()
        self.callback.get_collection_attribute_value.assert_not_called()

    def test_archive_titles_are_bulk_fetched_and_states_keep_categories(self):
        result = self.invoke('users/get_user_active_processes.py', 'get_user_active_processes', 'false', 'true', 'true')
        self.assertEqual(result['completed'][0]['project_title'], '123')
        self.assertEqual(result['completed'][0]['state'], 'archive-done')
        self.assertEqual(result['error'][0]['state'], 'error-unarchive-failed')
        self.assertEqual(self.query.call_count, 2)

    def test_no_process_flags_means_no_queries(self):
        self.assertEqual(self.invoke('users/get_user_active_processes.py', 'get_user_active_processes', 'false', 'false', 'false'),
                         {'completed': [], 'error': [], 'in_progress': [], 'open': []})
        self.query.assert_not_called()

    def test_denied_dropzone_access_fails_before_listing_metadata(self):
        self.callback.checkDropZoneACL.return_value = {'arguments': ['', '', 'false']}
        with self.assertRaisesRegex(RuntimeError, 'insufficient DropZone permissions'):
            self.invoke('drop_zones/list_active_drop_zones.py', 'list_active_drop_zones', 'false')
        self.query.assert_not_called()

    def test_missing_required_process_title_is_fatal(self):
        self.values[PROJECT].pop('title')
        with self.assertRaisesRegex(RuntimeError, "attribute 'title'.*has no value"):
            self.invoke('users/get_user_active_processes.py', 'get_user_active_processes', 'false', 'true', 'true')

    def test_thousand_dropzones_share_creator_and_project_lookups(self):
        template = self.values[DROPZONE]
        self.dz_rows = [(DROPZONE + str(i), '01700000000', '/nlmumc/ingest/direct', '01600000000') for i in range(1000)]
        self.values.update({row[0]: dict(template) for row in self.dz_rows})
        result = self.invoke('drop_zones/list_active_drop_zones.py', 'list_active_drop_zones', 'false')
        self.assertEqual(len(result), 1000)
        self.assertLess(self.query.call_count, 150)
        creator_queries = [call for call in self.query.call_args_list if call.args[0] == 'order(USER_NAME), USER_ID, USER_TYPE']
        self.assertEqual(len(creator_queries), 1)
        self.assertTrue(all(len(call.args[1].encode()) < 1024 for call in self.query.call_args_list))

    def test_thousand_processes_share_project_title_and_use_bounded_path_batches(self):
        self.processes = [(PROJECT + f'/C{i:09d}', 'archiveState', 'archive-done', str(i)) for i in range(1000)]
        self.values.update({row[0]: {'title': 'Collection'} for row in self.processes})
        result = self.invoke('users/get_user_active_processes.py', 'get_user_active_processes', 'false', 'true', 'true')
        self.assertEqual(len(result['completed']), 1000)
        self.assertLess(self.query.call_count, 120)
        self.assertTrue(all(len(call.args[1].encode()) < 1024 for call in self.query.call_args_list))


class ActiveDropZoneTests(RuleTests):
    def setUp(self):
        super().setUp()
        sys.modules['irods_types'] = SimpleNamespace(RodsObjStat=Mock())
        sys.modules['datahubirodsruleset.formatters'].format_dropzone_path = (
            lambda ctx, token, kind: self.formatters.format_dropzone_path(token, kind)
        )
        self.module('users/get_user_active_processes.py')
        self.callback.getCollectionAVU.side_effect = lambda path, attribute, *args: {
            'arguments': [path, attribute, 'Project' if attribute == 'title' else 'false'],
        }
        self.values = {'project': 'P000000001', 'creator': 'alice', 'state': 'ingesting',
                       'totalSize': '1000', 'destination': 'C000000001'}
        self.size_ingested = '333'

    def rows(self, columns, condition, mode, callback):
        if columns == 'COLL_MODIFY_TIME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE':
            self.assertIn(self.dropzone_path, condition)
            return [('01700000000', key, value) for key, value in self.values.items()]
        if columns == 'COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE':
            self.assertIn(PROJECT + '/C000000001', condition)
            self.assertIn('sizeIngested', condition)
            return [(PROJECT + '/C000000001', 'sizeIngested', self.size_ingested)] if self.size_ingested else []
        return super().rows(columns, condition, mode, callback)

    def test_polling_progress_for_direct_and_mounted_dropzones(self):
        for kind in ('direct', 'mounted'):
            self.dropzone_path = self.formatters.format_dropzone_path('test-token', kind)
            for state, destination, size_ingested, total_size, expected in (
                ('open', '', '', '1000', 0),
                ('ingesting', 'C000000001', '333', '1000', 33.0),
                ('ingesting', 'C000000001', '', '1000', 0),
                ('ingesting', 'C000000001', '333', '0', 0),
                ('ingested', 'C000000001', '', '1000', 100),
            ):
                with self.subTest(kind=kind, state=state, size=size_ingested, total=total_size):
                    self.values.update(state=state, destination=destination, totalSize=total_size)
                    self.size_ingested = size_ingested
                    result = self.invoke('drop_zones/get_active_drop_zone.py', 'get_active_drop_zone',
                                         'test-token', 'false', kind)
                    self.assertEqual(result['percentage_ingested'], expected)
                    self.assertEqual(result['token'], 'test-token')
                    self.assertEqual(result['state'], state)


class NavigationTests(RuleTests):
    def setUp(self):
        super().setUp()
        self.paths = [f'/nlmumc/projects/P{i:09d}' for i in range(1000)]
        self.missing_title = False

    def rows(self, columns, condition, mode, callback):
        if columns == 'COLL_NAME':
            return [(path,) for path in self.paths]
        if columns == 'COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE':
            return [(path, 'title', 'Title') for path in self.paths if not self.missing_title or path != self.paths[-1]]
        return super().rows(columns, condition, mode, callback)

    def test_thousand_project_titles_need_two_scans(self):
        self.assertEqual(len(self.invoke('projects/list_projects_minimal.py', 'list_projects_minimal')), 1000)
        self.assertEqual(self.query.call_count, 2)
        self.callback.getCollectionAVU.assert_not_called()

    def test_missing_required_title_is_not_silently_omitted(self):
        self.missing_title = True
        with self.assertRaisesRegex(RuntimeError, "attribute 'title'.*has no value"):
            self.invoke('projects/list_projects_minimal.py', 'list_projects_minimal')


class ConditionTests(RuleTests):
    def test_unicode_conditions_and_quoted_paths_stay_bounded(self):
        values = ["/some/" + '漢' * 30 + str(i) + "'" for i in range(100)]
        conditions = list(self.helpers.in_conditions('COLL_NAME', values))
        self.assertGreater(len(conditions), 1)
        self.assertTrue(all(len(condition.encode()) < 700 for condition in conditions))
        self.assertIn("''", conditions[0])


if __name__ == '__main__':
    unittest.main()
