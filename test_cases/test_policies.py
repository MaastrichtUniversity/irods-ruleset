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
        print(f"Start {cls.__name__}.setup_class")
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        cls.token = create_dropzone(cls)
        cls.add_metadata_files_to_dropzone(cls.token)
        set_project_acl_to_dropzone = f'/rules/tests/run_test.sh -r set_project_acl_to_dropzone -a "{cls.project_id},{cls.token},true"'
        subprocess.check_call(set_project_acl_to_dropzone, shell=True)
        print(f"End {cls.__name__}.setup_class")

    @classmethod
    def teardown_class(cls):
        print(f"Start {cls.__name__}.teardown_class")
        remove_project(cls.project_path)
        remove_dropzone(cls.token, cls.dropzone_type)
        print(f"End {cls.__name__}.teardown_class")

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
            f"iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{project['project_path']}' and META_COLL_ATTR_NAME = '{ProjectAVUs.LATEST_PROJECT_COLLECTION_NUMBER.value}' \""
        )
        current_value = subprocess.check_output(run_iquest, shell=True).strip()
        collection_path = formatters.format_project_collection_path(
            project["project_id"], "C000000001"
        )
        create_collection = f"imkdir {collection_path}"
        subprocess.check_call(create_collection, shell=True)
        new_value = subprocess.check_output(run_iquest, shell=True).strip()
        assert int(current_value) + 1 == int(new_value)

        # teardown
        remove_project(project["project_path"])

    def test_post_proc_for_modify_avu_metadata(self):
        """This tests whether toggling the 'enableDropzoneSharing' AVU sets properly the ACLs on the dropzones of the changed project"""
        run_ils = f"ils -A /nlmumc/ingest/direct/{self.token}"
        first_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert self.manager2 in first_ils_output
        subprocess.check_call(
            f"imeta set -C /nlmumc/projects/{self.project_id} enableDropzoneSharing false", shell=True
        )
        second_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert self.manager2 not in second_ils_output
        subprocess.check_call(
            f"imeta set -C /nlmumc/projects/{self.project_id} enableDropzoneSharing true", shell=True
        )
        third_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert self.manager2 in third_ils_output

    def test_post_proc_for_modify_access_control(self):
        """This tests whether adding a user to a project properly adds the users ACLS to the projects direct dropzones"""
        run_ils = f"ils -A /nlmumc/ingest/direct/{self.token}"
        first_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert "dlinssen" not in first_ils_output
        subprocess.check_call(f"ichmod -M own dlinssen /nlmumc/projects/{self.project_id}", shell=True)
        second_ils_output = subprocess.check_output(
            run_ils, shell=True, encoding="UTF-8"
        )
        assert "dlinssen" in second_ils_output
        subprocess.check_call(f"ichmod -M null dlinssen /nlmumc/projects/{self.project_id}", shell=True)
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
    #     collection_path = f"/nlmumc/projects/{self.project_id}/C000000001"
    #     create_collection = f"imkdir {collection_path}"
    #     subprocess.check_call(create_collection, shell=True)
    #     get_instance()
    #     put_instance = f"iput -R {self.destination_resource} {TMP_INSTANCE_PATH} {collection_path}/instance.json"
    #     subprocess.check_call(put_instance, shell=True)
    #     # The policy assumes 3 replicas for direct ingest sizeIngested to be triggered (0-stagingresc, 1 and 2).
    #     # Therefor an extra replica on rootResc is created
    #     repl_instance = f"irepl -R rootResc {collection_path}/instance.json"
    #     subprocess.check_call(repl_instance, shell=True)
    #     # Test sizeIngested AVU
    #     get_size_ingested = f"iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{collection_path}' and META_COLL_ATTR_NAME = 'sizeIngested' \""
    #     size_ingested = subprocess.check_output(
    #         get_size_ingested, shell=True, encoding="UTF-8"
    #     ).rstrip("\n")
    #     assert int(size_ingested) == 12521
    #     # Test metadata file ACL
    #     run_ils = f"ils -A /nlmumc/ingest/direct/{self.token}/instance.json"
    #     ils_output = subprocess.check_output(run_ils, shell=True, encoding="UTF-8")
    #     assert f"{self.manager1}#nlmumc:read" in ils_output
    #     assert f"{self.manager1}#nlmumc:own" not in ils_output
    #     # teardown
    #     subprocess.check_call(f"irm -rf {collection_path}", shell=True)
    #     revert_latest_project_collection_number(self.project_path)

    def test_pre_proc_for_modify_avu_metadata(self):
        """This tests if a regular contributor is allowed to modify certain project AVUs (they should not be)"""
        # Setup: Add a non-admin manager to the project
        test_manager = "policy_test_manager"
        create_user(test_manager)
        mod_acl = f"ichmod own {test_manager} /nlmumc/projects/{self.project_id}"
        subprocess.check_call(mod_acl, shell=True)

        financial_manager = self.manager1
        contributor = "service-pid"
        def check(user, project_id, avu):
            return f"export clientUserName={user} && imeta set -C /nlmumc/projects/{project_id} {avu} false"

        # Financial => Only Principal Investigator or Data steward
        financial_avu_to_check = "responsibleCostCenter"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(
                check(contributor, self.project_id, financial_avu_to_check),
                shell=True,
            )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(
                check(test_manager, self.project_id, financial_avu_to_check),
                shell=True,
            )
        subprocess.check_call(
            check(financial_manager, self.project_id, financial_avu_to_check),
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
                    check(contributor, self.project_id, avu), shell=True
                )
            subprocess.check_call(
                check(test_manager, self.project_id, avu), shell=True
            )
            subprocess.check_call(
                check(
                    financial_manager, self.project_id, financial_avu_to_check
                ),
                shell=True,
            )

        # teardown
        remove_user(test_manager)

    def test_pre_proc_for_coll_create_first(self):
        """This tests if a user is allowed to make a dir in a direct dropzone that is already ingesting (they should not be)"""
        subprocess.check_call(f"imeta -M set -C /nlmumc/ingest/direct/{self.token} state ingesting", shell=True)
        create_coll_when_ingesting = (
            f"export clientUserName={self.manager1} && imkdir /nlmumc/ingest/direct/{self.token}/foobar"
        )
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(create_coll_when_ingesting, shell=True)
        subprocess.check_call(f"imeta -M set -C /nlmumc/ingest/direct/{self.token} state open", shell=True)

    def test_pre_proc_for_coll_create_second(self):
        """This tests if a user is allowed to create the .metadata_versions directory in a direct dropzone (they should not be)"""
        metadata_versions = f"export clientUserName={self.manager1} && imkdir /nlmumc/ingest/direct/{self.token}/.metadata_versions"
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
        wrong_collection = f"imkdir /nlmumc/projects/{self.project_id}/foobar"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(wrong_collection, shell=True)

    def test_pre_proc_for_data_obj_open(self):
        """Test if an iget of a file that is on tape does not work"""
        put_file_on_tape = f"export clientUserName={self.manager1} && iput -fR arcRescSURF01 {TMP_INSTANCE_PATH} /nlmumc/home/{self.manager1}/instance.json"
        get_file_from_tape = (
            f"export clientUserName={self.manager1} && iget /nlmumc/home/{self.manager1}/instance.json"
        )
        subprocess.check_call(put_file_on_tape, shell=True)
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(get_file_from_tape, shell=True)
        subprocess.check_call(
            f"export clientUserName={self.manager1} && irm -rf /nlmumc/home/{self.manager1}/instance.json",
            shell=True,
        )

    def test_set_resc_scheme_for_create_first(self):
        """Test if a file that is put in a project collection is put on the correct resource"""
        collection_path = f"/nlmumc/projects/{self.project_id}/C000000001"
        create_collection = f"imkdir {collection_path}"
        subprocess.check_call(create_collection, shell=True)
        get_instance()
        put_instance = f"export clientUserName={self.manager1} && iput {TMP_INSTANCE_PATH} {collection_path}/instance.json"
        subprocess.check_call(put_instance, shell=True)
        check_resource = f"ils -l {collection_path}/instance.json"
        output = subprocess.check_output(check_resource, shell=True, encoding="UTF-8")
        assert self.destination_resource in output
        # teardown
        subprocess.check_call(f"irm -rf {collection_path}", shell=True)
        revert_latest_project_collection_number(self.project_path)

    def test_set_resc_scheme_for_create_second(self):
        """Test if a file put directly in a project is properly blocked"""
        get_instance()
        put_instance = f"export clientUserName={self.manager1} && iput {TMP_INSTANCE_PATH} /nlmumc/projects/{self.project_id}/instance.json"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(put_instance, shell=True)

    def test_set_resc_scheme_for_create_third(self):
        """Test if a file put directly in the direct dropzone dir is properly blocked and if files put in a direct dropzone have the correct resource"""
        get_instance()
        put_instance = f"export clientUserName={self.manager1} && iput {TMP_INSTANCE_PATH} /nlmumc/ingest/direct"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(f"{put_instance}/instance_test_3.json", shell=True)
        subprocess.check_call(f"{put_instance}/{self.token}/instance_test_3.json", shell=True)
        output_ils = subprocess.check_output(
            f"ils -l /nlmumc/ingest/direct/{self.token}/instance_test_3.json",
            shell=True,
            encoding="UTF-8",
        )
        assert "stagingResc01" in output_ils
        subprocess.check_call(
            f"export clientUserName={self.manager1} && irm -f /nlmumc/ingest/direct/{self.token}/instance_test_3.json",
            shell=True,
        )

    def test_set_resc_scheme_for_create_fourth(self):
        """Test if a file put directly in the mounted dropzone dir is properly blocked and if files put in a mounted dropzone have the correct resource"""
        get_instance()
        self.dropzone_type = "mounted"
        token = create_dropzone(self)
        put_instance = f"export clientUserName={self.manager1} && iput {TMP_INSTANCE_PATH} /nlmumc/ingest/zones"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(f"{put_instance}/instance_test_3.json", shell=True)
        subprocess.check_call(f"{put_instance}/{token}/instance_test_3.json", shell=True)
        output_ils = subprocess.check_output(
            f"ils -l /nlmumc/ingest/zones/{token}/instance_test_3.json",
            shell=True,
            encoding="UTF-8",
        )
        assert "stagingResc01" in output_ils

        # clean up
        subprocess.check_call(
            f"irm -f /nlmumc/ingest/zones/{token}/instance_test_3.json",
            shell=True,
        )
        remove_dropzone(token, "mounted")
        self.dropzone_type = "direct"

    def test_set_resc_scheme_for_create_fifth(self):
        """Test if a file put in a direct dropzone when it is ingesting is properly blocked"""
        subprocess.check_call(f"imeta -M set -C /nlmumc/ingest/direct/{self.token} state ingesting", shell=True)
        put_instance = f"export clientUserName={self.manager1} && iput {TMP_INSTANCE_PATH} /nlmumc/ingest/direct/{self.token}/instance_test_3.json"
        with pytest.raises(subprocess.CalledProcessError) as e_info:
            subprocess.check_call(put_instance, shell=True)
        subprocess.check_call(f"imeta -M set -C /nlmumc/ingest/direct/{self.token} state open", shell=True)
