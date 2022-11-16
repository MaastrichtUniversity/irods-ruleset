import json
import subprocess
import time
from os import path

import requests
from dhpythonirodsutils import formatters, validators

TMP_INSTANCE_PATH = "/tmp/metadata_instance.json"
TMP_SCHEMA_PATH = "/tmp/metadata_schema.json"


def get_instance():
    if path.exists(TMP_INSTANCE_PATH):
        return

    url = "https://gist.githubusercontent.com/JonathanMELIUS/bc9812da8c5eb946d5ef90eaf3b55b27/raw/a36e19ab313986177366b6041afcdb089b03c8b0/instance.json"
    response = requests.get(url)

    with open(TMP_INSTANCE_PATH, "w") as json_file:
        json_file.write(response.content)


def get_schema():
    if path.exists(TMP_SCHEMA_PATH):
        return

    url = "https://gist.githubusercontent.com/JonathanMELIUS/bc9812da8c5eb946d5ef90eaf3b55b27/raw/a36e19ab313986177366b6041afcdb089b03c8b0/schema.json"
    response = requests.get(url)

    with open(TMP_SCHEMA_PATH, "w") as json_file:
        json_file.write(response.content)


def add_metadata_files_to_dropzone(token, dropzone_type):
    get_instance()
    instance_path = formatters.format_instance_dropzone_path(token, dropzone_type)
    iput_instance = "iput -R stagingResc01 {} {}".format(TMP_INSTANCE_PATH, instance_path)
    subprocess.check_call(iput_instance, shell=True)

    get_schema()
    schema_path = formatters.format_schema_dropzone_path(token, dropzone_type)
    iput_schema = "iput -R stagingResc01 {} {}".format(TMP_SCHEMA_PATH, schema_path)
    subprocess.check_call(iput_schema, shell=True)


def add_metadata_files_to_mounted_dropzone(token):
    add_metadata_files_to_dropzone(token, "mounted")


def add_metadata_files_to_direct_dropzone(token):
    add_metadata_files_to_dropzone(token, "direct")


def revert_latest_project_number():
    run_iquest = "iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '/nlmumc/projects' and META_COLL_ATTR_NAME = 'latest_project_number' \""
    latest_project_number = subprocess.check_output(run_iquest, shell=True).strip()
    assert latest_project_number.isdigit()
    revert_value = int(latest_project_number) - 1

    run_set_meta = "imeta set -C /nlmumc/projects latest_project_number {}".format(revert_value)
    subprocess.check_call(run_set_meta, shell=True)


def remove_project(project_path):
    set_acl = "ichmod -rM own rods {}".format(project_path)
    subprocess.check_call(set_acl, shell=True)
    run_remove_project = "irm -rf {}".format(project_path)
    subprocess.check_call(run_remove_project, shell=True)


def remove_dropzone(token, dropzone_type):
    dropzone_path = formatters.format_dropzone_path(token, dropzone_type)
    set_dropzone_acl = "ichmod -rM own rods {}".format(dropzone_path)
    subprocess.check_call(set_dropzone_acl, shell=True)
    run_remove_dropzone = "irm -rf {}".format(dropzone_path)
    subprocess.check_call(run_remove_dropzone, shell=True)


def create_project(test_case):
    rule_create_new_project = "/rules/tests/run_test.sh -r create_new_project -a \"{},{},{},{},{},{},{{'enableDropzoneSharing':'true'}}\"".format(
        test_case.ingest_resource,
        test_case.destination_resource,
        test_case.project_title,
        test_case.manager1,
        test_case.manager2,
        test_case.budget_number,
    )
    ret_create_new_project = subprocess.check_output(rule_create_new_project, shell=True)

    project = json.loads(ret_create_new_project)
    assert validators.validate_project_id(str(project["project_id"]))
    assert validators.validate_project_path(project["project_path"])

    rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(
        test_case.manager1, project["project_path"]
    )
    subprocess.check_call(rule_set_acl, shell=True)
    rule_set_acl = '/rules/tests/run_test.sh -r set_acl -a "default,own,{},{}"'.format(
        test_case.manager2, project["project_path"]
    )
    subprocess.check_call(rule_set_acl, shell=True)

    return project


