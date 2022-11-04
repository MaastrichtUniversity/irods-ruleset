import json
import subprocess

from test_cases.utils import (
    revert_latest_project_number,
    remove_project,
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
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

        cls.edit_collection_metadata()

        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    @classmethod
    def edit_collection_metadata(cls):
        """
        TODO Replicate save_metadata_json_to_collection
        set_acl_for_metadata_snapshot

        save_metadata_json_to_collection
                metadata_json.write_instance(instance, instance_irods_path)
                    self.session.data_objects.put(instance_path, instance_irods_path)

                metadata_json.write_schema(schema_dict["schema_path"], schema_irods_path)
                    self.session.data_objects.put(schema_path, schema_irods_path)

                self.set_collection_avu(collection_path, "schemaVersion", schema_dict["schema_version"])
                self.set_collection_avu(collection_path, "schemaName", schema_dict["schema_file_name"])
                self.set_collection_avu(collection_path, "title", schema_dict["title"])

                pid_request_status = self.create_collection_metadata_snapshot(project_id, collection_id)
        """