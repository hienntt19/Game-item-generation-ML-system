pipeline {
    agent any

    environment {
        PROJECT_ID = 'game-item-generation'
        GKE_CLUSTER = 'game-item-generation-service-cluster'
        GKE_REGION = 'asia-southeast1'
        DOCKER_IMAGE_NAME = 'sheehan19/api-gateway'

        HELM_CHART_PATH   = 'deployments/api_gateway'
        HELM_RELEASE_NAME = 'api-gateway'
        TARGET_NAMESPACE  = 'service-dev'
        TEST_DIRECTORY    = 'tests'

        POSTGRES_USER         = credentials('api-gateway-postgres-user')
        POSTGRES_PASSWORD     = credentials('api-gateway-postgres-pass')
        POSTGRES_DB           = credentials('api-gateway-postgres-db')
        RABBITMQ_HOST         = credentials('api-gateway-rabbitmq-host')
        RABBITMQ_DEFAULT_USER = credentials('api-gateway-rabbitmq-user')
        RABBITMQ_DEFAULT_PASS = credentials('api-gateway-rabbitmq-pass')
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo 'Checking out source code...'
                checkout scm
            }
        }

        stage('Test') {
            steps {
                echo "Installing Python3, Pip, and Venv..."
                sh 'apt-get update && apt-get install -y python3 python3-pip python3-venv'

                echo "Creating and activating virtual environment..."
                sh 'python3 -m venv .venv' 

                echo "Installing dependencies into virtual environment..."
                sh '''
                    . .venv/bin/activate
                    pip install -r requirements.txt
                '''

                echo "Running unit tests using virtual environment..."
                sh '''
                    . .venv/bin/activate
                    export PYTHONPATH=.
                    pytest tests/
                '''
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    script {
                        echo "Logging into Docker Hub..."
                        sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
                        
                        def imageTag = "${env.DOCKER_IMAGE_NAME}:${env.BUILD_NUMBER}"
                        
                        echo "Building Docker image: ${imageTag}"
                        sh "docker build -t ${imageTag} ."
                        
                        echo "Pushing Docker image to Docker Hub..."
                        sh "docker push ${imageTag}"
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    echo "Installing prerequisites and Google Cloud SDK repository..."
                    sh '''
                        apt-get update
                        apt-get install -y apt-transport-https ca-certificates gnupg curl
                        
                        echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
                        
                        curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --batch --yes --dearmor -o /usr/share/keyrings/cloud.google.gpg
                        
                        apt-get update
                    '''

                    echo "Installing GKE auth plugin..."
                    sh 'apt-get install -y google-cloud-cli google-cloud-sdk-gke-gcloud-auth-plugin'

                    echo "Deploying to GKE cluster '${env.GKE_CLUSTER}'..."
                    sh "gcloud container clusters get-credentials ${env.GKE_CLUSTER} --region ${env.GKE_REGION} --project ${env.PROJECT_ID}"
                    
                    withCredentials([
                        string(credentialsId: 'api-gateway-postgres-user', variable: 'PG_USER'),
                        string(credentialsId: 'api-gateway-postgres-pass', variable: 'PG_PASS'),
                        string(credentialsId: 'api-gateway-postgres-db', variable: 'PG_DB'),
                        string(credentialsId: 'api-gateway-rabbitmq-host', variable: 'RMQ_HOST'),
                        string(credentialsId: 'api-gateway-rabbitmq-user', variable: 'RMQ_USER'),
                        string(credentialsId: 'api-gateway-rabbitmq-pass', variable: 'RMQ_PASS')
                    ]) {
                        sh """
                        helm upgrade --install ${env.HELM_RELEASE_NAME} ${env.HELM_CHART_PATH} \
                            --namespace ${env.TARGET_NAMESPACE} \
                            --set image.repository=${env.DOCKER_IMAGE_NAME} \
                            --set image.tag=${env.BUILD_NUMBER} \
                            --set-string database.user="$PG_USER" \
                            --set-string database.password="$PG_PASS" \
                            --set-string database.name="$PG_DB" \
                            --set-string secret.rabbitmqHost="$RMQ_HOST" \
                            --set-string secret.rabbitmqUser="$RMQ_USER" \
                            --set-string secret.rabbitmqPass="$RMQ_PASS" \
                            --wait
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished. Cleaning up...'
            sh 'docker logout'
            cleanWs()
        }
    }
}
