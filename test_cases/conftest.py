import fcntl

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "parallel: safe to run alongside other parallel tests")
    if config.getoption("numprocesses", 0) and pytest.version_tuple >= (9, 2):
        raise pytest.UsageError(
            "Parallel tests require pytest>=7,<9.2 and pytest-xdist>=3.8; "
            "install the ruleset test dependencies or use --workers 0"
        )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    if not (hasattr(config, "workerinput") or config.getoption("numprocesses", 0)):
        return
    # Add groups before xdist appends them to node IDs. Ingest scenarios
    # already carry their own class/scenario groups.
    for item in items:
        if item.get_closest_marker("parallel") and item.cls and "ingest_scenario" not in item.fixturenames:
            item.add_marker(pytest.mark.xdist_group(item.nodeid.rsplit("::", 1)[0]))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_finish(session):
    # Check only the selection left after pytest has applied -m/-k filters.
    config = session.config
    if not session.items or not (hasattr(config, "workerinput") or config.getoption("numprocesses", 0)):
        return
    if any(not item.get_closest_marker("parallel") for item in session.items):
        raise pytest.UsageError("Unmarked tests must run sequentially; select -m parallel or use -n 0")
    if config.getoption("dist") != "loadgroup" and not config.getoption("loadgroup", False):
        raise pytest.UsageError("Parallel tests require --dist=loadgroup")


@pytest.fixture(scope="session", autouse=True)
def parallel_index(request, tmp_path_factory):
    if not hasattr(request.config, "workerinput"):
        return

    from test_cases.utils import run_index_all_project_collections_metadata

    shared_directory = tmp_path_factory.getbasetemp().parent
    ready = shared_directory / "parallel-index-ready"
    with (shared_directory / "parallel-index.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not ready.exists():
            run_index_all_project_collections_metadata()
            ready.touch()
