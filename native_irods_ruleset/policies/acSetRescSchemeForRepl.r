
# acSetRescSchemeForRepl{
#     # Policy to increment the size of the ingested files for the progress bar
#     # For mounted ingest there is a difference between old acPostProcForPut and acSetRescSchemeForRepl.
#     # Difference is that size of /nlmumc/projects/P000000001/C000000001/instance.json and
#     # /nlmumc/projects/P000000001/C000000001/schema.json are now included in the count
#     # The direct ingest has a perfect match
#     if($objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
#           *creator = "";
#           *sizeIngestedRepl = 0;
#           uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
#           uuChop(*tail, *project, *tail, "/", true);
#           uuChop(*tail, *collection, *tail, "/", true);
#           # Get the creator AVU from the collection, if it exists, that means the collection already is fully ingested
#           getCollectionAVU("/nlmumc/projects/*project/*collection","creator",*creator,"","false");
#           if(*creator == ""){
#              # During ingest this policy is triggered twice for each file
#              # Last seen file is stored in temporaryStorage. If they match no calculation is performed
#              if (errorcode(temporaryStorage.last_seen) == 0){
#                 if (temporaryStorage.static_content){
#                       updateCollectionsizeIngestedRepl($objPath,*project,*collection)
#                       temporaryStorage.last_seen = $objPath
#                 }
#              }
#              # temporaryStorage is empty because this is the first file
#              else {
#                      updateCollectionsizeIngestedRepl($objPath,*project,*collection)
#                      temporaryStorage.last_seen = $objPath
#              }
#           }
#     }
# }

#
# updateCollectionsizeIngestedRepl(*objPath,*project,*collection){
#          getCollectionAVU("/nlmumc/projects/*project/*collection","sizeIngested",*sizeIngested,"","false");
#          uuChop(*objPath, *folder, *file, "/", false);
#          foreach ( *Row in SELECT DATA_SIZE WHERE DATA_NAME = "*file" AND COLL_NAME = "*folder") {
#                 *sizeBytes = *Row.DATA_SIZE;
#          }
#          *sizeIngested = *sizeIngested + double(*sizeBytes);
#          msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
#          msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
# }


