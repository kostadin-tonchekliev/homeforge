# homeforge — context for Claude sessions

This repository describes the owner's home server, **bigboy**, in Ansible, so the whole
server can be rebuilt from it. Read this before changing anything. The README covers
day-to-day usage; this file covers how everything fits together, the conventions, and the
traps.

## Ground rules

- **Never apply anything to prod without the owner's explicit OK.** That covers playbook
  runs against `inventory/production.yml`, `docker compose` on the server, and edits of
  app settings. Dry runs (`--check --diff`) and anything in the sandbox are fine at any
  time.
- **Test every change in the sandbox first** (`inventory/dev.yml`, see [Sandbox](#sandbox)),
  then dry-run on prod, then apply on prod after the OK.
- **Show the prod `--check --diff` before applying.** Most stacks are already running, so
  the diff should be empty or contain only the intended change.
- **One-off migrations** (moving data, switching a service from the host to a container)
  are run as commands directly on the server, with `sudo`, checking each step. The roles
  only ever describe the end state: no one-time migration playbooks.
- **Work on a branch** named `<type>/<kebab-case>` (`feature/`, `bugfix/`, `chore/`,
  `refactor/`, `docs/`, `test/`), branched from `main`, and open a PR. CI must be green:
  ansible-lint (production profile), yamllint, syntax check.
- **Never commit secrets.** The repo is **public**. Secrets go in the vault (see
  [Secrets](#secrets)). Before merging, check for leaks (for example with gitleaks).
- **Use `:latest` image tags** for new services. Only pin with a concrete reason;
  existing pins are listed in [Services](#services).

## The server

| | |
|---|---|
| Hardware | HP mini PC, Intel Core i3-9100T (4 cores), 15 GB RAM, x86_64 |
| OS | Ubuntu 24.04 LTS, host timezone `Etc/UTC` (containers use `Europe/Sofia`) |
| System disk | 256 GB NVMe (KIOXIA). LVM root is 200 GB, ext4, and `/opt` lives here |
| Media disk | 1.8 TB NVMe (Seagate), ext4, mounted at `/media` by UUID. **~98% full** (Oct 2026) |
| LAN | `192.168.1.0/24`. The server is **192.168.1.113**, `eno1`, an address fixed on the router. The router (TP-Link Archer A8) hands out DNS `192.168.1.113` with `192.168.1.1` as fallback |
| Users | `chonk` (uid 1001) is the admin user with passwordless sudo. Group `media` is gid 1003 |
| Backups | **None.** Neither disk is redundant and nothing is backed up off the box |

The owner develops on an **M1 MacBook (arm64)**, so every role must work on both arm64
and x86_64.

## How the server is laid out

Everything runs in **Docker Compose stacks in `/opt/<stack>`**, one directory per stack.
Each holds a `docker-compose.yaml`, an optional `.env` (mode 0600) and the stack's data
directories. Since Oct 2026 nothing runs as a host service except Docker, ufw and sshd;
Jellyfin, Grafana, Prometheus and node_exporter used to be apt or binary installs and are
now containers.

### Access: LAN only, HTTPS everywhere

- Every web UI is `https://<subdomain>.home.tonchekliev.info`. The dashboard (Homepage) is
  the bare `https://home.tonchekliev.info`.
- **Pi-hole** is the LAN DNS. A dnsmasq wildcard resolves `home.tonchekliev.info` and
  every subdomain to `192.168.1.113`. **There are no public DNS records** for these
  names; never add any. Don't touch the apex `tonchekliev.info` either: it's a Cloudflare
  Workers site.
- **Caddy** terminates TLS with a Let's Encrypt **wildcard** certificate obtained through
  the Cloudflare DNS-01 challenge (custom build with the Cloudflare plugin). Its
  `(lan_only)` snippet aborts any request that doesn't come from a private range. Unknown
  subdomains are aborted too.
- Nothing is port-forwarded on the router.

### Docker networks

All three are external networks, created by `roles/docker`.

| Network | Subnet | Purpose |
|---|---|---|
| `proxy` | `10.40.0.0/24`, dynamic range `.128/25` | Everything Caddy fronts. **Caddy is pinned at 10.40.0.2**, which is the trusted-proxy IP for Jellyfin, GitLab and HA |
| `db` | `10.41.0.0/24`, **internal** (no route out) | Apps that use the shared PostgreSQL |
| `arr_network` | `172.22.0.0/16` | Deluge, Flaresolverr, Prowlarr, Sonarr, Radarr |

Don't use `172.32.0.0`+ for new networks: those addresses aren't private.

Host-networked containers (Jellyfin, Home Assistant, ntopng, node_exporter) are reached by
other containers as `host.docker.internal:<port>`. Every compose file that needs this has
`extra_hosts: host.docker.internal:host-gateway`.

### Firewall (ufw)

Default deny incoming, allow outgoing, deny routed. The rules, in order:
1. allow SSH;
2. allow from the Docker networks: `10.40.0.0/24`, `172.16.0.0/12`, `192.168.48.0/20`,
   `192.168.64.0/20`;
3. deny `3000,3010,8123,9090,9100/tcp` from anywhere else (host-only ports);
4. allow the LAN `192.168.1.0/24`;
5. allow IPv6 link-local.

**Ports published by Docker bypass ufw entirely.** To keep a service private, don't
publish its port (or publish it on `127.0.0.1`) and let Caddy reach it over `proxy`.

### Services

`/opt` directory = stack name. Subdomain is under `home.tonchekliev.info`. "Net" is
`host` for host networking, otherwise the Docker networks.

| Service | Stack (`/opt/…`) | Image | Net | Subdomain | Published ports | Database |
|---|---|---|---|---|---|---|
| Caddy | `caddy` | `caddy-cloudflare:latest` (built from `caddy:builder` + `caddy:latest`) | proxy (10.40.0.2) | (all) | 80, 443, 443/udp | – |
| Pi-hole | `pihole` | `pihole/pihole:latest` | proxy | `pihole` | 53 tcp/udp on 192.168.1.113 | – |
| PostgreSQL 17 + exporter | `postgres` | **`postgres:17` (pinned major)**, `prometheuscommunity/postgres-exporter` | db, default | – | 5432 on 127.0.0.1 only | is the DB |
| Homepage + socket proxy | `gethomepage` | `ghcr.io/gethomepage/homepage`, `tecnativa/docker-socket-proxy` | proxy, socket | (bare domain) | – | – |
| Homarr + socket proxy (trial) | `homarr` | `ghcr.io/homarr-labs/homarr`, `tecnativa/docker-socket-proxy` | proxy, db, socket | `homarr` | 7575 on 127.0.0.1 only | `homarr` |
| Jellyfin | `jellyfin` | `jellyfin/jellyfin:latest` | **host** (8096) | `jellyfin` | (host 8096, 7359/udp) | SQLite |
| Jellystat | `jellystat` | `cyfershepard/jellystat` | proxy, db | `jellystat` | 3005 | `jfstat` |
| Deluge | `deluge` | **`lscr.io/linuxserver/deluge:2.2.0-r1-ls364` (pinned)** | arr_network, proxy | `deluge` | 8112, 6881 tcp/udp | – |
| Flaresolverr | `flaresolverr` | `ghcr.io/flaresolverr/flaresolverr` | arr_network | – | – | – |
| Prowlarr | `prowlarr` | `lscr.io/linuxserver/prowlarr` | arr_network, proxy, db | `prowlarr` | 9696 | `prowlarr-main/-log` |
| Sonarr | `sonarr` | `lscr.io/linuxserver/sonarr` | arr_network, proxy, db | `sonarr` | 8989 | `sonarr-main/-log` |
| Radarr | `radarr` | `lscr.io/linuxserver/radarr` | arr_network, proxy, db | `radarr` | 7878 | `radarr-main/-log` |
| Audiobookshelf | `audiobookshelf` | `ghcr.io/advplyr/audiobookshelf` | proxy | `abs` | 13378 | SQLite |
| Kavita | `kavita` | `jvmilazz0/kavita` | proxy | `kavita` | 5000 | SQLite |
| deadair + Redis | `deadair` | `deadair/deadair` (**amd64 only**), `redis` | default, proxy, db | `radio` | – | `deadair` |
| Prometheus | `prometheus` | `prom/prometheus` | proxy, db | `prometheus` | – | TSDB, 15 d |
| node_exporter | `node_exporter` | `prom/node-exporter` | **host** (9100), host PID | – | (host 9100) | – |
| Grafana | `grafana` | `grafana/grafana` | proxy, db | `grafana` | – | `grafana` |
| cAdvisor | `cadvisor` | `gcr.io/cadvisor/cadvisor` | proxy | `cadvisor` | – | – |
| Uptime Kuma | `uptime-kuma` | **`louislam/uptime-kuma:2`** | proxy | `uptime` | 3001 | SQLite |
| ntopng | `ntopng` | `ntop/ntopng` (amd64) or `ntop/ntopng_arm64.dev` (arm64) | **host** (3010) | `ntopng` | – | – |
| Home Assistant | `home-assistant` | `ghcr.io/home-assistant/home-assistant:stable` | **host** (8123), privileged | `ha` | – | `homeassistant` (via 127.0.0.1:5432) |
| ESPHome | `esphome` | **`ghcr.io/esphome/esphome:2025.12.0` (pinned)** | default, proxy | `esphome` | 6052, 6053, 3232, 8266 | – |
| Ollama + Open WebUI | `ollama` | `ollama/ollama`, `ghcr.io/open-webui/open-webui:main` | default, proxy, db | `ai` | 3004 | `openwebui` |
| GitLab CE + 2 runners | `gitlab` | `gitlab/gitlab-ce`, `gitlab/gitlab-runner` | default, proxy, db | `gitlab` | – | `gitlabhq_production` |
| Dockhand | `dockhand` | `fnsys/dockhand` | proxy | `dockhand` | – | SQLite |

Notes:
- **GitLab** uses `hostname: gitlab`. **Never set a container `hostname:` to its public
  FQDN**: Docker DNS would then answer that name with the container IP for every
  container on the network, bypassing Caddy. The runners use `url = "http://gitlab"` and
  `clone_url = https://gitlab.home…`. Its SSH port is 222.
- **Homepage** never gets the raw Docker socket. It reads container status through
  `homepage-dockerproxy`, which is read-only and allows only `CONTAINERS`.
- **Homarr** is on trial as a Homepage replacement, at its own subdomain; Homepage stays on
  the bare domain. Its apps and integrations live in its database, not in files.
  `roles/homarr` registers the missing ones (`homarr_apps`, `homarr_integrations`) through
  the tRPC API its UI uses, authenticated with `homarr_api_key`. That key can only be
  created in the UI after the onboarding, so until it's in the vault that step is skipped.
  Items are matched by name and only ever created. So are its custom widgets
  (`homarr_custom_widgets`, templates in `roles/homarr/files/custom_widgets/*.jsx`, Homarr's
  restricted JSX): library counts (Jellyfin via its integration, Kavita via `x-api-key`), host
  stats and `/media` free space (Prometheus queries) and Dockhand stats; to change one,
  delete it in Manage → Custom widgets and rerun. It also lays out the `homelab` board
  (`homarr_board_sections`: containers of apps and widgets, sized so the rows have no holes),
  but only while that board doesn't exist or is empty; after that its layout is UI state. Its
  socket proxy is read-only, so the start/stop buttons on its Docker page are refused.
  The 127.0.0.1:7575 port exists only so Ansible can call the API from the host.
- **Home Assistant** keeps its reverse-proxy trust (`use_x_forwarded_for`, trusted proxy
  10.40.0.2) in its UI storage (`.storage/http`), not in YAML. On a fresh install it has to
  be set once in the UI.
- **Prometheus** scrapes `node` (host.docker.internal:9100), `cadvisor`, `caddy`
  (`caddy:2020`), `postgres` (`postgres-exporter:9187`) and itself. **Each target keeps
  the `instance` label it had when Prometheus ran on the host** (`localhost:9100`,
  `localhost:8080`, `10.40.0.2:2020`, `127.0.0.1:9187`), so history stays continuous. Keep
  those labels if you touch the targets.
- **deadair** (AI radio station) is the one exception to "works on arm64": its image is
  amd64-only, so the compose file sets `platform: linux/amd64`. In the Mac sandbox it needs
  qemu registered inside the box once (`docker run --privileged --rm tonistiigi/binfmt
  --install amd64`), otherwise it fails with `exec format error`. Its migrations run as the
  `deadair` login and grant to a NOLOGIN `app_user` role that `roles/postgres` creates
  (`nologin_roles`), so the login needs no CREATEROLE. Sessions live in the stack's own
  `deadair-redis`. The music provider (Spotify), presenter, AI model and voice are set in its
  console (app state); the two keys it generates are in `/opt/deadair/data/secrets`.
- **Caddy's `:2020` listener** is internal and not published. It serves `/metrics` and a
  read-only `/reverse_proxy/upstreams` for the Homepage widget. The admin API stays on
  localhost:2019.

### Shared PostgreSQL

- One server (`postgres:17`, pinned because a new major can't open the old data
  directory), with **one login and its own database(s) per app**. `CONNECT` is revoked
  from `PUBLIC` on every app database.
- Apps reach it as `postgres:5432` over the `db` network. Home Assistant (host network)
  uses `127.0.0.1:5432`.
- `roles/postgres` creates the logins, databases and extensions from `postgres_apps`, and
  the read-only `exporter` login (`pg_monitor`). `nologin_roles` creates roles without a
  login that an app's migrations grant to (deadair's `app_user`). GitLab needs `pg_trgm`,
  `btree_gist` and `amcheck`, created by the superuser.
- `/opt/postgres/README.md` (from `roles/postgres/files/README.md`) is the runbook for
  manual backup and restore.
- **Staying on SQLite** because there's no Postgres support: Jellyfin, Uptime Kuma,
  Kavita, Audiobookshelf, Pi-hole, Dockhand, ntopng.

### Media pipeline and file permissions

1. Prowlarr (indexers, with Flaresolverr for Cloudflare-protected sites) feeds Sonarr
   (TV/anime) and Radarr (movies).
2. They send downloads to **Deluge** at `deluge:8112`, with categories `tv-sonarr` and
   `radarr`. Deluge downloads to `/media/deluge`.
3. Sonarr and Radarr **hardlink** finished downloads into `/media/plex/Series` and
   `/media/plex/Movies`, so a file takes no extra space while it seeds.
4. **Jellyfin** reads the library and writes subtitles and `.nfo` files next to the media.
   Jellystat and Homepage talk to Jellyfin at `host.docker.internal:8096`.

These apps must keep talking to each other **and must be able to modify each other's
files**. The model, which must stay consistent:

- **Deluge, Sonarr, Radarr, Prowlarr and Jellyfin all run as uid 1001 (the server user),
  gid 1003 (`media`), umask 002.** The linuxserver images get `PUID`, `PGID=<media gid>`
  and `UMASK=002`. Jellyfin gets `user: 1001:1003` plus an entrypoint wrapper that sets
  `umask 002`.
- Media directories are **setgid `2775`**, so everything created in them inherits group
  `media`. Files are `664`.
- Sonarr and Radarr have "Set Permissions" on, but **"chown group" must stay empty**. The
  containers don't know the group by name, and setting it caused an "Unknown group:
  media" error on every import.
- All of them mount `/media` at the same path on the same filesystem, which is what keeps
  hardlinks possible.
- When changing any of these services, test real writes as each container's own user:
  download → hardlink import → Jellyfin writes a `.srt` → Sonarr or Radarr can delete it.
  An HTTP health check isn't enough.

Jellyfin specifics:
- **Host networking** keeps the LAN address, client discovery (7359/udp) and the Caddy
  upstream unchanged, with no NAT.
- The old apt paths are mounted at the **same paths inside the container**:
  `/opt/jellyfin/data` → `/var/lib/jellyfin`, `config` → `/etc/jellyfin`, `cache` →
  `/var/cache/jellyfin`, `log` → `/var/log/jellyfin`. Paths stored in its database (the
  Collections library lives at `/var/lib/jellyfin/data/collections`) therefore stay
  valid. Don't "clean this up" to `/config`.
- `/dev/dri` (the Intel UHD 630 iGPU) is passed through, with `group_add` of the host's
  video and render GIDs. Hardware transcoding is currently off in Jellyfin's settings.
- The role only manages `KnownProxies` (Caddy) in `network.xml`. Everything else is
  Jellyfin's own state.

### Monitoring

- Grafana is provisioned from files. The data sources (`prometheus` uid `belryhxaxsu0we`,
  plus a dead `influxdb`) are in `/opt/grafana/provisioning/datasources/homelab.yaml`. The
  dashboards ("Node Exporter Full", "Docker Host & Container Overview", "Caddy",
  "PostgreSQL") are in `/opt/grafana/data/dashboards/{general,homelab}`. Keep data source
  UIDs stable, because the dashboards reference them.
- **Uptime Kuma** has 27 monitors, mostly hitting the Caddy URLs. Its monitors are app
  state: add one by hand in its UI for each new service.
- ntopng watches `eno1` for "who connects to the server".

## How the repository works

```
ansible.cfg            default inventory = inventory/dev.yml (prod must be passed explicitly)
requirements.txt       ansible-core 2.21, ansible-lint, yamllint (pinned)
requirements.yml       collections: ansible.posix, community.docker, community.general, community.postgresql
setup.sh               venv with Python 3.12–3.14 (ansible-core breaks on 3.15), collections, sandbox SSH key
docker/                the sandbox: Ubuntu 24.04 + 26.04 systemd boxes running Docker inside
inventory/
  dev.yml              homeserver -> dev -> test-ubuntu-noble (127.0.0.1:2222), test-ubuntu-resolute (:2223)
  production.yml       homeserver -> prod -> bigboy (192.168.1.113, user chonk)
  group_vars/
    homeserver/main.yml      shared vars (homeserver_*), see below
    homeserver/services.yml  the service registry (homelab_services)
    dev/main.yml             sandbox overrides + dummy secrets in plain text
    prod/main.yml            prod overrides; secrets as "{{ vault_* }}"
    prod/vault.yml           Ansible Vault (AES256), password in .vault_pass (gitignored)
playbooks/
  setup.yml            imports base, core, media, monitoring, apps; every role is tagged with its name
  base.yml             common, firewall, docker
  core.yml             caddy, pihole, postgres
  media.yml            jellyfin, deluge, flaresolverr, prowlarr, sonarr, radarr, jellystat, audiobookshelf, kavita
  monitoring.yml       node_exporter, cadvisor, prometheus, grafana, uptime_kuma, ntopng
  apps.yml             homepage, homarr, home_assistant, esphome, ollama, gitlab, dockhand
  update.yml           apt dist-upgrade, then every play again with pull/build = always, then prune dangling images
roles/                 one role per service + common, firewall, docker, compose_app
```

`dev` and `prod` are **child groups of `homeserver`**, so their `group_vars` override the
shared ones. Environment differences are **variables, never `when: env == …`**. The
important ones:

| Var | prod | dev (sandbox) |
|---|---|---|
| `homeserver_user` | `chonk` | `ansible` (also uid 1001 in the image) |
| `homeserver_lan_ip` | `192.168.1.113` | the box's default IPv4 |
| `caddy_tls_mode` | `cloudflare` (DNS-01) | `internal` (Caddy's local CA) |
| `common_media_disk_uuid` | the data disk's UUID | unset, so `/media` is just a directory |
| `jellyfin_devices`, `home_assistant_devices` | `/dev/dri`, `/dev/ttyUSB0` (Zigbee) | none |
| `ntopng_interface` | `eno1` | the default interface |
| `node_exporter_rootfs_propagation` | `rslave` | `""` (nested Docker refuses rslave) |

Other shared vars in `group_vars/homeserver/main.yml`:
- `homeserver_domain`, `homeserver_timezone`, `homeserver_host_timezone`;
- `homeserver_media_group` / `_gid`;
- `homeserver_proxy_subnet`, `homeserver_caddy_ip`, `homeserver_lan_subnet`;
- `homeserver_deb_arch` (amd64/arm64, for apt repos).

`homeserver_uid` and `homeserver_gid` are **facts set by `compose_app`** (from `getent`),
so they exist in every compose template.

### The `compose_app` role: how every stack is deployed

Service roles are thin. They call `include_role: compose_app` with vars, and
`compose_app`:
1. creates `/opt/<compose_app_name>` (owned by the server user, 0755);
2. creates the `compose_app_dirs` entries: `[{path, owner?, group?, mode?}]`, **never
   recursive**, and owner/mode untouched when not given, because containers chown their
   own data;
3. writes `compose_app_env` to `.env` (0600, `no_log`). The compose file references the
   values as `${VAR}`;
4. renders `compose_app_templates` and copies `compose_app_files`
   (`[{src, dest, mode?, owner?, group?}]`, dest relative to the stack directory);
5. renders `docker-compose.yaml.j2`;
6. runs `community.docker.docker_compose_v2` (`state: present`, pull/build policy from
   `compose_app_pull` / `compose_app_build`, optional `compose_app_wait`);
7. if a config file changed but compose didn't recreate anything:
   `compose_app_on_config_change` = `restart` (default), `command` (runs
   `compose_app_reload_command`, as Caddy does with a graceful `caddy reload` and
   Prometheus with a SIGHUP) or `none`.

**Templates and files are looked up in the *calling* role** (`templates/`, `files/`),
through the include_role dependency chain. A service role is usually just:

```
roles/<service>/
  defaults/main.yml                    <service>_* variables (prefix is required by ansible-lint)
  tasks/main.yml                       include_role: compose_app with vars
  templates/docker-compose.yaml.j2     mirrors the stack's compose file
```

### The service registry: Caddy routes and the Homepage dashboard

`inventory/group_vars/homeserver/services.yml` → `homelab_services`, keyed by service id:
- `subdomain` (`""` = the bare domain) and `upstream` (`container:port` on `proxy`, or
  `host.docker.internal:port`) feed **the Caddyfile**. `caddy_matcher` and
  `caddy_directives` are optional.
- `tile` feeds **Homepage's `services.yaml`**: name, icon, description, `container` (which
  gives a status dot via `my-docker`), `widget` and an optional `href`. Widget keys come
  from `homepage_widget_keys` (the vault in prod).
- The order and grouping live in `roles/caddy/defaults` (`caddy_sections`) and
  `roles/homepage/defaults` (`homepage_groups`). A service appears only if its id is
  listed there.

### Secrets

- **Prod:** `inventory/group_vars/prod/vault.yml` holds the `vault_*` variables:
  - the Cloudflare token;
  - the Pi-hole, Postgres superuser and exporter passwords, and every app's DB password
    (`vault_postgres_app_passwords.<role>`);
  - the Homepage widget keys, the Deluge and ESPHome passwords;
  - Home Assistant `secrets.yaml` values;
  - the GitLab runner tokens and the Jellystat JWT secret;
  - the Homarr encryption key (`vault_homarr_secret_encryption_key`, never change it) and
    API key (`vault_homarr_api_key`, optional until the onboarding is done).

  `prod/main.yml` maps them to the role variables.
- Edit with `ansible-vault edit inventory/group_vars/prod/vault.yml --vault-password-file .vault_pass`.
  `.vault_pass` exists only on the server (`~/homeforge`) and on the owner's machines.
  It's gitignored.
- **Dev:** dummy values in plain text in `group_vars/dev/main.yml`. Every secret variable
  needs a dev dummy too, or sandbox runs fail.
- Tasks that handle secrets use `no_log`. Don't print vault contents; read them with
  scripts that never echo the values.

### Running it

```bash
source .venv/bin/activate

# sandbox (the default inventory)
docker compose -f docker/docker-compose.yml up -d --build
ansible-playbook playbooks/setup.yml --limit test-ubuntu-noble
ansible-playbook playbooks/setup.yml --limit test-ubuntu-noble --tags sonarr   # one service

# prod: always dry-run first, and apply only with the owner's OK
ansible-playbook -i inventory/production.yml playbooks/setup.yml --vault-password-file .vault_pass --check --diff
# from bigboy itself (no SSH to self), add:
#   -e ansible_connection=local -e ansible_python_interpreter=/usr/bin/python3
```

A converged prod run reports `changed=0`, apart from Docker's GPG key task in check mode.
Run the sandbox twice after a change to prove idempotence; the second run must report
`changed=0`.

### Sandbox

- `docker/docker-compose.yml` runs two privileged systemd boxes (Ubuntu 24.04 "noble" and
  26.04 "resolute"). Their SSH listens on **127.0.0.1** only: 2222 and 2223. The key is
  generated by `setup.sh` and gitignored.
- Docker runs inside each box, with named volumes for `/var/lib/docker` **and**
  `/var/lib/containerd`. Both are needed: Docker 29 keeps images in containerd's store.
- A box with the full stack takes about 2.6 GB of RAM and many GB of disk; GitLab adds
  about 3.5 GB. **On bigboy, test on one box at a time (`--limit`) and don't start GitLab
  or Ollama there**: the real services share that RAM. The full stack on both boxes is
  for the Mac.
- Remove the sandbox completely with `docker compose -f docker/docker-compose.yml down -v`.
  Old volumes once filled bigboy's system disk.

## Adding a new service: checklist

1. **Look up the official install docs** for the image and its settings. Don't guess
   install steps; ask the owner when unsure.
2. **`roles/<service>/`:** `defaults/main.yml`, `tasks/main.yml` (include `compose_app`)
   and `templates/docker-compose.yaml.j2`. In the compose file:
   - `container_name: <name>`, `restart: unless-stopped`, `TZ={{ homeserver_timezone }}`;
   - join `proxy` (external), plus `db` if it uses Postgres;
   - **don't publish ports** unless the LAN must reach it directly;
   - use `:latest`, and an image that exists for amd64 **and** arm64;
   - if it touches `/media`, follow the media permission model.
3. **Postgres?** Add `{role, databases, extensions?}` to `postgres_apps`, a vault password
   `vault_postgres_app_passwords.<role>` (and the dev dummy), and pass it in through
   `compose_app_env`.
4. **Web UI?** Add an entry to `homelab_services` (subdomain, upstream, tile), and its id
   to a `caddy_sections` entry and a `homepage_groups` entry.
5. **Secrets?** Add `vault_<x>` to the vault, map it in `prod/main.yml`, and add a dummy
   in `dev/main.yml`.
6. **Add the role to the right playbook**, tagged with its own name.
7. **Monitoring:** if the service exposes Prometheus metrics, add a scrape job in
   `roles/prometheus/defaults`. Tell the owner to add an Uptime Kuma monitor.
8. **README:** update the playbook description.
9. **Verify:**
   - lint and yamllint pass;
   - the sandbox run passes twice, with `changed=0` the second time;
   - the URL answers through Caddy, e.g.
     `curl -k --resolve x.home.tonchekliev.info:443:127.0.0.1 https://x.home.tonchekliev.info`
     inside the box;
   - the prod dry run shows only the intended change;
   - only then apply on prod, with the OK.

## Conventions

- **Task names:** `<file> | <Sentence>`, e.g. `main | Deploy the Sonarr stack` or
  `install | Add the repo` (ansible-lint's `name[casing]` rule is skipped).
- **Role variables are prefixed with the role name.** Shared values are `homeserver_*` in
  group_vars. A deliberately unprefixed `set_fact` needs a `# noqa` with a reason.
- **FQCNs everywhere** (`ansible.builtin.*`, `community.docker.*`, …). Octal modes are
  quoted strings (`"0644"`); yamllint forbids bare octals.
- **Comments explain *why***, briefly, in the same style as the existing roles and compose
  files.
- **Compose templates mirror the files on the server.** Keep them close to what the
  service's upstream docs show, and don't reorder keys gratuitously, since that creates
  prod diffs.
- **Commit trailers:** commits made by Claude end with a `Co-Authored-By` line.

## Gotchas (learned the hard way)

- **`community.docker.docker_network` is banned here.** It matches a network by name *or
  ID prefix*, so `db` matched the built-in `host` network on a box whose `host` ID started
  with "db", and it tried to delete it. `roles/docker` uses the `docker network` CLI and
  only asserts settings; it never recreates a network.
- **The Servarr apps (Sonarr, Radarr, Prowlarr) refuse unknown `Host` headers** once
  Allowed Hosts is set. It's set through `<APP>__SERVER__ALLOWEDHOSTS` to the Caddy name,
  the container name and the LAN IP. Anything new that calls them under another hostname
  must be added there.
- **Container names are the API between services.** `sonarr`, `radarr`, `prowlarr`,
  `deluge`, `postgres`, `caddy`, `gitlab`, `homepage` and others are used by URL in other
  apps' settings, which are app state. Don't rename containers.
- **Docker-published ports ignore ufw.**
- **Caddy mounts `conf/` as a folder** (a single-file mount goes stale when the file is
  replaced) and reloads gracefully. Prometheus mounts `config/` the same way.
- **Postgres stays on the 17 major.** Upgrading needs dump/restore (see the runbook), and
  `postgres:18` stores data at `/var/lib/postgresql`, not `…/data`.
- **The ESPHome and Deluge images are pinned on purpose.** Don't bump them casually.
- **`update.yml` never reboots.** It reports when `/var/run/reboot-required` exists.
- **The Mac needs Python 3.12–3.14** (`setup.sh` picks one) and a copy of `.vault_pass`.
- **Dry runs:** steps that need a Python library on the target (psycopg2, lxml) skip
  themselves with a message in check mode when the library isn't installed yet. So do the
  steps that need something a dry run doesn't really create: `docker compose` for a new
  stack, and the privileges and extensions of a new database.
- **GitLab's container writes some `/opt/gitlab` files as uid 996.** On the host that
  number has no name (it used to be the `prometheus` user). That's harmless.

## What the repo does NOT manage (app state)

These live only on the server and are **not backed up**:
- the Postgres data (all app databases);
- Jellyfin's library, users, plugins and settings (`/opt/jellyfin/{data,config}`);
- Home Assistant's `.storage`, `automations.yaml`, HACS, `zigbee.db`;
- GitLab repositories, uploads and `config/gitlab-secrets.json`;
- the data of Kavita, Audiobookshelf, Uptime Kuma (including its monitors), Pi-hole,
  Deluge (torrent state), ESPHome device configs, Dockhand, Ollama's models, and deadair
  (`/opt/deadair/data`: settings, presenters, provider credentials and the keys encrypting them);
- app settings made in UIs: Sonarr/Radarr/Prowlarr indexers, download clients and quality
  profiles; Jellyfin plugins such as Trakt; Jellystat's Jellyfin URL.

After a fresh rebuild without that state:
- set Home Assistant's trusted proxy in its UI;
- put the new apps' API keys into `vault_homepage_widget_keys`;
- re-register the GitLab runners and update `vault_gitlab_runner_tokens`;
- finish Homarr's onboarding, create an API key and update `vault_homarr_api_key`.

## Known issues the owner has chosen to leave

- **Jellyfin's Trakt plugin:** the nightly "Export library to trakt.tv" (collection sync)
  fails with HTTP 420. About 1,100 library items don't fit a free account's collection
  limit. Watch history still syncs. Leave it unless asked.
- **The 1337x indexer** in Prowlarr fails. Leave it unless asked.
