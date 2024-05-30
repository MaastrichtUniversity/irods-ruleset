import json
import subprocess
import time

import pytest
from dhpythonirodsutils import formatters

from test_cases.utils import (
    remove_project,
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

    def test_delete_dropzone(self):
        new_token = create_dropzone(self)
        self.add_metadata_files_to_dropzone(new_token)
        dropzone_path = formatters.format_dropzone_path(new_token, self.dropzone_type)

        # Make sure rods has own access
        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "recursive,admin:own,{},{}"'.format(
            "rods", dropzone_path
        )
        subprocess.check_call(rule_set_acl, shell=True)

        # Check that the depositor lost access on the dropzone collection (not all files)
        acl = "ils -A {}".format(dropzone_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        # 3 => dropzone collection, instance.json & schema.json
        assert ret_acl.count(self.depositor) == 3

        rule_remove_acl = '/rules/tests/run_test.sh -r remove_users_dropzone_acl -a "{}"'.format(dropzone_path)
        subprocess.check_call(rule_remove_acl, shell=True)

        ret_acl = subprocess.check_output(acl, shell=True)
        # 2 => instance.json & schema.json
        assert ret_acl.count(self.depositor) == 2

        # Put the dropzone deletion to the queue
        rule_remove_dropzone = (
            "irule -r irods_rule_engine_plugin-irods_rule_language-instance "
            "-F /rules/native_irods_ruleset/ingest/closeDropZone.r \"*token='{}'\"".format(new_token)
        )
        subprocess.check_call(rule_remove_dropzone, shell=True)

        # Check the deletion
        run_iquest = 'iquest "%s" "SELECT COLL_NAME WHERE COLL_NAME = \'{}\' "'.format(dropzone_path)

        fail_safe = 100
        while fail_safe != 0:
            try:
                subprocess.check_output(run_iquest, shell=True)
                fail_safe = fail_safe - 1
                time.sleep(3)
            except subprocess.CalledProcessError:
                fail_safe = 0
        # Starting from 4.2.12:
        # When iquest returns a "CAT_NO_ROWS_FOUND", the exit status code is 1 instead of 0.
        # And therefore, a CalledProcessError is raised.
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output(run_iquest, shell=True)
