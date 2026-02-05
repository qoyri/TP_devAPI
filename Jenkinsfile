pipeline {
    agent any

    options {
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timestamps()
    }

    environment {
        DOKPLOY_URL = 'http://192.168.0.103:3000'
        DOKPLOY_TOKEN = 'CMP_fcdf0ce662f5dbde70db'
        SONAR_HOST_URL = 'http://192.168.0.219:9000'
        SONAR_TOKEN = credentials('sonarqube-token')
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                git branch: 'main', url: 'https://github.com/Lajavel-gg/TP_devAPI.git'
                script {
                    env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.GIT_AUTHOR = sh(script: 'git log -1 --format=%an', returnStdout: true).trim()
                    env.GIT_MESSAGE = sh(script: 'git log -1 --format=%s', returnStdout: true).trim()
                }
                sh 'echo "Commit: ${GIT_COMMIT_SHORT} | Author: ${GIT_AUTHOR}"'
            }
        }

        stage('Code Quality') {
            parallel {
                stage('Python') {
                    steps {
                        script {
                            try {
                                sh 'python3 -m py_compile mysql-api/main.py'
                                env.PYTHON_STATUS = 'passed'
                            } catch (e) {
                                env.PYTHON_STATUS = 'failed'
                                throw e
                            }
                        }
                    }
                }
                stage('JavaScript') {
                    steps {
                        script {
                            try {
                                sh 'node --check spark-api/index.js'
                                env.JS_STATUS = 'passed'
                            } catch (e) {
                                env.JS_STATUS = 'failed'
                                throw e
                            }
                        }
                    }
                }
                stage('Elixir Tests') {
                    agent {
                        docker {
                            image 'elixir:1.15-alpine'
                            args '-u root'
                            reuseNode true
                        }
                    }
                    steps {
                        script {
                            try {
                                sh '''
                                    apk add --no-cache build-base git
                                    cd oauth2-server
                                    mix local.hex --force
                                    mix local.rebar --force
                                    mix deps.get
                                    MIX_ENV=test mix test --color
                                '''
                                env.ELIXIR_STATUS = 'passed'
                            } catch (e) {
                                env.ELIXIR_STATUS = 'failed'
                                throw e
                            } finally {
                                // Copy test results before cleanup
                                sh 'cp -r oauth2-server/test-results . || true'
                                // Clean build artifacts to fix permission issues
                                sh 'rm -rf oauth2-server/_build oauth2-server/deps || true'
                            }
                        }
                    }
                }
                stage('YAML') {
                    steps {
                        script {
                            try {
                                sh "python3 -c \"import yaml; yaml.safe_load(open('docker-compose.yaml'))\""
                                env.YAML_STATUS = 'passed'
                            } catch (e) {
                                env.YAML_STATUS = 'failed'
                                throw e
                            }
                        }
                    }
                }
                stage('Dockerfiles') {
                    steps {
                        script {
                            try {
                                sh 'grep -q "^FROM" mysql-api/Dockerfile && grep -q "^FROM" spark-api/Dockerfile'
                                env.DOCKER_STATUS = 'passed'
                            } catch (e) {
                                env.DOCKER_STATUS = 'failed'
                                throw e
                            }
                        }
                    }
                }
            }
        }

        stage('Security') {
            steps {
                script {
                    def issues = sh(script: 'grep -rn "password.*=.*[0-9]" --include="*.py" --include="*.js" . 2>/dev/null || true', returnStdout: true).trim()
                    env.SECURITY_STATUS = issues ? 'warning' : 'passed'
                }
            }
        }

        stage('Publish Test Results') {
            steps {
                // Publish JUnit XML results for test trends
                junit allowEmptyResults: true, testResults: 'test-results/*.xml'

                // Publish HTML report
                publishHTML(target: [
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'test-results',
                    reportFiles: 'report.html',
                    reportName: 'ExUnit Test Report',
                    reportTitles: 'ExUnit Tests'
                ])
            }
        }

        stage('SonarQube Analysis') {
            agent {
                docker {
                    image 'sonarsource/sonar-scanner-cli:latest'
                    args '-u root --network host'
                    reuseNode true
                }
            }
            steps {
                script {
                    try {
                        sh '''
                            sonar-scanner \
                                -Dsonar.host.url=${SONAR_HOST_URL} \
                                -Dsonar.token=${SONAR_TOKEN} \
                                -Dsonar.projectKey=tp-devapi \
                                -Dsonar.projectName="TP DevAPI" \
                                -Dsonar.sources=mysql-api,spark-api,oauth2-server/lib \
                                -Dsonar.exclusions="**/node_modules/**,**/_build/**,**/deps/**,**/__pycache__/**,**/data/**"
                        '''
                        env.SONAR_STATUS = 'passed'
                    } catch (e) {
                        env.SONAR_STATUS = 'failed'
                        // Don't fail the build on SonarQube issues
                        echo "SonarQube analysis failed: ${e.message}"
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                writeFile file: 'payload.json', text: '{"ref":"refs/heads/main","repository":{"full_name":"Lajavel-gg/TP_devAPI"}}'
                script {
                    def response = sh(script: 'curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -H "X-GitHub-Event: push" -d @payload.json ${DOKPLOY_URL}/api/deploy/compose/${DOKPLOY_TOKEN}', returnStdout: true).trim()
                    def httpCode = response.split('\n')[-1]
                    if (httpCode == '200') {
                        env.DEPLOY_STATUS = 'passed'
                    } else {
                        env.DEPLOY_STATUS = 'failed'
                        error "Deployment failed"
                    }
                }
            }
        }

        stage('Report') {
            steps {
                script {
                    def reportName = "build-report-${BUILD_NUMBER}.txt"
                    def status = """
Build Report #${BUILD_NUMBER}
========================================
Date: ${new Date().format('yyyy-MM-dd HH:mm:ss')}
Commit: ${env.GIT_COMMIT_SHORT}
Author: ${env.GIT_AUTHOR}
Message: ${env.GIT_MESSAGE}

Test Results:
- Python:      ${env.PYTHON_STATUS ?: 'passed'}
- JavaScript:  ${env.JS_STATUS ?: 'passed'}
- Elixir:      ${env.ELIXIR_STATUS ?: 'passed'}
- YAML:        ${env.YAML_STATUS ?: 'passed'}
- Dockerfiles: ${env.DOCKER_STATUS ?: 'passed'}
- Security:    ${env.SECURITY_STATUS ?: 'passed'}
- SonarQube:   ${env.SONAR_STATUS ?: 'skipped'}
- Deploy:      ${env.DEPLOY_STATUS ?: 'passed'}

Reports:
- ExUnit HTML: ${BUILD_URL}ExUnit_20Test_20Report/
- JUnit:       ${BUILD_URL}testReport/
- SonarQube:   ${env.SONAR_HOST_URL}/dashboard?id=tp-devapi
========================================
"""
                    writeFile file: reportName, text: status
                    archiveArtifacts artifacts: reportName, fingerprint: true
                    echo status
                }
            }
        }
    }

    post {
        success {
            echo '=========================================='
            echo '  BUILD SUCCESS - PDF Report Generated'
            echo '=========================================='
        }
        failure {
            echo '=========================================='
            echo '  BUILD FAILED - Check logs'
            echo '=========================================='
        }
        always {
            cleanWs(cleanWhenNotBuilt: false, deleteDirs: true, disableDeferredWipeout: true, notFailBuild: true)
        }
    }
}
