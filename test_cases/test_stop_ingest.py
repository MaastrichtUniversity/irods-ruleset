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

    def test_stop_running_ingest_and_restart(self, tmp_path):
        if os.environ.get("STOP_INGEST_TEST_TYPE") != self.dropzone_type:
            pytest.skip("Opt in on the transfer host with STOP_INGEST_TEST_TYPE=direct or mounted")

        self.project_path = None
        self.dropzone_path = None
        self.ingest_started = False
        self.ingest_finished = False
        self.restart_pending = False
        try:
            self.prepare_ingest(tmp_path)
            self.start_ingest_and_wait_for_transfer()
            self.stop_and_verify_transfer()
            self.restart_ingest()
            self.wait_for_transfer()
            self.stop_and_verify_transfer()
            self.restart_and_verify_ingest()
            self.wait_for_dropzone_removal_to_be_scheduled()
        finally:
            self.cleanup_project()

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
        self.ingest_started = True
        self.wait_for_transfer()

    def wait_for_transfer(self):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            collection_id = self.get_dropzone_avu("destination")
            if collection_id:
                self.destination = f"{self.project_path}/{collection_id}"
                pids = get_irsync_pids_from_log(self.log_position, self.destination)
                if pids and is_irsync_process_running(pids[-1], self.destination):
                    self.transfer_pid = pids[-1]
                    assert self.get_dropzone_avu("ingestTransferState") == "active"
                    assert self.get_dropzone_avu("ingestStopRequested") == "false"
                    assert self.get_dropzone_avu("ingestWorkerResult") == ""
                    return
            state = self.get_dropzone_avu("state")
            assert not state.startswith("error-"), f"{self.dropzone_path} entered {state} before stopping"
            time.sleep(0.1)
        pytest.fail(
            f"No running irsync observed for {self.dropzone_path}: run on icat for direct, "
            "ires-hnas-um for mounted; increase STOP_INGEST_TEST_BYTES if the transfer finishes too quickly"
        )

    def stop_and_verify_transfer(self):
        before = time.monotonic()
        run_rule("stop_ingest", self.token, self.dropzone_type)
        assert time.monotonic() - before < 35
        assert not is_irsync_process_running(self.transfer_pid, self.destination)
        assert self.get_dropzone_avu("state") == DropzoneState.ERROR_INGESTION.value
        assert self.get_dropzone_avu("ingestTransferState") == "stopped"
        assert self.get_dropzone_avu("ingestStopRequested") == "true"
        assert self.get_dropzone_avu("ingestWorkerResult") == "stopped"
        # stop_ingest returns after worker exit and coordinator acknowledgement.
        # Retry cancellation is covered by the mocked tests; no fixed wait here.
        subprocess.check_call(["ils", f"{self.dropzone_path}/instance.json"])
        if self.dropzone_type == "mounted":
            assert self.source_file.stat().st_size == self.file_size
        else:
            subprocess.check_call(["ils", f"{self.dropzone_path}/stop-test.bin"])

    def restart_ingest(self):
        self.log_position = get_log_position()
        self.restart_pending = True
        run_rule("restart_ingest", self.token, self.dropzone_type)
        # Restart is delayed; allow it to leave the previously stopped state.
        deadline = time.monotonic() + 60
        while self.get_dropzone_avu("state") == DropzoneState.ERROR_INGESTION.value and time.monotonic() < deadline:
            time.sleep(0.2)
        assert self.get_dropzone_avu("state") != DropzoneState.ERROR_INGESTION.value, "Restart did not begin"
        self.restart_pending = False

    def restart_and_verify_ingest(self):
        self.restart_ingest()
        self.wait_for_ingested_state()
        assert self.get_dropzone_avu("ingestTransferState") == "finished"
        assert self.get_dropzone_avu("ingestStopRequested") == "false"
        assert self.get_dropzone_avu("ingestWorkerResult") == "exited"
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
                self.ingest_finished = True
                return
            time.sleep(1)
        pytest.fail(f"Post-ingest work did not schedule removal of {self.dropzone_path}")

    def cleanup_project(self):
        # Never remove data underneath a transfer that has not confirmed a stop.
        if self.restart_pending:
            print(f"Restart still pending; retaining {self.dropzone_path} and {self.project_path}")
            return
        if self.dropzone_path and self.get_dropzone_avu("ingestTransferState") == "active":
            try:
                run_rule("stop_ingest", self.token, self.dropzone_type)
            except subprocess.CalledProcessError:
                print(f"Stop unconfirmed; retaining {self.dropzone_path} and {self.project_path} for inspection")
                return
        if self.ingest_started and not self.ingest_finished:
            if not self.get_dropzone_avu("state").startswith("error-"):
                print(f"Ingest workflow still unfinished; retaining {self.dropzone_path} and {self.project_path}")
                return
        if self.project_path:
            remove_project(self.project_path)


class TestStopDirectIngestUM(BaseTestCaseStopIngest):
    dropzone_type = "direct"

    def add_data_to_dropzone(self, tmp_path):
        self.create_source_file(tmp_path / "stop-test.bin")
        subprocess.check_call([
            "iput", "-R", "stagingResc01", str(self.source_file), f"{self.dropzone_path}/stop-test.bin",
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
        source_file = Path(f"/mnt/ingest/zones/{self.token}/stop-test.bin")
        assert source_file.parent.is_dir(), "Run the mounted case on ires-hnas-um as the irods OS user"
        self.create_source_file(source_file)
