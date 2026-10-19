# Shared PostgreSQL server: operations & restore guide

One PostgreSQL 17 server for the homelab. Each app has its **own database and its own login**, and can't see the others.

| App | Database(s) | Login | Connects via | Password stored in |
|---|---|---|---|---|
| GitLab | `gitlabhq_production` | `gitlab` | `postgres:5432` (docker network `db`) | `/opt/gitlab/.env` |
| Home Assistant (recorder) | `homeassistant` | `homeassistant` | `127.0.0.1:5432` (HA uses host networking) | `/opt/home-assistant/config/secrets.yaml` (`recorder_db_url`) |
| Sonarr / Radarr / Prowlarr | `<app>-main`, `<app>-log` | `sonarr` / `radarr` / `prowlarr` | `postgres:5432` | `/opt/<app>/.env` |
| Jellystat | `jfstat` (+ empty `jellystat`) | `jellystat` | `postgres:5432` | `/opt/jellystat/.env` |
| Grafana (systemd) | `grafana` | `grafana` | `127.0.0.1:5432` | `/etc/grafana/grafana.ini` `[database]` |
| Open WebUI | `openwebui` | `openwebui` | `postgres:5432` | `/opt/ollama/.env` |
| *(metrics)* | – | `exporter` (read-only, `pg_monitor`) | `postgres:5432` | `/opt/postgres/.env` |

Superuser: `postgres`, password in `/opt/postgres/.env` (`POSTGRES_PASSWORD`).

Still on their own SQLite files (no PostgreSQL support): Uptime Kuma, Jellyfin, Kavita, Audiobookshelf, Pi-hole, Dockhand, ntopng.

## Layout

```
/opt/postgres/
├── docker-compose.yaml      postgres (17), postgres-exporter
├── .env                     POSTGRES_PASSWORD, EXPORTER_PASSWORD  (chmod 600)
├── data/                    the database files. Never copy these while postgres is running.
├── init/                    runs only when data/ is empty (creates the exporter role)
└── create-app-db.sh         helper: create a login + database(s) for a new app
```

- **Networking:** the `db` docker network is internal-only. Port 5432 is published on `127.0.0.1` only, for Home Assistant and Grafana. Nothing on the LAN can reach the database.
- **Monitoring:**
  - Grafana dashboard **PostgreSQL** (Homelab folder), fed by Prometheus job `postgres` (`127.0.0.1:9187`).
  - Uptime Kuma: docker monitors `postgres` and `postgres-exporter`.

## Backups

