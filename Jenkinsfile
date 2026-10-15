pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "albion-ci"
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Код получен из репозитория'
            }
        }

        stage('Build') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Run') {
            steps {
                sh 'docker compose up -d'
                sh 'sleep 5'
                sh 'docker compose ps'
            }
        }
    }

    post {
        always {
            sh 'docker compose down || true'
        }
    }
}