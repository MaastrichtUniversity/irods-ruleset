import json
from pathlib import Path
import subprocess
import uuid

import pytest


pytestmark = pytest.mark.parallel
RULES = Path(__file__).resolve().parents[1] / "native_irods_ruleset" / "misc"


@pytest.fixture(scope="module")
def avu_objects():
    identifier = uuid.uuid4().hex
    collection = "/nlmumc/avu-helper-" + identifier
    resource = "avu-helper-" + identifier
    subprocess.check_call(["imkdir", collection])
    try:
        subprocess.check_call(["iadmin", "mkresc", resource, "passthru"])
        try:
            for kind, name in (("-C", collection), ("-R", resource)):
                for attribute, value, unit in (("target", "value", "unit"), ("target_extra", "wrong", ""),
                                               ("literal_%", "literal", ""), ("literal_other", "wrong", ""),
                                               ("multi", "alpha", "a"), ("multi", "omega", "b")):
                    subprocess.check_call(["imeta", "add", kind, name, attribute, value, unit])
            yield collection, resource
        finally:
            subprocess.check_call(["iadmin", "rmresc", resource])
    finally:
        subprocess.check_call(["irm", "-rf", collection])


def read_avu(rule, name, attribute, default="fallback", fatal="false", installed=False):
    if installed:
        parameters = [json.dumps(name), json.dumps(attribute)]
        if rule == "getCollectionAVUTriple":
            parameters += [json.dumps(default), json.dumps(fatal), "*result"]
        else:
            parameters += ["*result", json.dumps(default), json.dumps(fatal)]
        expression = f"{rule}({','.join(parameters)}); writeLine('stdout', *result)"
        return subprocess.check_output(
            ["irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance", expression, "null", "ruleExecOut"],
            text=True, stderr=subprocess.STDOUT,
        ).strip()
    path_argument = {"getCollectionAVU": "collName", "getCollectionAVUTriple": "path", "getResourceAVU": "resourceName"}[rule]
    command = ["irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance", "-F", str(RULES / (rule + ".r"))]
    command += [f"*{key}='{value}'" for key, value in ((path_argument, name), ("attribute", attribute),
                                                     ("overrideValue", default), ("fatal", fatal))]
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()


@pytest.mark.parametrize("rule", ["getCollectionAVU", "getResourceAVU", "getCollectionAVUTriple"])
@pytest.mark.parametrize("installed", [False, True])
def test_native_avu_exact_attribute_and_fallbacks(avu_objects, rule, installed):
    collection, resource = avu_objects
    name = resource if rule == "getResourceAVU" else collection
    value = read_avu(rule, name, "target", fatal="true", installed=installed)
    if rule == "getCollectionAVUTriple":
        assert json.loads(value) == [{"attribute": "target", "value": "value", "unit": "unit"}]
        assert json.loads(read_avu(rule, name, "literal_%", installed=installed))[0]["value"] == "literal"
    else:
        assert value == "value"
        assert read_avu(rule, name, "literal_%", installed=installed) == "literal"
    assert read_avu(rule, name, "absent", installed=installed) == "fallback"
    assert read_avu(rule, name, "absent", default="", installed=installed) == ""
    with pytest.raises(subprocess.CalledProcessError) as error:
        read_avu(rule, name, "absent", fatal="true", installed=installed)
    assert "has no value in iCAT" in error.value.output


@pytest.mark.parametrize("installed", [False, True])
def test_native_avu_triples_preserve_all_values_and_units(avu_objects, installed):
    collection, _ = avu_objects
    values = json.loads(read_avu("getCollectionAVUTriple", collection, "multi", fatal="true", installed=installed))
    assert sorted(values, key=lambda row: row["value"]) == [
        {"attribute": "multi", "value": "alpha", "unit": "a"},
        {"attribute": "multi", "value": "omega", "unit": "b"},
    ]
