import json
import os
import subprocess
import time
import uuid
from os import path
from typing import Callable

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
        json_file.write(response.text)


def get_schema():
    if path.exists(TMP_SCHEMA_PATH):
        return

    url = "https://gist.githubusercontent.com/JonathanMELIUS/bc9812da8c5eb946d5ef90eaf3b55b27/raw/a36e19ab313986177366b6041afcdb089b03c8b0/schema.json"
    response = requests.get(url)

    with open(TMP_SCHEMA_PATH, "w") as json_file:
        json_file.write(response.text)


def add_metadata_files_to_dropzone(token, dropzone_type):
    get_instance()
    instance_path = formatters.format_instance_dropzone_path(token, dropzone_type)
    iput_instance = f"iput -R stagingResc01 {TMP_INSTANCE_PATH} {instance_path}"
    subprocess.check_call(iput_instance, shell=True)

    get_schema()
    schema_path = formatters.format_schema_dropzone_path(token, dropzone_type)
    iput_schema = f"iput -R stagingResc01 {TMP_SCHEMA_PATH} {schema_path}"
    subprocess.check_call(iput_schema, shell=True)


def add_metadata_files_to_mounted_dropzone(token):
    add_metadata_files_to_dropzone(token, "mounted")


def add_metadata_files_to_direct_dropzone(token):
    add_metadata_files_to_dropzone(token, "direct")


def add_data_to_direct_dropzone(dropzone_info):
    for filename, size in dropzone_info.files_per_protocol.items():
        file_path = f"/tmp/{filename}"
        dropzone_path = formatters.format_dropzone_path(
            dropzone_info.token, dropzone_info.dropzone_type
        )
        logical_path = f"{dropzone_path}/{filename}"

        with open(file_path, "wb") as file_buffer:
            file_buffer.write(b"0" * size)
        iput = f"iput -R stagingResc01 {file_path} {logical_path}"
        subprocess.check_call(iput, shell=True)


def revert_latest_project_collection_number(project_path):
    run_iquest = f"iquest \"%s\" \"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{project_path}' and META_COLL_ATTR_NAME = 'latestProjectCollectionNumber' \""
    latest_project_number = subprocess.check_output(run_iquest, shell=True).strip()
    assert latest_project_number.isdigit()
    revert_value = int(latest_project_number) - 1

    run_set_meta = f"imeta set -C {project_path} latest_project_number {revert_value}"
    subprocess.check_call(run_set_meta, shell=True)


def remove_project(project_path):
    set_acl = f"ichmod -rM own rods {project_path}"
    subprocess.check_call(set_acl, shell=True)
    run_remove_project = f"irm -rf {project_path}"
    subprocess.check_call(run_remove_project, shell=True)


def remove_dropzone(token, dropzone_type):
    dropzone_path = formatters.format_dropzone_path(token, dropzone_type)
    set_dropzone_acl = f"ichmod -rM own rods {dropzone_path}"
    subprocess.check_call(set_dropzone_acl, shell=True)
    run_remove_dropzone = f"irm -rf {dropzone_path}"
    subprocess.check_call(run_remove_dropzone, shell=True)


def create_project(test_case):
    rule_create_new_project = f"/rules/tests/run_test.sh -r create_new_project -a \"{test_case.ingest_resource},{test_case.destination_resource},{test_case.project_title},{test_case.manager1},{test_case.manager2},{test_case.budget_number},{{'enableDropzoneSharing':'true'}}\""
    ret_create_new_project = subprocess.check_output(
        rule_create_new_project, shell=True
    )

    project = json.loads(ret_create_new_project)
    assert validators.validate_project_id(str(project["project_id"]))
    assert validators.validate_project_path(project["project_path"])

    rule_set_acl = f"/rules/tests/run_test.sh -r set_acl -a \"default,own,{test_case.manager1},{project['project_path']}\""
    subprocess.check_call(rule_set_acl, shell=True)
    rule_set_acl = f"/rules/tests/run_test.sh -r set_acl -a \"default,own,{test_case.manager2},{project['project_path']}\""
    subprocess.check_call(rule_set_acl, shell=True)

    return project


def create_dropzone(test_case):
    rule_create_drop_zone = (
        f'/rules/tests/run_test.sh -r create_drop_zone -a "{test_case.dropzone_type},{test_case.depositor},{test_case.project_id},{test_case.collection_title},{test_case.schema_name},{test_case.schema_version}"'
    )
    ret_create_drop_zone = subprocess.check_output(rule_create_drop_zone, shell=True)
    token = json.loads(ret_create_drop_zone)

    return token


