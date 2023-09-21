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
        rule = '/rules/tests/run_test.sh -r calculate_direct_dropzone_size_files -a "{}"'.format(self.token)
        ret = subprocess.check_output(rule, shell=True)

        drop_zone = json.loads(ret)
        assert drop_zone["total_file_count"] == 2
        assert drop_zone["total_file_size"] == 203618

    def test_get_dropzone_files(self):
        rule = '/rules/tests/run_test.sh -r get_dropzone_files -a "{},/"'.format(self.token)
        ret = subprocess.check_output(rule, shell=True, encoding="UTF-8")

        drop_zones = json.loads(ret)
        assert len(drop_zones) == 2
        for dz in drop_zones:
            assert dz["type"] == "file"
            assert dz["date"] > 0
            assert dz["size"].isnumeric()
            assert dz["id"] == "/{}".format(dz["value"])

    def test_get_dropzone_folders(self):
        tmp_folder = "foobar"
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        full_path = "{}/{}".format(dropzone_path, tmp_folder)

        run_create_folder = "imkdir {}".format(full_path)
        subprocess.check_call(run_create_folder, shell=True)

        rule = '/rules/tests/run_test.sh -r get_dropzone_folders -a "{},"'.format(self.token)
        ret = subprocess.check_output(rule, shell=True)
        drop_zone = json.loads(ret)
        assert len(drop_zone) == 1
        assert len(drop_zone[0]["data"]) == 0
        assert drop_zone[0]["full_path"] == full_path
        assert drop_zone[0]["id"] == "/{}".format(tmp_folder)
        assert drop_zone[0]["value"] == tmp_folder

        run_remove_folder = "irm -fr {}".format(full_path)
        subprocess.check_call(run_remove_folder, shell=True)

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
        change_project_acl = "ichmod write {} {}".format(user_to_check, self.project_path)
        self.check_acl_changes(change_project_acl, user_to_check)

    def check_acl_changes(self, rule_set_acl, user_to_check):
        # Check the acl before set_project_acl_to_dropzone
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        acl = "ils -A {}".format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}#nlmumc:own".format(user_to_check) not in ret

        rule_drop_zone = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,direct" -u {}'.format(
            self.token, user_to_check
        )
        ret = subprocess.getoutput(rule_drop_zone)
        assert "status = -310000" in ret

        # Run set_project_acl_to_dropzone(s) to give to the input user own access
        subprocess.check_call(rule_set_acl, shell=True)

        # Check the acl after set_project_acl_to_dropzone
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}#nlmumc:own".format(user_to_check) in ret

        ret = subprocess.check_output(rule_drop_zone, shell=True)
        drop_zone = json.loads(ret)
        assert drop_zone["token"] == self.token

        # Remove the input user from the dropzone ACL
        ichmod = "ichmod -rM null {} {}".format(user_to_check, dropzone_path)
        subprocess.check_call(ichmod, shell=True)

        # Check that the input user has no access
        acl = "ils -A {}".format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}".format(user_to_check) not in ret

    def test_share_dropzone_avu(self):
        user_to_check = self.manager2
        dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)

        # Check manager2 has no access
        acl = "ils -A {}".format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}".format(user_to_check) not in ret

        # Change project AVU enableDropzoneSharing to give access
        avu_change = "imeta set -C {} enableDropzoneSharing true".format(self.project_path)
        subprocess.check_call(avu_change, shell=True)

        # Check manager2 gained access
        acl = "ils -A {}".format(dropzone_path)
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}#nlmumc:own".format(user_to_check) in ret

        # Change project AVU enableDropzoneSharing to revoke access
        avu_change = "imeta set -C {} enableDropzoneSharing false".format(self.project_path)
        subprocess.check_call(avu_change, shell=True)

        # Check manager2 lost access
        ret = subprocess.check_output(acl, shell=True, encoding="UTF-8")
        assert "rods#nlmumc:own" in ret
        assert "{}#nlmumc:own".format(self.depositor) in ret
        assert "{}".format(user_to_check) not in ret
