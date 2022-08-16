import json
import subprocess


def test_rule_get_groups():
    rule = '/rules/tests/run_test.sh -r get_groups -a "false" -j -u jmelius'
    ret = subprocess.check_output(rule, shell=True)

    groups = json.loads(ret)
    assert groups is not None
    assert len(groups) == 5
    assert groups[3]["name"] == "m4i-nanoscopy-phd0815"
    assert groups[3]["groupId"].isdigit() is True
    assert groups[3]["displayName"] == "Novel approach for smashing ions"
    assert groups[3]["description"] == "CO for PhD project of P7000815"