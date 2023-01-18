-- create ta_docker_stats table
CREATE TABLE ta_docker_stats (
    id SERIAL NOT NULL PRIMARY KEY,
    time_stamp INT NOT NULL,
    time_stamp_human VARCHAR(20) NOT NULL,
    last_updated INT NOT NULL,
    last_updated_human VARCHAR(20) NOT NULL,
    stars SMALLINT NOT NULL,
    pulls INT NOT NULL
);

-- index for time_stamp where queries
CREATE INDEX docker_time_stamp ON ta_docker_stats (time_stamp DESC);

-- ingest old csv archive
COPY ta_docker_stats(time_stamp,time_stamp_human,last_updated,last_updated_human,stars,pulls)
FROM '/dockerstats.csv'
DELIMITER ','
CSV HEADER;

-- create ta_version_stats table
CREATE TABLE ta_version_stats (
    id SERIAL NOT NULL PRIMARY KEY,
    ping_date DATE NOT NULL,
    ping_count INT NOT NULL,
    latest_version VARCHAR(10) NOT NULL
);

-- create release history table
CREATE TABLE ta_release (
    id SERIAL NOT NULL PRIMARY KEY,
    time_stamp INT NOT NULL,
    time_stamp_human VARCHAR(20) NOT NULL,
    release_version VARCHAR(10) NOT NULL,
    release_is_latest BOOLEAN NOT NULL,
    breaking_changes BOOLEAN NOT NULL,
    release_notes TEXT NOT NULL 
);

-- create roadmap history table
CREATE TABLE ta_roadmap (
    id SERIAL NOT NULL PRIMARY KEY,
    time_stamp INT NOT NULL,
    time_stamp_human VARCHAR(20) NOT NULL,
    last_id VARCHAR(20) NOT NULL,
    implemented TEXT NOT NULL,
    pending TEXT NOT NULL
);
