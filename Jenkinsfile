pipeline {
    agent {
       label "fhml-srv020"
    }
    parameters {
        string(name: 'TARGET_BRANCH', defaultValue: 'main', description: 'The branch to deploy')
        string(name: 'FALLBACK_BRANCH', defaultValue: 'main', description: 'The branch to fall back on if the target branch does not exist')
        string(name: 'TARGET_MACHINE', defaultValue: 'fhml-srv020', description: 'The machine to build on')
    }
    options {
        ansiColor('xterm')
    }
    environment {
        GIT_TOKEN     = credentials('datahub-git-token')
    }
    stages {
        stage('Build docker-dev'){
            steps{
                build job: 'build-docker-dev', parameters: [
                    string(name: 'TARGET_BRANCH', value: params.TARGET_BRANCH),
                    string(name: 'FALLBACK_BRANCH', value: params.FALLBACK_BRANCH),
                    string(name: 'TARGET_MACHINE', value: params.TARGET_MACHINE)
                ]
                copyArtifacts projectName: 'build-docker-dev'
            }
        }
        stage('Down any remaining iRODS environment'){
            steps{
                dir('docker-dev'){
                    sh 'echo "Stop existing docker-dev"'
                    sh returnStatus: true, script: './rit.sh down'
                }
            }
        }
        stage('Set sram-sync and epicpid to run as jenkins user'){
            steps {
                dir('docker-dev'){
                        sh """#!/bin/bash
                            sed -i '/externals\\/epicpid-microservice\\/docker.*/a \\ \\ \\ \\ user: 1000:1000' docker-compose.yml
                            sed -i '/sram-sync:\${ENV_TAG}.*/a \\ \\ \\ \\ user: 1000:1000' docker-compose.yml
                        """
                }
            }
        }
        stage('Start iRODS dev env'){
            steps{
                dir('docker-dev'){
                    sh 'echo "Start iRODS dev environnement"'
                    sh './rit.sh up -d icat keycloak elastic epicpid'

                    sh '''until docker logs --tail 15 corpus_icat_1 2>&1 | grep -q "Config OK";
                        do
                        echo "Waiting for iCAT to finish"
                        sleep 10
                        done
                        echo "iCAT is Done!"
                        '''
                    sh './rit.sh up -d ires-hnas-um ires-hnas-azm ires-ceph-ac ires-ceph-gl'
                    sh '''until docker logs --tail 15 corpus_ires-hnas-um_1 2>&1 | grep -q "Config OK";
                        do
                          echo "Waiting for iRES to finish"
                          sleep 10
                        done
                        echo "iRES is Done!"
                        '''
                    sh '''until docker logs --tail 1 corpus_keycloak_1 2>&1 | grep -q "Done syncing LDAP";
                        do
                          echo "Waiting for keycloak to finally finish"
                          sleep 5
                        done
                        '''
                    sh './rit.sh up -d sram-sync'
                    sh '''until docker logs --tail 1 corpus_sram-sync_1 2>&1 | grep -q "Sleeping for 300 seconds";
                        do
                          echo "Waiting for sram-sync"
                          sleep 5
                        done
                        '''
                }
            }
        }
        stage('Test') {
            steps {
                sh "echo 'Starting the iRODS-ruleset test cases'"
                sh "docker exec -t -u irods corpus_ires-hnas-um_1 /var/lib/irods/.local/bin/pytest -v -p no:cacheprovider /rules/test_cases"
            }
        }
    }
    post {
        always {
            sh 'echo "Cleaning up workspace and remaining containers"'
            dir('docker-dev') {
                    sh 'echo "Stop docker-dev containers"'
                    sh returnStatus: true, script: './rit.sh down'
                }
            cleanWs()
        }
    }
}
