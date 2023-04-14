import json
import subprocess

from test_cases.utils import (
    remove_project,
    revert_latest_project_number,
    remove_dropzone,
    create_project,
    create_dropzone,
)


class BaseTestCaseDropZones:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = ""
    token = ""

    collection_title = "collection_title"

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
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        remove_dropzone(cls.token, cls.dropzone_type)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    def test_dropzone_avu(self):
        rule = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,{}"'.format(
            self.token, self.dropzone_type
        )
        ret = subprocess.check_output(rule, shell=True)

        drop_zone = json.loads(ret)
        assert drop_zone["creator"] == self.depositor
        assert drop_zone["date"].isnumeric()
        assert drop_zone["enableDropzoneSharing"] == "true"
        assert drop_zone["project"] == self.project_id
        assert drop_zone["projectTitle"] == self.project_title
        assert drop_zone["resourceStatus"] == ""
        assert drop_zone["schemaName"] == self.schema_name
        assert drop_zone["schemaVersion"] == self.schema_version
        assert drop_zone["sharedWithMe"] == "true"
        assert drop_zone["state"] == "open"
        assert drop_zone["title"] == self.collection_title
        assert drop_zone["token"] == self.token
        assert drop_zone["type"] == self.dropzone_type
