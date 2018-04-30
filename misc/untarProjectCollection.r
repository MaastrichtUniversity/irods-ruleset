############################
# Author: Matthew Saum
# Copyright 2018 SURFsara BV
# Apache License 2.0
############################
# Original source: https://github.com/Msaum87/iRODS-Tar-Untar/tree/master/ruleFiles/SURFuntar.r

# Call with
# irule -F untarProjectCollection.r "*Tar='/nlmumc/projects/P000000001/C000000001/C000000001.tar'" "*Resc='replRescUM01'"

irule_dummy() {
    IRULE_untarProjectCollection(*Tar, *Resc);
}

# *Tar will be our target TAR file for processing.
# *Resc Resource to unpack the tarball on
IRULE_untarProjectCollection(*Tar, *Resc){
    # Need to separate the Collection and Data Object Name into two values.
    msiSplitPath(*Tar, *Coll, *tData);
 
    # The name of the table of contents / manifest file you want generated
    *tocFile = "manifest.txt";
 
    # This exception here will prevent us from checking checksums in data that was not tarballed
    # This includes: the tarball itself, the checksum file itself, and a meta-data.xml file
    *excludeFile = "metadata.xml";

    # Checking that *Resc exists
    if ( resourceExists(*Resc) == 0 ){
        failmsg(-1,"Error, resource *Resc does not exist");
    }

    msiWriteRodsLog("untarProjectCollection: Starting untar of *Tar to *Resc.", 0);

    # Step 1, untar the collection after moving it to the right resource
    msiDataObjPhymv(*Tar, *Resc, "null", "", "null", *stat);
    msiTarFileExtract(*Tar, *Coll, *Resc, *Stat);
    writeLine("stdout","Unpacking TAR file to " ++ *Coll);

    # Step 2, validate the checksums of the files.
    # Opens our checksum file. Currently set to 10000 bytes.
    *CheckSums = trimr(*tData, ".tar")++".cksums"

    if( fileOrCollectionExists(*Coll++"/"++*CheckSums) == 1){

        msiWriteRodsLog("untarProjectCollection: Finished untar. Starting checksums", 0);

        msiDataObjOpen(*Coll++"/"++*CheckSums,*CKsums);
        msiDataObjRead(*CKsums, 25000, *file_BUF);

        # To prevent the searching of similarily named collections (such as ~/FileGen and ~/FileGeneration)
        # We have to search twice, once for the precise collection and another with
        foreach( *row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME = *Coll){
            # Our logical iRODS Path
            *ipath = *row.COLL_NAME++"/"++*row.DATA_NAME;

            # Our relative path to the tar collection
            *rpath = "."++triml(*ipath, *Coll);

            # Checks our new checksum of each file from the tarball
            msiDataObjChksum(*ipath, "forceChksum=", *new);

            # Builds our Tag Structure for filtering meta-data out of a bytes-buffer
            msiStrToBytesBuf("<PRETAG>*rpath::</PRETAG>*rpath<POSTTAG>\n</POSTTAG>", *tag_BUF);
            msiReadMDTemplateIntoTagStruct(*tag_BUF, *tags);

            # Takes our Tag Structure and searches the opened checksum manifest for a match
            msiExtractTemplateMDFromBuf(*file_BUF, *tags, *cKVP);

            # Converts our result into a string useable for operations.
            *old=triml(str(*cKVP),*rpath++"=");

            # Check checksums
            if ( *row.DATA_NAME == *tData
                || *row.DATA_NAME == *tocFile
                || *row.DATA_NAME == *excludeFile
                || *row.DATA_NAME == *CheckSums
            ) {
                writeLine("stdout","Skipping " ++ *rpath ++ " for checksums.");
            } else if( *old != *new ) {
                writeLine("stdout","ERROR!!!\n"++*rpath++" does not have a matching checksum to our records! This is bad.");
                failmsg(-1, "ERROR!!!\n"++*rpath++" does not have a matching checksum to our records! This is bad.");
            } else {
                writeLine("stdout","Checksum for "++*rpath++" is good.");
            }
        }

        # Our recursive search to deal with the subdirectories
        *CollRec = *Coll ++ "/%";
        foreach(*row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME like *CollRec){
            # Our logical iRODS Path
            *ipath = *row.COLL_NAME++"/"++*row.DATA_NAME;

            # Our relative path to the tar collection
            *rpath = "."++triml(*ipath, *Coll);

            # Checks our new checksum of each file from the tarball
            msiDataObjChksum(*ipath, "forceChksum=", *new);

            # Builds our Tag Structure for filtering meta-data out of a bytes-buffer
            msiStrToBytesBuf("<PRETAG>*rpath::</PRETAG>*rpath<POSTTAG>\n</POSTTAG>", *tag_BUF);
            msiReadMDTemplateIntoTagStruct(*tag_BUF, *tags);

            # Takes our Tag Structure and searches the opened checksum manifest for a match
            msiExtractTemplateMDFromBuf(*file_BUF, *tags, *cKVP);

            # Converts our result into a string useable for operations.
            *old=triml(str(*cKVP),*rpath++"=");

            # Check checksums
            if ( *row.DATA_NAME == *tData
                || *row.DATA_NAME == *tocFile
                || *row.DATA_NAME == *excludeFile
                || *row.DATA_NAME == *CheckSums
            ) {
                writeLine("stdout","Skipping " ++ *rpath ++ " for checksums.");
            } else if( *old != *new ) {
                writeLine("stdout","ERROR!!!\n"++*rpath++" does not have a matching checksum to our records! This is bad.");
                failmsg(-1, "ERROR!!!\n"++*rpath++" does not have a matching checksum to our records! This is bad.");
            } else {
                writeLine("stdout","Checksum for "++*rpath++" is good.");
            }
        }

        msiDataObjClose(*CKsums, *stat);
        msiDataObjUnlink("objPath="++*Coll++"/"++*CheckSums++"++++forceFlag=", *stat2);
        writeLine("stdout","Deleted checksums file "++*Coll++"/"++*CheckSums);
    }

    msiWriteRodsLog("untarProjectCollection: Finished checkums. Deleting tarbals and manifest", 0);

    # Step 3, we remove the original tarball.
    # Forceflag will prevent trash holdings
    msiDataObjUnlink("objPath="++*Tar++"++++forceFlag=", *stat);
    msiDataObjUnlink("objPath="++*Coll++"/"++*tocFile++"++++forceFlag=", *stat2);
    writeLine("stdout","Deleting original tarball "++*Tar);
    writeLine("stdout","Deleted manifest "++*Coll++"/"++*tocFile);
}

INPUT *Tar="",*Resc=""
OUTPUT ruleExecOut
