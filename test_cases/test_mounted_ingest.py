import subprocess

from test_cases.base_ingest_test_case import BaseTestCaseIngest


class TestMountedIngest(BaseTestCaseIngest):
    dropzone_type = "mounted"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        # TODO improve how to retrieve instance.json & schema.json
        copy_instance = 'cp instance.json /mnt/ingest/zones/{}/instance.json'.format(token)
        subprocess.check_call(copy_instance, shell=True)

        copy_schema = 'cp schema.json /mnt/ingest/zones/{}/schema.json'.format(token)
        subprocess.check_call(copy_schema, shell=True)
