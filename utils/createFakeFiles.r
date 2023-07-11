# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/utils/createFakeFiles.r '*dropzonePath="/mnt/ingest/zones/foo-bar"' '*remoteResource="ires-hnas-um.dh.local"'

def main(rule_args, callback, rei):
    dropzone_path = global_vars['*dropzonePath'][1:-1]
    remote_resource = global_vars['*remoteResource'][1:-1]
    rule_code=\
    '''def main(rule_args,callback,rei):
          import subprocess
          subprocess.check_call("touch /tmp/0bytes.devfile && fallocate -l 50K /tmp/50K.devfile && fallocate -l 15M /tmp/15M.devfile && fallocate -l 45M /tmp/45M.devfile", shell=True)
          subprocess.check_call("mv /tmp/*.devfile {}", shell=True)
    '''.format(dropzone_path)
    callback.py_remote(remote_resource, '<INST_NAME>irods_rule_engine_plugin-python-instance</INST_NAME>', rule_code, '')

INPUT *dropzonePath="", *remoteResource=""
OUTPUT ruleExecOut