def start_and_wait_for_ingest(test_case):
    if test_case.dropzone_type == "direct":
        rule_set_acl_instance = f'/rules/tests/run_test.sh -r set_acl -a "default,admin:own,{test_case.depositor},{formatters.format_instance_dropzone_path(test_case.token, test_case.dropzone_type)}"'
        rule_set_acl_schema = f'/rules/tests/run_test.sh -r set_acl -a "default,admin:own,{test_case.depositor},{formatters.format_schema_dropzone_path(test_case.token, test_case.dropzone_type)}"'
        rule_set_acl_rods = f'/rules/tests/run_test.sh -r set_acl -a "recursive,admin:own,rods,{formatters.format_dropzone_path(test_case.token, test_case.dropzone_type)}"'
        subprocess.check_call(rule_set_acl_instance, shell=True)
        subprocess.check_call(rule_set_acl_schema, shell=True)
        subprocess.check_call(rule_set_acl_rods, shell=True)

    rule_start_ingest = (f'/rules/tests/run_test.sh -r start_ingest -a "{test_case.depositor},{test_case.token},{test_case.dropzone_type}"')
    subprocess.check_call(rule_start_ingest, shell=True)
    print(
        f"Starting {test_case.dropzone_type} ingestion of '{test_case.token}'"
    )
    rule_get_active_drop_zone = (
        f'/rules/tests/run_test.sh -r get_active_drop_zone -a "{test_case.token},false,{test_case.dropzone_type}"'
    )
    ret_get_active_drop_zone = subprocess.check_output(
        rule_get_active_drop_zone, shell=True
    )

    drop_zone = json.loads(ret_get_active_drop_zone)
    assert drop_zone["token"] == test_case.token

    fail_safe = 100
    while fail_safe != 0:
        ret_get_active_drop_zone = subprocess.check_output(
            rule_get_active_drop_zone, shell=True
        )

        drop_zone = json.loads(ret_get_active_drop_zone)
        if drop_zone["state"] == "ingested":
            fail_safe = 0
        else:
            fail_safe = fail_safe - 1
            time.sleep(3)
    assert drop_zone["state"] == "ingested"
    print("Dropzone ingested, continuing tests")


def wait_for_set_acl_for_metadata_snapshot_to_finish(project_id):
    """
    Wait for upto 90 seconds for the delay queue part of set_acl_for_metadata_snapshot to finish
    Continue when completed in time
    Parameters
    ----------
    project_id : str
        The project to request and set a pid for (e.g: P000000010)
    """
    cmd = f"iqstat -a | grep \"setCollectionSize('{project_id}'\""
    fail_safe = 30
    output = ""
    while fail_safe != 0:
        try:
            output = subprocess.check_output(cmd, shell=True)
            fail_safe = fail_safe - 1
            time.sleep(3)
        except subprocess.CalledProcessError:
            fail_safe = 0
            output = ""
    assert project_id not in output


def wait_for_change_project_permissions_to_finish():
    """
    Wait for upto 90 seconds for the delay queue part of changeProjectPermissions to finish
    Continue when completed in time
    """
    cmd = "iqstat -a | grep changeProjectPermission"
    fail_safe = 30
    output = ""
    while fail_safe != 0:
        try:
            output = subprocess.check_output(cmd, shell=True)
            fail_safe = fail_safe - 1
            time.sleep(3)
        except subprocess.CalledProcessError:
            fail_safe = 0
            output = ""
    assert "changeProjectPermission" not in output


def wait_for_revoke_project_collection_user_acl():
    """
    Wait for upto 90 seconds for the delay queue part of revoke_project_collection_user_acl to finish
    Continue when completed in time
    """
    cmd = "iqstat -a | grep msiSetACL"
    fail_safe = 30
    output = ""
    while fail_safe != 0:
        try:
            output = subprocess.check_output(cmd, shell=True)
            fail_safe = fail_safe - 1
            time.sleep(3)
        except subprocess.CalledProcessError:
            fail_safe = 0
            output = ""
    assert "msiSetACL" not in output


def does_path_exist(absolute_path):
    run_ilocate = f"ilocate {absolute_path}"
    try:
        subprocess.check_output(run_ilocate, shell=True).strip()
    except subprocess.CalledProcessError:
        return False

    return True


def set_collection_avu(collection_path, attribute, value):
    run_imeta = f'imeta set -C {collection_path} {attribute} "{value}"'
    subprocess.check_call(run_imeta, shell=True)


def create_user(username):
    run_imeta = f"iadmin mkuser {username} rodsuser"
    try:
        subprocess.check_call(run_imeta, shell=True)
    except subprocess.CalledProcessError:
        print(f"User {username} already exists, continuing code execution")

    set_user_avu(username, "displayName", f"{username} LastName")
    set_user_avu(username, "eduPersonUniqueID", f"{username}@sram.surf.nl")
    set_user_avu(username, "email", f"{username}@maastrichtuniversity.nl")
    set_user_avu(
        username,
        "voPersonExternalAffiliation",
        f"{username}@maastrichtuniversity.nl",
    )
    set_user_avu(username, "voPersonExternalID", f"{username}@unimaas.nl")

    run_ichmod = f"ichmod -M write {username} /nlmumc/ingest/direct"
    subprocess.check_call(run_ichmod, shell=True)


