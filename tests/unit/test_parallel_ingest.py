from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from test_cases import base_ingest_test_case as ingest
from test_cases import conftest as ingest_config
from test_cases import utils


def _prepare_worker(directory, number):
    directory = Path(directory)
    worker_directory = directory / f"worker-{number}"
    worker_directory.mkdir()

    def record(event):
        with (directory / "events").open("a") as output:
            output.write(event + "\n")

    utils.run_index_all_project_collections_metadata = lambda: record("index")
    request = SimpleNamespace(config=SimpleNamespace(workerinput={}))
    factory = SimpleNamespace(getbasetemp=lambda: worker_directory)
    ingest_config.parallel_index.__wrapped__(request, factory)
    with ingest.ingest_preparation(request, factory):
        record(f"enter-{number}")
        time.sleep(0.03)
        record(f"exit-{number}")


def test_parallel_preparation_resets_index_once_and_excludes_other_workers(tmp_path):
    context = multiprocessing.get_context("spawn")
    processes = [context.Process(target=_prepare_worker, args=(tmp_path, i)) for i in range(4)]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
                process.join()

    events = (tmp_path / "events").read_text().splitlines()
    assert events.count("index") == 1
    assert events[0] == "index"
    for enter, exit in zip(events[1::2], events[2::2]):
        assert enter.replace("enter-", "exit-") == exit
    assert len(events) == 9


def test_sequential_preparation_retains_per_scenario_index_reset(monkeypatch):
    resets = []
    monkeypatch.setattr(ingest, "run_index_all_project_collections_metadata", lambda: resets.append(True))
    request = SimpleNamespace(config=SimpleNamespace())
    for _ in range(2):
        with ingest.ingest_preparation(request, None):
            pass
    assert len(resets) == 2


def test_parallel_ingest_accepts_worker_loadgroup_option():
    config = SimpleNamespace(
        workerinput={}, getoption=lambda name, default=None: {"dist": "no", "loadgroup": True}.get(name, default),
    )
    ingest_config.pytest_collection_finish(SimpleNamespace(config=config, items=[
        SimpleNamespace(fixturenames=["ingest_scenario"], cls=None, get_closest_marker=lambda name: True),
    ]))


def test_parallel_ingest_rejects_schedulers_that_split_scenarios():
    config = SimpleNamespace(
        workerinput={}, getoption=lambda name, default=None: {"dist": "no", "loadgroup": False}.get(name, default),
    )
    with pytest.raises(pytest.UsageError, match="--dist=loadgroup"):
        ingest_config.pytest_collection_finish(SimpleNamespace(config=config, items=[
            SimpleNamespace(fixturenames=["ingest_scenario"], cls=None, get_closest_marker=lambda name: True),
        ]))


def test_incompatible_pytest_is_rejected_before_workers_start(monkeypatch):
    monkeypatch.setattr(pytest, "version_tuple", (9, 2, 0))
    config = SimpleNamespace(getoption=lambda name, default=None: 3, addinivalue_line=lambda *args: None)
    with pytest.raises(pytest.UsageError, match="pytest>=7,<9.2"):
        ingest_config.pytest_configure(config)


