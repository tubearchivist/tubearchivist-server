#!/bin/bash
# deploy the tube archivist website

test_host="tubearchivist-website.local"
public_host="tubearchivist.com"

function rebuild_test {
    echo "rebuild testing environment"
    rsync -a --progress --delete docker-compose_testing.yml $test_host:docker/docker-compose.yml
    rsync -a --progress --delete tubearchivist $test_host:docker
    rsync -a --progress --delete env $test_host:docker
    
    ssh "$test_host" 'docker-compose -f docker/docker-compose.yml up -d --build'
}

function docker_publish {
    echo "publish to production"

    rsync -a --progress --delete docker-compose_production.yml $public_host:docker/docker-compose.yml
    rsync -a --progress --delete tubearchivist $public_host:docker
    rsync -a --progress --delete env $public_host:docker

    ssh "$public_host" 'docker compose -f docker/docker-compose.yml build tubearchivist'
    ssh "$public_host" 'docker compose -f docker/docker-compose.yml up -d'
}

# check package versions in requirements.txt for updates
python version_check.py

if [[ $1 == "test" ]]; then
    rebuild_test
elif [[ $1 == "docker" ]]; then
    docker_publish
else
    echo "valid options are: test | docker "
fi

##
exit 0
