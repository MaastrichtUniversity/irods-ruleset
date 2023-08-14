import json
import subprocess

from dhpythonirodsutils import formatters

from test_cases.utils import (
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    set_collection_avu,
    does_path_exist,
    remove_project,
    revert_latest_project_number,
    wait_for_set_acl_for_metadata_snapshot_to_finish,
    run_index_all_project_collections_metadata,
)


class BaseTestCaseCustomizableMetadata:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = ""
    destination_resource = ""
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = ""
    token = ""

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title = "collection_title"
    collection_id = "C000000001"

    project_collection_path = ""
    new_collection_title = ""
    num_files = 0
    byte_size = 0

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        pass

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        start_and_wait_for_ingest(cls)

        # Running the index all rule: delete the current elasticsearch index that could be in a bad state
        run_index_all_project_collections_metadata()
        cls.project_collection_path = formatters.format_project_collection_path(cls.project_id, cls.collection_id)
        cls.edit_collection_metadata()

        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        wait_for_set_acl_for_metadata_snapshot_to_finish(cls.project_id)
        remove_project(cls.project_path)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    # region extended setup

    @classmethod
    def edit_collection_metadata(cls):
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
        open_acl = '/rules/tests/run_test.sh -r set_acl_for_metadata_snapshot -a "{},{},{},true,false"'.format(
            cls.project_id, cls.collection_id, cls.depositor
        )
        subprocess.check_call(open_acl, shell=True)

        cls.edit_metadata_instance()
        cls.edit_metadata_schema()
        cls.update_avu()

        metadata_snapshot = '/rules/tests/run_test.sh -r create_collection_metadata_snapshot -a "{},{}" -u {}'.format(
            cls.project_id, cls.collection_id, cls.depositor
        )
        pid_request_status = subprocess.check_output(metadata_snapshot, shell=True).strip()
        assert pid_request_status == "true"

        # setCollectionSize is also called in set_acl_for_metadata_snapshot but in a delay queue
        # to avoid using a sleep call, we execute it synchronously to have the updated value during the test.
        set_size = "irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/setCollectionSize.r \"*project='{}'\" \"*projectCollection='{}'\" \"*openPC='false'\" \"*closePC='false'\"".format(
            cls.project_id, cls.collection_id
        )
        subprocess.check_call(set_size, shell=True)

        close_acl = '/rules/tests/run_test.sh -r set_acl_for_metadata_snapshot -a "{},{},{},false,true"'.format(
            cls.project_id, cls.collection_id, cls.depositor
        )
        subprocess.check_call(close_acl, shell=True)

    @classmethod
    def edit_metadata_instance(cls):
        pass

    @classmethod
    def edit_metadata_schema(cls):
        pass

    @classmethod
    def update_avu(cls):
        set_collection_avu(cls.project_collection_path, "schemaVersion", cls.schema_version)
        set_collection_avu(cls.project_collection_path, "schemaName", cls.schema_name)
        set_collection_avu(cls.project_collection_path, "title", cls.new_collection_title)

    # endregion

    # region default tests

    def test_collection_avu(self):
        rule_collection_detail = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(
            self.project_id, self.collection_id
        )
        ret_collection_detail = subprocess.check_output(rule_collection_detail, shell=True)
        collection_detail = json.loads(ret_collection_detail)
        assert collection_detail["creator"] == self.collection_creator
        assert collection_detail["collection"] == self.collection_id
        assert collection_detail["title"] == self.new_collection_title
        assert self.manager1 in collection_detail["managers"]["users"]
        assert self.manager2 in collection_detail["managers"]["users"]

        run_iquest = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{}' and META_COLL_ATTR_NAME = 'latest_version_number' \"".format(
            self.project_collection_path
        )
        latest_version_number = subprocess.check_output(run_iquest, shell=True).strip()
        assert latest_version_number.isdigit()
        assert int(latest_version_number) == 2

        assert int(collection_detail["numFiles"]) == self.num_files
        assert int(collection_detail["byteSize"]) == self.byte_size

    def test_collection_metadata_version_folder(self):
        metadata_versions_path = formatters.format_metadata_versions_path(self.project_id, self.collection_id)
        for version in [1, 2]:
            instance_path = "{}/instance.{}.json".format(metadata_versions_path, version)
            assert does_path_exist(instance_path)

            schema_path = "{}/schema.{}.json".format(metadata_versions_path, version)
            assert does_path_exist(schema_path)

    # endregion
