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
