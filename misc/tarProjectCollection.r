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

 #Now we address some names of files: the tarball, the manifest, and the excluded file
 #The name of your tarball. The default provided is the name of the collection.
 #This is a bit tricky to reliably gett
 #rim from the left all of our /'s away until only 1 block of text remains.
 #If you have more than 9 subdirectories, it will need expanded
 #in any case, a suffix of '.tar' is appended in the rule.
 *Tar=triml(triml(triml(triml(triml(triml(triml(triml(triml(*Coll, "/"), "/"), "/"), "/"), "/"), "/"), "/"), "/"), "/");
 #*Tar=S"somefilename"

 # Build path for the manifest, tarball, and temp holding of any excluded file
 *foundation="/nlmumc/home/"++$userNameClient++"/tar-temp";
 if(ifExists(*foundation)==0){
    msiCollCreate(*foundation, 0, *status)
 }

 #The name of the table of contents / manifest file you want generated
 *ToCfile="manifest.txt";

 #The flag to do checksums    not. 1 = true. any other value is false.
 *CheckSums=1;
 #*CheckSums=0;

 #The metadata file name (collection and parent collection pathing and all is mapped out below)
 #This file will be excluded from tarring and such.
 #limited to one file at the moment.
 *excludeFile="metadata.xml";


 #----------------------------------------------
 #Step 1- Checks on existing data, some location mapping
 #Up and Down refer to up in the build spot of *foundation or down in the target collection
 #Tarball file name, with a suffix to make it uniquely identifiable
 *TarUp=*foundation++"/"++*Tar++".tar";
 *TarDown=*Coll++"/"++*Tar++".tar"; 
	
 #Checksum File for manifest/record
 *tocUp=*foundation++"/"++*ToCfile;
 *tocDown=*Coll++"/"++*ToCfile;
	
 #Excluded file
 *EXup=*foundation++"/"++*excludeFile; 
 *EXdown=*Coll++"/"++*excludeFile; 
 
 #Checksums File
 *CKSup=*foundation++"/"++*Tar++".cksums";
 *CKSdown=*Coll++"/"++*Tar++".cksums"
 
 #Make sure no tarball already exists with this name in this location
 if(ifExists(*TarUp)==1){
    writeLine("stdout","Have to delete an existing tarball");
    failmsg(-1,"Warning, already found a tarball. Check in"++*foundation++".");
 }
 #Checking that there is no manifest file already existing.
 if(ifExists(*tocUp)==1){
    writeLine("stdout","metadata file already exists");
    failmsg(-1,"Warning, almost overwrote manifest file. Check in"++*foundation++".");
 }
    #Make sure no meta-data was currently migrated and risk overwrite.
 if(ifExists(*EXup)==1){
    writeLine("stdout","metadata file already exists");
    failmsg(-1,"Warning, almost overwrote meta-data. Check in"++*foundation++".");
 }	    
    #Make sure that the exlucded file actually exists..
 if((ifExists(*EXdown))==0){
    writeLine("stdout","excluded file does not exist");
    failmsg(-1,"Warning, file targeted for exclusion does not exist..");
 }
    #Checking that no existing CKSUM file exists
 if(
        ifExists(*CKSup)==1 
 && *CheckSums==1
 ){
    writeLine("stdout","Have to delete an existing tarball");
    failmsg(-1,"Warning, already found a checksum file. Check in"++*foundation++".");
 }
    
#----------------------------------------------
 #Step 1

 #Move meta-data out of the collection
 #DO THIS. Otherwise you may overwrite an updated file upon un-tarring, replacing new information with an old tar image.
 msiDataObjRename(*EXdown, *EXup, "0", *stat);

 #Then tarball entire collection.
 #remote("ires","") {
 msiTarFileCreate(*TarUp, *Coll, *Resc, "");
 #}
 writeLine("stdout","created TAR file "++*TarUp);

 #Creates a new table of contents in our collection
 msiDataObjCreate(*tocUp, "forceFlag=", *TOC);
 #Creates our checksums if desired
 if(*CheckSums == 1){
    msiDataObjCreate(*CKSup, "forceFlag=", *CKS)
 }
 
 #----------------------------------------------
 #Step 2- Creating file manifest (and optional checksumming). Then, delete the file.

 #We need to list two COLL_NAME filters.
 #The first is "/zone/coll/coll" which will grab the contents of our target collection
 #The second is "/zone/coll/coll/%" which will grab subdirectories if they exist.
 #This is because if we ran "/zone/coll/coll%" we would get /zone/coll/coll AND /zone/coll/collate
 foreach(*data in SELECT 
                         COLL_NAME, 
                         DATA_NAME 
                  WHERE 
                         COLL_NAME = *Coll
    ){
    *ipath=*data.COLL_NAME++"/"++*data.DATA_NAME;
    *rpath="./"++triml(*ipath, *Coll++"/");
    #Filtering out optional checksums or not
    if(*CheckSums==1){
     #msiDataObjChksum(*ipath, "forceChksum=++++replNum=0", *chkSum);
     msiDataObjChksum(*ipath, "forceChksum=", *chkSum);
     msiDataObjWrite(*CKS, *rpath++"::"++*chkSum++"\n", *stat);
    }

    msiDataObjWrite(*TOC, *rpath++"\n", *stat);

    msiDataObjUnlink("objPath="++*ipath++"++++forceFlag=", *rmstat);
 }#*Coll search

 #This second query pulls the subdirectories of our target collection. Adding "/%" to our collection name.
 *CollRec=*Coll++"/%";
 foreach(*data in SELECT 
                         COLL_NAME, 
                         DATA_NAME 
                  WHERE 
                         COLL_NAME like *CollRec
    ){
    *ipath=*data.COLL_NAME++"/"++*data.DATA_NAME;
    *rpath="./"++triml(*ipath, *Coll++"/");
    #Filtering out optional checksums or not
    if(*CheckSums==1){
     #msiDataObjChksum(*ipath, "forceChksum=++++replNum=0", *chkSum);
     msiDataObjChksum(*ipath, "forceChksum=", *chkSum);
     msiDataObjWrite(*CKS, *rpath++"::"++*chkSum++"\n", *stat);
    }

    msiDataObjWrite(*TOC, *rpath++"\n", *stat);

    msiDataObjUnlink("objPath="++*ipath++"++++forceFlag=", *rmstat);
 }#*Coll search

 #Close our file
 msiDataObjClose(*TOC, *stat);
 msiDataObjClose(*CKS, *stat);

#----------------------------------------------
 #Step 3- Move the tarball and manifest into the collection, along with previously existing meta-data file.
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

}#SURFtar

# Matthew's basic file-existance checker function.
# Checks if a file exists
# *i is a full file path "/tempZone/home/rods/testfile.dat" or so
# Returns 0 if no file, 1 if file found.
ifExists(*i){
 *b = 0;
 msiSplitPath(*i, *coll, *data);
 foreach(*row in SELECT 
                        COLL_NAME, 
                        DATA_NAME 
                 WHERE 
                        COLL_NAME = '*coll' 
                    AND DATA_NAME = '*data'
    ){
    *b = 1;
    break;
 }
 *b;
}

INPUT *Coll="",*Resc="",*tocResc="",*tarResc=""
OUTPUT ruleExecOut