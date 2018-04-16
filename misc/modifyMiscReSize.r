# This rule does nothing and will never be called from other rules.
# Its only purpose is to easily modify the size of the rule-engine set (rit-misc.re) by adding or removing log statements
#
modifyMiscReSize() {
    msiWriteRodsLog("Prevent SYS_HEADER_READ_LENGTH and SYS_HEADER_WRITE_LEN_ERR at approximately 16kB ruleset", 0);
    msiWriteRodsLog("Prevent SYS_HEADER_READ_LENGTH and SYS_HEADER_WRITE_LEN_ERR at approximately 16kB ruleset", 0);
    msiWriteRodsLog("Prevent SYS_HEADER_READ_LENGTH and SYS_HEADER_WRITE_LEN_ERR at approximately 16kB ruleset", 0);
}

INPUT null
OUTPUT ruleExecOut
