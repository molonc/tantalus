node {

    try {
        stage 'Checkout'
            checkout scm

            sh 'git log HEAD^..HEAD --pretty="%h %an - %s" > GIT_CHANGES'
            def lastChanges = readFile('GIT_CHANGES')
            slackSend color: "warning", message: "Started `${env.JOB_NAME}#${env.BUILD_NUMBER}`\n\n_The changes:_\n${lastChanges}"

        stage 'Testing'
            slackSend color: "warning", message: "Deploying to Test Server for build `${env.JOB_NAME}#${env.BUILD_NUMBER}`"
            sh "az login --service-principal --username $CLIENT_ID --password $SECRET_KEY --tenant $TENANT_ID"
            sh "az vm start -g olympus -n tantalus-test"

            slackSend color: "warning", message: "Test Server Initialized" 
            sh "ssh ubuntu@$TantalusTestVM bash -e /home/ubuntu/tantalus/test/test_tantalus.sh"
            sh "az vm stop -g olympus -n tantalus-test"
            slackSend color: "warning", message: "Finished Testing `${env.JOB_NAME}#${env.BUILD_NUMBER}` and Test Server Deallocated"

        stage 'Deploy'
            sh "ssh ubuntu@$TantalusVM_IP bash -e /home/dalai/tantalus/deployment/deploy_production_tantalus.sh"

        stage 'Publish results'
            slackSend color: "good", message: "Congrats! Build successful: `${env.JOB_NAME}#${env.BUILD_NUMBER}` <${env.BUILD_URL}|Open in Jenkins>"
    }

    catch (err) {
        slackSend color: "danger", message: "Error! Build failed :face_with_head_bandage: \n`${env.JOB_NAME}#${env.BUILD_NUMBER}` <${env.BUILD_URL}|Open in Jenkins>"

        throw err
    }

}