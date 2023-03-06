#!/bin/bash
# deploy the tube archivist website

test_host="tubearchivist-website.local"
public_host="vps3"

function rebuild_test {
    echo "rebuild testing environment"
    rsync -a --progress --delete docker-compose_testing.yml $test_host:docker/docker-compose.yml
    rsync -a --progress --delete tubearchivist $test_host:docker
    rsync -a --progress --delete env $test_host:docker
    rsync -a --progress --delete helper_scripts $test_host:
    rsync -a --progress --delete builder/ $test_host:builder
    ssh "$test_host" "mkdir -p builder/clone"
    ssh "$test_host" 'docker compose -f docker/docker-compose.yml up -d --build'
}

function docker_publish {
    echo "publish to production"

    rsync -a --progress --delete docker-compose_production.yml $public_host:docker/docker-compose.yml
    rsync -a --progress --delete tubearchivist $public_host:docker
    rsync -a --progress --delete env $public_host:docker
    rsync -a --progress --delete helper_scripts $public_host:
    rsync -a --progress --delete builder/ $public_host:builder
    ssh "$public_host" "mkdir -p builder/clone"
    ssh "$public_host" 'docker compose -f docker/docker-compose.yml up -d --build'
}

if [[ $1 == "test" ]]; then
    rebuild_test
elif [[ $1 == "docker" ]]; then
    docker_publish
else
    echo "valid options are: test | docker "
fi

##
exit 0
