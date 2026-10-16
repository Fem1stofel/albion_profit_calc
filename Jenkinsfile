pipeline {
    agent any

    environment {
        // Настройки подключения к базе данных (БД работает локально, НЕ в контейнере)
        DB_HOST = 'localhost'
        DB_PORT = '5432'
        DB_NAME = 'albion_profit'
        DB_USER = 'postgres'
        DB_PASSWORD = '123'
        DB_SCHEMA = 'albion'
        APP_PORT = '8000'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '=== [1/5] Получение исходного кода ==='
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '=== [2/5] Проверка и установка зависимостей Python ==='
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv .venv || true
                            . .venv/bin/activate || true
                            pip install -r requirements.txt
                        '''
                    } else {
                        bat 'ci_runner.bat -m pip install -r requirements.txt'
                    }
                }
            }
        }

        stage('Database Setup (No Container)') {
            steps {
                echo '=== [3/5] Инициализация БД (без контейнеров): подключение к существующей или создание новой ==='
                script {
                    if (isUnix()) {
                        sh '''
                            . .venv/bin/activate || true
                            python3 init_db.py
                        '''
                    } else {
                        bat 'ci_runner.bat init_db.py'
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                echo '=== [4/5] Запуск модульных и интеграционных тестов ==='
                script {
                    if (isUnix()) {
                        sh '''
                            . .venv/bin/activate || true
                            pytest test_main.py -v --junitxml=test-results.xml
                        '''
                    } else {
                        bat 'ci_runner.bat -m pytest test_main.py -v --junitxml=test-results.xml'
                    }
                }
            }
        }

        stage('Smoke Test App') {
            steps {
                echo '=== [5/5] Проверка запуска веб-сервера FastAPI ==='
                script {
                    if (isUnix()) {
                        sh '''
                            . .venv/bin/activate || true
                            python3 -c "from main import app; print('[OK] FastAPI app successfully initialized')"
                        '''
                    } else {
                        bat 'ci_runner.bat -c "from main import app; print(\'[OK] FastAPI app successfully initialized\')"'
                    }
                }
            }
        }
    }

    post {
        always {
            echo 'Пайплайн завершён.'
            junit allowEmptyResults: true, testResults: 'test-results.xml'
        }
        success {
            echo '======================================================='
            echo ' [OK] CI/CD успешно пройден: база подключена, тесты пройдены!'
            echo '======================================================='
        }
        failure {
            echo '======================================================='
            echo ' [!] Ошибка в процессе сборки / тестирования!'
            echo '======================================================='
        }
    }
}