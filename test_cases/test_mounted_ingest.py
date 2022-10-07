import json
import subprocess
import time
import pytest


class TestMountedIngest:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "jmelius"

    ingest_resource = "iresResource"
    destination_resource = "replRescUM01"
    budget_number = "UM-30001234X"

    dropzone_type = "mounted"

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
        ret = subprocess.check_output(rule_create_new_project, shell=True)

        project = json.loads(ret)
        # print (project)
        # TODO Validate Project id format
        assert project['project_id'] is not None
        cls.project_path = project['project_path']
        cls.project_id = project['project_id']
        # print (cls.project_path)

        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(cls.manager1, project['project_path'])
        subprocess.check_call(rule_set_acl, shell=True)
        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(cls.manager2, project['project_path'])
        subprocess.check_call(rule_set_acl, shell=True)

        rule_create_drop_zone = '/rules/tests/run_test.sh -r create_drop_zone -a "{},{},{},{},DataHub_general_schema,1.0.0"'.format(cls.dropzone_type, cls.depositor, project['project_id'], cls.collection_title)
        ret = subprocess.check_output(rule_create_drop_zone, shell=True)
        token = json.loads(ret)
        # print (token)

        copy_instance = 'cp instance.json /mnt/ingest/zones/{}/instance.json'.format(token)
        subprocess.check_call(copy_instance, shell=True)

        copy_schema = 'cp schema.json /mnt/ingest/zones/{}/schema.json'.format(token)
        subprocess.check_call(copy_schema, shell=True)

        rule_start_ingest = '/rules/tests/run_test.sh -r start_ingest -a "{},{},{}" -u "{}"'.format(cls.depositor, token, cls.dropzone_type, cls.depositor)
        subprocess.check_call(rule_start_ingest, shell=True)

        rule_get_active_drop_zone = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,{}"'.format(token, cls.dropzone_type)
        ret = subprocess.check_output(rule_get_active_drop_zone, shell=True)

        drop_zone = json.loads(ret)
        # print (drop_zone)
        # print (drop_zone['state'])
        assert drop_zone['token'] == token

        fail_safe = 5
        while fail_safe != 0:
            ret = subprocess.check_output(rule_get_active_drop_zone, shell=True)

            drop_zone = json.loads(ret)
            # print (drop_zone['state'])
            if drop_zone['state'] == "ingested":
                fail_safe = 0
            else:
                fail_safe = fail_safe - 1
                time.sleep(10)

        print("")
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
        # print(TestMountedIngest.project_path)
        rule = '/rules/tests/run_test.sh -r list_collections -a "{}"'.format(self.project_path)
        ret = subprocess.check_output(rule, shell=True)
        list_collections = json.loads(ret)
        # print (list_collections)
        assert list_collections[0]['creator'] == self.collection_creator
        assert list_collections[0]['id'] == self.collection_id
        assert list_collections[0]['numFiles'] == 4
        assert list_collections[0]['size'] == 550514.0

        rule = '/rules/tests/run_test.sh -r detailsProjectCollection -a "{},{},false"'.format(self.project_id, self.collection_id)
        ret = subprocess.check_output(rule, shell=True)
        collection_detail = json.loads(ret)
        print (json.dumps(collection_detail, indent=4, sort_keys=True))
        # TODO ADD collection_detail tests

    def test_collection_instance(self):
        pytest.fail("Not implemented")

    def test_collection_acl(self):
        pytest.fail("Not implemented")

    def test_project_acl(self):
        pytest.fail("Not implemented")

    def test_collection_pid(self):
        pytest.fail("Not implemented")

    def test_collection_data_resource(self):
        pytest.fail("Not implemented")

    def test_collection_data_replicas(self):
        pytest.fail("Not implemented")
