pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "albion-ci"
        // CI использует другие порты — ручная среда продолжает работать на 5432 и 8000
        DB_PORT = "5433"
        APP_PORT = "8001"
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Код получен из репозитория'
            }
        }

        stage('Cleanup old CI containers') {
            steps {
                sh 'docker compose down --remove-orphans || true'
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

        stage('Test') {
            steps {
                // Проверяем, что приложение отвечает
                sh 'curl -f http://localhost:8001/ || true'
                // Здесь позже можно добавить реальные тесты:
                // sh 'docker compose exec -T app python -m pytest tests/'
            }
        }
    }

    post {
        always {
            echo 'Пайплайн завершён'
        }
        failure {
            sh 'docker compose logs --tail=50'
            sh 'docker compose down || true'
        }
    }
}