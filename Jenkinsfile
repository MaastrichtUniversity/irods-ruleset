pipeline {
    agent any
    environment {
        GIT_TOKEN     = credentials('datahub-git-token')
    }
    stages {
        stage('Checkout docker repositories'){
            steps{
                sh "echo 'Pulling...  $GIT_BRANCH'"
                sh "printenv"
                cleanWs()
                sh "mkdir docker-dev"
                dir('docker-dev'){
                    git branch: '2022.3', url: 'https://github.com/MaastrichtUniversity/docker-dev.git'
                }
                withCredentials([
                    file(credentialsId: 'lib-dh', variable: 'libdh')]) {
                       sh "cp \$libdh ./lib-dh.sh"
                }
                sh "ls -ll"
            }
        }
        stage('Clone docker-dev externals'){
            steps{
                dir('docker-dev'){
                    sh "git config --global credential.helper \"/bin/bash /tmp/git_creds.sh\""
                    sh "echo '#!/bin/bash' > /tmp/git_creds.sh"
                    sh "echo \"sleep 1\" >> /tmp/git_creds.sh"
                    sh "echo \"echo username=datahub-deployment\" >> /tmp/git_creds.sh"
                    sh "echo \"echo password=$GIT_TOKEN\" >> /tmp/git_creds.sh"
                    sh "./rit.sh externals clone"
                    sh "./rit.sh externals checkout 2022.3"
                }
                dir('docker-dev/externals/dh-irods'){
                    sh "git checkout DHDO-633"
                }
                dir('docker-dev/externals/irods-ruleset'){
                	git branch: "automated_rule_tests", url:'https://github.com/MaastrichtUniversity/irods-ruleset.git'
                }
                withCredentials([
                    file(credentialsId: 'irods_secrets', variable: 'cfg'),
                    file(credentialsId: 'certificate-only', variable: 'cert'),
                    file(credentialsId: 'private-key', variable: 'pk'),
                    file(credentialsId: 'my-credentials-test', variable: 'creds')]) {
                    sh "cp \$cfg docker-dev/irods.secrets.cfg && chmod 664 docker-dev/irods.secrets.cfg"
                    sh "cp \$cert docker-dev/externals/epicpid-microservice/credentials/305_21_T12996_USER01_UM_certificate_only.pem"
                    sh "cp \$pk docker-dev/externals/epicpid-microservice/credentials/305_21_T12996_USER01_UM_privkey.pem"
                    sh "cp \$creds docker-dev/externals/epicpid-microservice/my_credentials_test.json"
                }
            }
        }
        stage('Build iRODS dev env'){
            steps{
                dir('docker-dev'){
                    sh 'git status'
                    sh 'ls -all'
                    sh './rit.sh build icat ires-hnas-um ires-hnas-azm ires-ceph-ac ires-ceph-gl sram-sync epicpid keycloak elastic'
                }
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
                    sh './rit.sh up -d icat keycloak elastic'

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
                    sh './rit.sh up -d sram-sync'
                    sh '''until docker logs --tail 1 corpus_sram-sync_1 2>&1 | grep -q "Sleeping for 300 seconds";
                        do
                          echo "Waiting for sram-sync"
                          sleep 5
                        done
                        '''
                    sh '''until docker logs --tail 1 corpus_keycloak_1 2>&1 | grep -q "Done syncing LDAP";
                        do
                          echo "Waiting for keycloak to finally finish"
                          sleep 5
                        done    
                        '''  
                    sh './rit.sh up -d epicpid'
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
