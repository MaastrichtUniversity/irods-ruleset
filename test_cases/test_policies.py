import json
import subprocess
import pytest

from test_cases.utils import (
    TMP_INSTANCE_PATH,
    get_instance,
    remove_project,
    revert_latest_project_number,
    remove_dropzone,
    create_project,
    create_dropzone,
    add_metadata_files_to_direct_dropzone,
)


class TestPolicies:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = "iresResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"

    dropzone_type = "direct"
    token = ""

    collection_title = "collection_title"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def setup_class(cls):
        print("Start {}.setup_class".format(cls.__name__))
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        set_project_acl_to_dropzone = "/rules/tests/run_test.sh -r set_project_acl_to_dropzone -a \"{},{},true\"".format(cls.project_id, cls.token)
        subprocess.check_call(set_project_acl_to_dropzone, shell=True)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        remove_dropzone(cls.token, cls.dropzone_type)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    def test_post_proc_for_coll_create(self):
        run_iquest = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '/nlmumc/projects' and META_COLL_ATTR_NAME = 'latest_project_number' \""
        current_value = subprocess.check_output(run_iquest, shell=True).strip()
        project = create_project(self)
        new_value = subprocess.check_output(run_iquest, shell=True).strip()
        assert int(current_value) + 1 == int(new_value)
        remove_project(project["project_path"])
        revert_latest_project_number()

    def test_post_proc_for_modify_avu_metadata(self):
        run_ils = "ils -A /nlmumc/ingest/direct/{}".format(self.token)
        first_ils_output = subprocess.check_output(run_ils, shell=True)
        assert manager2 in first_ils_output
        set_enable_sharing = "imeta set -C /nlmumc/projects/{project_id} enableDropzoneSharing {{value}}".format(project_id=self.project_id)
        subprocess.check_call(set_enable_sharing.format(value="false"), shell=True)
        second_ils_output = subprocess.check_output(run_ils, shell=True)
        assert manager2 not in second_ils_output
        subprocess.check_call(set_enable_sharing.format(value="true"), shell=True)
        third_ils_output = subprocess.check_output(run_ils, shell=True)
        assert manager2 in third_ils_output

    def test_post_proc_for_modify_access_control(self):
        change_user_access_to_project = "ichmod -M {{access}} dlinssen /nlmumc/projects/{project_id}".format(project_id=self.project_id)
        run_ils = "ils -A /nlmumc/ingest/direct/{}".format(self.token)
        first_ils_output = subprocess.check_output(run_ils, shell=True)
        assert "dlinssen" not in first_ils_output
        subprocess.check_call(change_user_access_to_project.format(access="own"), shell=True)
        second_ils_output = subprocess.check_output(run_ils, shell=True)
        assert "dlinssen" in second_ils_output
        subprocess.check_call(change_user_access_to_project.format(access="null"), shell=True)
        third_ils_output = subprocess.check_output(run_ils, shell=True)
        assert "dlinssen" not in third_ils_output

    def test_post_proc_for_put(self):
        collection_path = "/nlmumc/projects/{}/C000000001".format(self.project_id)
        create_collection = "imkdir {}".format(collection_path)
        subprocess.check_call(create_collection, shell=True)
        get_instance()
        put_instance = "iput -R {} {} {}/instance.json".format(self.destination_resource, TMP_INSTANCE_PATH, collection_path)
        subprocess.check_call(put_instance, shell=True)
        get_size_ingested = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{}' and META_COLL_ATTR_NAME = 'sizeIngested' \"".format(collection_path)
        size_ingested = subprocess.check_output(get_size_ingested, shell=True)
        assert int(size_ingested) == 12521
        run_ils = "ils -A /nlmumc/ingest/direct/{}/instance.json".format(self.token)
        ils_output = subprocess.check_output(run_ils, shell=True)
        assert "{}#nlmumc:read".format(manager1) in ils_output
        assert "{}#nlmumc:own".format(manager1) not in ils_output

    def test_pre_proc_for_modify_avu_metadata(self):
        check = "export clientUserName={} && imeta {} -C /nlmumc/projects/{} enableArchive false"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(check.format("service-pid", "set", self.project_id), shell=True)
        subprocess.check_call(check.format(self.manager1, "set", self.project_id), shell=True)

    def test_ac_pre_proc_for_coll_create(self):
        assert 1 == 1