def create_dropzone(test_case):
    rule_create_drop_zone = '/rules/tests/run_test.sh -r create_drop_zone -a "{},{},{},{},{},{}"'.format(
        test_case.dropzone_type,
        test_case.depositor,
        test_case.project_id,
        test_case.collection_title,
        test_case.schema_name,
        test_case.schema_version,
    )
    ret_create_drop_zone = subprocess.check_output(rule_create_drop_zone, shell=True)
    token = json.loads(ret_create_drop_zone)

    return token


def start_and_wait_for_ingest(test_case):
    rule_start_ingest = '/rules/tests/run_test.sh -r start_ingest -a "{},{},{}" -u "{}"'.format(
        test_case.depositor, test_case.token, test_case.dropzone_type, test_case.depositor
    )
    subprocess.check_call(rule_start_ingest, shell=True)
    print("Starting {} ingestion of '{}'".format(test_case.dropzone_type, test_case.token))
    rule_get_active_drop_zone = '/rules/tests/run_test.sh -r get_active_drop_zone -a "{},false,{}"'.format(
        test_case.token, test_case.dropzone_type
    )
    ret_get_active_drop_zone = subprocess.check_output(rule_get_active_drop_zone, shell=True)

    drop_zone = json.loads(ret_get_active_drop_zone)
    assert drop_zone["token"] == test_case.token

    fail_safe = 100
    while fail_safe != 0:
        ret_get_active_drop_zone = subprocess.check_output(rule_get_active_drop_zone, shell=True)

        drop_zone = json.loads(ret_get_active_drop_zone)
        if drop_zone["state"] == "ingested":
            fail_safe = 0
        else:
            fail_safe = fail_safe - 1
            time.sleep(3)
    assert drop_zone["state"] == "ingested"
    print("Dropzone ingested, continuing tests")


def does_path_exist(absolute_path):
    run_ilocate = "ilocate {}".format(absolute_path)
    try:
        subprocess.check_output(run_ilocate, shell=True).strip()
    except subprocess.CalledProcessError:
        return False

    return True


def set_collection_avu(collection_path, attribute, value):
    run_imeta = 'imeta set -C {} {} "{}"'.format(
        collection_path, attribute, value
    )
    subprocess.check_call(run_imeta, shell=True)


def create_user(username):
    run_imeta = 'iadmin mkuser {} rodsuser'.format(username)
    subprocess.check_call(run_imeta, shell=True)

    set_user_avu(username, "displayName", "{} LastName".format(username))
    set_user_avu(username, "eduPersonUniqueID", "{}@sram.surf.nl".format(username))
    set_user_avu(username, "email", "{}@maastrichtuniversity.nl".format(username))
    set_user_avu(username, "voPersonExternalAffiliation", "{}@maastrichtuniversity.nl".format(username))
    set_user_avu(username, "voPersonExternalID", "{}@unimaas.nl".format(username))

    run_ichmod = 'ichmod -M write {} /nlmumc/ingest/direct'.format(username)
    subprocess.check_call(run_ichmod, shell=True)


def remove_user(username):
    run_imeta = 'iadmin rmuser {}'.format(username)
    subprocess.check_call(run_imeta, shell=True)


def set_user_avu(username, attribute, value):
    run_imeta = 'imeta set -u {} {} "{}"'.format(
        username, attribute, value
    )
    subprocess.check_call(run_imeta, shell=True)


def set_irods_collection_avu(collection_path, attribute, value):
    run_imeta = 'imeta set -C {} {} "{}"'.format(
        collection_path, attribute, value
    )
    subprocess.check_call(run_imeta, shell=True)
