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
        failmsg(-1,"untarProjectCollection: Error, resource *Resc does not exist");
    }

    # Checking that checksum file exists
    *CheckSums = trimr(*tData, ".tar")++".cksums"
    if( fileOrCollectionExists(*Coll++"/"++*CheckSums) != 1 ){
        failmsg(-1,"untarProjectCollection: Error, checksum ile *CheckSums does not exist");
    }

    msiWriteRodsLog("untarProjectCollection: Starting untar of *Tar to *Resc.", 0);

    # Step 1, untar the collection after moving it to the right resource
    msiDataObjPhymv(*Tar, *Resc, "null", "", "null", *stat);

    # Due to a bug the extraction of files over a certain size fail. So we manually have do this
    #msiTarFileExtract(*Tar, *Coll, *Resc, *Stat);

    foreach(*tarball in select DATA_PATH where DATA_NAME = *tData AND COLL_NAME = *Coll and DATA_REPL_NUM = '0'){
        # Physical data path
        *dataPath = *tarball.DATA_PATH;

        # Physical data dir
        *dataDir = trimr(*dataPath, "/");
    }

    # Execute external untar command
    msiExecCmd("untar.sh", "*dataPath *dataDir", "", "", "", *result);

    # Register extracted files into icat
    msiPhyPathReg(*Coll, *Resc, *dataDir, "collection", *stat);

    writeLine("stdout","Unpacked TAR file to " ++ *Coll);

    # Step 2, open the checksums of the files. And all files were extracted and registered by looping through checksums
    msiWriteRodsLog("untarProjectCollection: Finished untar. Validating all file in checksum exist", 0);

    # Opens our checksum file.
    msiDataObjOpen(*Coll++"/"++*CheckSums,*CKsums);

    # (2^32)/2 - 1 = 2147483647
    # Could not figure out a way to find the actual size of the file. Instead trying to read the maximum size that's
    # possible. Not pretty, but workable
    msiDataObjRead(*CKsums, 2147483647, *file_BUF);

    # This block of code will convert our buff to a string for manipulation.
    # We trim the leading "." and everything after the "::"
    # Then we run a check if the file exists in the collection.
    # If a file is not found, the process is halted
    msiBytesBufToStr(*file_BUF, *file_BUF_str);
    *file_List = split(*file_BUF_str,"\n");
    *countFileList = size(*file_List);

    foreach(*file_S in *file_List){

        if( fileOrCollectionExists( *Coll ++ trimr( triml( *file_S, "\."), "::") ) != 1 ){
            writeLine("stdout", "Error: Did not find " ++ *file_S);
            failmsg(-1, "untarProjectCollection: ERROR! Not all files listed in checksum file were found registered in iCAT after untar. Did not find " ++ *file_S);
        }
    }

    msiWriteRodsLog("untarProjectCollection: Found *countFileList files in checksum file and all were present in iCAT.", 0);

    # Step 3, Validate checksums
    msiWriteRodsLog("untarProjectCollection: Finished untar. Validating checksums", 0);

    # To prevent the searching of similarily named collections (such as ~/FileGen and ~/FileGeneration)
    # We have to search twice, once for the precise collection and another with
    foreach( *row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME = *Coll){
        # Our logical iRODS Path
        *ipath = *row.COLL_NAME++"/"++*row.DATA_NAME;

        # Our relative path to the tar collection
        *rpath = "."++triml(*ipath, *Coll);

        # Check for objects that need to be excluded
        if ( *row.DATA_NAME == *tData
            || *row.DATA_NAME == *tocFile
            || *row.DATA_NAME == *excludeFile
            || *row.DATA_NAME == *CheckSums
        ) {
            writeLine("stdout","Skipping " ++ *rpath ++ " for checksums.");
        } else {
            # Escape the path to prevent undesired regexes to be performed
            *escapedRpath = escapeRegexString(*rpath);

            # Checks our new checksum of each file from the tarball
            msiDataObjChksum(*ipath, "forceChksum=", *new);

            # Builds our Tag Structure for filtering meta-data out of a bytes-buffer
            msiStrToBytesBuf("<PRETAG>*escapedRpath::</PRETAG>*escapedRpath<POSTTAG>\n</POSTTAG>", *tag_BUF);
            msiReadMDTemplateIntoTagStruct(*tag_BUF, *tags);

            # Takes our Tag Structure and searches the opened checksum manifest for a match
            msiExtractTemplateMDFromBuf(*file_BUF, *tags, *cKVP);

            # Converts our result into a string useable for operations.
            *old = triml(str(*cKVP),*escapedRpath ++ "=");

            # Check checksums
            if( *old != *new ) {
                writeLine("stdout","ERROR!!!\n"++*rpath++" (*escapedRpath) does not have a matching checksum to our records! This is bad. *old != *new");
                failmsg(-1, "untarProjectCollection: ERROR " ++ *rpath ++ " does not have a matching checksum to our records! This is bad. *old != *new");
            } else {
                writeLine("stdout","Checksum for "++*rpath++" is good.");
            }
        }
    }

    # Our recursive search to deal with the subdirectories
    *CollRec = *Coll ++ "/%";
    foreach(*row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME like *CollRec){
        # Our logical iRODS Path
        *ipath = *row.COLL_NAME++"/"++*row.DATA_NAME;

        # Our relative path to the tar collection
        *rpath = "."++triml(*ipath, *Coll);

        # Escape the path to prevent undesired regexes to be performed
        *escapedRpath = escapeRegexString(*rpath);

        # Checks our new checksum of each file from the tarball
        msiDataObjChksum(*ipath, "forceChksum=", *new);

        # Builds our Tag Structure for filtering meta-data out of a bytes-buffer
        msiStrToBytesBuf("<PRETAG>*escapedRpath::</PRETAG>*escapedRpath<POSTTAG>\n</POSTTAG>", *tag_BUF);
        msiReadMDTemplateIntoTagStruct(*tag_BUF, *tags);

        # Takes our Tag Structure and searches the opened checksum manifest for a match
        msiExtractTemplateMDFromBuf(*file_BUF, *tags, *cKVP);

        # Converts our result into a string useable for operations.
        *old = triml(str(*cKVP), *escapedRpath ++ "=");

        # Check checksums
        if( *old != *new ) {
            writeLine("stdout","ERROR!!!\n"++*rpath++" (*escapedRpath) does not have a matching checksum to our records! This is bad. *old != *new");
            failmsg(-1, "untarProjectCollection: ERROR " ++ *rpath ++ " does not have a matching checksum to our records! This is bad. *old != *new");
        } else {
            writeLine("stdout","Checksum for "++*rpath++" is good.");
        }
    }

    msiDataObjClose(*CKsums, *stat);
    msiDataObjUnlink("objPath="++*Coll++"/"++*CheckSums++"++++forceFlag=", *stat2);
    writeLine("stdout","Deleted checksums file "++*Coll++"/"++*CheckSums);

    msiWriteRodsLog("untarProjectCollection: Finished checkums. Deleting tarbals and manifest", 0);

    # Step 4, we remove the original tarball.
    # Forceflag will prevent trash holdings
    msiDataObjUnlink("objPath="++*Tar++"++++forceFlag=", *stat);
    msiDataObjUnlink("objPath="++*Coll++"/"++*tocFile++"++++forceFlag=", *stat2);
    writeLine("stdout","Deleting original tarball "++*Tar);
    writeLine("stdout","Deleted manifest "++*Coll++"/"++*tocFile);
}

INPUT *Tar="",*Resc=""
OUTPUT ruleExecOut
