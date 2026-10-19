#!/bin/bash
# Create a login role for an app plus one or more databases it owns.
#   ./create-app-db.sh <role> <db> [<db> ...]
# Prints the generated password ONCE on stdout (store it in the app's .env, chmod 600).
# Re-running for an existing role leaves its password unchanged and only adds missing databases.
set -euo pipefail
[ $# -ge 2 ] || { echo "usage: $0 <role> <db> [<db>...]" >&2; exit 2; }
role=$1; shift
psql() { docker exec -i postgres psql -U postgres -v ON_ERROR_STOP=1 -Aqt "$@"; }

if [ "$(psql -c "select 1 from pg_roles where rolname='$role'")" != 1 ]; then
    pw=$(openssl rand -hex 24)
    psql -c "create role \"$role\" login password '$pw'"
    echo "$pw"
else
    echo "role $role exists, password unchanged" >&2
fi
for db in "$@"; do
    if [ "$(psql -c "select 1 from pg_database where datname='$db'")" != 1 ]; then
        psql -c "create database \"$db\" owner \"$role\""
        # nobody else may connect to this app's database
        psql -c "revoke connect on database \"$db\" from public"
        echo "created database $db" >&2
    fi
done
