# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F writeToMountedFile.r "*arg='value'"
#
# This rule:
# - Creates iRODS file *ObjB
# - Reads the amount of bytes specified in *Len and *Offset from iRODS file *Obj
# - And copies that content to iRODS file *ObjB

irule_dummy() {
    IRULE_writeToMountedFile(*Obj,*OFlags,*ObjB,*OFlagsB,*Offset,*Loc,*Len);
}

IRULE_writeToMountedFile(*Obj,*OFlags,*ObjB,*OFlagsB,*Offset,*Loc,*Len) {
   msiDataObjOpen(*OFlags,*S_FD);
   msiDataObjCreate(*ObjB,*OFlagsB,*D_FD);
   msiDataObjLseek(*S_FD,*Offset,*Loc,*Status1);
   msiDataObjRead(*S_FD,*Len,*R_BUF);
   msiDataObjWrite(*D_FD,*R_BUF,*W_LEN);
   msiDataObjClose(*S_FD,*Status2);
   msiDataObjClose(*D_FD,*Status3);
   writeLine("stdout","Open file *Obj, create file *ObjB, copy *Len bytes starting at location *Offset");
} 

#INPUT *Obj="/nlmumc/home/rods/foo1", *OFlags="objPath=/nlmumc/home/rods/foo1++++rescName=rootResc++++replNum=0++++openFlags=O_RDONLY", *ObjB="/nlmumc/home/rods/foo4", *OFlagsB="destRescName=rootResc++++forceFlag=", *Offset="10", *Loc="SEEK_SET", *Len="100"
INPUT *Obj="/nlmumc/home/rods/foo1", *OFlags="objPath=/nlmumc/home/rods/foo1++++rescName=rootResc++++replNum=0++++openFlags=O_RDONLY", *ObjB="/nlmumc/ingest/zones/smiling-stoat/metadata.xml", *OFlagsB="destRescName=iresResource++++forceFlag=", *Offset="10", *Loc="SEEK_SET", *Len="100"
OUTPUT ruleExecOut