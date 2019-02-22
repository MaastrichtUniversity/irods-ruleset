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

@test "/rules/projectCollection/closeProjectCollection.r" {
  run irule -v -s -F /rules/projectCollection/closeProjectCollection.r *project="$project" *projectCollection="$collection"
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}

@test "/rules/projectCollection/createProjectCollection.r" {
  run bash -c "irule -s -F /rules/projectCollection/createProjectCollection.r *project="$project" *title='Testing' | grep -Eo '^C[0-9]{9}$' | xargs -I % echo /nlmumc/projects/P000000010/% | xargs -I % irm -f -r -V % && echo 0"
  [ $status -eq 0 ]
}

@test "/rules/projectCollection/detailsProjectCollection.r" {
  run irule -s -F /rules/projectCollection/detailsProjectCollection.r *project="$project" *collection="$collection" *inherited='false' 
  [ $status -eq 0 ]
  [[ ${output} =~ \{\"(.*?)\} ]]
}

@test "/rules/projectCollection/openProjectCollection.r" {
  run irule -v -s -F /rules/projectCollection/openProjectCollection.r *project="$project" *projectCollection="$collection" *user='rods' *rights='own'
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}

#Projects

@test "/rules/projects/createProject.r" {
	run bash -c "irule -s -F /rules/projects/createProject.r *authorizationPeriodEndDate='1-1-2018' *dataRetentionPeriodEndDate='1-1-2018' *ingestResource='iresResource' *resource='replRescUM01' *storageQuotaGb='10' *title='Testing' *principalInvestigator='jonathan.melius@maastrichtuniversity.nl' *respCostCenter='UM-30001234X' *pricePerGBPerYear='0.32' | grep -Eo '^P[0-9]{9}$' | xargs -I % echo /nlmumc/projects/% | xargs -I % irm -f -r -V % && echo 0"      
  [ $status -eq 0 ]
}

@test "/rules/projects/detailsProject.r" {
  run irule -s -F /rules/projects/detailsProject.r *project="$project" *inherited='false' 
  [ $status -eq 0 ]
  [[ ${output} =~ \{\"(.*?)\} ]]
}

@test "/rules/projects/listContributingProjects.r" {
  run irule -s -F /rules/projects/listContributingProjects.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/projects/listManagingProjects.r" {
  run irule -s -F /rules/projects/listManagingProjects.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/projects/listProjectContributors.r" {
  run irule -s -F /rules/projects/listProjectContributors.r *project="$project" *inherited='true'
  [ $status -eq 0 ]
  [[ "${output}" =~ "$regex_users_output" ]]
}

@test "/rules/projects/listProjectManagers.r" {
  run irule -s -F /rules/projects/listProjectManagers.r *project="$project"
  [ $status -eq 0 ]
  [[ "${output}" =~ "$regex_users_output" ]]
}

@test "/rules/projects/listProjectsByUser.r" {
  run irule -s -F /rules/projects/listProjectsByUser.r 
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/projects/listProjectViewers.r" {
  run irule -s -F /rules/projects/listProjectViewers.r *project="$project" *inherited='true' 
  [ $status -eq 0 ]
  [[ "${output}" =~ "$regex_users_output" ]]
}

@test "/rules/projects/listViewingProjects.r" {
  run irule -s -F /rules/projects/listViewingProjects.r 
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/projects/reportProjects.r" {
  run irule -s -F /rules/projects/reportProjects.r 
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

#Misc

@test "/rules/misc/calcCollectionFiles.r" {
  run irule -s -F /rules/misc/calcCollectionFiles.r *collection="$collection_path"
  [ $status -eq 0 ]
  [[ "${output}" =~ $regex_digital ]] 
}

@test "/rules/misc/calcCollectionSize.r" {
  run irule -s -F /rules/misc/calcCollectionSize.r *collection="$collection_path" *unit='GiB' *round='ceiling'
  [ $status -eq 0 ]
  [[ "${output}" =~ $regex_digital ]] 
}

@test "/rules/misc/fileOrCollectionExists.r" {
  run irule -s -F /rules/misc/fileOrCollectionExists.r *fileOrCollection="$collection_path"
  [ $status -eq 0 ]
  [ "${output}" ==  "true" ]
}

@test "/rules/misc/getCollectionAVU.r" {
  run irule -s -F /rules/misc/getCollectionAVU.r *collName="$collection_path" *attribute='title' *overrideValue='' *fatal='true' 
  [ $status -eq 0 ]
  [ "${output}" ==  "MDL placeholder collection" ]
}

@test "/rules/misc/getCollectionSize.r" {
  run irule -s -F /rules/misc/getCollectionSize.r *collection="$collection_path" *unit='GiB' *round='ceiling'
  [ $status -eq 0 ]
  [[ "${output}" =~ $regex_digital ]] 
}

@test "/rules/misc/getDestinationResources.r" {
  run irule -s -F /rules/misc/getDestinationResources.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/misc/getIngestResources.r" {
  run irule -s -F /rules/misc/getIngestResources.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/misc/getGroups.r" {
  run irule -s -F /rules/misc/getGroups.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/misc/getUsers.r" {
  run irule -s -F /rules/misc/getUsers.r
  [ $status -eq 0 ]
  [ "${output}" != $regex_array ]
}

@test "/rules/misc/resourceExists.r" {
  run irule -s -F /rules/misc/resourceExists.r *resource='rootResc'
  [ $status -eq 0 ]
  [ "${output}" ==  "true" ]
}

@test "/rules/misc/setCollectionSize.r" {
  run irule -v -s -F /rules/misc/setCollectionSize.r *project="$project" *projectCollection="$collection"
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}

@test "/rules/misc/setCollectionAVU.r" {
	irule -v -s -F /rules/projectCollection/openProjectCollection.r *project="$project" *projectCollection="$collection" *user='rods' *rights='own'
  run irule -v -s -F /rules/misc/setCollectionAVU.r *collection="$collection_path" *attribute='title' *value='UnitTest'  
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
  run irule -v -s -F /rules/misc/setCollectionAVU.r *collection="$collection_path" *attribute='title' *value='MDL placeholder collection'
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
  irule -v -s -F /rules/projectCollection/closeProjectCollection.r *project="$project" *projectCollection="$collection"
}

@test "/rules/misc/sendAllMetadata.r" {
  run irule -v -s -F /rules/misc/sendAllMetadata.r
  [ $status -eq 0 ]
  [[ ${output} =~ $regex_completed_message ]]
}