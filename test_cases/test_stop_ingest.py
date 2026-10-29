"""Opt-in live stop/restart tests. See test_cases/README.md for host selection."""
import json
import os
from pathlib import Path
import re
import subprocess
import time

import pytest
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState

from test_cases.utils import (
    add_metadata_files_to_dropzone, create_dropzone, create_project,
    get_log_position, read_new_log_lines, remove_project,
)


def run_rule(rule, *args, user=None):
    command = ["/rules/tests/run_test.sh", "-r", rule, "-a", ",".join(args)]
    if user is not None:
        command.extend(["-u", user])
    return subprocess.check_output(command, text=True)


def get_irsync_pids_from_log(log_position, destination):
    pids = []
    for line in read_new_log_lines(log_position):
        try:
            message = json.loads(line).get("log_message", "")
        except (json.JSONDecodeError, AttributeError):
            continue
        match = re.search(r"irsync started for " + re.escape(destination) + r" \(pid (\d+)\)", message)
        if match:
            pids.append(int(match[1]))
    return pids


def is_irsync_process_running(pid, destination):
    """Check both PID and destination so a reused PID cannot confirm a transfer."""
    try:
        arguments = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except FileNotFoundError:
        return False
    return Path(os.fsdecode(arguments[0])).name == "irsync" and f"i:{destination}".encode() in arguments


