node('master'){
    def params
    switch(env.BRANCH_NAME) {
        case "master":
            environment = "staging"
            app_id_group = "/staging/"
        break
        case "production":
            environment = "production"
            app_id_group = ""
        break
        default:
            print "Invalid branch"
            currentBuild.result = "FAILURE"
            throw err
        break
    }
    type = 'group'
}

node('mesos') {
    def image
    def flower_image
    def app_id = "mozillians"
    def dockerRegistry = "docker-registry.ops.mozilla.community:443"

    stage('Prep') {
        checkout scm
        gitCommit = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
        params = [string(name: 'environment', value: "production"),
                  string(name: 'commit_id', value: gitCommit),
                  string(name: 'marathon_id', value: app_id_group + app_id),
                  string(name: 'marathon_config', value: 'mozillians_' + environment + '.json'),
                  string(name: 'type', value: 'group')]
    }

    stage('Build') {
        image = docker.build(app_id + ":" + gitCommit, "-f docker/prod .")
        flower_image = docker.build(app_id + "-flower:" + gitCommit, "-f docker/flower .")
    }

    stage('Push') {
      parallel (
        push-mozillians: {
          sh "docker tag ${image.imageName()} " + dockerRegistry + "/${image.imageName()}"
          sh "docker push " + dockerRegistry + "/${image.imageName()}"
        },
        push-flower: {
          sh "docker tag ${flower-image.imageName()} " + dockerRegistry + "/${flower-image.imageName()}"
          sh "docker push " + dockerRegistry + "/${flower-image.imageName()}"
        }
      )
    }
}

node('master') {
    stage('Deploy') {
        build job: 'deploy-test', parameters: params
    }
}
