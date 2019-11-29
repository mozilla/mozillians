# Deploying to ECS
## Current setup

* One `generic` ECS cluster for mozillians prod/staging
* We are hosting images in amazon ECR
  * One repository for all images
  * Images are using tags with git hashes for versioning
* 4 services per env
  * mozillians-{staging,prod}-media
    * Nginx to serve media files
    * Media files are stored in EFS and mounted in all cluster nodes
  * mozillians-{staging,prod}-web
    * Web workers for mozillians.org
    * State
      * MySQL
        * RDS
      * Redis for celery message broker
        * ElasticCache
      * Memcache for caching
        * ElasticCache
  * mozillians-{staging,prod}-celery
    * Celery workers for mozillians
  * mozillians-{staging,prod}-celerybeat
    * Celerybeat scheduler for celery
    * Needs to be only a single instance running
* Load balancing
  * SSL termination and load balancing is happening using ALB
  * One ALB instance for both envs

## Deploying code

Given that development cadence is very low there is no CI for releasing code.
Tests are run in travis using GitHub automation. There is `Makefile` to make
deploying code easier.

To deploy new code

* Make sure you have dependencies installed
  * `aws`
  * `jq`
  * `ecs-deploy`
* We are building images locally so make sure your local setup is clean (eg. no `.env` files, no untracked files)
* Assume the AWS IAM `AdminAccessRole` to be able to deploy changes
* Authenticate docker to use ECR
* Export required environment variables
  * `ECS_DOCKER_REPO`
  * `ECS_ENV`
  * `ECS_CLUSTER`
* `git checkout` to the branch/tag you want to deploy
* `make deploy-all` to deploy all services
  * Builds new docker images tagged as `mozillians:<git-rev>`
  * Pushes images in docker registry (ECR)
  * Deploys new code to ECS
