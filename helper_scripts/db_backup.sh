#!/bin/bash
# postgres backup and log management

time_stamp=$(date '+%Y%m%d')
time_date=$(date '+%Y%m%d_%H%M%S')
backup_dir="$HOME/backup"

# backup
docker exec postgres pg_dump -U archivist | gzip > "$backup_dir/pg_$time_stamp.gz"

# rotate
find "$backup_dir" -type f -name "pg_*.gz" | sort -r | tail -n +7 | xargs --no-run-if-empty trash

# log
log_file="$backup_dir/pg_status.log"

query1="SELECT schemaname AS table_schema, \
       relname AS table_name, \
       pg_size_pretty(pg_relation_size(relid)) AS data_size \
FROM pg_catalog.pg_statio_user_tables \
ORDER BY pg_relation_size(relid) DESC;"

query2="SELECT schemaname,relname,n_live_tup \
       FROM pg_stat_user_tables \
       ORDER BY n_live_tup DESC;"

echo "postgres dump run at $time_date" > "$log_file"
echo "table size" >> "$log_file"
docker exec postgres psql -U archivist -c "$query1" >> "$log_file"
echo "row count" >> "$log_file"
docker exec postgres psql -U archivist -c "$query2" >> "$log_file"

##
exit 0
