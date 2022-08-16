import json
import subprocess


def test_projects():
    rule = '/rules/tests/run_test.sh -r list_projects -a "false"'
    ret = subprocess.check_output(rule, shell=True)

    projects = json.loads(ret)["projects"]
    assert projects is not None
    assert len(projects) == 7
    assert projects[0]["title"] == "(MDL) Placeholder project"