def test_xdist_keeps_each_scenario_fixture_on_one_worker(tmp_path):
    (tmp_path / "conftest.py").write_text('''from pathlib import Path
from test_cases import utils
pytest_plugins = ["test_cases.conftest"]

def pytest_configure(config):
    def reset_index():
        with Path(__file__).with_suffix(".index").open("a") as output:
            output.write("index\\n")
    utils.run_index_all_project_collections_metadata = reset_index
''')
    module = tmp_path / "test_grouping.py"
    module.write_text('''import json
from pathlib import Path
import pytest
from test_cases.base_ingest_test_case import INGEST_SCENARIOS

pytestmark = pytest.mark.parallel

class Base:
    @pytest.fixture(scope="class", autouse=True)
    @staticmethod
    def ingest_scenario(request):
        with Path(__file__).with_suffix(".setups").open("a") as output:
            output.write(json.dumps([request.cls.__name__, request.param]) + "\\n")
        yield

    def test_one(self):
        pass

    def test_two(self):
        pass

@pytest.mark.parametrize("ingest_scenario", INGEST_SCENARIOS, indirect=True, scope="class")
@pytest.mark.xdist_group("direct")
class TestDirect(Base):
    pass

@pytest.mark.parametrize("ingest_scenario", INGEST_SCENARIOS, indirect=True, scope="class")
@pytest.mark.xdist_group("mounted")
class TestMounted(Base):
    pass

class TestIndependentOne:
    @classmethod
    def setup_class(cls):
        cls.order = []
        with Path(__file__).with_suffix(".setups").open("a") as output:
            output.write(json.dumps([cls.__name__]) + "\\n")

    def test_one(self):
        self.order.append(1)

    def test_two(self):
        assert self.order == [1]

class TestIndependentTwo(TestIndependentOne):
    pass
''')
    root = str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-n", "2",
         "--dist", "loadgroup", str(module)],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=root), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    setups = module.with_suffix(".setups").read_text().splitlines()
    assert len(setups) == len(set(setups)) == 14
    assert (tmp_path / "conftest.index").read_text().splitlines() == ["index"]


@pytest.mark.parametrize("project, matches", [("P000000001", True), ("P000000002", False)])
def test_progress_log_must_belong_to_this_collection(monkeypatch, project, matches):
    case = SimpleNamespace(
        project_path="/nlmumc/projects/P000000001", collection_id="C000000001",
        log_position_before_ingest=0, dropzone_total_size="63169378",
        SIZE_INGESTED_LOG_DETECTION_TIMEOUT_SECONDS=10,
    )
    message = f"/nlmumc/projects/{project}/C000000001: Remove AVU 'sizeIngested':'63169378'"
    monkeypatch.setattr(ingest, "wait_for_log_matching", lambda offset, predicate, timeout: predicate(message))
    if matches:
        ingest.BaseTestCaseIngest.test_size_ingested_avu(None, case)
    else:
        with pytest.raises(pytest.fail.Exception):
            ingest.BaseTestCaseIngest.test_size_ingested_avu(None, case)


