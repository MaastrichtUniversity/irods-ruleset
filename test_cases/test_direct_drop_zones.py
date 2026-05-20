import json
import subprocess

from dhpythonirodsutils import formatters
from test_cases.base_dropzone_test_case import BaseTestCaseDropZones
from test_cases.utils import add_metadata_files_to_direct_dropzone


class TestDirectDropZones(BaseTestCaseDropZones):
    dropzone_type = "direct"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    def test_calculate_direct_dropzone_size_files(self):
        rule = f'/rules/tests/run_test.sh -r calculate_direct_dropzone_size_files -a "{self.token}"'
        ret = subprocess.check_output(rule, shell=True)

        drop_zone = json.loads(ret)
        assert drop_zone["total_file_count"] == 2
        assert drop_zone["total_file_size"] == 203618

    def test_get_dropzone_files(self):
        rule = f'/rules/tests/run_test.sh -r get_dropzone_files -a "{self.token},/"'
        ret = subprocess.check_output(rule, shell=True, encoding="UTF-8")

        drop_zones = json.loads(ret)
        assert len(drop_zones) == 2
        for dz in drop_zones:
            assert dz["type"] == "file"
            assert dz["date"] > 0
            assert dz["size"].isnumeric()
            assert dz["id"] == f"/{dz['value']}"

    def test_get_dropzone_folders(self):
        tmp_folder = "foobar"
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        full_path = f"{dropzone_path}/{tmp_folder}"

        run_create_folder = f"imkdir {full_path}"
        subprocess.check_call(run_create_folder, shell=True)

        rule = f'/rules/tests/run_test.sh -r get_dropzone_folders -a "{self.token},"'
        ret = subprocess.check_output(rule, shell=True)
        drop_zone = json.loads(ret)
        assert len(drop_zone) == 1
        assert len(drop_zone[0]["data"]) == 0
        assert drop_zone[0]["full_path"] == full_path
        assert drop_zone[0]["id"] == f"/{tmp_folder}"
        assert drop_zone[0]["value"] == tmp_folder

        run_remove_folder = f"irm -fr {full_path}"
        subprocess.check_call(run_remove_folder, shell=True)

    def test_set_project_acl_to_dropzone(self):
        # Run set_project_acl_to_dropzone to give project manager2 own access
        rule_set_acl = f'/rules/tests/run_test.sh -r set_project_acl_to_dropzone -a "{self.project_id},{self.token},false"'
        self.check_acl_changes(rule_set_acl, self.manager2)

    def test_set_project_acl_to_dropzones(self):
        # TODO check multiple dropzones
        rule_set_acl = f'/rules/tests/run_test.sh -r set_project_acl_to_dropzones -a "{self.project_id}"'
        self.check_acl_changes(rule_set_acl, self.manager2)

    def test_set_single_user_project_acl_to_dropzones(self):
        # set_single_user_project_acl_to_dropzones is trigger when a project ACL changes in the policy:
        # acPostProcForModifyAccessControl
        user_to_check = "dlinssen"
        change_project_acl = f"ichmod write {user_to_check} {self.project_path}"
        self.check_acl_changes(change_project_acl, user_to_check)

    def check_acl_changes(self, rule_set_acl, user_to_check):
        # Check the acl before set_project_acl_to_dropzone
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        acl = f"ils -A {dropzone_path}"
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.depositor}#nlmumc:own" in ret
        assert f"{user_to_check}#nlmumc:own" not in ret

        rule_drop_zone = f'/rules/tests/run_test.sh -r get_active_drop_zone -a "{self.token},false,direct" -u {user_to_check}'
        ret = subprocess.getoutput(rule_drop_zone)
        assert "status = -310000" in ret

        # Run set_project_acl_to_dropzone(s) to give to the input user own access
        subprocess.check_call(rule_set_acl, shell=True)

        # Check the acl after set_project_acl_to_dropzone
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.depositor}#nlmumc:own" in ret
        assert f"{user_to_check}#nlmumc:own" in ret

        ret = subprocess.check_output(rule_drop_zone, shell=True)
        drop_zone = json.loads(ret)
        assert drop_zone["token"] == self.token

        # Remove the input user from the dropzone ACL
        ichmod = f"ichmod -rM null {user_to_check} {dropzone_path}"
        subprocess.check_call(ichmod, shell=True)

        # Check that the input user has no access
        acl = f"ils -A {dropzone_path}"
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.depositor}#nlmumc:own" in ret
        assert f"{user_to_check}" not in ret

    def test_share_dropzone_avu(self):
        user_to_check = self.manager2
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)

        # Check manager2 has no access
        acl = f"ils -A {dropzone_path}"
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.depositor}#nlmumc:own" in ret
        assert f"{user_to_check}" not in ret

        # Change project AVU enableDropzoneSharing to give access
        avu_change = f"imeta set -C {self.project_path} enableDropzoneSharing true"
        subprocess.check_call(avu_change, shell=True)

        # Check manager2 gained access
        acl = f"ils -A {dropzone_path}"
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.depositor}#nlmumc:own" in ret
        assert f"{user_to_check}#nlmumc:own" in ret

        # Change project AVU enableDropzoneSharing to revoke access
        avu_change = f"imeta set -C {self.project_path} enableDropzoneSharing false"
        subprocess.check_call(avu_change, shell=True)

        # Check manager2 lost access
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert f"{self.depositor}#nlmumc:own" in ret
        assert f"{user_to_check}" not in ret
