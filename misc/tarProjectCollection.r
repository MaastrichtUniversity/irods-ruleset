############################
# Author: Matthew Saum
# Copyright 2018 SURFsara BV
# Apache License 2.0
############################
# Original source: https://github.com/Msaum87/iRODS-Tar-Untar/tree/master/ruleFiles/SURFtar.r

# Call with
# irule -F tarProjectCollection.r "*Coll='/nlmumc/projects/P000000001/C000000001'" "*Resc='replRescUM01'" "*tocResc='replRescUM01'" "*tarResc='iresResource'"

irule_dummy() {
    IRULE_tarProjectCollection(*Coll, *Resc, *tocResc, *tarResc);
}

# TO DO:
# Allow multiple file exclusions

# NOTE: Please do not add trailing "/" symbols.
# *Coll Target collection for tar processing.
# *Resc Resource to build the tarball on. This will create replicas if not the same as data objects in the target collection.
# *tocResc Resource for metadata and manifest to reside on afterwards. (Could be the same as *Resc)
# *tarResc Target resource for the tarball to reside on (Tape archive ideally)
IRULE_tarProjectCollection(*Coll, *Resc, *tocResc, *tarResc){

    # Now we address some names of files: the tarball, the manifest, and the excluded file
    # The name of your tarball. The default provided is the name of the collection.
    # This is a bit tricky to reliably get
    # Trim from the left all of our /'s away until only 1 block of text remains.
    # If you have more than 9 subdirectories, it will need expanded
    # in any case, a suffix of '.tar' is appended in the rule.
    *Tar = triml(triml(triml(triml(triml(triml(triml(triml(triml(*Coll, "/"), "/"), "/"), "/"), "/"), "/"), "/"), "/"), "/");

    # Build path for the manifest, tarball, and temp holding of any excluded file
    *foundation="/nlmumc/home/"++$userNameClient++"/tar-temp";
    if(fileOrCollectionExists(*foundation)==1){
        failmsg(-1,"Error, already found a temporary tar directory. Unfinished existing tar process? Check "++*foundation++".");
    }

    # The name of the table of contents / manifest file you want generated
    *ToCfile = "manifest.txt";

    # The flag to do checksums    note: 1 = true; any other value is false.
    *CheckSums = 1;

    # The metadata file name (collection and parent collection pathing and all is mapped out below)
    # This file will be excluded from tarring and such.
    # limited to one file at the moment.
    *excludeFile = "metadata.xml";


    #----------------------------------------------
    # Step 1- Checks on existing data, some location mapping
    # Up and Down refer to up in the build spot of *foundation or down in the target collection
    # Tarball file name, with a suffix to make it uniquely identifiable
    *TarUp = *foundation++"/"++*Tar++".tar";
    *TarDown = *Coll++"/"++*Tar++".tar";

    # Checksum File for manifest/record
    *tocUp = *foundation++"/"++*ToCfile;
    *tocDown = *Coll++"/"++*ToCfile;

    # Excluded file
    *EXup = *foundation++"/"++*excludeFile;
    *EXdown = *Coll++"/"++*excludeFile;

    # Checksums File
    *CKSup = *foundation++"/"++*Tar++".cksums";
    *CKSdown = *Coll++"/"++*Tar++".cksums"

    # Make sure no tarball already exists with this name in this location
    if( fileOrCollectionExists(*TarUp) == 1 ){
        failmsg(-1,"Warning, already found a tarball. Check in"++*foundation++".");
    }

    # Checking that there is no manifest file already existing.
    if( fileOrCollectionExists(*tocUp) == 1 ){
        failmsg(-1,"Warning, almost overwrote manifest file. Check in"++*foundation++".");
    }

    # Make sure no meta-data was currently migrated and risk overwrite.
    if( fileOrCollectionExists(*EXup) == 1 ){
        failmsg(-1,"Warning, almost overwrote meta-data. Check in"++*foundation++".");
    }

    # Make sure that the excluded file actually exists..
    if( fileOrCollectionExists(*EXdown) == 0 ){
        failmsg(-1,"Warning, file targeted for exclusion does not exist.");
    }

    # Checking that no existing CKSUM file exists
    if ( fileOrCollectionExists(*CKSup) == 1 && *CheckSums == 1 ){
        failmsg(-1,"Warning, already found a checksum file. Check in"++*foundation++".");
    }

    # Checking that *Resc exists
    if ( resourceExists(*Resc) == 0 ){
        failmsg(-1,"Error, resource *Resc does not exist");
    }

    # Checking that *tocResc exists
    if ( resourceExists(*Resc) == 0 ){
        failmsg(-1,"Error, resource *tocResc does not exist");
    }

    # Checking that *tarResc exists
    if ( resourceExists(*tarResc) == 0 ){
        failmsg(-1,"Error, resource *tarResc does not exist");
    }

    msiWriteRodsLog("tarProjectCollection: Finished checks. Started creating TAR file: *TarUp", 0);

    # Create temporary directory
    msiCollCreate(*foundation, 0, *status)
    
    # Move meta-data out of the collection. Otherwise you may overwrite an updated file upon un-tarring,
    # replacing new information with an old tar image.
    msiDataObjRename(*EXdown, *EXup, "0", *stat);

    # Then tarball entire collection.
    msiTarFileCreate(*TarUp, *Coll, *Resc, "");

    msiWriteRodsLog("tarProjectCollection: Created TAR file. Starting checksums.", 0);
    writeLine("stdout","tarProjectCollection: Created TAR file. Starting checksums.");

    # Creates a new table of contents in our collection
    msiDataObjCreate(*tocUp, "forceFlag=", *TOC);
    # Creates our checksums if desired
    if(*CheckSums == 1){
        msiDataObjCreate(*CKSup, "forceFlag=", *CKS)
    }
 
    #----------------------------------------------
    # Step 2- Creating file manifest (and optional checksumming). Then, delete the file.

    # We need to list two COLL_NAME filters.
    # The first is "/zone/coll/coll" which will grab the contents of our target collection
    # The second is "/zone/coll/coll/%" which will grab subdirectories if they exist.
    # This is because if we ran "/zone/coll/coll%" we would get /zone/coll/coll AND /zone/coll/collate

    foreach(*data in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *Coll) {
        *ipath = *data.COLL_NAME++"/"++*data.DATA_NAME;
        *rpath = "./"++triml(*ipath, *Coll++"/");

        # Filtering out optional checksums or not
        if(*CheckSums==1){
            #msiDataObjChksum(*ipath, "forceChksum=++++replNum=0", *chkSum);
            msiDataObjChksum(*ipath, "forceChksum=", *chkSum);
            msiDataObjWrite(*CKS, *rpath++"::"++*chkSum++"\n", *stat);
        }

        msiDataObjWrite(*TOC, *rpath++"\n", *stat);
    }

    # This second query pulls the subdirectories of our target collection. Adding "/%" to our collection name.
    *CollRec=*Coll++"/%";
    foreach(*data in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME like *CollRec) {
        *ipath = *data.COLL_NAME++"/"++*data.DATA_NAME;
        *rpath = "./"++triml(*ipath, *Coll++"/");

        # Filtering out optional checksums or not
        if(*CheckSums==1){
            #msiDataObjChksum(*ipath, "forceChksum=++++replNum=0", *chkSum);
            msiDataObjChksum(*ipath, "forceChksum=", *chkSum);
            msiDataObjWrite(*CKS, *rpath++"::"++*chkSum++"\n", *stat);
        }

        msiDataObjWrite(*TOC, *rpath++"\n", *stat);
    }

    # Close our file
    msiDataObjClose(*TOC, *stat);
    msiDataObjClose(*CKS, *stat);

    msiWriteRodsLog("tarProjectCollection: Finished checksums. Starting cleanup.", 0);

    #----------------------------------------------
    #Step 3- Cleanup. Deleting objects as they are now in the tarball
    #
    # Deleting objects in a foreach loop will race-conditon out
    # if there are more than 255 items found
    # To counter this, we use a while/foreach combo that counts out
    # and resets if over 200 items.

    # Using *i to count and reset, we delete in batches of 200 and reset the foreach
    *deleted = 1;
    *i = 0;
    while(*deleted == 1) {
        *deleted = 0;
        foreach(*row in SELECT COLL_NAME where COLL_PARENT_NAME = *Coll){
            *deleted = 1;
            *i = *i + 1;

            # If *i is at 200, break the foreach and reset.
            if(*i >= 200){
                *i = 0;
                break;
            }

            # As long as our counter is below 201, we proceed to delete and lower total
            msiRmColl(*row.COLL_NAME,"forceFlag=",*Status);
            msiWriteRodsLog(*row.COLL_NAME++" was removed, status: "++*Status, 0);
        }
    }

    # Now we scrub the data objects left in the target collection
    # Using the same while/foreach to counter the race condition

    # Using *i to count and reset, we delete in batches of 200 and reset the foreach
    *deleted = 1;
    *i = 0;
    while(*deleted == 1){
        *deleted = 0;
        foreach(*cleanup in select DATA_NAME where COLL_NAME = *Coll){
            *ipath=*Coll++"/"++*cleanup.DATA_NAME;
            *deleted = 1;
            *i = *i + 1;

            # If *i is at 200, break the foreach and reset.
            if(*i >= 200){
                *i = 0;
                break;
            }

            msiDataObjUnlink("objPath="++*ipath++"++++forceFlag=", *rmstat);
        }
    }

    #----------------------------------------------
    #Step 4- Move the tarball and manifest into the collection, along with previously existing meta-data file.

    msiWriteRodsLog("tarProjectCollection: Finished cleanup. Starting objPhyMove to destination resource *tarResc", 0);

    msiDataObjRename(*TarUp, *TarDown, "0", *Stat);
    msiDataObjPhymv(*TarDown, *tarResc, "null", "", "null", *stat);

    msiDataObjRename(*tocUp, *tocDown, "0", *Stat3);
    msiDataObjPhymv(*tocDown, *tocResc, "null", "", "null", *stat);

    msiDataObjRename(*EXup, *EXdown, "0", *stat);
    msiDataObjPhymv(*EXdown, *tocResc, "null", "", "null", *stat);

    if(*CheckSums==1){
        msiDataObjRename(*CKSup, *CKSdown, "0", *stat);
        msiDataObjPhymv(*CKSdown, *tocResc, "null", "", "null", *stat);
    }

    # Safety check. *foundation collection should be empty!
    foreach(*row in SELECT DATA_NAME WHERE COLL_NAME = '*foundation'){
        failmsg(-1,"Warning, collecion used for tar'ing is not empty! Not deleting it. Check in"++*foundation++".");
    }
    msiRmColl(*foundation, "forceFlag=", *status);

    msiWriteRodsLog("tarProjectCollection: Finished objPhyMove and cleaned up *foundation.", 0);
}

INPUT *Coll="",*Resc="",*tocResc="",*tarResc=""
OUTPUT ruleExecOut