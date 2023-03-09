#!/usr/bin/env groovy
def getGitBranchName() {
    if (params.TARGET_BRANCH == '') {
        echo 'INFO: Build seems to be automatically triggered, using pushed branch as target branch'
        return env.GIT_BRANCH
    } else {
        echo 'INFO: Build seems to be manually triggered, defined branch as target branch'
        return params.TARGET_BRANCH
    }
}

pipeline {
    agent {
       label "fhml-srv020"
    }
    parameters {
        string(name: 'TARGET_BRANCH', description: 'The branch to deploy')
        string(name: 'FALLBACK_BRANCH', defaultValue: 'main', description: 'The branch to fall back on if the target branch does not exist')
    }
    options {
        ansiColor('xterm')
    }
    environment {
        GIT_TOKEN         = credentials('datahub-git-token')
        TARGET_BRANCH     = getGitBranchName()
    }
    stages {
        stage('Build docker-dev'){
            steps{
                build job: 'build-docker-dev', parameters: [
                    string(name: 'TARGET_BRANCH', value: env.TARGET_BRANCH),
                    string(name: 'FALLBACK_BRANCH', value: params.FALLBACK_BRANCH),
                ]
                copyArtifacts projectName: 'build-docker-dev'
            }
        }
        stage('Down any remaining iRODS environment'){
            steps{
                dir('docker-dev'){
                    echo "Stop existing docker-dev"
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
                    echo "Start iRODS dev environnement"
                    sh 'mkdir -p ./staging-data/direct-ingest ./staging-data/zones'
                    sh './rit.sh backend'
                }
            }
        }
        stage('Test') {
            steps {
                echo 'Starting the iRODS-ruleset test cases'
                sh "docker exec -t -u irods dev-ires-hnas-um-1 /var/lib/irods/.local/bin/pytest -v -p no:cacheprovider /rules/test_cases"
            }
        }
    }
    post {
        always {
            echo "Cleaning up workspace and remaining containers"
            dir('docker-dev') {
                    echo "Stop docker-dev containers"
                    sh returnStatus: true, script: './rit.sh down'
                }
            cleanWs()
        }
    }
}
