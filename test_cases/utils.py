import subprocess

from dhpythonirodsutils import formatters


# TODO improve how to retrieve instance.json & schema.json

def add_metadata_files_to_mounted_dropzone(token):
    copy_instance = 'cp instance.json /mnt/ingest/zones/{}/instance.json'.format(token)
    subprocess.check_call(copy_instance, shell=True)

    copy_schema = 'cp schema.json /mnt/ingest/zones/{}/schema.json'.format(token)
    subprocess.check_call(copy_schema, shell=True)


def add_metadata_files_to_direct_dropzone(token):
    instance_path = formatters.format_instance_dropzone_path(token, "direct")
    iput_instance = "iput -R stagingResc01 instance.json {}".format(instance_path)
    subprocess.check_call(iput_instance, shell=True)

    schema_path = formatters.format_schema_dropzone_path(token, "direct")
    iput_schema = "iput -R stagingResc01 schema.json {}".format(schema_path)
    subprocess.check_call(iput_schema, shell=True)
