import json
import subprocess
import time


class TestDirectIngest:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = "iresResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"

    dropzone_type = "direct"

    collection_creator = "jonathan.melius@maastrichtuniversity.nl"
    collection_title = "collection_title"
    collection_id = "C000000001"

    @classmethod
    def setup_class(cls):
        print("")
        print("Start TestMountedIngest.setup_class")

        rule_create_new_project = '/rules/tests/run_test.sh -r create_new_project -a "{},{},{},{},{},{},{{\'enableDropzoneSharing\':\'true\'}}"'.format(
                                    cls.ingest_resource,
                                    cls.destination_resource,
                                    cls.project_title,
                                    cls.manager1,
                                    cls.manager2,
                                    cls.budget_number
        )
        ret_create_new_project = subprocess.check_output(rule_create_new_project, shell=True)

        project = json.loads(ret_create_new_project)
        # TODO Validate Project id format
        assert project['project_id'] is not None
        cls.project_path = project['project_path']
        cls.project_id = project['project_id']

        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(cls.manager1, project['project_path'])
        subprocess.check_call(rule_set_acl, shell=True)
        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(cls.manager2, project['project_path'])
        subprocess.check_call(rule_set_acl, shell=True)

        rule_create_drop_zone = '/rules/tests/run_test.sh -r create_drop_zone -a "{},{},{},{},DataHub_general_schema,1.0.0"'.format(cls.dropzone_type, cls.depositor, project['project_id'], cls.collection_title)
        ret_create_drop_zone = subprocess.check_output(rule_create_drop_zone, shell=True)
        token = json.loads(ret_create_drop_zone)

        # TODO improve how to retrieve instance.json & schema.json
        iput_instance = "iput -R stagingResc01 instance.json /nlmumc/ingest/direct/{}".format(token)
        subprocess.check_call(iput_instance, shell=True)

        iput_schema = "iput -R stagingResc01 schema.json /nlmumc/ingest/direct/{}".format(token)
        subprocess.check_call(iput_schema, shell=True)

        rule_start_ingest = '/rules/tests/run_test.sh -r start_ingest -a "{},{},{}" -u "{}"'.format(cls.depositor, token, cls.dropzone_type, cls.depositor)
        subprocess.check_call(rule_start_ingest, shell=True)

        rule_get_active_drop_zone = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,{}"'.format(token, cls.dropzone_type)
        ret_get_active_drop_zone = subprocess.check_output(rule_get_active_drop_zone, shell=True)

        drop_zone = json.loads(ret_get_active_drop_zone)
        assert drop_zone['token'] == token

        fail_safe = 10
        while fail_safe != 0:
            ret_get_active_drop_zone = subprocess.check_output(rule_get_active_drop_zone, shell=True)

            drop_zone = json.loads(ret_get_active_drop_zone)
            if drop_zone['state'] == "ingested":
                fail_safe = 0
            else:
                fail_safe = fail_safe - 1
                time.sleep(5)

        print("End TestMountedIngest.setup_class")

    @classmethod
    def teardown_class(cls):
        print("")
        print("Start TestMountedIngest.teardown_class")
        set_acl = 'ichmod -rM own rods {}'.format(cls.project_path)
        subprocess.check_call(set_acl, shell=True)
        remove_project = 'irm -rf {}'.format(cls.project_path)
        subprocess.check_call(remove_project, shell=True)
        # TODO reset latest_project_number increment from acPostProcForCollCreate
        print("End TestMountedIngest.teardown_class")

    def test_collection_avu(self):
        rule_list_collections = '/rules/tests/run_test.sh -r list_collections -a "{}"'.format(self.project_path)
        ret_list_collections = subprocess.check_output(rule_list_collections, shell=True)
        list_collections = json.loads(ret_list_collections)
        assert list_collections[0]['id'] == self.collection_id

        rule_collection_detail = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(self.project_id, self.collection_id)
        ret_collection_detail = subprocess.check_output(rule_collection_detail, shell=True)
        collection_detail = json.loads(ret_collection_detail)
        assert collection_detail['creator'] == self.collection_creator
        assert collection_detail['collection'] == self.collection_id
        assert collection_detail['title'] == self.collection_title
        assert int(collection_detail['numFiles']) == 4
        assert int(collection_detail['byteSize']) == 550514
        assert self.manager1 in collection_detail['managers']["users"]
        assert self.manager2 in collection_detail['managers']["users"]

    def test_collection_instance(self):
        tmp_instance_path = "/tmp/tmp_instance.json"
        iget = 'iget -f {}/{}/instance.json {}'.format(self.project_path, self.collection_id, tmp_instance_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_instance_path) as tmp_instance_file:
            tmp_instance = json.load(tmp_instance_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}instance.1".format(self.project_id, self.collection_id))

    def test_collection_schema(self):
        tmp_schema_path = "/tmp/tmp_schema.json"
        iget = 'iget -f {}/{}/schema.json {}'.format(self.project_path, self.collection_id, tmp_schema_path)
        subprocess.check_call(iget, shell=True)
        with open(tmp_schema_path) as tmp_schema_file:
            tmp_instance = json.load(tmp_schema_file)
            pid = tmp_instance["@id"]
            assert pid.startswith("https://hdl.handle.net/")
            assert pid.endswith("{}{}schema.1".format(self.project_id, self.collection_id))

    def test_collection_acl(self):
        """
        Check the project collection acl; assume that all members only have read access.
        """
        acl = 'ils -A {}/{}'.format(self.project_path, self.collection_id)
        ret = subprocess.check_output(acl, shell=True)
        assert "own" not in ret
        assert "{}#nlmumc:read object".format(self.manager1) in ret
        assert "{}#nlmumc:read object".format(self.manager2) in ret

    def test_project_acl(self):
        acl = 'ils -A {}'.format(self.project_path, self.collection_id)
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own".format(self.manager1) in ret
        assert "{}#nlmumc:own".format(self.manager1) in ret
        assert "{}#nlmumc:own".format(self.manager2) in ret

    # def test_collection_pid(self):
    #     # TODO Cannot resolve PID inside iRODS container?
    #     rule = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(self.project_id,
    #                                                                                           self.collection_id)
    #     ret = subprocess.check_output(rule, shell=True)
    #     collection_detail = json.loads(ret)
    #     print (json.dumps(collection_detail, indent=4, sort_keys=True))
    #     print (collection_detail['PID'])
    #     url = "https://hdl.handle.net/{}".format(collection_detail['PID'])
    #     print (url)
    #     response = requests.get(url)
    #     assert response.status_code == 200

    def test_collection_data_resource(self):
        """
        Check the data object that are in the project collection use the correct project destination resource.
        """
        query = 'iquest --no-page "%s" "SELECT DATA_RESC_HIER WHERE COLL_PARENT_NAME = \'{}/{}\'"'.format(self.project_path, self.collection_id)
        ret = subprocess.check_output(query, shell=True)
        resources = ret.splitlines()
        assert len(resources) == 2
        assert self.destination_resource in resources[0]
        assert self.destination_resource in resources[1]

    def test_collection_data_replicas(self):
        """
        Check that data objects (instance.json & schema.json) at the root of project collection are correctly replicated
        """
        query = 'iquest --no-page "%s" "SELECT count(DATA_RESC_NAME) WHERE COLL_PARENT_NAME = \'{}/{}\'"'.format(self.project_path, self.collection_id)
        ret = subprocess.check_output(query, shell=True)
        assert int(ret) == 4
