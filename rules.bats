#!/usr/bin/env bats

#./rit.sh exec irods
#su irods
#cd rules
#bats rules.bats
#sudo apt-get install bats

regex_completed_message="ExecMyRule completed successfully."
regex_array="[]"
regex_digital=^[0-9]{1,}$
regex_project_id='{"project": "P000000010"'
regex_users_output='{"users":' 

project='P000000010'
collection='C000000001'
collection_path='/nlmumc/projects/P000000010/C000000001'

#Collection

@test "projectCollection/closeProjectCollection.r" {
  run irule -v -s -F projectCollection/closeProjectCollection.r *project="$project" *projectCollection="$collection"
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}

@test "projectCollection/createProjectCollection.r" {
  run bash -c "irule -s -F projectCollection/createProjectCollection.r *project="$project" *title='Testing' | grep -Eo '^C[0-9]{9}$' | xargs -I % echo /nlmumc/projects/P000000010/% | xargs -I % irm -f -r -V % && echo 0"
  [ $status -eq 0 ]
}

@test "projectCollection/detailsProjectCollection.r" {
  run irule -s -F projectCollection/detailsProjectCollection.r *project="$project" *collection="$collection" *inherited='false' 
  [ $status -eq 0 ]
  [[ ${output} =~ "$regex_project_id" ]]
}

@test "projectCollection/openProjectCollection.r" {
  run irule -v -s -F projectCollection/openProjectCollection.r *project="$project" *projectCollection="$collection" *user='rods' *rights='own'
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}

#Projects

@test "projects/createProject.r" {
	run bash -c "irule -s -F projects/createProject.r *authorizationPeriodEndDate='1-1-2018' *dataRetentionPeriodEndDate='1-1-2018' *ingestResource='iresResource' *resource='replRescUM01' *storageQuotaGb='10' *title='Testing' *principalInvestigator='jonathan.melius@maastrichtuniversity.nl' *respCostCenter='UM-30001234X' *pricePerGBPerYear='0.32' | grep -Eo '^P[0-9]{9}$' | xargs -I % echo /nlmumc/projects/% | xargs -I % irm -f -r -V % && echo 0"      
  [ $status -eq 0 ]
}

@test "projects/detailsProject.r" {
  run irule -s -F projects/detailsProject.r *project="$project" *inherited='false' 
  [ $status -eq 0 ]
  [[ ${output} =~ "$regex_project_id" ]]
}

@test "projects/listContributingProjects.r" {
  run irule -s -F projects/listContributingProjects.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "projects/listManagingProjects.r" {
  run irule -s -F projects/listManagingProjects.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "projects/listProjectContributors.r" {
  run irule -s -F projects/listProjectContributors.r *project="$project" *inherited='true'
  [ $status -eq 0 ]
  [[ "${output}" =~ "$regex_users_output" ]]
}

@test "projects/listProjectManagers.r" {
  run irule -s -F projects/listProjectManagers.r *project="$project"
  [ $status -eq 0 ]
  [[ "${output}" =~ "$regex_users_output" ]]
}

@test "projects/listProjectsByUser.r" {
  run irule -s -F projects/listProjectsByUser.r 
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "projects/listProjectViewers.r" {
  run irule -s -F projects/listProjectViewers.r *project="$project" *inherited='true' 
  [ $status -eq 0 ]
  [[ "${output}" =~ "$regex_users_output" ]]
}

@test "projects/listViewingProjects.r" {
  run irule -s -F projects/listViewingProjects.r 
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "projects/reportProjects.r" {
  run irule -s -F projects/reportProjects.r 
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

#Misc

@test "misc/calcCollectionFiles.r" {
  run irule -s -F misc/calcCollectionFiles.r *collection="$collection_path"
  [ $status -eq 0 ]
  [[ "${output}" =~ $regex_digital ]] 
}

@test "misc/calcCollectionSize.r" {
  run irule -s -F misc/calcCollectionSize.r *collection="$collection_path" *unit='GiB' *round='ceiling'
  [ $status -eq 0 ]
  [[ "${output}" =~ $regex_digital ]] 
}

@test "misc/fileOrCollectionExists.r" {
  run irule -s -F misc/fileOrCollectionExists.r *fileOrCollection="$collection_path"
  [ $status -eq 0 ]
  [ "${output}" ==  "true" ]
}

@test "misc/getCollectionAVU.r" {
  run irule -s -F misc/getCollectionAVU.r *collName="$collection_path" *attribute='title' *overrideValue='' *fatal='true' 
  [ $status -eq 0 ]
  [ "${output}" ==  "MDL placeholder collection" ]
}

@test "misc/getCollectionSize.r" {
  run irule -s -F misc/getCollectionSize.r *collection="$collection_path" *unit='GiB' *round='ceiling'
  [ $status -eq 0 ]
  [[ "${output}" =~ $regex_digital ]] 
}

@test "misc/getDestinationResources.r" {
  run irule -s -F misc/getDestinationResources.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "misc/getIngestResources.r" {
  run irule -s -F misc/getIngestResources.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "misc/getGroups.r" {
  run irule -s -F misc/getGroups.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "misc/getUsers.r" {
  run irule -s -F misc/getUsers.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "misc/resourceExists.r" {
  run irule -s -F misc/resourceExists.r *resource='rootResc'
  [ $status -eq 0 ]
  [ "${output}" ==  "true" ]
}

@test "misc/setCollectionSize.r" {
  run irule -v -s -F misc/setCollectionSize.r *project="$project" *projectCollection="$collection"
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}

@test "misc/setCollectionAVU.r" {
	irule -v -s -F projectCollection/openProjectCollection.r *project="$project" *projectCollection="$collection" *user='rods' *rights='own'
  run irule -v -s -F misc/setCollectionAVU.r *collection="$collection_path" *attribute='title' *value='UnitTest'  
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
  run irule -v -s -F misc/setCollectionAVU.r *collection="$collection_path" *attribute='title' *value='MDL placeholder collection'
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
  irule -v -s -F projectCollection/closeProjectCollection.r *project="$project" *projectCollection="$collection"
}

@test "misc/sendAllMetadata.r" {
  run irule -v -s -F misc/sendAllMetadata.r
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}