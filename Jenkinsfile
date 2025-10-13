pipeline {
    agent any

    environment {
        PROJECT_ID = 'game-item-generation'
        GKE_CLUSTER = 'game-item-generation-service-cluster'
        GKE_ZONE = 'asia-southeast1-a'
        DOCKER_IMAGE = 'sheehan19/api-gateway'

        HELM_CHART_PATH   = 'deployments/api_gateway'
        HELM_RELEASE_NAME = 'api-gateway'
        TARGET_NAMESPACE  = 'service-dev'
        TEST_DIRECTORY    = 'tests'
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
                    pytest tests/
                '''
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                withCredentials(
                    [usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]
                )
                script {
                    echo "Logging into dockerhub..."
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    def imageTag = "${env.DOCKER_IMAGE_NAME}:${env.BUILD_NUMBER}"

                    echo "Building Docker image: ${imageTag}"
                    sh "docker build -t ${imageTag} ."
                    
                    echo "Pushing Docker image to Docker Hub..."
                    sh "docker push ${imageTag}"
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    echo "Deploying to GKE cluster '${env.GKE_CLUSTER}'... in namespace '${env.TARGET_NAMESPACE}'..."
                    sh "gcloud container clusters get-credentials ${env.GKE_CLUSTER} --zone ${env.GKE_ZONE} --project ${env.PROJECT_ID}"
                    
                    sh """
                    helm upgrade --install ${env.HELM_RELEASE_NAME} ${env.HELM_CHART_PATH} \
                        --set image.repository=${env.DOCKER_IMAGE_NAME} \
                        --set image.tag=${env.BUILD_NUMBER} \
                        --namespace ${env.TARGET_NAMESPACE} \
                        --wait
                    """
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
