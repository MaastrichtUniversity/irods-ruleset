import json
import subprocess

from dhpythonirodsutils import validators, formatters


class TestDirectDropZones:
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
        iput_instance = "iput -R stagingResc01 instance.json /nlmumc/ingest/direct/{}/instance.json".format(token)
        subprocess.check_call(iput_instance, shell=True)

        iput_schema = "iput -R stagingResc01 schema.json /nlmumc/ingest/direct/{}/schema.json".format(token)
        subprocess.check_call(iput_schema, shell=True)

    @classmethod
    def setup_class(cls):
        print("")
        print("Start {}.setup_class".format(cls.__name__))

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
        assert validators.validate_project_id(str(project['project_id']))
        assert validators.validate_project_path(project['project_path'])
        cls.project_path = project['project_path']
        cls.project_id = project['project_id']

        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(cls.manager1, project['project_path'])
        subprocess.check_call(rule_set_acl, shell=True)
        rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(cls.manager2, project['project_path'])
        subprocess.check_call(rule_set_acl, shell=True)

        rule_create_drop_zone = '/rules/tests/run_test.sh -r create_drop_zone -a "{},{},{},{},DataHub_general_schema,1.0.0"'.format(
            cls.dropzone_type, cls.depositor, project['project_id'], cls.collection_title, cls.schema_name, cls.schema_version
        )
        ret_create_drop_zone = subprocess.check_output(rule_create_drop_zone, shell=True)
        cls.token = json.loads(ret_create_drop_zone)

        cls.add_metadata_files_to_dropzone(cls.token)

        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("")
        print("Start {}.teardown_class".format(cls.__name__))

        set_project_acl = 'ichmod -rM own rods {}'.format(cls.project_path)
        subprocess.check_call(set_project_acl, shell=True)
        remove_project = 'irm -rf {}'.format(cls.project_path)
        subprocess.check_call(remove_project, shell=True)

        dropzone_path = formatters.format_dropzone_path(cls.token, cls.dropzone_type)
        set_dropzone_acl = 'ichmod -rM own rods {}'.format(dropzone_path)
        subprocess.check_call(set_dropzone_acl, shell=True)
        remove_dropzone = 'irm -rf {}'.format(dropzone_path)
        subprocess.check_call(remove_dropzone, shell=True)

        # TODO reset latest_project_number increment from acPostProcForCollCreate
        print("End {}.teardown_class".format(cls.__name__))

    def test_dropzone_avu(self):
        rule = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,{}"'.format(self.token, self.dropzone_type)
        ret = subprocess.check_output(rule, shell=True)

        drop_zone = json.loads(ret)
        assert drop_zone['creator'] == self.depositor
        assert drop_zone['date'].isnumeric()
        assert drop_zone['enableDropzoneSharing'] == "true"
        assert drop_zone['project'] == self.project_id
        assert drop_zone['projectTitle'] == self.project_title
        assert drop_zone['resourceStatus'] == ""
        assert drop_zone['schemaName'] == self.schema_name
        assert drop_zone['schemaVersion'] == self.schema_version
        assert drop_zone['sharedWithMe'] == "true"
        assert drop_zone['state'] == "open"
        assert drop_zone['title'] == self.collection_title
        assert drop_zone['token'] == self.token
        assert drop_zone['type'] == self.dropzone_type

    def test_calculate_direct_dropzone_size_files(self):
        rule = '/rules/tests/run_test.sh -r calculate_direct_dropzone_size_files -a "{}"'.format(self.token)
        ret = subprocess.check_output(rule, shell=True)

        drop_zone = json.loads(ret)
        assert drop_zone['total_file_count'] == 2
        assert drop_zone['total_file_size'] == 203618

    def test_get_dropzone_files(self):
        rule = '/rules/tests/run_test.sh -r get_dropzone_files -a "{},/"'.format(self.token)
        ret = subprocess.check_output(rule, shell=True)

        drop_zones = json.loads(ret)
        # print(json.dumps(drop_zones, indent=4, sort_keys=True))
        assert len(drop_zones) == 2
        for dz in drop_zones:
            assert dz["type"] == "file"
            assert dz['date'] > 0
            assert dz["size"].isnumeric()
            assert dz["id"] == "/{}".format(dz["value"])

    def test_get_dropzone_folders(self):
        tmp_folder = "foobar"
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        full_path = "{}/{}".format(dropzone_path, tmp_folder)

        run_create_folder = 'imkdir {}'.format(full_path)
        subprocess.check_call(run_create_folder, shell=True)

        rule = '/rules/tests/run_test.sh -r get_dropzone_folders -a "{},"'.format(self.token)
        ret = subprocess.check_output(rule, shell=True)
        drop_zone = json.loads(ret)
        assert len(drop_zone) == 1
        assert len(drop_zone[0]['data']) == 0
        assert drop_zone[0]['full_path'] == full_path
        assert drop_zone[0]['id'] == "/{}".format(tmp_folder)
        assert drop_zone[0]['value'] == tmp_folder
        # print(json.dumps(drop_zone, indent=4, sort_keys=True))

        run_remove_folder = 'irm -fr {}'.format(full_path)
        subprocess.check_call(run_remove_folder, shell=True)

    def test_set_dropzone_total_size_avu(self):
        rule_set_size = '/rules/tests/run_test.sh -r set_dropzone_total_size_avu -a "{},{}"'.format(self.token, self.dropzone_type)
        subprocess.check_call(rule_set_size, shell=True)

        rule = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,{}"'.format(self.token, self.dropzone_type)
        ret = subprocess.check_output(rule, shell=True)

        drop_zone = json.loads(ret)
        assert int(drop_zone['totalSize']) == 203618
        # print(json.dumps(drop_zone, indent=4, sort_keys=True))

    def test_set_project_acl_to_dropzone(self):
        # Run set_project_acl_to_dropzone to give project manager2 own access
        rule_set_acl = '/rules/tests/run_test.sh -r set_project_acl_to_dropzone -a "{},{},false"'.format(
            self.project_id, self.token
        )
        self.check_acl_changes(rule_set_acl, self.manager2)

    def test_set_project_acl_to_dropzones(self):
        # TODO check multiple dropzones
        rule_set_acl = '/rules/tests/run_test.sh -r set_project_acl_to_dropzones -a "{}"'.format(self.project_id)
        self.check_acl_changes(rule_set_acl, self.manager2)

    def test_set_single_user_project_acl_to_dropzones(self):
        # set_single_user_project_acl_to_dropzones is trigger when a project ACL changes in the policy:
        # acPostProcForModifyAccessControl
        user_to_check = "dlinssen"
        change_project_acl = 'ichmod write {} {}'.format(user_to_check, self.project_path)
        self.check_acl_changes(change_project_acl, user_to_check)

    def check_acl_changes(self, rule_set_acl, user_to_check):
        # Check the acl before set_project_acl_to_dropzone
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        acl = 'ils -A {}'.format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}#nlmumc:own".format(user_to_check) not in ret

        rule_drop_zone = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,direct" -u {}'.format(
            self.token, user_to_check
        )
        ret = subprocess.check_output(rule_drop_zone, shell=True)
        assert "status = -310000" in ret

        # Run set_project_acl_to_dropzone(s) to give to the input user own access
        subprocess.check_call(rule_set_acl, shell=True)

        # Check the acl after set_project_acl_to_dropzone
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}#nlmumc:own".format(user_to_check) in ret

        ret = subprocess.check_output(rule_drop_zone, shell=True)
        drop_zone = json.loads(ret)
        assert drop_zone['token'] == self.token

        # Remove the input user from the dropzone ACL
        ichmod = 'ichmod -rM null {} {}'.format(user_to_check, dropzone_path)
        subprocess.check_call(ichmod, shell=True)

        # Check that the input user has no access
        acl = 'ils -A {}'.format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}".format(user_to_check) not in ret

    def test_share_dropzone_avu(self):
        user_to_check = self.manager2
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)

        # Check manager2 has no access
        acl = 'ils -A {}'.format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}".format(user_to_check) not in ret

        # Change project AVU enableDropzoneSharing to give access
        avu_change = 'imeta set -C {} enableDropzoneSharing true'.format(self.project_path)
        subprocess.check_call(avu_change, shell=True)

        # Check manager2 gained access
        acl = 'ils -A {}'.format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}#nlmumc:own".format(user_to_check) in ret

        # Change project AVU enableDropzoneSharing to revoke access
        avu_change = 'imeta set -C {} enableDropzoneSharing false'.format(self.project_path)
        subprocess.check_call(avu_change, shell=True)

        # Check manager2 lost access
        ret = subprocess.check_output(acl, shell=True)
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}".format(user_to_check) not in ret

