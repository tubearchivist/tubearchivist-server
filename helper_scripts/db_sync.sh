#!/bin/bash
# sync production db to local testing vm

remote_host="vps3"
local_host="tubearchivist-website.local"

echo "------------------------------------------------------------"
echo "sync db from $remote_host to $local_host"
echo "------------------------------------------------------------"

# download
printf "\n  -> backup\n"
ssh $remote_host 'docker exec postgres pg_dump -U archivist | gzip > backup.gz'
printf "\n  -> download\n"
rsync --progress -r --delete-after -e ssh $remote_host:backup.gz /tmp/backup.gz

# sync
printf "\n  -> sync\n"
rsync --progress -r --delete-after /tmp/backup.gz -e ssh $local_host:backup
ssh $local_host 'gzip -df backup/backup.gz'

# replace
printf "\n  -> replace\n"
ssh $local_host "docker exec -i postgres psql -U archivist -c 'DROP TABLE IF EXISTS ta_docker_stats;'"
ssh $local_host "docker exec -i postgres psql -U archivist -c 'DROP TABLE IF EXISTS ta_release;'"
ssh $local_host "docker exec -i postgres psql -U archivist -c 'DROP TABLE IF EXISTS ta_roadmap;'"
ssh $local_host "docker exec -i postgres psql -U archivist -c 'DROP TABLE IF EXISTS ta_version_stats;'"
ssh $local_host 'docker exec -i postgres psql -U archivist -d archivist < backup/backup'
ssh $local_host "trash backup/backup"
printf "\n  -> done\n"

##
exit 0
