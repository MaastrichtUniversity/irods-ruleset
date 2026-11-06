from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from test_cases import test_stop_ingest as live


@pytest.fixture
def scenario(monkeypatch):
    case = live.BaseTestCaseStopIngest()
    case.project_path = "/nlmumc/projects/P000000001"
    case.destination = case.project_path + "/C000000001"
    case.dropzone_path = "/nlmumc/ingest/direct/test-zone"
    case.log_position = 0
    case.dropzone_type = "direct"
    monkeypatch.setattr(live, "time", SimpleNamespace(monotonic=Mock(return_value=0), sleep=Mock()))
    return case


def test_running_client_is_not_enough_without_an_active_payload(scenario, monkeypatch):
    values = {"destination": "C000000001", "state": "ingesting", "ingestTransferState": "active",
              "ingestStopRequested": "false", "ingestWorkerResult": ""}
    monkeypatch.setattr(scenario, "get_dropzone_avu", lambda attribute: values[attribute])
    monkeypatch.setattr(live, "get_irsync_pids_from_log", Mock(return_value=[44]))
    monkeypatch.setattr(live, "is_irsync_process_running", Mock(return_value=True))
    states = Mock(side_effect=[[(scenario.payload_names[0], "1")], [(scenario.payload_names[1], "2")]])
    monkeypatch.setattr(scenario, "get_payload_replica_states", states)

    scenario.wait_for_transfer()

    assert states.call_count == 2
    assert scenario.transfer_pid == 44
    live.time.sleep.assert_called_once_with(0.1)


def test_waits_for_server_write_after_client_stop(scenario, monkeypatch):
    name = scenario.payload_names[0]
    states = Mock(side_effect=[[(name, "2")], [(name, "4")], [(name, "0")]])
    monkeypatch.setattr(scenario, "get_payload_replica_states", states)

    scenario.wait_for_payload_replicas_to_settle()

    assert states.call_count == 3
    assert live.time.sleep.call_count == 2


def test_persistent_server_write_still_fails(scenario, monkeypatch):
    live.time.monotonic.side_effect = [0, 121]
    monkeypatch.setattr(scenario, "get_payload_replica_states", Mock(return_value=[(scenario.payload_names[0], "2")]))
    with pytest.raises(pytest.fail.Exception, match="Payload replicas still active"):
        scenario.wait_for_payload_replicas_to_settle()


def test_replica_query_only_tracks_this_scenarios_payloads(scenario, monkeypatch):
    query = Mock(return_value=f"instance.json|2\n{scenario.payload_names[0]}|2\n{scenario.payload_names[1]}|1\nother-file|4\n")
    monkeypatch.setattr(live.subprocess, "check_output", query)

    assert scenario.get_payload_replica_states() == [(scenario.payload_names[0], "2"), (scenario.payload_names[1], "1")]
    assert query.call_args.args[0] == [
        "iquest", "%s|%s", "SELECT DATA_NAME, DATA_REPL_STATUS " + f"WHERE COLL_NAME = '{scenario.destination}'",
    ]


@pytest.mark.parametrize("message,empty", [("CAT_NO_ROWS_FOUND", True), ("CAT_INSUFFICIENT_PRIVILEGE", False)])
def test_absent_replicas_are_distinct_from_query_failure(scenario, monkeypatch, message, empty):
    error = live.subprocess.CalledProcessError(1, ["iquest"], output=message)
    monkeypatch.setattr(live.subprocess, "check_output", Mock(side_effect=error))
    if empty:
        assert scenario.get_payload_replica_states() == []
    else:
        with pytest.raises(live.subprocess.CalledProcessError):
            scenario.get_payload_replica_states()


def test_checksum_assertions_follow_post_ingest_completion(scenario, monkeypatch):
    events = []
    values = {"ingestTransferState": "finished", "ingestStopRequested": "false", "ingestWorkerResult": "exited"}
    monkeypatch.setattr(scenario, "get_dropzone_avu", lambda attribute: values[attribute])
    monkeypatch.setattr(scenario, "restart_ingest", lambda: events.append("restart"))
    monkeypatch.setattr(scenario, "wait_for_ingested_state", lambda: events.append("ingested"))
    monkeypatch.setattr(scenario, "wait_for_dropzone_removal_to_be_scheduled", lambda: events.append("finalized"))
    monkeypatch.setattr(live.subprocess, "check_call", lambda argv: events.append(argv[:2]))
    monkeypatch.setattr(live, "get_irsync_pids_from_log", Mock(return_value=[44]))

    scenario.restart_and_verify_ingest()

    assert events == ["restart", "ingested", "finalized", ["ichksum", "-Mr"], ["ichksum", "-K"]]