def create_data_steward(username):
    create_user(username)
    set_user_avu(username, "specialty", "data-steward")


def create_group(groupname):
    run_iadmin = f"iadmin mkgroup {groupname}"
    subprocess.check_call(run_iadmin, shell=True)
    set_user_avu(groupname, "description", f"{groupname} is a cool group!")
    set_user_avu(groupname, "displayName", f"{groupname}")
    set_user_avu(groupname, "uniqueIdentifier", f"{uuid.uuid1()!s}")


def remove_group(groupname):
    run_iadmin = f"iadmin rmgroup {groupname}"
    subprocess.check_call(run_iadmin, shell=True)


def add_user_to_group(groupname, username):
    run_iadmin = f"iadmin atg {groupname} {username}"
    subprocess.check_call(run_iadmin, shell=True)


def remove_user_from_group(groupname, username):
    run_iadmin = f"iadmin rfg {groupname} {username}"
    subprocess.check_call(run_iadmin, shell=True)


def remove_user(username):
    run_imeta = f"iadmin rmuser {username}"
    try:
        subprocess.check_call(run_imeta, shell=True)
    except subprocess.CalledProcessError:
        print(f"User {username} does not exist, continuing code execution")


def set_user_avu(username, attribute, value):
    run_imeta = f'imeta set -u {username} {attribute} "{value}"'
    subprocess.check_call(run_imeta, shell=True)


def set_irods_collection_avu(collection_path, attribute, value):
    run_imeta = f'imeta set -C {collection_path} {attribute} "{value}"'
    subprocess.check_call(run_imeta, shell=True)


def check_if_key_value_in_dict_list(dictionaries_list, key, value):
    found = False
    for dictionary in dictionaries_list:
        if dictionary[key] == value:
            found = True
    return found


def run_index_all_project_collections_metadata():
    rule = "/rules/tests/run_test.sh -r index_all_project_collections_metadata -u service-disqover"
    subprocess.check_call(rule, shell=True)


def get_project_collection_instance_in_elastic(project_id):
    elastic_host = os.environ.get("ENV_ELASTIC_HOST")
    elastic_port = os.environ.get("ENV_ELASTIC_PORT")
    elastic_password = os.environ.get("ENV_ELASTIC_PASSWORD")
    search_url = f"{elastic_host}:{elastic_port}/collection_metadata/_doc/_search"
    query = f"curl -u elastic:{elastic_password} {search_url}?q={project_id}"

    instance = ""
    # The AVU 'ingested' is set before calling index_add_single_project_collection_metadata in finish_ingest.py
    # test_elastic_index_update might be called before index_add_single_project_collection_metadata is done
    fail_safe = 30
    while fail_safe != 0:
        try:
            ret = subprocess.check_output(query, shell=True)
            result = json.loads(ret)
            instance = result["hits"]["hits"][0]["_source"]
            fail_safe = 0
        except IndexError:
            fail_safe = fail_safe - 1
            time.sleep(3)

    assert instance

    return instance


IRODS_LOG_PATH = "/var/log/irods/irods.log"


def get_log_position(log_path: str = IRODS_LOG_PATH) -> int:
    """Return the current byte offset at the end of the iRODS log file."""
    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            return f.tell()
    except OSError:
        return 0


def read_new_log_lines(from_position: int, log_path: str = IRODS_LOG_PATH) -> list:
    """
    Return all lines added to the iRODS log file since *from_position*.

    Parameters
    ----------
    from_position : int
        Byte offset to start reading from (as returned by get_log_position).
    log_path : str
        Path to the log file.

    Returns
    -------
    list[str]
    """
    try:
        with open(log_path, "r", errors="replace") as f:
            f.seek(from_position)
            return f.readlines()
    except OSError:
        return []


def wait_for_log_matching(
    from_position: int,
    predicate: Callable[[str], bool],
    timeout_seconds: int = 120,
    log_path: str = IRODS_LOG_PATH,
) -> bool:
    """
    Poll the iRODS log for any entry whose log_message satisfies *predicate*,
    up to *timeout_seconds*.

    Parameters
    ----------
    from_position : int
        Byte offset in the log file captured before the operation started.
    predicate : Callable[[str], bool]
        A function that receives the log_message string and returns True when
        the expected entry is found.
    timeout_seconds : int
        How long to wait for a matching log entry before giving up.
    log_path : str
        Path to the log file.

    Returns
    -------
    bool
        True if a matching log entry is found before the timeout,
        False otherwise.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for line in read_new_log_lines(from_position, log_path):
            try:
                entry = json.loads(line)
                log_message = entry.get("log_message", "")
                if predicate(log_message):
                    return True
            except (json.JSONDecodeError, AttributeError):
                pass
        time.sleep(2)
    return False