@pytest.mark.parametrize("selection,workers,phases", [
    ((), 0, [1, 2, 3]),
    ((), 2, [1, 2, 3]),
    (("TestEditCollectionMetadata",), 0, [2]),
    (("TestChangeCollectionMetadataSchema",), 2, [2, 3]),
    (("TestIngest",), 0, [1]),
    (("TestChangeCollectionMetadataSchema", "TestIngest", "TestEditCollectionMetadata"), 0, [1, 2, 3]),
])
def test_shared_lifecycle_and_standalone_class_selection(tmp_path, selection, workers, phases):
    (tmp_path / "conftest.py").write_text('''from pathlib import Path
from test_cases import base_ingest_test_case as ingest, utils
from test_cases import base_customizable_metadata_test_case as metadata
import json
import uuid

pytest_plugins = ["test_cases.conftest"]

def record(scenario, phase):
    with Path(__file__).with_suffix(".events").open("a") as output:
        output.write(json.dumps([scenario.project_path, phase]) + "\\n")

def create_project(scenario):
    project = f"P{uuid.uuid4().int % 10**9:09d}"
    return {"project_id": project, "project_path": f"/nlmumc/projects/{project}"}

def remove_project(project):
    with Path(__file__).with_suffix(".events").open("a") as output:
        output.write(json.dumps([project, "cleanup"]) + "\\n")

def pytest_configure(config):
    utils.run_index_all_project_collections_metadata = lambda: None
    ingest.run_index_all_project_collections_metadata = lambda: None
    ingest.create_project = create_project
    ingest.create_dropzone = lambda scenario: "token"
    ingest.get_log_position = lambda: 0
    ingest.start_and_wait_for_ingest = lambda scenario: record(scenario, 1)
    ingest.wait_for_set_acl_for_metadata_snapshot_to_finish = lambda project: None
    ingest.remove_project = remove_project
    ingest.subprocess.check_call = lambda *args, **kwargs: None
    metadata.edit_collection_metadata = lambda scenario, edit: record(scenario, scenario.metadata_version)
''')
    module = tmp_path / "test_lifecycle.py"
    module.write_text('''import pytest
from test_cases.base_ingest_test_case import (
    BaseIngestScenario, INGEST_SCENARIOS,
    ingest_scenario, edited_collection, schema_changed_collection,
)

pytestmark = [
    pytest.mark.parallel,
    pytest.mark.parametrize("ingest_scenario", INGEST_SCENARIOS, indirect=True, scope="module"),
    pytest.mark.xdist_group("direct"),
]

class IngestScenario(BaseIngestScenario):
    def calculate_all_dropzone_sizes(self):
        pass

class TestIngest:
    lifecycle_phase = 0

    def test_first(self, ingest_scenario):
        assert not hasattr(ingest_scenario, "metadata_version")

    def test_second(self, ingest_scenario):
        assert not hasattr(ingest_scenario, "metadata_version")

class TestEditCollectionMetadata:
    lifecycle_phase = 1

    def test_first(self, edited_collection):
        assert edited_collection.metadata_version == 2

    def test_second(self, edited_collection):
        assert edited_collection.metadata_version == 2

class TestChangeCollectionMetadataSchema:
    lifecycle_phase = 2

    def test_first(self, schema_changed_collection):
        assert schema_changed_collection.metadata_version == 3

    def test_second(self, schema_changed_collection):
        assert schema_changed_collection.metadata_version == 3
''')
    options = ["-n", str(workers), "--dist", "loadgroup"] if workers else []
    nodes = [f"{module}::{name}" for name in selection] if selection else [str(module)]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *options, *nodes],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2])),
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    projects = {}
    for line in (tmp_path / "conftest.events").read_text().splitlines():
        project, phase = json.loads(line)
        projects.setdefault(project, []).append(phase)
    assert len(projects) == len(ingest.INGEST_SCENARIOS)
    expected = ([1] if phases[0] != 1 else []) + phases + ["cleanup"]
    assert all(events == expected for events in projects.values())


def test_direct_payloads_do_not_share_scratch_files(monkeypatch):
    barrier = threading.Barrier(2)
    uploaded = []

    def upload(command):
        source = Path(command[-2])
        barrier.wait(timeout=5)
        assert source.read_bytes() == b"0" * 12
        uploaded.append(source)

    monkeypatch.setattr(utils.subprocess, "check_call", upload)
    cases = [SimpleNamespace(token=token, dropzone_type="direct", files_per_protocol={"50K' and data.file": 12})
             for token in ("first-token", "second-token")]
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(utils.add_data_to_direct_dropzone, cases))
    assert len(set(uploaded)) == 2
    assert all(not source.exists() for source in uploaded)


def test_mounted_payloads_are_created_in_their_own_dropzones(tmp_path):
    source = (Path(__file__).resolve().parents[2] / "utils/createFakeFiles.r").read_text().split("\nINPUT ")[0]

    def create(number):
        directory = tmp_path / str(number)
        directory.mkdir()

        def remote(host, engine, code, output):
            namespace = {}
            exec(code, namespace)
            namespace["main"]([], None, None)

        namespace = {"global_vars": {"*dropzonePath": f'"{directory}"', "*remoteResource": '"host"'}}
        exec(source, namespace)
        namespace["main"]([], SimpleNamespace(py_remote=remote), None)
        return {file.name: file.stat().st_size for file in directory.iterdir()}

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, range(2)))
    assert results == [{"0bytes.devfile": 0, "50K.devfile": 51200,
                        "15M.devfile": 15728640, "45M.devfile": 47185920}] * 2