def test_teardown_waits_for_payload_write_before_removing_data(scenario, monkeypatch):
    events = []
    monkeypatch.setattr(scenario, "get_dropzone_avu", Mock(return_value="finished"))
    monkeypatch.setattr(scenario, "wait_for_payload_replicas_to_settle", lambda: events.append("settled"))
    monkeypatch.setattr(scenario, "cleanup_dropzone", lambda: events.append("dropzone"))
    monkeypatch.setattr(live, "remove_project", lambda path: events.append("project"))

    scenario.teardown()

    assert events == ["settled", "dropzone", "project"]


@pytest.mark.parametrize("preparation_fails", [False, True])
def test_setup_registers_teardown_before_preparing_ingest(scenario, monkeypatch, tmp_path, preparation_fails):
    monkeypatch.setenv("STOP_INGEST_TEST_TYPE", scenario.dropzone_type)
    finalizers = []
    request = SimpleNamespace(addfinalizer=finalizers.append)
    prepare = Mock(side_effect=RuntimeError("preparation failed") if preparation_fails else None)
    teardown = Mock()
    monkeypatch.setattr(scenario, "prepare_ingest", prepare)
    monkeypatch.setattr(scenario, "teardown", teardown)

    if preparation_fails:
        with pytest.raises(RuntimeError, match="preparation failed"):
            live.BaseTestCaseStopIngest.setup.__wrapped__(scenario, request, tmp_path)
    else:
        live.BaseTestCaseStopIngest.setup.__wrapped__(scenario, request, tmp_path)

    prepare.assert_called_once_with(tmp_path)
    assert len(finalizers) == 1
    finalizers[0]()
    teardown.assert_called_once_with()


def test_cleanup_cancels_only_this_dropzones_removal_rules_before_deleting(scenario, monkeypatch):
    scenario.token = "test-zone"
    commands = []

    def query(argv, **kwargs):
        commands.append(argv)
        return "123\n456\n" if "RULE_EXEC_ID" in argv[-1] else "ingest-host\n"

    monkeypatch.setattr(live.subprocess, "check_output", query)
    monkeypatch.setattr(live.subprocess, "check_call", commands.append)
    monkeypatch.setattr(scenario, "get_dropzone_avu", Mock(return_value="ingested"))

    scenario.cleanup_dropzone()

    assert commands[0] == [
        "iquest", "%s", "SELECT RULE_EXEC_ID WHERE RULE_EXEC_NAME LIKE "
        f"'%removeDropzone(''{scenario.dropzone_path}'',%'",
    ]
    assert commands[1:3] == [["iqdel", "123"], ["iqdel", "456"]]
    assert commands[3] == ["ichmod", "-rM", "own", "rods", scenario.dropzone_path]
    assert commands[-1][0] == "irule"
    assert f"removeDropzone('{scenario.dropzone_path}'," in commands[-1][3]


def test_cleanup_cancels_pending_rule_even_if_dropzone_was_already_deleted(scenario, monkeypatch):
    monkeypatch.setattr(live.subprocess, "check_output", Mock(return_value="123\n"))
    delete = Mock()
    monkeypatch.setattr(live.subprocess, "check_call", delete)
    monkeypatch.setattr(scenario, "get_dropzone_avu", Mock(return_value=""))

    scenario.cleanup_dropzone()

    delete.assert_called_once_with(["iqdel", "123"])


@pytest.mark.parametrize("message,absent", [("CAT_NO_ROWS_FOUND", True), ("CAT_INSUFFICIENT_PRIVILEGE", False)])
def test_cleanup_distinguishes_empty_queue_from_query_failure(scenario, monkeypatch, message, absent):
    error = live.subprocess.CalledProcessError(1, ["iquest"], output=message)
    monkeypatch.setattr(live.subprocess, "check_output", Mock(side_effect=error))
    delete = Mock()
    monkeypatch.setattr(live.subprocess, "check_call", delete)
    monkeypatch.setattr(scenario, "get_dropzone_avu", Mock(return_value=""))

    if absent:
        scenario.cleanup_dropzone()
    else:
        with pytest.raises(live.subprocess.CalledProcessError):
            scenario.cleanup_dropzone()
    delete.assert_not_called()


def test_two_payloads_leave_work_for_both_stop_cycles(tmp_path, monkeypatch):
    case = live.TestStopDirectIngestUM()
    case.file_size = 64
    case.token = "test-zone"
    case.dropzone_path = "/nlmumc/ingest/direct/test-zone"
    commands = []
    monkeypatch.setattr(live.subprocess, "check_call", commands.append)
    monkeypatch.setattr(live, "run_rule", Mock())

    case.add_data_to_dropzone(tmp_path)

    uploads = [command for command in commands if command[0] == "iput"]
    assert len(uploads) == 2
    assert [command[-1] for command in uploads] == [case.dropzone_path + "/" + name for name in case.payload_names]
    assert case.source_file.stat().st_size == 64
