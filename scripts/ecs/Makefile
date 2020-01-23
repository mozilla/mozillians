COMMIT_HASH=$(shell git rev-parse --short HEAD)
DOCKER_REPO=$(ECS_DOCKER_REPO)
ENV=$(ECS_ENV)
CLUSTER=$(ECS_CLUSTER)

.PHONY: help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

check-aws-dep:
	@which aws

check-ecs-deploy-dep:
	@which ecs-deploy

check-jq-dep:
	@which jq

check-deps: check-aws-dep check-ecs-deploy-dep check-jq-dep

build-web: ## Build mozillians web docker image
	docker build -t mozillians:$(COMMIT_HASH) -f ../../docker/prod ../../ --no-cache

tag-web: build-web ## Tag mozillians web docker image
	docker tag mozillians:$(COMMIT_HASH) $(DOCKER_REPO):$(COMMIT_HASH)

push-web: tag-web ## Push mozillians web docker image
	docker push $(DOCKER_REPO):$(COMMIT_HASH)

deploy-web: push-web check-deps ## Deploy new image to ECS web service
	ecs-deploy -c $(CLUSTER) -n mozillians-$(ENV)-web -i $(DOCKER_REPO):$(COMMIT_HASH) --skip-deployments-check --timeout 300

deploy-celery: push-web check-deps ## Deploy new image to ECS celery service
	ecs-deploy -c $(CLUSTER) -n mozillians-$(ENV)-celery -i $(DOCKER_REPO):$(COMMIT_HASH) --skip-deployments-check --timeout 300

deploy-celerybeat: push-web check-deps ## Deploy new image to ECS celerybeat service
	ecs-deploy -c $(CLUSTER) -n mozillians-$(ENV)-celery-beat -i $(DOCKER_REPO):$(COMMIT_HASH) --skip-deployments-check --timeout 300

deploy-all: deploy-web deploy-celery deploy-celerybeat ## Deploy new image to all ECS services
