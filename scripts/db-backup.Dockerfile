# Image for the db-backup compose service: postgres:15 for pg_dump (same
# major version as the db service), plus the AWS CLI to copy each dump
# off-site and curl to post failure alerts to Discord.
FROM postgres:15

RUN apt-get update \
    && apt-get install -y --no-install-recommends awscli curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
