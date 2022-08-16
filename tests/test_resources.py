import json
import subprocess


def test_get_resource_size_for_all_collections():
    rule = "/rules/tests/run_test.sh -r get_resource_size_for_all_collections"
    ret = subprocess.check_output(rule, shell=True)

    assert json.loads(ret) == {}


def test_list_destination_resources_status():
    rule = "/rules/tests/run_test.sh -r list_destination_resources_status"
    ret = subprocess.check_output(rule, shell=True)

    resources = json.loads(ret)
    assert resources is not None
    assert resources[0]["name"] == "replRescUM01"
    assert resources[0]["comment"] == "Replicated-resource-for-UM"
    assert resources[0]["available"] is True