**There is no automatic backup job** (removed on 2026-10-11 at the owner's request). Take backups by hand with the commands below. They produce the same layout the restore steps expect: `/media/backups/postgres/YYYY-MM-DD/`, root-only.

```bash
B=/media/backups/postgres/$(date +%F); sudo install -d -m 700 "$B" "$B/jellyfin"
# logins (roles) with their password hashes
docker exec postgres pg_dumpall -U postgres --globals-only | sudo tee "$B/globals.sql" >/dev/null
# one file per database
for DB in $(docker exec postgres psql -U postgres -Atc "select datname from pg_database where not datistemplate and datname <> 'postgres'"); do
  docker exec postgres pg_dump -U postgres -Fc -d "$DB" | sudo tee "$B/$DB.dump" >/dev/null && echo "dumped $DB"
done
sudo chmod 600 "$B"/*
# Jellyfin (SQLite): stop it briefly for a consistent copy
sudo systemctl stop jellyfin && sudo zstd -q -f /var/lib/jellyfin/data/jellyfin.db -o "$B/jellyfin/jellyfin.db.zst"; sudo systemctl start jellyfin
```

- **No backups exist right now.** The post-migration backup and the pre-migration restore point were deleted on 2026-10-11 at the owner's request. Run the commands above to create one.
- GitLab note: a database dump covers GitLab's **database only**. Repositories, uploads and `gitlab-secrets.json` live under `/opt/gitlab`. For a complete GitLab backup, use `docker exec gitlab gitlab-backup create` and keep `/opt/gitlab/config/gitlab-secrets.json` with it.

## Restore

All commands run on the server. Set this first:

```bash
B=/media/backups/postgres/YYYY-MM-DD      # pick the day to restore from: sudo ls /media/backups/postgres
```

### A. Restore one app's database (most common)

1. **Stop the app** so it isn't writing:

   | App | Stop | Start |
   |---|---|---|
   | Sonarr/Radarr/Prowlarr/Jellystat | `cd /opt/<app> && docker compose stop` | `docker compose start` |
   | Open WebUI | `cd /opt/ollama && docker compose stop open-webui` | `docker compose start open-webui` |
   | Home Assistant | `cd /opt/home-assistant && docker compose stop` | `docker compose start` |
   | Grafana | `sudo systemctl stop grafana-server` | `sudo systemctl start grafana-server` |
   | GitLab | `docker exec gitlab gitlab-ctl stop puma && docker exec gitlab gitlab-ctl stop sidekiq` | `docker exec gitlab gitlab-ctl restart` |

2. **Recreate the database empty and restore it** (example: Sonarr. Swap the database name and owner login):

   ```bash
   DB=sonarr-main; OWNER=sonarr
   docker exec postgres psql -U postgres -c "drop database if exists \"$DB\" with (force)" \
       -c "create database \"$DB\" owner \"$OWNER\"" -c "revoke connect on database \"$DB\" from public"
   # GitLab only: re-create the extensions first (its login isn't allowed to):
   #   docker exec postgres psql -U postgres -d gitlabhq_production -c "create extension pg_trgm; create extension btree_gist; create extension amcheck;"
   sudo cat "$B/$DB.dump" | docker exec -i postgres pg_restore -U postgres -d "$DB" --no-owner --role="$OWNER" --exit-on-error
   ```
   For GitLab, leave out `--exit-on-error`. The "must be owner of extension" errors are expected and harmless.

3. **Start the app again** and check that it works.

### B. Rebuild the whole server (lost/corrupt `data/` directory)

```bash
cd /opt/postgres && docker compose down
sudo mv data data.broken-$(date +%F) && mkdir data           # keep the broken copy until you're done
docker compose up -d postgres                                  # fresh, empty server (re-creates the exporter role)
until docker exec postgres pg_isready -U postgres; do sleep 2; done
# 1) logins, with their original passwords ("already exists" errors for postgres/exporter are fine)
sudo cat "$B/globals.sql" | docker exec -i postgres psql -U postgres -q
# 2) every database (owner = the login that owned it before)
for f in $(sudo ls "$B"/*.dump); do
  DB=$(basename "$f" .dump)
  OWNER=$(echo "$DB" | sed -E 's/-(main|log)$//; s/^gitlabhq_production$/gitlab/; s/^jfstat$/jellystat/')
  docker exec postgres psql -U postgres -qc "create database \"$DB\" owner \"$OWNER\"" -c "revoke connect on database \"$DB\" from public"
  [ "$DB" = gitlabhq_production ] && docker exec postgres psql -U postgres -d "$DB" -qc "create extension pg_trgm; create extension btree_gist; create extension amcheck;"
  sudo cat "$f" | docker exec -i postgres pg_restore -U postgres -d "$DB" --no-owner --role="$OWNER"
done
docker compose up -d                                           # starts the exporter too
```
Then restart the apps (table above). Passwords in the apps' `.env` files still match, because `globals.sql` restored the same password hashes.

### C. Restore Jellyfin's database

```bash
sudo systemctl stop jellyfin
sudo cp -p /var/lib/jellyfin/data/jellyfin.db /var/lib/jellyfin/data/jellyfin.db.before-restore
sudo zstd -d -f "$B/jellyfin/jellyfin.db.zst" -o /var/lib/jellyfin/data/jellyfin.db
sudo rm -f /var/lib/jellyfin/data/jellyfin.db-wal /var/lib/jellyfin/data/jellyfin.db-shm
sudo chown jellyfin:jellyfin /var/lib/jellyfin/data/jellyfin.db
sudo systemctl start jellyfin
```
The Intro Skipper plugin databases (`introskipper*.db`) restore the same way, into `/var/lib/jellyfin/data/introskipper/`.

### D. Test a backup without touching anything

```bash
docker exec postgres psql -U postgres -c "create database restore_test"
sudo cat "$B/sonarr-main.dump" | docker exec -i postgres pg_restore -U postgres -d restore_test --no-owner --exit-on-error && echo OK
docker exec postgres psql -U postgres -c "drop database restore_test"
```

## Maintenance

- **Add a new app:**
  1. Run `/opt/postgres/create-app-db.sh <login> <database> [<database>...]`. It prints a new password once; store it in the app's `.env` (chmod 600).
  2. Put the app on the external `db` network (or use `127.0.0.1:5432` for host-network apps).

- **psql shell:** `docker exec -it postgres psql -U postgres` (add `-d <database>`).
- **Sizes:** `docker exec postgres psql -U postgres -c "select datname, pg_size_pretty(pg_database_size(datname)) from pg_database order by pg_database_size(datname) desc"`
- **Minor updates** (17.x → 17.y): `docker compose pull postgres && docker compose up -d postgres`.
- **Major upgrade** (17 → 18): the data directory can't be reused. Do it before GitLab requires it:
  1. Run a fresh backup.
  2. Change the image to `postgres:18`.
  3. Move `data/` aside.
  4. Follow **B** using the fresh backup.
  5. The `postgres:18` image stores data at `/var/lib/postgresql` (not `.../data`), so adjust the volume line.

## History

- **2026-10-11:** apps moved here from SQLite, Jellystat's private Postgres 18 and GitLab's bundled Postgres 17.
  - The pre-migration restore point was deleted on 2026-10-11 once the changes were accepted.
  - The old data was deleted the same day: Jellystat's `/opt/jellystat/db`, GitLab's bundled `/opt/gitlab/data/postgresql`, and the apps' original SQLite files.
