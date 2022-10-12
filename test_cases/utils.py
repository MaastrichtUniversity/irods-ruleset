import subprocess
import requests
from os import path

from dhpythonirodsutils import formatters

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


def add_metadata_files_to_mounted_dropzone(token):
    get_instance()
    copy_instance = 'cp {} /mnt/ingest/zones/{}/instance.json'.format(TMP_INSTANCE_PATH, token)
    subprocess.check_call(copy_instance, shell=True)

    get_schema()
    copy_schema = 'cp {} /mnt/ingest/zones/{}/schema.json'.format(TMP_SCHEMA_PATH, token)
    subprocess.check_call(copy_schema, shell=True)


def add_metadata_files_to_direct_dropzone(token):
    get_instance()
    instance_path = formatters.format_instance_dropzone_path(token, "direct")
    iput_instance = "iput -R stagingResc01 {} {}".format(TMP_INSTANCE_PATH, instance_path)
    subprocess.check_call(iput_instance, shell=True)

    get_schema()
    schema_path = formatters.format_schema_dropzone_path(token, "direct")
    iput_schema = "iput -R stagingResc01 {} {}".format(TMP_SCHEMA_PATH, schema_path)
    subprocess.check_call(iput_schema, shell=True)


def revert_latest_project_number():
    run_iquest = 'iquest "%s" "SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = \'/nlmumc/projects\' and META_COLL_ATTR_NAME = \'latest_project_number\' "'
    latest_project_number = subprocess.check_output(run_iquest, shell=True).strip()
    assert latest_project_number.isdigit()
    revert_value = int(latest_project_number) - 1

    run_set_meta = 'imeta set -C /nlmumc/projects latest_project_number {}'.format(revert_value)
    subprocess.check_call(run_set_meta, shell=True)


def remove_project(project_path):
    set_acl = 'ichmod -rM own rods {}'.format(project_path)
    subprocess.check_call(set_acl, shell=True)
    run_remove_project = 'irm -rf {}'.format(project_path)
    subprocess.check_call(run_remove_project, shell=True)


def remove_dropzone(token, dropzone_type):
    dropzone_path = formatters.format_dropzone_path(token, dropzone_type)
    set_dropzone_acl = 'ichmod -rM own rods {}'.format(dropzone_path)
    subprocess.check_call(set_dropzone_acl, shell=True)
    run_remove_dropzone = 'irm -rf {}'.format(dropzone_path)
    subprocess.check_call(run_remove_dropzone, shell=True)
