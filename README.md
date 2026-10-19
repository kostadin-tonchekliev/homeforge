# homeforge

Ansible project to build, track, and rebuild my home server and the services running on it.

A local Docker sandbox (`docker/`) runs disposable Ubuntu 24.04 and Ubuntu 26.04 containers reachable over SSH, so playbooks can be developed and tested without touching the real mini PC. Both the sandbox and the real mini PC belong to the same inventory group (`homeserver`), so every playbook is written once and runs against either — only the inventory file passed on the command line changes.

## Project structure

```
.
├── .ansible-lint                  # ansible-lint rule configuration
├── .yamllint                      # yamllint configuration
├── ansible.cfg                    # points ansible-playbook at the test inventory by default
├── requirements.txt               # pinned ansible-core / lint versions (installed into .venv)
├── requirements.yml               # pinned Ansible collections (installed by setup.sh)
├── setup.sh                       # one-time local setup (venv, requirements, SSH keys) — see below
├── docker/                        # local test sandbox — never used against the real mini PC
│   ├── Dockerfile-24.04           # Ubuntu 24.04 + systemd + sshd, built for Ansible testing
│   ├── Dockerfile-26.04           # Ubuntu 26.04 + systemd + sshd, built for Ansible testing
│   ├── docker-compose.yml         # runs the images above, 127.0.0.1:2222 -> 22 and 127.0.0.1:2223 -> 22
│   └── ssh_keys/                  # keypair generated locally, gitignored
├── inventory/
│   ├── dev.yml                    # homeserver -> dev group -> the Docker sandbox
│   ├── production.yml             # homeserver -> prod group -> the real mini PC
│   ├── group_vars/
│   │   ├── homeserver/            # vars shared by both environments (e.g. ansible_become)
│   │   ├── dev/                   # sandbox overrides + dummy secrets (plain text)
│   │   └── prod/                  # mini PC overrides + vault.yml (encrypted secrets)
│   └── host_vars/
│       └── bigboy.yml             # machine-specific overrides (e.g. SSH key path), gitignored
├── playbooks/                     # locations for the different playbooks
└── roles/                         # the actual task implementations, called by playbooks
```

`dev` and `prod` are child groups of `homeserver`, so anything set in `group_vars/dev/`
or `group_vars/prod/` overrides the shared value in `group_vars/homeserver/`. Roles are
written once; the differences between the sandbox and the real box (LAN IP, TLS mode,
disks, devices…) are variables, never `when: env == ...` branches.

## Prerequisites

- Python 3
- Docker + the Docker Compose plugin
- SSH client (`ssh-keygen`)

## One-time setup

```bash
./setup.sh
```

- creates `.venv` and installs `requirements.txt` into it
- installs the Ansible collections from `requirements.yml`
- generates the sandbox SSH keypair (`docker/ssh_keys/ansible_test`)
- prompts for the path to your real SSH private key for the mini PC and writes it to `inventory/host_vars/bigboy.yml` (gitignored)

It's safe
to re-run at any time: existing steps are skipped or updated in place rather than
duplicated.

The script only sets up the venv for its own subshell — activate it in your shell
afterward to use it interactively:

```bash
source .venv/bin/activate
```

## Quick start: test against the Docker sandbox

```bash
# build & start the sandbox
docker compose -f docker/docker-compose.yml up -d --build

# run a playbook against it (uses inventory/dev.yml by default, per ansible.cfg)
ansible-playbook playbooks/setup.yml

# only one of the boxes
ansible-playbook playbooks/setup.yml --limit test-ubuntu-noble
```

The sandbox boxes run Docker inside themselves (each keeps its `/var/lib/docker` in a
named volume), so the whole stack can be brought up in them. Their SSH ports only listen
on `127.0.0.1`.

Tear the sandbox down when you're done:

```bash
docker compose -f docker/docker-compose.yml down

# also throw away the Docker data inside the boxes
docker compose -f docker/docker-compose.yml down -v
```

Rebuilding from scratch is just `down -v` followed by `up -d --build` again — that's the
point of the sandbox: it should always be safe to throw away and recreate.

## Running against the real mini PC

The production secrets live in `inventory/group_vars/prod/vault.yml`, encrypted with
Ansible Vault. Put the vault password in `.vault_pass` (gitignored, `chmod 600`) and
pass it on every production run:

