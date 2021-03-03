# Call with
#
# For a file in a mounted collection
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F readWriteFile.r "*Obj='/nlmumc/home/rods/mounted_coll/foo1'" "*OFlags='objPath=/nlmumc/home/rods/mounted_coll/foo1++++rescName=rootResc++++replNum=0++++openFlags=O_RDONLY'" "*ObjB='/nlmumc/home/rods/mounted_coll/foo2'" "*OFlagsB='destRescName=rootResc++++forceFlag='" "*Offset='10'" "*Loc='SEEK_SET'" "*Len='100'"
#
# For file in a normal collection
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F readWriteFile.r "*Obj='/nlmumc/home/rods/normal_coll/foo1'" "*OFlags='objPath=/nlmumc/home/rods/normal_coll/foo1++++rescName=rootResc++++replNum=0++++openFlags=O_RDONLY'" "*ObjB='/nlmumc/home/rods/normal_coll/foo2'" "*OFlagsB='destRescName=rootResc++++forceFlag='" "*Offset='10'" "*Loc='SEEK_SET'" "*Len='100'"
#
# Description
# This rule:
# - Creates iRODS file *ObjB
# - Reads the amount of bytes specified in *Len and *Offset from iRODS file *Obj
# - And copies that content to iRODS file *ObjB

irule_dummy() {
    IRULE_readWriteFile(*Obj,*OFlags,*ObjB,*OFlagsB,*Offset,*Loc,*Len);
}

IRULE_readWriteFile(*Obj,*OFlags,*ObjB,*OFlagsB,*Offset,*Loc,*Len) {
   msiDataObjOpen(*OFlags,*S_FD);
   msiDataObjCreate(*ObjB,*OFlagsB,*D_FD);
   msiDataObjLseek(*S_FD,*Offset,*Loc,*Status1);
   msiDataObjRead(*S_FD,*Len,*R_BUF);
   msiDataObjWrite(*D_FD,*R_BUF,*W_LEN);
   msiDataObjClose(*S_FD,*Status2);
   msiDataObjClose(*D_FD,*Status3);
   writeLine("stdout","Open file *Obj, create file *ObjB, copy *Len bytes starting at location *Offset");
} 

INPUT *Obj="", *OFlags="", *ObjB="", *OFlagsB="", *Offset="", *Loc="", *Len=""
OUTPUT ruleExecOut
