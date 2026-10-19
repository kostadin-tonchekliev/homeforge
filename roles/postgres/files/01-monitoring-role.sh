#!/bin/bash
# Runs once, when the data directory is first initialised: read-only role for postgres-exporter.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<SQL
CREATE ROLE exporter WITH LOGIN PASSWORD '${EXPORTER_PASSWORD}';
GRANT pg_monitor TO exporter;
SQL
