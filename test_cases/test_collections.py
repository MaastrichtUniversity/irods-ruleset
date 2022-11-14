import json
import subprocess

from dhpythonirodsutils import formatters

from test_cases.utils import (
    create_dropzone,
    create_project,
    start_and_wait_for_ingest,
    add_metadata_files_to_direct_dropzone,
    remove_project,
    revert_latest_project_number,
)


class TestCollections:
    project_path = "/nlmumc/projects/P000000028"
    project_id = "P000000028"
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

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title_base = "collection_title"
    collection_id = "C000000001"
    project_collection_path = ""

    number_of_collections = 3

    @classmethod
    def setup_class(cls):
        print()
        print("Start {}.setup_class".format(cls.__name__))
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        for collection_index in range(cls.number_of_collections):
            cls.collection_title = "{}{}".format(cls.collection_title_base, collection_index)
            cls.token = create_dropzone(cls)
            add_metadata_files_to_direct_dropzone(cls.token)
            start_and_wait_for_ingest(cls)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print()
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        revert_latest_project_number()
        print("End {}.teardown_class".format(cls.__name__))

    def test_list_collections(self):
        rule_list_collections = '/rules/tests/run_test.sh -r list_collections -a "{}"'.format(self.project_path)
        ret_list_collections = subprocess.check_output(rule_list_collections, shell=True)
        list_collections = json.loads(ret_list_collections)

        assert len(list_collections) == self.number_of_collections

        for collection_index in range(self.number_of_collections):
            assert list_collections[collection_index]["title"] == self.collection_title_base + str(collection_index)
            assert list_collections[collection_index]["creator"] == "jonathan.melius@maastrichtuniversity.nl"
            assert list_collections[collection_index]["numUserFiles"] == 0
            assert list_collections[collection_index]["numFiles"] == 4
            assert list_collections[collection_index]["size"] == 550514.0
            collection_id = self.collection_id[:-1] + str(collection_index + 1)
            assert list_collections[collection_index]["id"] == collection_id
            pid_suffix = "{}{}".format(self.project_id, collection_id)
            assert list_collections[collection_index]["PID"].endswith(pid_suffix)

    def test_collection_details(self):
        rule = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(
            self.project_id, self.collection_id
        )
        ret = subprocess.check_output(rule, shell=True)
        collection_detail = json.loads(ret)

        assert collection_detail["project"] == self.project_id
        assert collection_detail["collection"] == self.collection_id
        assert collection_detail["creator"] == self.collection_creator
        assert collection_detail["title"] == self.collection_title_base + "0"
        assert collection_detail["enableArchive"] == "false"
        assert collection_detail["enableUnarchive"] == "false"
        assert collection_detail["enableOpenAccessExport"] == "false"
        assert collection_detail["externals"] == "no-externalPID-set"
        assert collection_detail["exporterState"] == "no-state-set"

        assert int(collection_detail["numFiles"]) == 4
        assert int(collection_detail["byteSize"]) == 550514

        assert self.manager1 in collection_detail["managers"]["users"]
        assert self.manager2 in collection_detail["managers"]["users"]

        assert "service-pid" in collection_detail["contributors"]["users"]
        assert "service-disqover" in collection_detail["viewers"]["users"]

        assert not collection_detail["managers"]["groups"] and not collection_detail["managers"]["groupObjects"]
        assert not collection_detail["contributors"]["groups"] and not collection_detail["contributors"]["groupObjects"]
        assert not collection_detail["viewers"]["groups"] and not collection_detail["viewers"]["groupObjects"]

        assert collection_detail["managers"]["userObjects"][0]["userId"].isnumeric()
        assert collection_detail["contributors"]["userObjects"][0]["userId"].isnumeric()
        assert collection_detail["viewers"]["userObjects"][0]["userId"].isnumeric()

    def test_collection_tree(self):
        project_collection_path = "{}/{}".format(self.project_id, self.collection_id)
        rule = '/rules/tests/run_test.sh -r get_collection_tree -a "{}"'.format(project_collection_path)
        ret = subprocess.check_output(rule, shell=True)
        collection_tree = json.loads(ret)
        assert len(collection_tree) == 5

    def test_set_acl(self):
        collection_path = "/nlmumc/home/jmelius"
        user_to_check = "auser"
        acl = "ils -A {}".format(collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:own".format(user_to_check) not in ret_acl

        rule = '/rules/tests/run_test.sh -r set_acl -a "default,admin:own,{},{}"'.format(
            user_to_check, collection_path
        )
        subprocess.check_call(rule, shell=True)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:own".format(user_to_check) in ret_acl

        rule = '/rules/tests/run_test.sh -r set_acl -a "default,admin:null,{},{}"'.format(
            user_to_check, collection_path
        )
        subprocess.check_call(rule, shell=True)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:own".format(user_to_check) not in ret_acl

    def test_collection_size_per_resource(self):
        rule = '/rules/tests/run_test.sh -r get_collection_size_per_resource -a "{}"'.format(self.project_id)
        ret = subprocess.check_output(rule, shell=True)
        list_collections = json.loads(ret)

        assert len(list_collections) == self.number_of_collections

        for collection_index in range(self.number_of_collections):
            collection_id = self.collection_id[:-1] + str(collection_index + 1)
            assert list_collections[collection_id][0]["relativeSize"] == 100.0
            assert list_collections[collection_id][0]["resourceId"].isnumeric()
            assert list_collections[collection_id][0]["resourceName"] == self.destination_resource
            assert list_collections[collection_id][0]["size"] == "550514"

    def test_project_collection_acl_open_close_state(self):
        project_collection_path = formatters.format_project_collection_path(self.project_id, self.collection_id)
        user_to_check = "rods"
        acl = "ils -A {}".format(project_collection_path)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:own".format(user_to_check) not in ret_acl

        rule_open = 'irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/projectCollection/openProjectCollection.r "*project=\'{}\'" "*projectCollection=\'{}\'" "*user=\'{}\'" "*rights=\'own\'"'.format(
            self.project_id, self.collection_id, user_to_check
        )
        subprocess.check_call(rule_open, shell=True)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:own".format(user_to_check) in ret_acl

        rule_close = 'irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/projectCollection/closeProjectCollection.r "*project=\'{}\'" "*projectCollection=\'{}\'" '.format(
            self.project_id, self.collection_id
        )
        subprocess.check_call(rule_close, shell=True)
        ret_acl = subprocess.check_output(acl, shell=True)
        assert "{}#nlmumc:own".format(user_to_check) not in ret_acl
