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
                    sh "./rit.sh externals clone"
                }
//                 dir('docker-dev/externals'){
//                     sh """
//                     mkdir dh-faker
//                     mkdir dh-mdr
//                     mkdir -p epicpid-microservice/docker
//                     mkdir irods-frontend
//                     mkdir irods-helper-cmd
//                     mkdir irods-microservices
//                     mkdir irods-open-access-repo
//                     mkdir irods-ruleset
//                     mkdir rit-davrods
//                     mkdir sram-sync
//                     """
//                 }
                dir('docker-dev/externals/irods-helper-cmd'){
                	git branch: '2022.3', url:'https://github.com/MaastrichtUniversity/irods-helper-cmd.git'
                }
                dir('docker-dev/externals/irods-microservices'){
                	git branch: '2022.3', url:'https://github.com/MaastrichtUniversity/irods-microservices.git'
                }
//                 dir('docker-dev/externals/epicpid-microservice'){
//                 	git branch: '2022.3', url:'https://github.com/MaastrichtUniversity/epicpid-microservice.git', credentialsId: 'datahub-github'
//                 }
                dir('docker-dev/externals/epicpid-microservice'){
                    checkout([$class: 'GitSCM',
                        branches: [[name: '*/2022.3' ]],
                        extensions: scm.extensions,
                        userRemoteConfigs: [[
                            url: 'https://github.com/MaastrichtUniversity/epicpid-microservice.git',
                            credentialsId: 'dean-github'
                        ]]
                    ])
                }
                dir('docker-dev/externals/irods-ruleset'){
                	git branch: "${GIT_BRANCH}", url:'https://github.com/MaastrichtUniversity/irods-ruleset.git'
                }
//                 dir('docker-dev/externals/irods-ruleset'){
//                     // Checkout the trigger build git branch or the default develop
//                     sh returnStatus: true, script:'''
//                     git ls-remote --exit-code --heads https://github.com/MaastrichtUniversity/irods-ruleset ${GIT_BRANCH} &> /dev/null
//                     if [ $? -eq 0 ]
//                     then
//                       echo ${GIT_BRANCH}
//                       git checkout ${GIT_BRANCH}
//                       exit 0
//                     fi
//
//                     echo "develop"
//                     git checkout develop
//                     exit 0
//                     '''
//                     sh 'git status'
//                     sh 'ls -all'
//                 }
                dir('docker-dev/externals/sram-sync'){
                	git branch: '2022.3', url: 'https://github.com/MaastrichtUniversity/sram-sync.git'
                }
                withCredentials([
                    file(credentialsId: 'irods_secrets', variable: 'cfg'),
                    file(credentialsId: 'certificate-only', variable: 'cert'),
                    file(credentialsId: 'private-key', variable: 'pk'),
                    file(credentialsId: 'my-credentials-test', variable: 'creds')]) {
                    sh "cp \$cfg docker-dev/irods.secrets.cfg"
                    sh "cp \$cert docker-dev/externals/epicpid-microservice/credentials/305_21_T12996_USER01_UM_certificate_only.pem"
                    sh "cp \$pk docker-dev/externals/epicpid-microservice/credentials/305_21_T12996_USER01_UM_privkey.pem"
                    sh "cp \$creds docker-dev/externals/epicpid-microservice/my_credentials_test.json"
                }
            }
        }
        stage('Start iRODS dev env'){
            steps{
                dir('docker-dev'){
                    // Checkout the trigger build git branch or the default develop
//                     sh returnStatus: true, script:'''
//                     git ls-remote --exit-code --heads https://github.com/MaastrichtUniversity/docker-dev.git ${GIT_BRANCH} &> /dev/null
//                     if [ $? -eq 0 ]
//                     then
//                       echo ${GIT_BRANCH}
//                       git checkout ${GIT_BRANCH}
//                       exit 0
//                     fi
//
//                     echo "2022.3"
//                     git checkout 2022.3
//                     exit 0
//                     '''
                    //sh "git checkout ${GIT_BRANCH}"
                    sh 'git status'
                    sh 'ls -all'
                    sh 'echo "Stop existing docker-dev"'
                    sh returnStatus: true, script: './rit.sh down'
                    sh '''echo "Start iRODS dev environnement"
                        ./rit.sh build icat ires-hnas-um ires-hnas-azm ires-ceph-ac ires-ceph-gl sram-sync epicpid
                        ./rit.sh up -d icat ires-hnas-um ires-hnas-azm ires-ceph-ac ires-ceph-gl

                        until docker logs --tail 15 corpus_ires-hnas-um_1 2>&1 | grep -q "Config OK";
                        do
                          echo "Waiting for ires to finish"
                          sleep 10
                        done
                        echo "ires is Done!"
                        ./rit.sh up -d sram-sync
                        until docker logs --tail 1 corpus_sram-sync_1 2>&1 | grep -q "Sleeping for 300 seconds";
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
                sh "docker exec -t -u irods corpus_ires-hnas-um_1 /var/lib/irods/.local/bin/pytest -v -s -p no:cacheprovider /rules/test_cases"
            }
        }
        stage('CleanUp') {
            steps {
                dir('docker-dev') {
                    sh returnStatus: true, script: './rit.sh down'
                    sh 'echo "Stop docker-dev containers"'
                }
                cleanWs()
            }
        }
    }
}
