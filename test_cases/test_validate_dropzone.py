import json
import subprocess

from dhpythonirodsutils import formatters

from test_cases.utils import (
    add_metadata_files_to_direct_dropzone,
    create_dropzone,
    create_project,
    remove_dropzone,
    remove_project,
)


class TestValidateDropzone:
    """
    Integration tests for validate_dropzone.

    Each test creates a fresh dropzone, triggers a specific validation scenario, asserts that:
      - the returned validation_errors list contains (or does not contain) the expected message, and
      - the 'state' AVU on the dropzone is set to the expected value.
    The dropzone is removed in a finally block after each test.

    Scenarios covered:
      1. Happy path - no validation errors
      2. User with insufficient dropzone permissions
      3. Non-creator ingesting a direct dropzone when dropzone sharing is disabled
      4. Metadata validation failure (empty / unparseable metadata files)
      5. Dropzone not ingestable (file with unsupported characters in its name)
      6. Dropzone contains a stale file replica
    """

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
    collection_title = "collection_title"

    @classmethod
    def setup_class(cls):
        print()
        print(f"Start {cls.__name__}.setup_class")
        project = create_project(cls)
        cls.project_path = project["project_path"]
        cls.project_id = project["project_id"]
        print(f"End {cls.__name__}.setup_class")

    @classmethod
    def teardown_class(cls):
        print()
        print(f"Start {cls.__name__}.teardown_class")
        remove_project(cls.project_path)
        print(f"End {cls.__name__}.teardown_class")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fresh_dropzone_with_metadata(self):
        """Create a fresh dropzone and add valid metadata files. Returns the token."""
        token = create_dropzone(self)
        add_metadata_files_to_direct_dropzone(token)
        return token

    def _run_validate_dropzone(self, dropzone_path, username=None):
        """Run validate_dropzone via run_test.sh and return the parsed result dict."""
        username = username or self.depositor
        rule = (
            f'/rules/tests/run_test.sh -r validate_dropzone'
            f' -a "{dropzone_path},{username},{self.dropzone_type}"'
        )
        ret = subprocess.check_output(rule, shell=True, encoding="UTF-8")
        # Extract JSON from the first line (iRODS may output debug messages after)
        json_line = ret.split('\n')[0]
        return json.loads(json_line)

    def _assert_state_avu(self, dropzone_path, expected_state):
        """Assert the 'state' AVU of the dropzone is set to *expected_state*."""
        ret = subprocess.check_output(
            f"imeta ls -C {dropzone_path} state", shell=True, encoding="UTF-8"
        )
        assert f"value: {expected_state}" in ret

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_validate_dropzone_happy_path(self):
        """Valid dropzone with correct metadata returns no errors and sets state to 'validating'."""
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            result = self._run_validate_dropzone(dropzone_path)

            assert result["validation_errors"] == []
            assert result["project_id"] == self.project_id
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)

    def test_validate_dropzone_dropzone_does_not_exist(self):
        """Validation of a non-existent dropzone returns the appropriate error message."""
        dropzone_path = formatters.format_dropzone_path("nonexistent-token", self.dropzone_type)
        result = self._run_validate_dropzone(dropzone_path)

        assert any(
            "does not exist" in err for err in result["validation_errors"]
        )

    def test_validate_dropzone_insufficient_permissions(self):
        """User without ingest write ACL receives an insufficient permissions error."""
        no_perm_user = "validate_dz_test_user"
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            # Create a user that intentionally has no write ACL on /nlmumc/ingest/direct
            subprocess.check_call(f"iadmin mkuser {no_perm_user} rodsuser", shell=True)

            result = self._run_validate_dropzone(dropzone_path, username=no_perm_user)

            assert any(
                "has insufficient DropZone permissions" in err
                for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "open")
        finally:
            remove_dropzone(token, self.dropzone_type)
            subprocess.check_call(f"iadmin rmuser {no_perm_user}", shell=True)

    def test_validate_dropzone_project_resource_down(self):
        """Project resource of dropzone is down, causing validation to fail with the appropriate error message."""
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            subprocess.check_call(f"iadmin modresc {self.destination_resource} status down", shell=True)

            result = self._run_validate_dropzone(dropzone_path)
            assert any(
                "project or ingest resource is disabled" in err
                for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)
            subprocess.check_call(f"iadmin modresc {self.destination_resource} status up", shell=True)
    
    def test_validate_dropzone_ingest_resource_down(self):
        """Ingest resource of dropzone is down, causing validation to fail with the appropriate error message."""
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            subprocess.check_call(f"iadmin modresc {self.ingest_resource} status down", shell=True)

            result = self._run_validate_dropzone(dropzone_path)
            assert any(
                "project or ingest resource is disabled" in err
                for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)
            subprocess.check_call(f"iadmin modresc {self.ingest_resource} status up", shell=True)

    def test_validate_dropzone_project_path_does_not_exist(self):
        """Project path of dropzone does not exist, causing validation to fail with the appropriate error message."""
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            # Set the project AVU to a non-existent project to trigger the error
            subprocess.check_call(
                f"imeta set -C {dropzone_path} project P999999999", shell=True
            )
            result = self._run_validate_dropzone(dropzone_path)
            assert any(
                "Unknown project" in err
                for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)

    def test_validate_dropzone_wrong_creator_direct(self):
        """Non-creator ingesting a direct dropzone when dropzone sharing is disabled gets an error."""
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            # Disable dropzone sharing so that only the creator may start ingestion
            subprocess.check_call(
                f"imeta set -C {self.project_path} enableDropzoneSharing false",
                shell=True,
            )
            subprocess.check_call(f"ichmod own rods -Mr {dropzone_path}",shell=True)

            # Run as manager2 (opalmen) who is not the creator of this dropzone (jmelius)
            result = self._run_validate_dropzone(dropzone_path, username=self.manager2)

            assert any(
                "is not the creator" in err for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            # Restore project sharing state before cleanup
            subprocess.check_call(
                f"imeta set -C {self.project_path} enableDropzoneSharing true",
                shell=True,
            )
            remove_dropzone(token, self.dropzone_type)

    def test_validate_dropzone_metadata_validation_failed(self):
        """Dropzone with empty (unparseable) metadata files causes metadata validation to fail."""
        token = create_dropzone(self)
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            # Upload zero-byte metadata files so the physical directory is created on the
            # staging resource but json.loads raises ValueError, causing validate_metadata
            # to return False.
            subprocess.check_call(
                "touch /tmp/empty_instance.json /tmp/empty_schema.json", shell=True
            )
            instance_path = formatters.format_instance_dropzone_path(token, self.dropzone_type)
            schema_path = formatters.format_schema_dropzone_path(token, self.dropzone_type)
            subprocess.check_call(
                f"iput -R stagingResc01 /tmp/empty_instance.json {instance_path}", shell=True
            )
            subprocess.check_call(
                f"iput -R stagingResc01 /tmp/empty_schema.json {schema_path}", shell=True
            )

            result = self._run_validate_dropzone(dropzone_path)

            assert any(
                "Metadata validation failed" in err for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)

    def test_validate_dropzone_not_ingestable(self):
        """Dropzone whose physical directory contains a file with unsupported characters fails the ingestable check.

        save_dropzone_pre_ingest_info walks the physical vault path and sets the 'isIngestable'
        AVU to 'false' when any path contains both a single-quote (') and the substring ' and '.
        """
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        try:
            # Create a subdirectory with a single quote in the name
            subdir = "foo'bar"
            subprocess.check_call(["imkdir", f"{dropzone_path}/{subdir}"])

            # Create a file with " and " in the name on the local filesystem
            temp_file = "/tmp/invalid_and_char.dat"
            subprocess.check_call(
                f"dd if=/dev/zero of={temp_file} bs=1K count=1",
                shell=True,
            )

            # Upload the file into the subdirectory with a name containing " and "
            # Use list form to avoid shell quoting issues with the special characters
            target_file = f"{dropzone_path}/{subdir}/invalid and char.dat"
            try:
                subprocess.check_call(
                    ["iput", "-R", "stagingResc01", temp_file, target_file]
                )
            except subprocess.CalledProcessError:
                # iput may fail due to the unsupported characters in the path, but that's OK.
                # The validation logic will still detect them when walking the physical path.
                pass

            result = self._run_validate_dropzone(dropzone_path)

            assert any(
                "unsupported characters" in err for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)

    def test_validate_dropzone_stale_file_direct(self):
        """Direct dropzone containing a stale file replica (DATA_REPL_STATUS = 0) is reported as an error.

        Steps to create a stale replica:
          1. iput a file to stagingResc01 (replica 0, status = good).
          2. irepl to the project destination resource (replica 1, status = good).
          3. iput -f back to stagingResc01 (replica 0 refreshed; replica 1 becomes stale, status = 0).
        """
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        file_logical_path = f"{dropzone_path}/validate_dz_stale.dat"
        try:
            subprocess.check_call(
                "dd if=/dev/zero of=/tmp/validate_dz_stale.dat bs=1K count=1",
                shell=True,
            )
            # Upload to staging resource (replica 0)
            subprocess.check_call(
                f"iput -R stagingResc01 /tmp/validate_dz_stale.dat {file_logical_path}",
                shell=True,
            )
            # Create a second replica on the destination resource (replica 1)
            subprocess.check_call(
                f"irepl -R {self.destination_resource} {file_logical_path}",
                shell=True,
            )
            # Overwrite on staging resource — replica 1 on destination becomes stale
            subprocess.check_call(
                f"iput -f -R stagingResc01 /tmp/validate_dz_stale.dat {file_logical_path}",
                shell=True,
            )

            result = self._run_validate_dropzone(dropzone_path)

            assert any("stale file" in err for err in result["validation_errors"])
            assert any(
                "validate_dz_stale.dat" in err for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            remove_dropzone(token, self.dropzone_type)

    def test_validate_dropzone_locked_file_direct(self):
        """Direct dropzone containing a locked file replica (DATA_REPL_STATUS = 2) is reported as an error.

        Steps to create a locked replica:
          1. iput a file to stagingResc01 (replica 0, status = good).
          2. irepl to the project destination resource (replica 1, status = good).
          3. iput -f back to stagingResc01 (replica 0 refreshed; replica 1 becomes stale, status = 0).
        """
        token = self._fresh_dropzone_with_metadata()
        dropzone_path = formatters.format_dropzone_path(token, self.dropzone_type)
        file_logical_path = f"{dropzone_path}/validate_dz_locked.dat"
        try:
            subprocess.check_call(
                "dd if=/dev/zero of=/tmp/validate_dz_locked.dat bs=1K count=1",
                shell=True,
            )
            # Upload to staging resource (replica 0)
            subprocess.check_call(
                f"iput -R stagingResc01 /tmp/validate_dz_locked.dat {file_logical_path}",
                shell=True,
            )
            print(subprocess.check_output(f"ils -l {file_logical_path}", shell=True, encoding="UTF-8"))
            subprocess.check_call(
                [
                    "iadmin",
                    "modrepl",
                    "logical_path",
                    file_logical_path,
                    "replica_number",
                    "0",
                    "DATA_REPL_STATUS",
                    "2",
                ],
                shell=False,
            )
            result = self._run_validate_dropzone(dropzone_path)

            assert any("locked file" in err for err in result["validation_errors"])
            assert any(
                "validate_dz_locked.dat" in err for err in result["validation_errors"]
            )
            self._assert_state_avu(dropzone_path, "validating")
        finally:
            subprocess.check_call(
                [
                    "iadmin",
                    "modrepl",
                    "logical_path",
                    file_logical_path,
                    "replica_number",
                    "0",
                    "DATA_REPL_STATUS",
                    "0",
                ],
                shell=False,
            )
            remove_dropzone(token, self.dropzone_type)
