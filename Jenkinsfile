pipeline {
  agent any
  stages {
    stage('Build') {
            steps {
                script {
                  withCredentials([file(credentialsId: 'jenkins-sa', variable: 'gcp')]) {
                            c = docker.build("phewas-development/ld-server:ci-${env.$GIT_COMMIT}", "-f deploy/Dockerfile ./")
                            docker.withRegistry('http://eu.gcr.io/phewas-development', 'gcr:phewas-development') { c.push("ci-${env.GIT_COMMIT}") }
                            docker.withRegistry('http://eu.gcr.io/phewas-development', 'gcr:phewas-development') { c.push("ci-latest") }
                  }
                }
            }
        }
    }
}
