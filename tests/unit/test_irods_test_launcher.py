import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def launcher(tmp_path):
    default = Path(__file__).resolve().parents[2].parent.parent / "rit.sh"
    script = Path(os.environ.get("IRODS_TEST_LAUNCHER", default))
    if not script.is_file():
        pytest.skip("Set IRODS_TEST_LAUNCHER to the docker-dev rit.sh")
    # The test branch only needs the library to exist; Docker is replaced below.
    (tmp_path / "lib-dh.sh").write_text("")
    docker = tmp_path / "docker"
    docker.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
log = pathlib.Path(os.environ["MOCK_DOCKER_LOG"])
with log.open("a") as output:
    output.write(json.dumps(sys.argv[1:]) + "\\n")
statuses = json.loads(os.environ["MOCK_DOCKER_STATUSES"])
index = len(log.read_text().splitlines()) - 1
sys.exit(statuses[index] if index < len(statuses) else 0)
''')
    docker.chmod(0o755)
    log = tmp_path / "calls"

    def run(*args, statuses=()):
        log.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f"{tmp_path}:" + os.environ["PATH"],
                   DH_ENV_HOME=str(tmp_path), MOCK_DOCKER_LOG=str(log),
                   MOCK_DOCKER_STATUSES=json.dumps(statuses))
        result = subprocess.run(["bash", str(script), "test", "irods", *args],
                                env=env, capture_output=True, text=True, timeout=10)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result.returncode, calls

    return run


def test_default_phases_and_hosts(launcher):
    code, calls = launcher()
    assert code == 0 and len(calls) == 3
    assert calls[0][-7:] == ["-n", "3", "--dist", "loadgroup", "-m", "parallel", "/rules/test_cases/"]
    assert calls[1][-3:] == ["-m", "not parallel", "/rules/test_cases/"]
    assert "-n" not in calls[1] and "dev-icat-1" in calls[1]
    assert "STOP_INGEST_TEST_TYPE=mounted" in calls[2]
    assert "dev-ires-hnas-um-1" in calls[2]


@pytest.mark.parametrize("args,workers", [
    (("--workers", "2", "test_resources.py"), "2"),
    (("test_resources.py", "--parallel", "--workers", "4"), "4"),
    (("--parallel", "test_resources.py"), "3"),
])
def test_custom_workers_and_selectors(launcher, args, workers):
    code, calls = launcher(*args)
    assert code == 0 and len(calls) == 2
    assert calls[0][calls[0].index("-n") + 1] == workers
    assert all(call[-1] == "/rules/test_cases/test_resources.py" for call in calls)


@pytest.mark.parametrize("args", [("--workers", "0"), ("--parallel", "--workers", "0"),
                                  ("--workers", "0", "--parallel")])
def test_zero_workers_runs_everything_sequentially(launcher, args):
    code, calls = launcher(*args)
    assert code == 0 and len(calls) == 2
    assert all("-n" not in call and "-m" not in call for call in calls)
    assert "STOP_INGEST_TEST_TYPE=mounted" in calls[1]


@pytest.mark.parametrize("statuses,expected", [((0, 5), 0), ((5, 0), 0), ((5, 5), 5)])
def test_empty_phases_and_no_matching_tests(launcher, statuses, expected):
    node = "test_tape_archive.py::test_unarchive_file"
    code, calls = launcher(node, statuses=statuses)
    assert code == expected and len(calls) == 2
    assert all(call[-1] == "/rules/test_cases/" + node for call in calls)


def test_explicit_stop_selection_runs_on_both_hosts(launcher):
    code, calls = launcher("test_stop_ingest.py", statuses=(5, 0, 0))
    assert code == 0 and len(calls) == 3
    assert "STOP_INGEST_TEST_TYPE=direct" in calls[1]
    assert "STOP_INGEST_TEST_TYPE=mounted" in calls[2]


@pytest.mark.parametrize("phase", [0, 1, 2])
@pytest.mark.parametrize("failure", [1, 2, 3, 4, 17])
def test_failures_stop_later_phases(launcher, phase, failure):
    code, calls = launcher(statuses=[0] * phase + [failure])
    assert code == failure and len(calls) == phase + 1


@pytest.mark.parametrize("args", [("--workers",), ("--workers", "-1"), ("--workers", "two"),
                                  ("--workers", "1.5"), ("--unknown",), ("first.py", "second.py")])
def test_invalid_arguments_do_not_start_docker(launcher, args):
    code, calls = launcher(*args)
    assert code == 2 and not calls
