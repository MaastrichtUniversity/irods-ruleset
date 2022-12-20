pipeline {
    agent {
       label "fhml-srv020"
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
                    string(name: 'workspace', value: "${WORKSPACE}")
                ]
            }
        }
        stage('Down any remaining iRODS environment'){
            steps{
                sh 'echo "Stop existing docker-dev"'
                sh returnStatus: true, script: './rit.sh down'
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
