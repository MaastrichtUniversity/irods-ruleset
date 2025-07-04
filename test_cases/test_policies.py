import subprocess
import pytest
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs

from test_cases.utils import (
    TMP_INSTANCE_PATH,
    get_instance,
    remove_project,
    remove_dropzone,
    create_project,
    create_dropzone,
    add_metadata_files_to_direct_dropzone,
    create_user,
    remove_user,
    revert_latest_project_collection_number,
)


class TestPolicies:
    project_path = ""
    project_id = ""
    project_title = "PROJECTNAME"

    depositor = "jmelius"
    manager1 = depositor
    manager2 = "opalmen"

    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"
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
        set_project_acl_to_dropzone = '/rules/tests/run_test.sh -r set_project_acl_to_dropzone -a "{},{},true"'.format(
            cls.project_id, cls.token
        )
        subprocess.check_call(set_project_acl_to_dropzone, shell=True)
        print("End {}.setup_class".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("Start {}.teardown_class".format(cls.__name__))
        remove_project(cls.project_path)
        remove_dropzone(cls.token, cls.dropzone_type)
        print("End {}.teardown_class".format(cls.__name__))

    def test_post_proc_for_coll_create(self):
        """
        This tests whether the 'latest_project_number' and 'latestProjectCollectionNumber' are properly incremented
        when creating a project and a project collection.
        """
        # Project
        run_iquest = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '/nlmumc/projects' and META_COLL_ATTR_NAME = 'latest_project_number' \""
        current_value = subprocess.check_output(run_iquest, shell=True).strip()
        project = create_project(self)
        new_value = subprocess.check_output(run_iquest, shell=True).strip()
        assert int(current_value) + 1 == int(new_value)

        # Project collection
        run_iquest = (
            'iquest "%s" "SELECT META_COLL_ATTR_VALUE '
            "WHERE COLL_NAME = '{}' and META_COLL_ATTR_NAME = '{}' \"".format(
                project["project_path"],
                ProjectAVUs.LATEST_PROJECT_COLLECTION_NUMBER.value,
            )
        )
        current_value = subprocess.check_output(run_iquest, shell=True).strip()
        collection_path = formatters.format_project_collection_path(
            project["project_id"], "C000000001"
        )
        create_collection = "imkdir {}".format(collection_path)
        subprocess.check_call(create_collection, shell=True)
        new_value = subprocess.check_output(run_iquest, shell=True).strip()
        assert int(current_value) + 1 == int(new_value)

        # teardown
        remove_project(project["project_path"])

    def test_post_proc_for_modify_avu_metadata(self):
        """This tests whether toggling the 'enableDropzoneSharing' AVU sets properly the ACLs on the dropzones of the changed project"""
        run_ils = "ils -A /nlmumc/ingest/direct/{}".format(self.token)
        first_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert self.manager2 in first_ils_output
        set_enable_sharing = "imeta set -C /nlmumc/projects/{project_id} enableDropzoneSharing {{value}}".format(
            project_id=self.project_id
        )
        subprocess.check_call(set_enable_sharing.format(value="false"), shell=True)
        second_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert self.manager2 not in second_ils_output
        subprocess.check_call(set_enable_sharing.format(value="true"), shell=True)
        third_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert self.manager2 in third_ils_output

    def test_post_proc_for_modify_access_control(self):
        """This tests whether adding a user to a project properly adds the users ACLS to the projects direct dropzones"""
        change_user_access_to_project = (
            "ichmod -M {{access}} dlinssen /nlmumc/projects/{project_id}".format(
                project_id=self.project_id
            )
        )
        run_ils = "ils -A /nlmumc/ingest/direct/{}".format(self.token)
        first_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert "dlinssen" not in first_ils_output
        subprocess.check_call(
            change_user_access_to_project.format(access="own"), shell=True
        )
        second_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert "dlinssen" in second_ils_output
        subprocess.check_call(
            change_user_access_to_project.format(access="null"), shell=True
        )
        third_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert "dlinssen" not in third_ils_output

# DHDO-1731: This test is commented out for now. The progress bar is broken for ingests towards UM-HNAS
# due to a bug in iRODS. For replnum = 0, the pep does not have the dataSize information, and is not able to increment
# properly because of this.
    # def test_pep_api_data_obj_put_post(self):
    #     """
    #     This tests whether the sizeIngested AVU is properly incremented when a file in ingested.
    #     Also check the metadata files have the correct ACL for the dropzone creator
    #     """
    #     # Setup
    #     collection_path = "/nlmumc/projects/{}/C000000001".format(self.project_id)
    #     create_collection = "imkdir {}".format(collection_path)
    #     subprocess.check_call(create_collection, shell=True)
    #     get_instance()
    #     put_instance = "iput -R {} {} {}/instance.json".format(
    #         self.destination_resource, TMP_INSTANCE_PATH, collection_path
    #     )
    #     subprocess.check_call(put_instance, shell=True)
    #     # The policy assumes 3 replicas for direct ingest sizeIngested to be triggered (0-stagingresc, 1 and 2).
    #     # Therefor an extra replica on rootResc is created
    #     repl_instance = "irepl -R {} {}/instance.json".format(
    #         "rootResc", collection_path
    #     )
    #     subprocess.check_call(repl_instance, shell=True)
    #     # Test sizeIngested AVU
    #     get_size_ingested = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{}' and META_COLL_ATTR_NAME = 'sizeIngested' \"".format(
    #         collection_path
    #     )
    #     size_ingested = subprocess.check_output(
    #         get_size_ingested, shell=True, encoding="UTF-8"
    #     ).rstrip("\n")
    #     assert int(size_ingested) == 12521
    #     # Test metadata file ACL
    #     run_ils = "ils -A /nlmumc/ingest/direct/{}/instance.json".format(self.token)
    #     ils_output = subprocess.check_output(run_ils, shell=True, encoding="UTF-8")
    #     assert "{}#nlmumc:read".format(self.manager1) in ils_output
    #     assert "{}#nlmumc:own".format(self.manager1) not in ils_output
    #     # teardown
    #     subprocess.check_call("irm -rf {}".format(collection_path), shell=True)
    #     revert_latest_project_collection_number(self.project_path)

    def test_pre_proc_for_modify_avu_metadata(self):
        """This tests if a regular contributor is allowed to modify certain project AVUs (they should not be)"""
        # Setup: Add a non-admin manager to the project
        test_manager = "policy_test_manager"
        create_user(test_manager)
        mod_acl = "ichmod own {} /nlmumc/projects/{}".format(
            test_manager, self.project_id
        )
        subprocess.check_call(mod_acl, shell=True)

        financial_manager = self.manager1
        contributor = "service-pid"
        check = "export clientUserName={} && imeta set -C /nlmumc/projects/{} {} false"

        # Financial => Only Principal Investigator or Data steward
        financial_avu_to_check = "responsibleCostCenter"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(
                check.format(contributor, self.project_id, financial_avu_to_check),
                shell=True,
            )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(
                check.format(test_manager, self.project_id, financial_avu_to_check),
                shell=True,
            )
        subprocess.check_call(
            check.format(financial_manager, self.project_id, financial_avu_to_check),
            shell=True,
        )

        # Project settings => only project managers, Principal Investigator or Data steward
        list_project_setting_avu_to_check = [
            "enableArchive",
            "enableUnarchive",
            "collectionMetadataSchemas",
            "enableContributorEditMetadata",
            # "enableDropzoneSharing", triggers acPostProcForModifyAVUMetadata
            "description",
        ]
        for avu in list_project_setting_avu_to_check:
            with pytest.raises(subprocess.CalledProcessError) as e_info:
                subprocess.check_call(
                    check.format(contributor, self.project_id, avu), shell=True
                )
            subprocess.check_call(
                check.format(test_manager, self.project_id, avu), shell=True
            )
            subprocess.check_call(
                check.format(
                    financial_manager, self.project_id, financial_avu_to_check
                ),
                shell=True,
            )

        # teardown
        remove_user(test_manager)

    def test_pre_proc_for_coll_create_first(self):
        """This tests if a user is allowed to make a dir in a direct dropzone that is already ingesting (they should not be)"""
        set_dropzone_state = (
            "imeta -M set -C /nlmumc/ingest/direct/{token} state {{state}}".format(
                token=self.token
            )
        )
        subprocess.check_call(set_dropzone_state.format(state="ingesting"), shell=True)
        create_coll_when_ingesting = (
            "export clientUserName={} && imkdir /nlmumc/ingest/direct/{}/foobar".format(
                self.manager1, self.token
            )
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(create_coll_when_ingesting, shell=True)
        subprocess.check_call(set_dropzone_state.format(state="open"), shell=True)

    def test_pre_proc_for_coll_create_second(self):
        """This tests if a user is allowed to create the .metadata_versions directory in a direct dropzone (they should not be)"""
        metadata_versions = "export clientUserName={} && imkdir /nlmumc/ingest/direct/{}/.metadata_versions".format(
            self.manager1, self.token
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(metadata_versions, shell=True)

    def test_pre_proc_for_coll_create_third(self):
        """Check if a regular user is allowed to create a directory in the direct dropzones folder (they should not be)"""
        direct_dropzone = (
            "export clientUserName=service-pid && imkdir /nlmumc/ingest/direct/foo-bar"
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(direct_dropzone, shell=True)

    def test_pre_proc_for_coll_create_fourth(self):
        """Test if you can create a directory that does not follow our project standard format (you should not)"""
        wrong_collection = "imkdir /nlmumc/projects/{}/foobar".format(self.project_id)
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(wrong_collection, shell=True)

    def test_pre_proc_for_data_obj_open(self):
        """Test if an iget of a file that is on tape does not work"""
        put_file_on_tape = "export clientUserName={0} && iput -fR arcRescSURF01 {1} /nlmumc/home/{0}/instance.json".format(
            self.manager1, TMP_INSTANCE_PATH
        )
        get_file_from_tape = (
            "export clientUserName={0} && iget /nlmumc/home/{0}/instance.json".format(
                self.manager1
            )
        )
        subprocess.check_call(put_file_on_tape, shell=True)
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(get_file_from_tape, shell=True)
        subprocess.check_call(
            "export clientUserName={0} && irm -rf /nlmumc/home/{0}/instance.json".format(
                self.manager1
            ),
            shell=True,
        )

    def test_set_resc_scheme_for_create_first(self):
        """Test if a file that is put in a project collection is put on the correct resource"""
        collection_path = "/nlmumc/projects/{}/C000000001".format(self.project_id)
        create_collection = "imkdir {}".format(collection_path)
        subprocess.check_call(create_collection, shell=True)
        get_instance()
        put_instance = "export clientUserName={} && iput {} {}/instance.json".format(
            self.manager1, TMP_INSTANCE_PATH, collection_path
        )
        subprocess.check_call(put_instance, shell=True)
        check_resource = "ils -l {}/instance.json".format(collection_path)
        output = subprocess.check_output(check_resource, shell=True, encoding="UTF-8")
        assert self.destination_resource in output
        # teardown
        subprocess.check_call("irm -rf {}".format(collection_path), shell=True)
        revert_latest_project_collection_number(self.project_path)

    def test_set_resc_scheme_for_create_second(self):
        """Test if a file put directly in a project is properly blocked"""
        get_instance()
        put_instance = "export clientUserName={} && iput {} /nlmumc/projects/{}/instance.json".format(
            self.manager1, TMP_INSTANCE_PATH, self.project_id
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(put_instance, shell=True)

    def test_set_resc_scheme_for_create_third(self):
        """Test if a file put directly in the direct dropzone dir is properly blocked and if files put in a direct dropzone have the correct resource"""
        get_instance()
        put_instance = "export clientUserName={user} && iput {instance} /nlmumc/ingest/direct/{{path}}instance_test_3.json".format(
            user=self.manager1, instance=TMP_INSTANCE_PATH
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(put_instance.format(path=""), shell=True)
        subprocess.check_call(put_instance.format(path=self.token + "/"), shell=True)
        output_ils = subprocess.check_output(
            "ils -l /nlmumc/ingest/direct/{}/instance_test_3.json".format(self.token),
            shell=True,
            encoding="UTF-8",
        )
        assert "stagingResc01" in output_ils
        subprocess.check_call(
            "export clientUserName={user} && irm -f /nlmumc/ingest/direct/{{token}}/instance_test_3.json".format(
                user=self.manager1, token=self.token
            ),
            shell=True,
        )

    def test_set_resc_scheme_for_create_fourth(self):
        """Test if a file put directly in the mounted dropzone dir is properly blocked and if files put in a mounted dropzone have the correct resource"""
        get_instance()
        self.dropzone_type = "mounted"
        token = create_dropzone(self)
        put_instance = "export clientUserName={user} && iput {instance} /nlmumc/ingest/zones/{{path}}instance_test_3.json".format(
            user=self.manager1, instance=TMP_INSTANCE_PATH
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(put_instance.format(path=""), shell=True)
        subprocess.check_call(put_instance.format(path=token + "/"), shell=True)
        output_ils = subprocess.check_output(
            "ils -l /nlmumc/ingest/zones/{}/instance_test_3.json".format(token),
            shell=True,
            encoding="UTF-8",
        )
        assert "stagingResc01" in output_ils

        # clean up
        subprocess.check_call(
            "irm -f /nlmumc/ingest/zones/{}/instance_test_3.json".format(token),
            shell=True,
        )
        remove_dropzone(token, "mounted")
        self.dropzone_type = "direct"

    def test_set_resc_scheme_for_create_fifth(self):
        """Test if a file put in a direct dropzone when it is ingesting is properly blocked"""
        set_dropzone_state = (
            "imeta -M set -C /nlmumc/ingest/direct/{token} state {{state}}".format(
                token=self.token
            )
        )
        subprocess.check_call(set_dropzone_state.format(state="ingesting"), shell=True)
        put_instance = "export clientUserName={} && iput {} /nlmumc/ingest/direct/{}/instance_test_3.json".format(
            self.manager1, TMP_INSTANCE_PATH, self.token
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(put_instance, shell=True)
        subprocess.check_call(set_dropzone_state.format(state="open"), shell=True)