```bash
# always look at what would change first
ansible-playbook -i inventory/production.yml playbooks/setup.yml --vault-password-file .vault_pass --check --diff

# then apply
ansible-playbook -i inventory/production.yml playbooks/setup.yml --vault-password-file .vault_pass
```

Production is never used by accident — `ansible.cfg` defaults to the test inventory,
so you must pass `-i inventory/production.yml` explicitly to target the real box.

Edit the secrets with:

```bash
ansible-vault edit inventory/group_vars/prod/vault.yml --vault-password-file .vault_pass
```

## Adding a Docker Compose service

Every stack lives in `/opt/<name>` and is deployed by the shared `compose_app` role. A
service role is usually just a `templates/docker-compose.yaml.j2` plus a `tasks/main.yml`:

```yaml
- name: main | Deploy the Kavita stack
  ansible.builtin.include_role:
    name: compose_app
  vars:
    compose_app_name: kavita
    compose_app_dirs:           # created if missing, never chowned recursively
      - path: config
    compose_app_env:            # written to /opt/kavita/.env (0600), for ${VAR} in the compose file
      SOME_SECRET: "{{ kavita_some_secret }}"
    compose_app_templates:      # extra config files from this role's templates/
      - src: app.conf.j2
        dest: config/app.conf
```

`compose_app` looks the compose template and config files up in the calling role. When a
config file changes but compose doesn't recreate the containers, it restarts the stack
(or runs `compose_app_reload_command`, like Caddy's graceful reload). If the service is
reachable over HTTPS, add it to `homelab_services` and to a section in `caddy_sections`.

## Branch naming conventions

Branch names follow this pattern: `<type>/<short-description>`, using kebab-case for the description.

| Type | Use case | Example |
|---|---|---|
| `feature/` | New features or functionality | `feature/docker-sandbox-setup` |
| `bugfix/` | Bug fixes in non-production code | `bugfix/fix-ansible-lint-errors` |
| `chore/` | Maintenance, dependencies, configuration | `chore/update-requirements` |
| `refactor/` | Code refactoring without feature changes | `refactor/simplify-role-structure` |
| `docs/` | Documentation-only changes | `docs/add-deployment-guide` |
| `test/` | Testing changes | `test/rename-role` |

Always branch from `main` and open a pull request before merging. The branch name should be descriptive enough to understand the change at a glance.

## CI / Linting

Three lint jobs run automatically on every merge/pull request:

| Job | Tool | What it checks |
|---|---|---|
| `ansible-lint` | ansible-lint | Ansible best practices and task correctness |
| `yamllint` | yamllint | YAML syntax and formatting |
| `syntax-check` | ansible-playbook --syntax-check | Parses every playbook for structural errors |

GitHub Actions runs these automatically on every pull request (`.github/workflows/lint.yml`).

To run the checks locally (tools are included in `requirements.txt` and installed by `setup.sh`):

```bash
source .venv/bin/activate
ansible-lint
yamllint -c .yamllint .
ansible-playbook --syntax-check playbooks/*.yml -i inventory/dev.yml
```

## Playbooks

- [setup.yml](playbooks/setup.yml) - Set up everything (imports the playbooks below). Every role is tagged with its own name, e.g. `--tags firewall`
- [core.yml](playbooks/core.yml) - Core services: Caddy (reverse proxy + TLS, routes generated from `inventory/group_vars/homeserver/services.yml`), Pi-hole (LAN DNS + the `*.home` wildcard), PostgreSQL (shared server, one login + database per app)
- [media.yml](playbooks/media.yml) - Media: Jellyfin (official APT repo), Deluge, Flaresolverr, Prowlarr, Sonarr, Radarr, Jellystat, Audiobookshelf, Kavita
- [monitoring.yml](playbooks/monitoring.yml) - Monitoring: Prometheus + node_exporter (`prometheus.prometheus` collection, settings in `inventory/group_vars/homeserver/monitoring.yml`), Grafana (official APT repo, provisioned data sources and dashboards), cAdvisor, Uptime Kuma, ntopng
- [base.yml](playbooks/base.yml) - Base host: packages, timezone, users and the `media` group, `/media` (data disk mount in prod), ufw, Docker with its daemon config and shared networks
