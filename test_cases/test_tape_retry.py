import json
import subprocess
import time

import pytest
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProcessState

from test_cases.base_tape_archive import BaseTestTapeArchive
from test_cases.utils import add_metadata_files_to_direct_dropzone


class BaseTestTapeRetry(BaseTestTapeArchive):
    """
    Tests that specifically exercise the retry-on-transient-error behavior
    added to the archive and unarchive flows (perform_archive / perform_unarchive).

    For the failure-scenario tests, write/read access to the project's directory
    on the tape filesystem is revoked (chmod 000) before start_archive /
    start_unarchive is called.  The resource-availability checks in
    perform_archive_checks / perform_unarchive_checks query the iRODS catalog
    resource status (not the filesystem), so they pass.  When perform_archive /
    perform_unarchive then runs in the delay queue every irepl or checksum
    attempt raises a RuntimeError due to EACCES.

    Rather than waiting for all retries to exhaust (~10 minutes), each test:
      1. Blocks tape filesystem access (chmod 000)
      2. Starts the archive/unarchive
      3. Watches /var/log/irods/irods.log for a retry warning log entry
         (proving the retry mechanism fired)
      4. Restores tape access once a retry is confirmed
      5. Waits for the operation to complete successfully
    """

    # Base path of the tape resource vault as mounted inside the container
    SURF_ARCHIVE_PROJECTS_PATH = "/mnt/SURF-Archive/projects"

    # Path to the iRODS server log (JSON-formatted entries, one per line)
    IRODS_LOG_PATH = "/var/log/irods/irods.log"

    dropzone_type = "direct"

    # How long to wait for the first retry log message before failing the test
    RETRY_LOG_DETECTION_TIMEOUT_SECONDS = 120

    # How long to wait for the operation to complete after restoring tape access
    PROCESS_COMPLETION_TIMEOUT_SECONDS = 300

    # Paths to the shell scripts invoked by the tape MSIs
    DMATTR_PATH = "/var/lib/irods/msiExecCmd_bin/dmattr"
    DMGET_PATH = "/var/lib/irods/msiExecCmd_bin/dmget"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        add_metadata_files_to_direct_dropzone(token)

    @classmethod
    def add_archive_data_to_dropzone(cls):
        cls._add_large_file_to_direct_dropzone()

    @classmethod
    def _add_large_file_to_direct_dropzone(cls):
        dropzone_path = formatters.format_dropzone_path(cls.token, cls.dropzone_type)
        large_file_path = "/tmp/large_file"
        logical_path = f"{dropzone_path}/large_file"

        with open(large_file_path, "wb") as large_file:
            large_file.write(b"0" * 262144001)
        subprocess.check_call(f"iput -R stagingResc01 {large_file_path} {logical_path}", shell=True)

    # region retry-specific tests

    def test_archive_retries_on_transient_tape_failure(self):
        """
        Verify that the archive flow retries when tape I/O fails transiently and
        completes successfully once access is restored.

        Flow:
        1. chmod 000 on /mnt/SURF-Archive/projects/{project_id}  (blocks tape I/O)
        2. start_archive  (checks pass: resource status is UP in iRODS catalog)
        3. perform_archive runs: checksum OK, but irepl raises RuntimeError (EACCES)
           → retry_runtime_error logs "WARNING: ... retrying in Xs"
        4. Detect the retry log message within 2 minutes → confirm retries fire
        5. Restore tape access (chmod 750)
        6. perform_archive retries successfully → archive completes
        7. Assert the large file is replicated to arcRescSURF01
        """
        try:
            self._block_tape_access()

            subprocess.check_call(self.run_ichmod, shell=True)
            log_position = self._get_log_position()
            rule_archive = (
                f'/rules/tests/run_test.sh -r start_archive'
                f' -a "{self.project_collection_path},{self.manager1}"'
                f' -u {self.service_account}'
            )
            subprocess.check_call(rule_archive, shell=True)

            if not self._wait_for_retry_log(log_position):
                pytest.fail(
                    f"No retry log message detected within"
                    f" {self.RETRY_LOG_DETECTION_TIMEOUT_SECONDS}s;"
                    f" the retry mechanism may not be functioning"
                )

            # Retry confirmed — restore access so the next attempt succeeds
            self._restore_tape_access()

            self._wait_for_process_completion()

            output = subprocess.check_output(self.check_large_file_resource, shell=True, encoding="UTF-8")
            assert "arcRescSURF01" in output

        finally:
            self._restore_tape_access()
            self._remove_collection_avu(self.project_collection_path, "archiveState", "error-archive-failed")

    def test_unarchive_retries_on_transient_tape_failure(self):
        """
        Verify that the unarchive flow retries when tape I/O fails transiently and
        completes successfully once access is restored.

        Files must be on tape first, so a full archive cycle is run before the
        failure scenario.

        Flow:
        1. Archive the collection (full happy path, files land on tape)
        2. chmod 000 on /mnt/SURF-Archive/projects/{project_id}  (blocks tape I/O)
        3. start_unarchive  (checks pass: resource status is UP in iRODS catalog)
        4. perform_unarchive runs: every checksum raises RuntimeError (EACCES)
           → retry_runtime_error logs "WARNING: ... retrying in Xs"
        5. Detect the retry log message within 2 minutes → confirm retries fire
        6. Restore tape access (chmod 750)
        7. perform_unarchive retries successfully → unarchive completes
        8. Assert the large file is on the destination resource
        """
        # Files must be on tape for unarchive to have work to do
        self.run_archive()

        try:
            self._block_tape_access()

            subprocess.check_call(self.run_ichmod, shell=True)
            log_position = self._get_log_position()
            rule_unarchive = (
                f'/rules/tests/run_test.sh -r start_unarchive'
                f' -a "{self.project_collection_path},{self.manager1}"'
                f' -u {self.service_account}'
            )
            subprocess.check_call(rule_unarchive, shell=True)

            if not self._wait_for_retry_log(log_position):
                pytest.fail(
                    f"No retry log message detected within"
                    f" {self.RETRY_LOG_DETECTION_TIMEOUT_SECONDS}s;"
                    f" the retry mechanism may not be functioning"
                )

            # Retry confirmed — restore access so the next attempt succeeds
            self._restore_tape_access()

            self._wait_for_process_completion()

            output = subprocess.check_output(self.check_large_file_resource, shell=True, encoding="UTF-8")
            assert self.destination_resource in output

        finally:
            self._restore_tape_access()
            self._remove_collection_avu(
                self.project_collection_path, "unarchiveState", "error-unarchive-failed"
            )

    def test_dm_attr_retries_on_transient_failure(self):
        """
        Verify that move_offline_files_to_cache retries the dm_attr call when
        the underlying dmattr shell script fails transiently and completes
        successfully once the script is restored.

        Flow:
        1. Archive the collection (files land on tape)
        2. Set the dmattr script to exit 1 (simulate transient failure)
        3. start_unarchive  (checks pass, resource status is UP)
        4. move_offline_files_to_cache calls dm_attr → dmattr exits 1 → RuntimeError
           → retry_runtime_error logs "WARNING: dm_attr for ... retrying in Xs"
        5. Detect the retry log message → confirm retries fire
        6. Restore the dmattr script to exit 0
        7. Unarchive completes successfully
        8. Assert the large file is on the destination resource
        """
        self.run_archive()

        try:
            self._set_script_exit_code(self.DMATTR_PATH, 1)

            subprocess.check_call(self.run_ichmod, shell=True)
            log_position = self._get_log_position()
            rule_unarchive = (
                f'/rules/tests/run_test.sh -r start_unarchive'
                f' -a "{self.project_collection_path},{self.manager1}"'
                f' -u {self.service_account}'
            )
            subprocess.check_call(rule_unarchive, shell=True)

            if not self._wait_for_retry_log(log_position):
                pytest.fail(
                    f"No retry log message detected within"
                    f" {self.RETRY_LOG_DETECTION_TIMEOUT_SECONDS}s;"
                    f" the dm_attr retry mechanism may not be functioning"
                )

            self._set_script_exit_code(self.DMATTR_PATH, 0)

            self._wait_for_process_completion()

            output = subprocess.check_output(self.check_large_file_resource, shell=True, encoding="UTF-8")
            assert self.destination_resource in output

        finally:
            self._set_script_exit_code(self.DMATTR_PATH, 0)
            self._remove_collection_avu(
                self.project_collection_path, "unarchiveState", "error-unarchive-failed"
            )

    def test_dmget_retries_on_transient_failure(self):
        """
        Verify that move_offline_files_to_cache retries dmget calls when the
        underlying dmget shell script fails transiently and completes
        successfully once the script is restored.

        dmget is only invoked for files in the 'OFL' (offline) bucket, so the
        dmattr script is temporarily patched to echo 'OFL' instead of 'DUL'.
        Once the retry is confirmed, both scripts are restored: dmget to exit 0
        and dmattr back to 'DUL', so the next 30s move_offline_files_to_cache
        cycle sees the files as online and hands off to perform_unarchive.

        Flow:
        1. Archive the collection (files land on tape)
        2. Patch dmattr to echo 'OFL' so dm_attr reports files as offline
        3. Set the dmget script to exit 1 (simulate transient failure)
        4. start_unarchive  (checks pass, resource status is UP)
        5. move_offline_files_to_cache: dm_attr sees OFL → dmget is called
           → exits 1 → RuntimeError
           → retry_runtime_error logs "WARNING: dmget ... retrying in Xs"
        6. Detect the retry log message → confirm retries fire
        7. Restore dmget to exit 0 and dmattr to echo 'DUL'
        8. Unarchive completes successfully
        9. Assert the large file is on the destination resource
        """
        self.run_archive()

        try:
            self._set_dmattr_status("OFL")
            self._set_script_exit_code(self.DMGET_PATH, 1)

            subprocess.check_call(self.run_ichmod, shell=True)
            log_position = self._get_log_position()
            rule_unarchive = (
                f'/rules/tests/run_test.sh -r start_unarchive'
                f' -a "{self.project_collection_path},{self.manager1}"'
                f' -u {self.service_account}'
            )
            subprocess.check_call(rule_unarchive, shell=True)

            if not self._wait_for_log_matching(
                log_position,
                lambda msg: "retrying in" in msg and "dmget" in msg,
            ):
                pytest.fail(
                    f"No retry log message detected within"
                    f" {self.RETRY_LOG_DETECTION_TIMEOUT_SECONDS}s;"
                    f" the dmget retry mechanism may not be functioning"
                )

            # Retry confirmed — restore dmget and report files as online so the
            # next move_offline_files_to_cache cycle hands off to perform_unarchive
            self._set_script_exit_code(self.DMGET_PATH, 0)
            self._set_dmattr_status("DUL")

            self._wait_for_process_completion()

            output = subprocess.check_output(self.check_large_file_resource, shell=True, encoding="UTF-8")
            assert self.destination_resource in output

        finally:
            self._set_script_exit_code(self.DMGET_PATH, 0)
            self._set_dmattr_status("DUL")
            self._remove_collection_avu(
                self.project_collection_path, "unarchiveState", "error-unarchive-failed"
            )

    # endregion

    # region helpers

    def _block_tape_access(self):
        """
        Revoke all filesystem access to the project's directory on the tape
        mount.  mkdir -p ensures the path exists even before the first archive,
        then chmod 000 prevents any traversal, read, or write.
        """
        tape_path = f"{self.SURF_ARCHIVE_PROJECTS_PATH}/{self.project_id}"
        subprocess.check_call(f"mkdir -p {tape_path}", shell=True)
        subprocess.check_call(f"chmod 000 {tape_path}", shell=True)

    def _restore_tape_access(self):
        """
        Restore normal filesystem permissions on the project's tape directory
        so that subsequent operations (e.g. the unarchive in teardown) work.
        Failures are silently ignored in case the directory was never created.
        """
        tape_path = f"{self.SURF_ARCHIVE_PROJECTS_PATH}/{self.project_id}"
        try:
            subprocess.check_call(f"chmod 750 {tape_path}", shell=True)
        except subprocess.CalledProcessError:
            pass

    def _get_log_position(self):
        """Return the current byte offset at the end of the iRODS log file."""
        try:
            with open(self.IRODS_LOG_PATH, "rb") as f:
                f.seek(0, 2)
                return f.tell()
        except OSError:
            return 0

    def _read_new_log_lines(self, from_position):
        """
        Return all lines added to the iRODS log file since *from_position*.

        Parameters
        ----------
        from_position : int
            Byte offset to start reading from (as returned by _get_log_position).

        Returns
        -------
        list[str]
        """
        try:
            with open(self.IRODS_LOG_PATH, "r", errors="replace") as f:
                f.seek(from_position)
                return f.readlines()
        except OSError:
            return []

    def _wait_for_retry_log(self, from_position):
        """
        Poll the iRODS log for a retry warning originating from the current
        project collection, up to RETRY_LOG_DETECTION_TIMEOUT_SECONDS.

        Parameters
        ----------
        from_position : int
            Byte offset in the log file captured before the archive/unarchive
            was started; only lines after this point are inspected.

        Returns
        -------
        bool
            True if a matching retry log entry is found before the timeout,
            False otherwise.
        """
        return self._wait_for_log_matching(
            from_position,
            lambda msg: "retrying in" in msg and self.project_collection_path in msg,
        )

    def _wait_for_process_completion(self):
        """
        Poll get_user_active_processes until no archive/unarchive process is
        in-progress or PROCESS_COMPLETION_TIMEOUT_SECONDS is exceeded.
        """
        deadline = time.time() + self.PROCESS_COMPLETION_TIMEOUT_SECONDS
        active_processes = None
        while time.time() < deadline:
            ret = subprocess.check_output(self.rule_status, shell=True)
            active_processes = json.loads(ret)
            if not active_processes[ProcessState.IN_PROGRESS.value]:
                return
            time.sleep(5)
        assert active_processes is not None and not active_processes[ProcessState.IN_PROGRESS.value], (
            f"Archive/unarchive process did not complete within {self.PROCESS_COMPLETION_TIMEOUT_SECONDS}s"
        )

    @staticmethod
    def _get_collection_avu(collection_path, attribute):
        """
        Return the value of a single AVU on a collection using iquest.

        Parameters
        ----------
        collection_path : str
            Absolute iRODS path to the collection.
        attribute : str
            The AVU attribute name.

        Returns
        -------
        str
            The AVU value, stripped of surrounding whitespace.
        """
        cmd = (
            f"iquest \"%s\""
            f" \"SELECT META_COLL_ATTR_VALUE"
            f" WHERE COLL_NAME = '{collection_path}'"
            f" AND META_COLL_ATTR_NAME = '{attribute}'\""
        )
        return subprocess.check_output(cmd, shell=True, encoding="UTF-8").strip()

    @staticmethod
    def _remove_collection_avu(collection_path, attribute, value):
        """
        Remove a specific AVU from a collection, ignoring errors if it is absent.

        Parameters
        ----------
        collection_path : str
            Absolute iRODS path to the collection.
        attribute : str
            The AVU attribute name.
        value : str
            The AVU value.
        """
        try:
            subprocess.check_call(
                f"imeta -M rm -C {collection_path} {attribute} {value}",
                shell=True,
            )
        except subprocess.CalledProcessError:
            pass  # AVU may already be absent; not an error

    def _set_script_exit_code(self, script_path, exit_code):
        """
        Replace the trailing 'exit N' line in *script_path* with 'exit *exit_code*'.

        Parameters
        ----------
        script_path : str
            Absolute path to the shell script to modify.
        exit_code : int
            The exit code to set (0 for success, non-zero for failure).
        """
        subprocess.check_call(
            f"sed -i 's/^exit [0-9]\\+$/exit {exit_code}/' {script_path}",
            shell=True,
        )

    def _set_dmattr_status(self, status):
        """
        Replace the DMF status code echoed by the dmattr script.

        The script echoes a line of the form 'STATUS+FLAGS' (e.g. 'DUL+2147483648').
        This patches just the status prefix so the rest of the line is preserved.

        dmget is only triggered for files in the 'OFL' bucket; files in 'QUE' or
        'STG' land in files_unmigrating and are waited on without calling dmget.

        Parameters
        ----------
        status : str
            The DMF status code to echo, e.g. 'DUL' (online), 'OFL' (offline).
        """
        subprocess.check_call(
            f"sed -i 's/^echo \"[A-Z]*+/echo \"{status}+/' {self.DMATTR_PATH}",
            shell=True,
        )

    def _wait_for_log_matching(self, from_position, predicate):
        """
        Poll the iRODS log for any entry whose log_message satisfies *predicate*,
        up to RETRY_LOG_DETECTION_TIMEOUT_SECONDS.

        Parameters
        ----------
        from_position : int
            Byte offset in the log file captured before the operation started.
        predicate : Callable[[str], bool]
            A function that receives the log_message string and returns True when
            the expected entry is found.

        Returns
        -------
        bool
            True if a matching log entry is found before the timeout,
            False otherwise.
        """
        deadline = time.time() + self.RETRY_LOG_DETECTION_TIMEOUT_SECONDS
        while time.time() < deadline:
            for line in self._read_new_log_lines(from_position):
                try:
                    entry = json.loads(line)
                    log_message = entry.get("log_message", "")
                    if predicate(log_message):
                        return True
                except (json.JSONDecodeError, AttributeError):
                    pass
            time.sleep(2)
        return False

    # endregion


class TestTapeRetryDirectUM(BaseTestTapeRetry):
    depositor = "tape_retry_test_manager"
    manager1 = depositor
    manager2 = "tape_retry_test_data_steward"
    data_steward = manager2
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"
