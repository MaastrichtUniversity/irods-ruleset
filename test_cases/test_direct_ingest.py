import subprocess

from test_cases.base_ingest_test_case import BaseTestCaseIngest


class TestDirectIngest(BaseTestCaseIngest):
    dropzone_type = "direct"

    @classmethod
    def add_metadata_files_to_dropzone(cls, token):
        # TODO improve how to retrieve instance.json & schema.json
        iput_instance = "iput -R stagingResc01 instance.json /nlmumc/ingest/direct/{}/instance.json".format(token)
        subprocess.check_call(iput_instance, shell=True)

        iput_schema = "iput -R stagingResc01 schema.json /nlmumc/ingest/direct/{}/schema.json".format(token)
        subprocess.check_call(iput_schema, shell=True)
