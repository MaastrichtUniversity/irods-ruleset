# BEGIN temporary iRODS security mitigations
# 20260824 - remove after 5.1.0
# prevents direct Python rule execution via EXEC_RULE_EXPRESSION_AN 1206
# allows irodsDelayServer proxy for queued delay rules
pep_api_exec_rule_expression_pre(*INST, *COMM, *EXECRULE) {
 *proxy_user = *COMM.proxy_user_name
 *proxy_zone = *COMM.proxy_rods_zone
 foreach(*row in SELECT USER_TYPE where USER_NAME = '*proxy_user' and USER_ZONE = '*proxy_zone') {
   *user_type = *row.USER_TYPE;
 }
 if ("rodsadmin" != *user_type) {
   writeLine('serverLog', 'pep_api_exec_rule_expression_pre: prevented [*proxy_user#*proxy_zone] from calling rcExecRuleExpression (AN 1206)');
   failmsg(-169000, 'rcExecRuleExpression is not allowed'); # SYS_NOT_ALLOWED
 }
}

# 20260728 - remove after 5.1.0
# prevents bulk registration via BULK_DATA_OBJ_REG_AN 688
pep_api_bulk_data_obj_reg_pre(*INSTANCE_NAME, *COMM, *BULKDATAOBJREGINP, *BULKDATAOBJREGOUT){
 *client_user = *COMM.user_user_name
 *client_zone = *COMM.user_rods_zone
 writeLine('serverLog', 'pep_api_bulk_data_obj_reg_pre: prevented [*client_user#*client_zone] from bulk registering files');
 failmsg(-169000, 'rcBulkDataObjReg is not allowed'); # SYS_NOT_ALLOWED
}


# 20260728 - remove after 5.1.0
# prevents manual get of a subfile via SUB_STRUCT_FILE_GET_AN 657
pep_api_sub_struct_file_get_pre(*INSTANCE_NAME, *COMM, *SUBFILE, *OUTBUF) {
 *client_user = *COMM.user_user_name;
 *client_zone = *COMM.user_rods_zone;
 writeLine('serverLog', 'pep_api_sub_struct_file_get_pre: prevented [*client_user#*client_zone] from getting a subfile');
 failmsg(-169000, 'getting a subfile is not allowed'); # SYS_NOT_ALLOWED
}

# 20260723 - remove after 5.1.0
# prevents `ibun -x` from executing
pep_api_struct_file_ext_and_reg_pre(*INSTANCE_NAME, *COMM, *STRUCTFILEEXTANDREGINP) {
 *client_user = *COMM.user_user_name
 *client_zone = *COMM.user_rods_zone
 *logical_path = *STRUCTFILEEXTANDREGINP.obj_path
 writeLine('serverLog', 'pep_api_struct_file_ext_and_reg_pre: prevented [*client_user#*client_zone] from extracting logical_path[*logical_path]')
 failmsg(-169000, 'ibun -x is not allowed'); # SYS_NOT_ALLOWED
}

# 20260729 - remove after 5.1.0
# prevents single registration via REG_DATA_OBJ_AN 619
# allows server-to-server redirection for iput
pep_api_reg_data_obj_pre(*INSTANCE_NAME, *COMM, *DATAOBJINFO, *OUTDATAOBJINFO){
 *proxy_user = *COMM.proxy_user_name
 *proxy_zone = *COMM.proxy_rods_zone
 *logical_path = *DATAOBJINFO.logical_path
 *physical_path = *DATAOBJINFO.physical_path
 foreach(*row in SELECT USER_TYPE where USER_NAME = '*proxy_user' and USER_ZONE = '*proxy_zone') {
   *user_type = *row.USER_TYPE;
 }
 if ("rodsadmin" != *user_type) {
   writeLine('serverLog', 'pep_api_reg_data_obj_pre: prevented [*proxy_user#*proxy_zone(*user_type)] from registering logical_path[*logical_path] with physical_path[*physical_path]');
   failmsg(-169000, 'rcRegDataObj is not allowed'); # SYS_NOT_ALLOWED
 }
}
# END temporary iRODS security mitigations