# Keep transfer timing checks and global size scans in the sequential phase.
class BaseTestCaseStopIngest:
    ingest_resource = "ires-hnas-umResource"
    destination_resource = "passRescUM01"
    project_title = "Stopingestintegrationtest"
    manager1 = "jmelius"
    manager2 = "opalmen"
    depositor = manager1
    budget_number = "UM-30001234X"
    collection_title = "Stopingesttest"
    schema_name = "DataHub_general_schema"
    schema_version = "1.0.0"
    payload_names = ("stop-test-1.bin", "stop-test-2.bin")

    @pytest.fixture(autouse=True)
    def setup(self, request, tmp_path):
        if os.environ.get("STOP_INGEST_TEST_TYPE") != self.dropzone_type:
            pytest.skip("Opt in on the transfer host with STOP_INGEST_TEST_TYPE=direct or mounted")

        self.project_path = None
        self.dropzone_path = None
        self.destination = None
        request.addfinalizer(self.teardown)
        self.prepare_ingest(tmp_path)

    def test_stop_running_ingest_and_restart(self):
        self.start_ingest_and_wait_for_transfer()
        self.stop_and_verify_transfer()
        self.restart_ingest()
        self.wait_for_transfer()
        self.stop_and_verify_transfer()
        self.restart_and_verify_ingest()

    def get_dropzone_avu(self, attribute):
        result = run_rule("get_collection_attribute_value", self.dropzone_path, attribute)
        return json.loads(result)["value"]

    def prepare_ingest(self, tmp_path):
        project = create_project(self)
        self.project_id = project["project_id"]
        self.project_path = project["project_path"]
        self.token = create_dropzone(self)
        self.dropzone_path = formatters.format_dropzone_path(self.token, self.dropzone_type)
        add_metadata_files_to_dropzone(self.token, self.dropzone_type)
        self.file_size = int(os.environ.get("STOP_INGEST_TEST_BYTES", str(2 * 1024 ** 3)))
        self.add_data_to_dropzone(tmp_path)
        run_rule("calculate_all_dropzone_sizes")

    def create_source_file(self, path):
        self.source_file = path
        with path.open("wb") as output:
            output.truncate(self.file_size)

    def start_ingest_and_wait_for_transfer(self):
        self.log_position = get_log_position()
        run_rule(
            "start_ingest", self.depositor, self.token, self.dropzone_type,
            user=self.depositor if self.dropzone_type == "direct" else None,
        )
        self.wait_for_transfer()

    def wait_for_transfer(self):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            collection_id = self.get_dropzone_avu("destination")
            if collection_id:
                self.destination = f"{self.project_path}/{collection_id}"
                pids = get_irsync_pids_from_log(self.log_position, self.destination)
                if (pids and is_irsync_process_running(pids[-1], self.destination)
                        and any(status == "2" for _, status in self.get_payload_replica_states())):
                    self.transfer_pid = pids[-1]
                    assert self.get_dropzone_avu("ingestTransferState") == "active"
                    assert self.get_dropzone_avu("ingestStopRequested") == "false"
                    assert self.get_dropzone_avu("ingestWorkerResult") == ""
                    return
            state = self.get_dropzone_avu("state")
            assert not state.startswith("error-"), f"{self.dropzone_path} entered {state} before stopping"
            time.sleep(0.1)
        pytest.fail(
            f"No active payload transfer observed for {self.dropzone_path}: run on icat for direct, "
            "ires-hnas-um for mounted; increase STOP_INGEST_TEST_BYTES if the transfer finishes too quickly"
        )

    def get_payload_replica_states(self):
        query = (
            "SELECT DATA_NAME, DATA_REPL_STATUS "
            f"WHERE COLL_NAME = '{self.destination}'"
        )
        try:
            output = subprocess.check_output(["iquest", "%s|%s", query], text=True)
        except subprocess.CalledProcessError as error:
            if "CAT_NO_ROWS_FOUND" in error.output:
                return []
            raise
        return [
            (name, status) for name, status in (line.rsplit("|", 1) for line in output.splitlines())
            if name in self.payload_names
        ]

    def wait_for_payload_replicas_to_settle(self):
        # A server-side copy can outlive the cancelled irsync client. Wait for
        # its real replica transition before restarting or removing test data.
        deadline = time.monotonic() + 120
        while True:
            states = self.get_payload_replica_states()
            if all(status in ("0", "1") for _, status in states):
                return
            if time.monotonic() >= deadline:
                pytest.fail(f"Payload replicas still active for {self.destination}: {states}")
            time.sleep(1)

    def stop_and_verify_transfer(self):
        before = time.monotonic()
        run_rule("stop_ingest", self.token, self.dropzone_type)
        assert time.monotonic() - before < 35
        assert not is_irsync_process_running(self.transfer_pid, self.destination)
        assert self.get_dropzone_avu("state") == DropzoneState.ERROR_INGESTION.value
        assert self.get_dropzone_avu("ingestTransferState") == "stopped"
        assert self.get_dropzone_avu("ingestStopRequested") == "true"
        assert self.get_dropzone_avu("ingestWorkerResult") == "stopped"
        # Keep the stop acknowledgement and source-preservation assertions
        # separate from waiting for the server's current file request to finish.
        subprocess.check_call(["ils", f"{self.dropzone_path}/instance.json"])
        if self.dropzone_type == "mounted":
            for name in self.payload_names:
                assert (self.source_file.parent / name).stat().st_size == self.file_size
        else:
            for name in self.payload_names:
                subprocess.check_call(["ils", f"{self.dropzone_path}/{name}"])
        self.wait_for_payload_replicas_to_settle()

    def restart_ingest(self):
        self.log_position = get_log_position()
        run_rule("restart_ingest", self.token, self.dropzone_type)
        # Restart is delayed; allow it to leave the previously stopped state.
        deadline = time.monotonic() + 60
        while self.get_dropzone_avu("state") == DropzoneState.ERROR_INGESTION.value and time.monotonic() < deadline:
            time.sleep(0.2)
        assert self.get_dropzone_avu("state") != DropzoneState.ERROR_INGESTION.value, "Restart did not begin"

    def restart_and_verify_ingest(self):
        self.restart_ingest()
        self.wait_for_ingested_state()
        assert self.get_dropzone_avu("ingestTransferState") == "finished"
        assert self.get_dropzone_avu("ingestStopRequested") == "false"
        assert self.get_dropzone_avu("ingestWorkerResult") == "exited"
        self.wait_for_dropzone_removal_to_be_scheduled()
        subprocess.check_call(["ichksum", "-Mr", self.destination])
        subprocess.check_call(["ichksum", "-K", "-r", self.destination])
        assert get_irsync_pids_from_log(self.log_position, self.destination)

    def wait_for_ingested_state(self):
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            state = self.get_dropzone_avu("state")
            if state == DropzoneState.INGESTED.value:
                return
            assert not state.startswith("error-"), f"{self.dropzone_path} entered {state} after restart"
            time.sleep(1)
        pytest.fail(f"{self.dropzone_path} did not reach ingested within 600s")

    def wait_for_dropzone_removal_to_be_scheduled(self):
        # 'ingested' precedes final post-ingest work. Its completion log is not
        # local for mounted ingests, so inspect the queued deletion instead.
        removal_rule = f"removeDropzone('{self.dropzone_path}',"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            delayed_rules = subprocess.check_output(["iqstat", "-a"], text=True)
            if removal_rule in delayed_rules or not self.get_dropzone_avu("state"):
                return
            time.sleep(1)
        pytest.fail(f"Post-ingest work did not schedule removal of {self.dropzone_path}")

    def teardown(self):
        try:
            if self.dropzone_path and self.get_dropzone_avu("ingestTransferState") == "active":
                run_rule("stop_ingest", self.token, self.dropzone_type)
            if self.destination:
                self.wait_for_payload_replicas_to_settle()
        finally:
            try:
                if self.dropzone_path:
                    self.cleanup_dropzone()
            finally:
                if self.project_path:
                    remove_project(self.project_path)

    def cleanup_dropzone(self):
        # Cancel post-ingest removal before deleting its source collection.
        query = (
            "SELECT RULE_EXEC_ID WHERE RULE_EXEC_NAME LIKE "
            f"'%removeDropzone(''{self.dropzone_path}'',%'"
        )
        try:
            rule_ids = subprocess.check_output(["iquest", "%s", query], text=True).splitlines()
        except subprocess.CalledProcessError as error:
            if "CAT_NO_ROWS_FOUND" not in error.output:
                raise
            rule_ids = []
        for rule_id in rule_ids:
            subprocess.check_call(["iqdel", rule_id])
        if not self.get_dropzone_avu("state"):
            return
        subprocess.check_call(["ichmod", "-rM", "own", "rods", self.dropzone_path])
        ingest_host = subprocess.check_output([
            "iquest", "%s", f"SELECT RESC_LOC WHERE RESC_NAME = '{self.ingest_resource}'",
        ], text=True).strip()
        # Use the normal removal rule to also disable and delete physical zones.
        subprocess.check_call([
            "irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance",
            f"removeDropzone('{self.dropzone_path}', '{ingest_host}', '{self.token}', '{self.dropzone_type}')",
            "null", "ruleExecOut",
        ])


class TestStopDirectIngestUM(BaseTestCaseStopIngest):
    dropzone_type = "direct"

    def add_data_to_dropzone(self, tmp_path):
        self.create_source_file(tmp_path / "stop-test.bin")
        for name in self.payload_names:
            subprocess.check_call([
                "iput", "-R", "stagingResc01", str(self.source_file), f"{self.dropzone_path}/{name}",
            ])
        for metadata_path in (
            formatters.format_instance_dropzone_path(self.token, self.dropzone_type),
            formatters.format_schema_dropzone_path(self.token, self.dropzone_type),
        ):
            run_rule("set_acl", "default", "admin:own", self.depositor, metadata_path)
        run_rule("set_acl", "recursive", "admin:own", "rods", self.dropzone_path)


class TestStopMountedIngestUM(BaseTestCaseStopIngest):
    dropzone_type = "mounted"

    def add_data_to_dropzone(self, tmp_path):
        directory = Path(f"/mnt/ingest/zones/{self.token}")
        assert directory.is_dir(), "Run the mounted case on ires-hnas-um as the irods OS user"
        for name in self.payload_names:
            self.create_source_file(directory / name)
